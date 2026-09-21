#!/usr/bin/env python3
"""Tests for mail-reader.py. Touches no mail: IMAP is a fake, AppleScript is stubbed.

    python3 tools/test_mail_reader.py

The AppleScript the tool generates is checked with `osacompile`, which compiles
without running, so a script that would not parse fails here rather than in front
of a real mailbox. Skipped on machines without it.
"""
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("mr", os.path.join(HERE, "mail-reader.py"))
mr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mr)

RAW = (b"From: Sample Sender\r\nSubject: hello\r\n"
       b"Date: Mon, 21 Sep 2026 10:00:00 +0000\r\n\r\nbody\r\n")


# The fake never checks it. No address-shaped string appears in this file, on purpose:
# the publication gate blocks those, and the tests do not need one.
ACCOUNT = "account-under-test"


class FakeIMAP:
    """Just enough of imaplib.IMAP4_SSL. `uids` are what SEARCH returns."""
    def __init__(self, uids=(b"5", b"9", b"12"), select_ok=True, have=True):
        self.uids, self.select_ok, self.have = list(uids), select_ok, have
        self.readonly = None
        self.search = None
        self.fetches = []

    def login(self, *a): pass
    def close(self): pass
    def logout(self): pass

    def select(self, mailbox, readonly=False):
        self.readonly = readonly
        return ("OK", [b"42"]) if self.select_ok else ("NO", [b"no such mailbox"])

    def uid(self, cmd, *args):
        if cmd == "search":
            self.search = args
            return "OK", [b" ".join(self.uids)]
        self.fetches.append(args)
        return ("OK", [(b"1 (BODY[HEADER]", RAW)]) if self.have else ("OK", [None])


def run_main(argv, **patches):
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with redirect_stdout(out), redirect_stderr(err):
        try:
            mr.main(argv)
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class Arguments(unittest.TestCase):
    def test_both_option_forms_reach_the_function(self):
        for argv in (["list", "--limit", "30"], ["list", "--limit=30"]):
            with mock.patch.object(mr, "list_messages", return_value=[]) as lm:
                run_main(argv)
            self.assertEqual(lm.call_args.kwargs["limit"], 30, argv)

    def test_default_is_unchanged(self):
        with mock.patch.object(mr, "list_messages", return_value=[]) as lm:
            run_main(["list"])
        kw = lm.call_args.kwargs
        self.assertEqual((kw["limit"], kw["mail_account"], kw["mailbox"]), (10, "1", "INBOX"))

    def test_unknown_option_is_an_error_not_ignored(self):
        with mock.patch.object(mr, "list_messages", return_value=[]) as lm:
            code, _, err = run_main(["list", "--limt", "30"])
        self.assertEqual(code, 2)
        self.assertIn("unrecognized", err)
        lm.assert_not_called()

    def test_archive_and_find_need_an_account(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KONTOR_MAIL_ACCOUNT", None)
            for argv in (["archive", "1", "x.eml"], ["find", "--from", "x"]):
                code, _, err = run_main(argv)
                self.assertEqual(code, 1, argv)
                self.assertIn("account email required", err)


class AppleScriptIsValid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("osacompile"):
            raise unittest.SkipTest("osacompile not available (not macOS)")

    def compiles(self, script):
        r = subprocess.run(["osacompile", "-e", script, "-o", os.path.join(tempfile.mkdtemp(), "t.scpt")],
                           capture_output=True, text=True)
        return r.returncode == 0, r.stderr.strip()

    def captured(self, fn, *a, **k):
        seen = []
        with mock.patch.object(mr, "run_applescript", side_effect=lambda s: seen.append(s) or ""), \
                redirect_stderr(io.StringIO()):
            fn(*a, **k)
        return seen[0]

    def test_every_generated_script_compiles(self):
        cases = {
            "list default": lambda: self.captured(mr.list_messages),
            "list other account and folder": lambda: self.captured(
                mr.list_messages, 5, mail_account='Work "Main"', mailbox='Sent "Items"'),
            "read": lambda: self.captured(mr.read_message, "123", mail_account="2", mailbox="Archive"),
            "search subject": lambda: self.captured(mr.search_messages, "invoice"),
            "search sender": lambda: self.captured(mr.search_messages, "someone", field="sender"),
            "search either": lambda: self.captured(mr.search_messages, "someone", field="either"),
            "search with a quote and a backslash": lambda: self.captured(
                mr.search_messages, 'a "quoted" \\ word', field="either"),
        }
        for name, make in cases.items():
            ok, err = self.compiles(make())
            self.assertTrue(ok, f"{name}: {err}")

    def test_the_old_escaping_order_really_was_broken(self):
        """Guards the fix: quote first, then backslash, leaves the quote unescaped."""
        q = 'a "quoted" word'
        old = q.replace('"', '\\"').replace("\\", "\\\\")
        ok, _ = self.compiles(f'tell application "Mail" to return "{old}"')
        self.assertFalse(ok)
        ok, err = self.compiles(f'tell application "Mail" to return "{mr.as_string(q)}"')
        self.assertTrue(ok, err)

    def test_default_targets_account_1_inbox_as_before(self):
        s = self.captured(mr.list_messages)
        self.assertIn("account 1", s)
        self.assertIn('name of aBox is "INBOX"', s)


class Find(unittest.TestCase):
    def find(self, fake=None, **kw):
        fake = fake or FakeIMAP()
        with mock.patch.object(mr, "get_imap_password", return_value="pw"), \
                mock.patch.object(mr.imaplib, "IMAP4_SSL", return_value=fake), \
                redirect_stderr(io.StringIO()) as err:
            out = mr.find_messages(ACCOUNT, **kw)
        return out, fake, err.getvalue()

    def test_returns_real_uids_newest_first_with_their_id_space(self):
        out, fake, _ = self.find(sender="sender")
        self.assertEqual([m["uid"] for m in out], ["12", "9", "5"])
        self.assertTrue(all(m["id_space"] == "imap" for m in out))
        self.assertEqual(out[0]["subject"], "hello")

    def test_limit_keeps_the_newest(self):
        out, _, _ = self.find(sender="x", limit=2)
        self.assertEqual([m["uid"] for m in out], ["12", "9"])

    def test_read_only_and_peek_so_nothing_is_marked_read(self):
        _, fake, _ = self.find(sender="x")
        self.assertTrue(fake.readonly)
        self.assertTrue(all("BODY.PEEK" in f[1] for f in fake.fetches))

    def test_search_criteria(self):
        _, fake, _ = self.find(sender='a"b', subject="inv", since="2026-09-03")
        self.assertEqual(list(fake.search[1:]),
                         ["FROM", '"a\\"b"', "SUBJECT", '"inv"', "SINCE", "3-Sep-2026"])

    def test_no_criteria_means_all(self):
        _, fake, _ = self.find()
        self.assertEqual(list(fake.search[1:]), ["ALL"])

    def test_rejects_what_it_cannot_search_for(self):
        out, fake, err = self.find(sender="Grüße")
        self.assertIsNone(out); self.assertIn("ASCII", err); self.assertIsNone(fake.search)
        out, fake, err = self.find(since="21.09.2026")
        self.assertIsNone(out); self.assertIn("2026-09-21", err)

    def test_mailbox_that_will_not_open_is_reported(self):
        out, _, err = self.find(FakeIMAP(select_ok=False))
        self.assertIsNone(out); self.assertIn("could not open mailbox", err)

    def test_an_id_from_find_is_what_archive_accepts(self):
        out, fake, _ = self.find(sender="x")
        dest = os.path.join(tempfile.mkdtemp(), "m.eml")
        with mock.patch.object(mr, "get_imap_password", return_value="pw"), \
                mock.patch.object(mr.imaplib, "IMAP4_SSL", return_value=FakeIMAP()), \
                redirect_stderr(io.StringIO()):
            self.assertTrue(mr.archive_message(out[0]["uid"], dest, ACCOUNT))
        self.assertTrue(os.path.exists(dest))


class Labels(unittest.TestCase):
    def test_a_number_says_which_kind_it_is(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            mr.print_messages([{"uid": "1", "id_space": "mail-app"}, {"uid": "2", "id_space": "imap"}])
        self.assertIn("Mail.app id 1", buf.getvalue())
        self.assertIn("IMAP UID 2", buf.getvalue())


class ArchiveKeepsWorking(unittest.TestCase):
    def archive(self, fake):
        dest = os.path.join(tempfile.mkdtemp(), "m.eml")
        with mock.patch.object(mr, "get_imap_password", return_value="pw"), \
                mock.patch.object(mr.imaplib, "IMAP4_SSL", return_value=fake), \
                redirect_stderr(io.StringIO()) as err:
            return mr.archive_message("1", dest, ACCOUNT), dest, err.getvalue()

    def test_absent_uid_explains_the_id_space(self):
        ok, dest, err = self.archive(FakeIMAP(have=False))
        self.assertFalse(ok); self.assertFalse(os.path.exists(dest))
        self.assertIn("not IMAP UIDs", err)

    def test_suggested_name_has_a_real_date(self):
        ok, _, err = self.archive(FakeIMAP())
        self.assertTrue(ok); self.assertIn("mail_2026-09-21_hello.eml", err)


if __name__ == "__main__":
    unittest.main(verbosity=1)
