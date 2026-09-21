#!/usr/bin/env python3
"""Tests for letter_pdf.py. Standard library only, nothing written outside a temp dir.

    python3 tools/test_letter_pdf.py
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "letter_pdf.py")
CONF = os.path.join(HERE, "letter.conf.example")
LETTER = os.path.join(HERE, "letter.example.txt")


def run(config, out, source=LETTER):
    env = {k: v for k, v in os.environ.items() if k != "KONTOR_LETTER_CONFIG"}
    if config is not None:
        env["KONTOR_LETTER_CONFIG"] = config
    return subprocess.run([sys.executable, SCRIPT, source, out], capture_output=True, text=True, env=env)


class LetterPdf(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.out = os.path.join(self.dir, "out.pdf")

    def test_renders_a_valid_one_page_pdf_with_the_sender_from_config(self):
        r = run(CONF, self.out)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = open(self.out, "rb").read()
        self.assertTrue(data.startswith(b"%PDF-"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", data)), 1)
        self.assertIn(b"Example Sender", data)
        self.assertEqual(set(re.findall(rb"/BaseFont\s*/(\w+)", data)), {b"Helvetica"})

    def test_same_input_gives_the_same_bytes(self):
        other = os.path.join(self.dir, "again.pdf")
        run(CONF, self.out); run(CONF, other)
        self.assertEqual(open(self.out, "rb").read(), open(other, "rb").read())

    def _refuses(self, config):
        r = run(config, self.out)
        self.assertEqual(r.returncode, 1)
        self.assertIn("error", r.stderr.lower())
        self.assertFalse(os.path.exists(self.out), "must not write a letter with a guessed sender")

    def test_no_default_sender_when_unset(self):
        self._refuses(None)

    def test_missing_config_file(self):
        self._refuses(os.path.join(self.dir, "does-not-exist"))

    def test_incomplete_config(self):
        bad = os.path.join(self.dir, "bad.conf")
        open(bad, "w").write("phone: 1\n")
        self._refuses(bad)


if __name__ == "__main__":
    unittest.main(verbosity=1)
