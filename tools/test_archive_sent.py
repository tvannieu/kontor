#!/usr/bin/env python3
"""Tests for archive-sent.sh. Everything happens in temporary directories.

    python3 tools/test_archive_sent.py

The script deletes the draft folder at the end, so each test is about one way
that deletion could lose something that was never copied.
"""
import datetime
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "archive-sent.sh")
STAMP = datetime.date.today().isoformat()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class ArchiveSent(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.draft = os.path.join(self.root, "desk", "someone")
        self.archive = os.path.join(self.root, "branch", "sent")

    def run_script(self):
        return subprocess.run(["bash", SCRIPT, self.draft, self.archive],
                              capture_output=True, text=True)

    def test_archives_with_prefix_and_removes_the_folder(self):
        write(os.path.join(self.draft, "letter.txt"), "hello")
        write(os.path.join(self.draft, "scan.pdf"), "pdf")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(read(os.path.join(self.archive, f"{STAMP}_SENT_letter.txt")), "hello")
        self.assertTrue(os.path.exists(os.path.join(self.archive, f"{STAMP}_SENT_scan.pdf")))
        self.assertFalse(os.path.exists(self.draft))

    def test_the_register_is_not_archived(self):
        write(os.path.join(self.draft, "letter.txt"), "hello")
        write(os.path.join(self.draft, "00_README.txt"), "register")
        self.run_script()
        self.assertFalse(any("00_README" in n for n in os.listdir(self.archive)))

    def test_refuses_a_folder_with_a_subfolder_and_changes_nothing(self):
        write(os.path.join(self.draft, "letter.txt"), "hello")
        write(os.path.join(self.draft, "attachments", "scan.pdf"), "pdf")
        r = self.run_script()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("subfolder", r.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.draft, "attachments", "scan.pdf")))
        self.assertFalse(os.path.exists(self.archive), "nothing should be copied before refusing")

    def test_an_identical_archived_copy_is_skipped_and_the_folder_goes(self):
        write(os.path.join(self.draft, "letter.txt"), "hello")
        write(os.path.join(self.archive, f"{STAMP}_SENT_letter.txt"), "hello")
        r = self.run_script()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("identical", r.stderr)
        self.assertFalse(os.path.exists(self.draft))

    def test_a_differing_archived_copy_keeps_the_folder_and_both_texts(self):
        write(os.path.join(self.draft, "letter.txt"), "newer text")
        write(os.path.join(self.archive, f"{STAMP}_SENT_letter.txt"), "older text")
        r = self.run_script()
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(read(os.path.join(self.draft, "letter.txt")), "newer text")
        self.assertEqual(read(os.path.join(self.archive, f"{STAMP}_SENT_letter.txt")), "older text")


if __name__ == "__main__":
    unittest.main(verbosity=1)
