#!/usr/bin/env python3
"""Tests for the retry-with-backoff helper in run.py. No network, no sleeping:
time.sleep is mocked, so this runs in well under a second.

    python3 evals/test_run.py
"""
import importlib.util
import io
import os
import time
import unittest
import urllib.error
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("run", os.path.join(HERE, "run.py"))
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


def http_error(code, headers=None):
    return urllib.error.HTTPError("http://x", code, "err", headers or {}, io.BytesIO(b"{}"))


class RetryHelper(unittest.TestCase):
    def setUp(self):
        self.sleep_patch = mock.patch.object(run.time, "sleep")
        self.sleep = self.sleep_patch.start()
        self.addCleanup(self.sleep_patch.stop)

    def test_succeeds_without_retrying_when_nothing_is_wrong(self):
        with mock.patch.object(run.urllib.request, "urlopen", return_value="ok") as u:
            self.assertEqual(run._urlopen_with_retry("req", 10), "ok")
        u.assert_called_once()
        self.sleep.assert_not_called()

    def test_retries_on_429_then_succeeds(self):
        with mock.patch.object(run.urllib.request, "urlopen",
                               side_effect=[http_error(429), "ok"]) as u:
            self.assertEqual(run._urlopen_with_retry("req", 10), "ok")
        self.assertEqual(u.call_count, 2)
        self.sleep.assert_called_once()

    def test_retries_on_503_too(self):
        with mock.patch.object(run.urllib.request, "urlopen",
                               side_effect=[http_error(503), "ok"]):
            self.assertEqual(run._urlopen_with_retry("req", 10), "ok")

    def test_honours_retry_after_when_the_server_sends_one(self):
        with mock.patch.object(run.urllib.request, "urlopen",
                               side_effect=[http_error(429, {"Retry-After": "17"}), "ok"]):
            run._urlopen_with_retry("req", 10)
        self.sleep.assert_called_once_with(17)

    def test_falls_back_to_backoff_without_a_retry_after_header(self):
        with mock.patch.object(run.urllib.request, "urlopen",
                               side_effect=[http_error(429), "ok"]):
            run._urlopen_with_retry("req", 10)
        self.assertEqual(self.sleep.call_args.args[0], 5)

    def test_gives_up_after_max_retries_and_raises(self):
        with mock.patch.object(run.urllib.request, "urlopen",
                               side_effect=[http_error(429)] * 5):
            with self.assertRaises(urllib.error.HTTPError):
                run._urlopen_with_retry("req", 10, max_retries=3)
        self.assertEqual(self.sleep.call_count, 3)

    def test_a_non_retryable_error_is_not_retried_at_all(self):
        with mock.patch.object(run.urllib.request, "urlopen",
                               side_effect=http_error(400)) as u:
            with self.assertRaises(urllib.error.HTTPError):
                run._urlopen_with_retry("req", 10)
        u.assert_called_once()
        self.sleep.assert_not_called()

    def test_local_calls_never_go_through_the_retry_path(self):
        """ask() with an ollama/ model must use urlopen directly, not the retrying one."""
        with mock.patch.object(run, "_urlopen_with_retry") as retrying, \
                mock.patch.object(run.urllib.request, "urlopen") as plain:
            plain.return_value.__enter__.return_value = mock.Mock(
                read=lambda: b'{"choices":[{"message":{"content":"hi"},"finish_reason":"stop"}]}')
            run.ask("ollama/kontor-4b", "hello", key=None)
        retrying.assert_not_called()
        plain.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=1)
