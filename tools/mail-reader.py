#!/usr/bin/env python3
"""
mail-reader — read emails from macOS Mail.app and archive them as .eml.

Subcommands:
  list       List recent messages from the default Mail.app account.
  read       Read a message by UID (headers + plain-text body).
  search     Search subjects for a query term.
  archive    Save a message as a raw .eml file (RFC822, full headers).

All subcommands except 'archive' use AppleScript over Mail.app —
no password required. 'archive' reads the IMAP password from macOS
Keychain (account=<email>, service=imap.gmx.net) and fetches the
raw RFC822 source via Python imaplib.

Requirements:
  - macOS
  - Mail.app with at least one configured IMAP account
  - For 'archive': the IMAP password stored in macOS Keychain under
    account=<email>, service=imap.gmx.net (or pass --imap-service)

Tested with: GMX.net IMAP over Mail.app on macOS 26.6.

Usage:
  mail-reader list [--limit N] [--json]
  mail-reader read <uid> [--json]
  mail-reader search <query> [--json]
  mail-reader archive <uid> <output.eml> [--imap-service NAME] [--imap-host HOST]
                       [--account EMAIL] [--mailbox NAME] [--attachments-dir DIR]

'list', 'read' and 'search' only ever see Mail.app's own IMAP mailbox
(INBOX) as scripted by AppleScript. 'archive' talks IMAP directly and
its UIDs live in a different number space from Mail.app's AppleScript
message ids — an id from 'list' is not an IMAP UID for 'archive'.
"""

import sys
import os
import subprocess
import json
import re
import imaplib
import email as eml_lib
from email.header import decode_header, make_header

IMAP_HOST = "imap.gmx.net"
IMAP_PORT = 993
SEP = "|||"
BODY_START = "\n|||\n"


def get_imap_password(account_email, service="imap.gmx.net"):
    try:
        pw = subprocess.check_output(
            ["security", "find-generic-password",
             "-a", account_email, "-s", service, "-w"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return pw
    except subprocess.CalledProcessError:
        return None


def run_applescript(script):
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"AppleScript error: {result.stderr.strip()}", file=sys.stderr)
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print("AppleScript timed out", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("osascript not found — macOS required", file=sys.stderr)
        return None


def list_messages(limit=10):
    script = f'''
    tell application "Mail"
        set acct to account 1
        set theBoxes to every mailbox of acct
        set targetBox to missing value
        repeat with aBox in theBoxes
            if name of aBox is "INBOX" then
                set targetBox to aBox
                exit repeat
            end if
        end repeat
        if targetBox is missing value then return "NO_INBOX"
        set allMsgs to every message of targetBox
        set sliceEnd to count of allMsgs
        if sliceEnd > {limit} then set sliceEnd to {limit}
        set resultText to ""
        repeat with i from 1 to sliceEnd
            set m to item i of allMsgs
            set mSubj to subject of m
            set mSnd to sender of m
            set mDte to date sent of m
            set mRead to read status of m
            set mId to id of m
            set thisLine to mSubj & "{SEP}" & mSnd & "{SEP}" & mDte & "{SEP}" & mRead & "{SEP}" & mId
            if i > 1 then set resultText to resultText & "\\n"
            set resultText to resultText & thisLine
        end repeat
        return resultText
    end tell
    '''
    result = run_applescript(script)
    if result is None or result == "NO_INBOX":
        print("Could not reach INBOX in Mail.app", file=sys.stderr)
        return []
    messages = []
    for raw_line in result.split("\n"):
        if not raw_line:
            continue
        parts = raw_line.split(SEP, 4)
        if len(parts) >= 5:
            messages.append({
                "subject": parts[0],
                "from": parts[1],
                "date": parts[2],
                "read": parts[3].lower() == "true",
                "uid": parts[4],
            })
    return messages


def read_message(uid):
    script = f'''
    tell application "Mail"
        set acct to account 1
        set theBoxes to every mailbox of acct
        set targetBox to missing value
        repeat with aBox in theBoxes
            if name of aBox is "INBOX" then
                set targetBox to aBox
                exit repeat
            end if
        end repeat
        if targetBox is missing value then
            set headerText to ""
            set bodyText to ""
        else
            set matches to (messages of targetBox whose id is "{uid}")
            if (count of matches) is 0 then
                set foundMsg to missing value
            else
                set foundMsg to item 1 of matches
            end if
            if foundMsg is missing value then
                set headerText to ""
                set bodyText to ""
            else
                -- Mail's dictionary has no "in reply to" or "references"
                -- property, and bare "recipients" is not a valid class
                -- either (only "to recipients" / "cc recipients" are) —
                -- all three break AppleScript compilation.
                set mSubj to subject of foundMsg
                set mSnd to sender of foundMsg
                set mDte to date sent of foundMsg
                set mRec to ""
                repeat with r in (to recipients of foundMsg)
                    if mRec is not "" then set mRec to mRec & ", "
                    set mRec to mRec & (address of r)
                end repeat
                set mCc to ""
                repeat with r in (cc recipients of foundMsg)
                    if mCc is not "" then set mCc to mCc & ", "
                    set mCc to mCc & (address of r)
                end repeat
                set mMId to message id of foundMsg
                set headerText to mSubj & "{SEP}" & mSnd & "{SEP}" & mDte & "{SEP}" & mRec & "{SEP}" & mCc & "{SEP}" & mMId
                set bodyText to ""
                try
                    set bodyText to content of foundMsg
                end try
            end if
        end if
        set outStr to headerText & "{BODY_START}" & bodyText
        return outStr
    end tell
    '''
    result = run_applescript(script)
    if result is None:
        print(f"Could not read message {uid}", file=sys.stderr)
        return None
    if result in ("NO_INBOX", ""):
        print(f"Could not read message {uid}", file=sys.stderr)
        return None
    split_idx = result.find(BODY_START)
    if split_idx < 0:
        print("Malformed AppleScript output (no body marker)", file=sys.stderr)
        return None
    header_line = result[:split_idx]
    body_text = result[split_idx + len(BODY_START):]
    header_parts = header_line.split(SEP, 5)
    if len(header_parts) < 6:
        print(f"Malformed header from AppleScript ({len(header_parts)} parts)", file=sys.stderr)
        return None
    return {
        "subject": header_parts[0],
        "from": header_parts[1],
        "date": header_parts[2],
        "to": header_parts[3],
        "cc": header_parts[4],
        "message_id": header_parts[5],
        "body": body_text,
    }


def search_messages(query):
    safe_query = query.replace('"', '\\"').replace("\\", "\\\\")
    script = f'''
    tell application "Mail"
        set acct to account 1
        set theBoxes to every mailbox of acct
        set targetBox to missing value
        repeat with aBox in theBoxes
            if name of aBox is "INBOX" then
                set targetBox to aBox
                exit repeat
            end if
        end repeat
        if targetBox is missing value then return "NO_INBOX"
        set matches to (messages of targetBox whose subject contains "{safe_query}")
        set resultText to ""
        repeat with m in matches
            set mSubj to subject of m
            set mSnd to sender of m
            set mDte to date sent of m
            set mId to id of m
            set thisLine to mSubj & "{SEP}" & mSnd & "{SEP}" & mDte & "{SEP}" & mId
            if resultText is not "" then
                set resultText to resultText & "\\n" & thisLine
            else
                set resultText to thisLine
            end if
        end repeat
        return resultText
    end tell
    '''
    result = run_applescript(script)
    if result is None or result == "NO_INBOX":
        print("Could not search Mail.app", file=sys.stderr)
        return []
    matches = []
    for raw_line in result.split("\n"):
        if not raw_line:
            continue
        parts = raw_line.split(SEP, 3)
        if len(parts) >= 4:
            matches.append({
                "subject": parts[0],
                "from": parts[1],
                "date": parts[2],
                "uid": parts[3],
            })
    return matches


def safe_filename(name, fallback):
    name = decode_mime(name) if name else ""
    name = os.path.basename(name.replace("\\", "/"))
    name = re.sub(r'[^\w\-.]', '_', name).strip("._") or fallback
    return name[:200]


def extract_attachments(msg, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    written = []
    seen = set()
    for i, part in enumerate(msg.walk()):
        if part.get_content_maintype() == "multipart":
            continue
        filename = part.get_filename()
        if not filename:
            continue
        name = safe_filename(filename, f"attachment_{i}")
        while name in seen:
            name = f"_{name}"
        seen.add(name)
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        path = os.path.join(out_dir, name)
        with open(path, "wb") as f:
            f.write(payload)
        written.append(path)
    return written


def archive_message(uid, output_path, account_email, imap_service="imap.gmx.net", imap_host=None, mailbox="INBOX", attachments_dir=None):
    if imap_host is None:
        imap_host = IMAP_HOST
    pw = get_imap_password(account_email, imap_service)
    if pw is None:
        print(f"Error: IMAP password not in keychain for {account_email} / {imap_service}", file=sys.stderr)
        print("Add: security add-generic-password -a <email> -s <service> -w <password>", file=sys.stderr)
        return False
    try:
        M = imaplib.IMAP4_SSL(imap_host, IMAP_PORT)
        M.login(account_email, pw)
        M.select(mailbox)
        typ, data = M.uid('fetch', uid, "(RFC822)")
        if not (data and data[0] and data[0][1]):
            print(f"Error: no data for UID {uid}", file=sys.stderr)
            M.close()
            M.logout()
            return False
        raw = data[0][1]
        if not isinstance(raw, bytes):
            raw = bytes([raw])
        with open(output_path, "wb") as f:
            f.write(raw)
        msg = eml_lib.message_from_bytes(raw)
        date_str = ""
        if msg.get("Date"):
            date_str = re.sub(r'[^0-9]', '', msg.get("Date", ""))
        subj = decode_mime(msg.get("Subject", "unknown"))
        safe_name = re.sub(r'[^\w\-.]', '_', subj)[:80]
        base = os.path.basename(output_path)
        if not base.endswith(".eml"):
            base += ".eml"
        dirname = os.path.dirname(output_path) or "."
        print(f"Archived UID {uid} → {output_path} ({len(raw)} bytes)", file=sys.stderr)
        if date_str:
            alt = f"{dirname}/mail_{date_str}_{safe_name}.eml"
            print(f"  Suggested: {alt}", file=sys.stderr)
        elif safe_name:
            alt = f"{dirname}/{safe_name}.eml"
            print(f"  Suggested: {alt}", file=sys.stderr)
        if attachments_dir:
            written = extract_attachments(msg, attachments_dir)
            if written:
                print(f"Attachments ({len(written)}):", file=sys.stderr)
                for p in written:
                    print(f"  {p}", file=sys.stderr)
            else:
                print("No attachments found", file=sys.stderr)
        M.close()
        M.logout()
        return True
    except Exception as e:
        print(f"IMAP archive error: {e}", file=sys.stderr)
        return False


def print_message(msg, json_out=False):
    if json_out:
        print(json.dumps(msg, indent=2, ensure_ascii=False))
        return
    print(f"From:   {msg.get('from', '')}")
    print(f"Date:   {msg.get('date', '')}")
    print(f"Subject: {msg.get('subject', '')}")
    to = msg.get('to', '')
    if to:
        print(f"To:     {to}")
    cc = msg.get('cc', '')
    if cc and cc != to:
        print(f"Cc:     {cc}")
    print(f"Message-ID: {msg.get('message_id', '')}")
    print("-" * 70)
    body = msg.get('body', '')
    if body:
        body = body.replace("\r", "\n")
        print(body)
    else:
        print("[No body]")


def print_messages(messages, json_out=False):
    if json_out:
        print(json.dumps(messages, indent=2, ensure_ascii=False))
        return
    if not messages:
        print("No messages")
        return
    for i, msg in enumerate(messages, 1):
        print(f"\n--- [{i}] UID {msg.get('uid', '?')} ---")
        print(f"From:   {msg.get('from', '')}")
        print(f"Date:   {msg.get('date', '')}")
        print(f"Subject: {msg.get('subject', '')}")
        print(f"Read:   {msg.get('read', '?')}")


def decode_mime(s):
    if not s:
        return ""
    return str(make_header(decode_header(s)))


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        limit = 10
        json_out = "--json" in sys.argv
        for arg in sys.argv[2:]:
            if arg.startswith("--limit="):
                try:
                    limit = int(arg.split("=", 1)[1])
                except ValueError:
                    pass
        messages = list_messages(limit=limit)
        print_messages(messages, json_out=json_out)

    elif cmd == "read":
        if len(sys.argv) < 3:
            print("Usage: mail-reader read <uid> [--json]", file=sys.stderr)
            sys.exit(1)
        uid = sys.argv[2]
        json_out = "--json" in sys.argv
        msg = read_message(uid)
        if msg is None:
            sys.exit(1)
        print_message(msg, json_out=json_out)

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: mail-reader search <query> [--json]", file=sys.stderr)
            sys.exit(1)
        query = sys.argv[2]
        json_out = "--json" in sys.argv
        matches = search_messages(query)
        print_messages(matches, json_out=json_out)

    elif cmd == "archive":
        if len(sys.argv) < 4:
            print("Usage: mail-reader archive <uid> <output.eml> [--imap-service NAME] [--imap-host HOST] [--account EMAIL] [--mailbox NAME] [--attachments-dir DIR]", file=sys.stderr)
            sys.exit(1)
        uid = sys.argv[2]
        output_path = sys.argv[3]
        imap_service = "imap.gmx.net"
        imap_host = None
        mailbox = "INBOX"
        attachments_dir = None
        account_email = os.environ.get("KONTOR_MAIL_ACCOUNT")
        for arg in sys.argv[4:]:
            if arg.startswith("--imap-service="):
                imap_service = arg.split("=", 1)[1]
            elif arg.startswith("--imap-host="):
                imap_host = arg.split("=", 1)[1]
            elif arg.startswith("--account="):
                account_email = arg.split("=", 1)[1]
            elif arg.startswith("--mailbox="):
                mailbox = arg.split("=", 1)[1]
            elif arg.startswith("--attachments-dir="):
                attachments_dir = arg.split("=", 1)[1]
        if not account_email:
            print("Error: account email required. Pass --account=<email> or set KONTOR_MAIL_ACCOUNT.", file=sys.stderr)
            sys.exit(1)
        ok = archive_message(uid, output_path, account_email, imap_service, imap_host, mailbox, attachments_dir)
        sys.exit(0 if ok else 1)

    else:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
