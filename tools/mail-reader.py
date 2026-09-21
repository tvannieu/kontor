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
  mail-reader list   [--limit N] [--mail-account N|NAME] [--mailbox NAME] [--json]
  mail-reader read   <mail-app-id> [--mail-account N|NAME] [--mailbox NAME] [--json]
  mail-reader search <query> [--in subject|sender|either] [--mail-account ...] [--mailbox ...] [--json]
  mail-reader find   [--from TEXT] [--subject TEXT] [--since YYYY-MM-DD] [--limit N]
                     --account EMAIL [--mailbox NAME] [--json]
  mail-reader archive <imap-uid> <output.eml> --account EMAIL [--mailbox NAME] [--attachments-dir DIR]

`--name value` and `--name=value` both work. An option that is not recognised is an
error; it used to be ignored silently, so `--limit 30` quietly meant 10.

Two kinds of account, two kinds of id. list/read/search go through Mail.app and take
--mail-account (its own number or name; default 1) and print Mail.app ids. find and archive
speak IMAP and take --account (the e-mail address you log in with, or set
KONTOR_MAIL_ACCOUNT). To archive a message you already know how to describe, use `find` to get
its IMAP UID first:  mail-reader find --from someone --account EMAIL

'list', 'read' and 'search' see one Mail.app mailbox at a time (INBOX of account 1 unless told
otherwise), as scripted by AppleScript. 'archive' talks IMAP directly and
its UIDs live in a different number space from Mail.app's AppleScript
message ids — an id from 'list' is not an IMAP UID for 'archive'.

That is the most likely reason for `Error: no data for UID <n>` after a
successful `read <n>`: the same number was passed to both, and it means two
different things. This was reported as a bug in the fetch call on 2026-09-17
and again on 2026-09-21; the first report was a real one (fixed in the git
history of this file), the second was this.
"""

import sys
import os
import subprocess
import json
import re
import imaplib
import email as eml_lib
from email.header import decode_header, make_header
from email import utils as email_utils

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


def as_string(text):
    """Quote text for an AppleScript string literal. Backslash first, then the
    quote: the other order re-escapes the backslash it has just added, which
    leaves the quote unescaped and lets a query containing one break the script."""
    return str(text).replace("\\", "\\\\").replace('"', '\\"')


def mailbox_lookup(mail_account="1", mailbox="INBOX"):
    """AppleScript that leaves the chosen mailbox in `targetBox`.

    mail_account is Mail.app's own account: a number ("1", the default, which is
    what every version of this tool used) or an account name. Not the e-mail
    address that `archive` and `find` take, which names an IMAP login."""
    acct = f"account {int(mail_account)}" if str(mail_account).isdigit() else f'account "{as_string(mail_account)}"'
    return f'''        set acct to {acct}
        set theBoxes to every mailbox of acct
        set targetBox to missing value
        repeat with aBox in theBoxes
            if name of aBox is "{as_string(mailbox)}" then
                set targetBox to aBox
                exit repeat
            end if
        end repeat
'''


def list_messages(limit=10, mail_account="1", mailbox="INBOX"):
    script = f'''
    tell application "Mail"
{mailbox_lookup(mail_account, mailbox)}        if targetBox is missing value then return "NO_INBOX"
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
                "id_space": "mail-app",
            })
    return messages


def read_message(uid, mail_account="1", mailbox="INBOX"):
    script = f'''
    tell application "Mail"
{mailbox_lookup(mail_account, mailbox)}        if targetBox is missing value then
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


def search_messages(query, mail_account="1", mailbox="INBOX", field="subject"):
    safe_query = as_string(query)
    if field == "sender":
        cond = f'sender contains "{safe_query}"'
    elif field == "either":
        cond = f'subject contains "{safe_query}" or sender contains "{safe_query}"'
    else:
        cond = f'subject contains "{safe_query}"'
    script = f'''
    tell application "Mail"
{mailbox_lookup(mail_account, mailbox)}        if targetBox is missing value then return "NO_INBOX"
        set matches to (messages of targetBox whose {cond})
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
                "id_space": "mail-app",
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
        typ, sel = M.select(mailbox, readonly=True)
        if typ != "OK":
            print(f"Error: could not open mailbox {mailbox!r}: {sel}", file=sys.stderr)
            M.logout()
            return False
        typ, data = M.uid('fetch', uid, "(RFC822)")
        if not (data and data[0] and data[0][1]):
            count = sel[0].decode() if sel and isinstance(sel[0], bytes) else "?"
            print(f"Error: no data for UID {uid} in mailbox {mailbox!r} ({count} messages).",
                  file=sys.stderr)
            print("  If this number came from 'list' or 'read', that is why: those print Mail.app's own\n"
                  "  message ids, which are not IMAP UIDs. Other causes: the message is in a different\n"
                  "  mailbox (--mailbox=NAME) or belongs to a different account (--account=EMAIL).",
                  file=sys.stderr)
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
            # Stripping every non-digit from "Mon, 21 Sep 2026 10:00:00 +0000"
            # loses the month name and yields 2120261000000000, which is not a
            # date. Parse it, and fall back to nothing rather than to a wrong one.
            try:
                date_str = email_utils.parsedate_to_datetime(msg["Date"]).strftime("%Y-%m-%d")
            except (TypeError, ValueError):
                date_str = ""
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


def find_messages(account_email, imap_service="imap.gmx.net", imap_host=None,
                  mailbox="INBOX", sender=None, subject=None, since=None, limit=10):
    """Search over IMAP and return messages carrying their real IMAP UID.

    This is the way from "I know who sent it" to something `archive` accepts.
    `list`, `read` and `search` print Mail.app's own ids, which are a different
    number space, so nothing they print can be handed to `archive`. Read-only:
    the mailbox is opened read-only and headers are fetched with PEEK, so the
    messages are not marked as read.

    Search terms must be plain ASCII. IMAP SEARCH on other characters needs a
    charset negotiation this does not attempt; a fragment of an address is
    usually enough."""
    for label, value in (("sender", sender), ("subject", subject)):
        if value is not None and not value.isascii():
            print(f"Error: --{label} must be plain ASCII (use a fragment of the address or subject).",
                  file=sys.stderr)
            return None
    if since is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
        print("Error: --since must look like 2026-09-21.", file=sys.stderr)
        return None
    criteria = []
    if sender:
        criteria += ["FROM", '"' + sender.replace("\\", "\\\\").replace('"', '\\"') + '"']
    if subject:
        criteria += ["SUBJECT", '"' + subject.replace("\\", "\\\\").replace('"', '\\"') + '"']
    if since:
        y, m, d = since.split("-")
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        criteria += ["SINCE", f"{int(d)}-{months[int(m) - 1]}-{y}"]
    if not criteria:
        criteria = ["ALL"]
    pw = get_imap_password(account_email, imap_service)
    if pw is None:
        print(f"Error: IMAP password not in keychain for {account_email} / {imap_service}", file=sys.stderr)
        return None
    try:
        M = imaplib.IMAP4_SSL(imap_host or IMAP_HOST, IMAP_PORT)
        M.login(account_email, pw)
        typ, sel = M.select(mailbox, readonly=True)
        if typ != "OK":
            print(f"Error: could not open mailbox {mailbox!r}: {sel}", file=sys.stderr)
            M.logout()
            return None
        typ, data = M.uid("search", None, *criteria)
        uids = data[0].split() if typ == "OK" and data and data[0] else []
        uids = uids[-limit:][::-1]  # newest first: higher UIDs are later arrivals
        found = []
        for uid in uids:
            typ, parts = M.uid("fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            raw = next((x[1] for x in parts or [] if isinstance(x, tuple)), b"")
            msg = eml_lib.message_from_bytes(raw)
            found.append({
                "subject": decode_mime(msg.get("Subject", "")),
                "from": decode_mime(msg.get("From", "")),
                "date": msg.get("Date", ""),
                "uid": uid.decode(),
                "id_space": "imap",
            })
        M.close()
        M.logout()
        return found
    except Exception as e:
        print(f"IMAP find error: {e}", file=sys.stderr)
        return None


def print_messages(messages, json_out=False):
    if json_out:
        print(json.dumps(messages, indent=2, ensure_ascii=False))
        return
    if not messages:
        print("No messages")
        return
    for i, msg in enumerate(messages, 1):
        label = "IMAP UID" if msg.get("id_space") == "imap" else "Mail.app id"
        print(f"\n--- [{i}] {label} {msg.get('uid', '?')} ---")
        print(f"From:   {msg.get('from', '')}")
        print(f"Date:   {msg.get('date', '')}")
        print(f"Subject: {msg.get('subject', '')}")
        print(f"Read:   {msg.get('read', '?')}")


def decode_mime(s):
    if not s:
        return ""
    return str(make_header(decode_header(s)))


def build_parser():
    import argparse
    ap = argparse.ArgumentParser(
        prog="mail-reader", description=__doc__.split("Usage:")[0].strip().splitlines()[0],
        epilog="`--name value` and `--name=value` are both accepted. Anything not recognised is "
               "an error, not ignored: `--limit 30` used to be dropped silently and the default of 10 used.")
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="{list,read,search,find,archive}")

    def mail_app_opts(p):
        p.add_argument("--mail-account", default="1", metavar="N|NAME",
                       help="Mail.app account, by number or name (default 1). Not an e-mail address.")
        p.add_argument("--mailbox", default="INBOX", metavar="NAME", help="mailbox to look in (default INBOX)")
        p.add_argument("--json", action="store_true")

    def imap_opts(p):
        p.add_argument("--account", default=os.environ.get("KONTOR_MAIL_ACCOUNT"), metavar="EMAIL",
                       help="IMAP login; or set KONTOR_MAIL_ACCOUNT")
        p.add_argument("--imap-service", default="imap.gmx.net", metavar="NAME", help="Keychain service name")
        p.add_argument("--imap-host", default=None, metavar="HOST")
        p.add_argument("--mailbox", default="INBOX", metavar="NAME")

    p = sub.add_parser("list", help="recent messages, as Mail.app ids")
    p.add_argument("--limit", type=int, default=10, metavar="N"); mail_app_opts(p)
    p = sub.add_parser("read", help="one message by Mail.app id (from list/search, NOT an IMAP UID)")
    p.add_argument("id"); mail_app_opts(p)
    p = sub.add_parser("search", help="search Mail.app; subjects by default")
    p.add_argument("query"); mail_app_opts(p)
    p.add_argument("--in", dest="field", choices=["subject", "sender", "either"], default="subject",
                   help="what the query is matched against (default subject)")
    p = sub.add_parser("find", help="search over IMAP; returns real IMAP UIDs that `archive` accepts")
    imap_opts(p)
    p.add_argument("--from", dest="sender", default=None, metavar="TEXT", help="sender contains TEXT (ASCII)")
    p.add_argument("--subject", default=None, metavar="TEXT", help="subject contains TEXT (ASCII)")
    p.add_argument("--since", default=None, metavar="YYYY-MM-DD")
    p.add_argument("--limit", type=int, default=10, metavar="N"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("archive", help="save one message as .eml by IMAP UID (from `find`)")
    p.add_argument("imap_uid"); p.add_argument("output"); imap_opts(p)
    p.add_argument("--attachments-dir", default=None, metavar="DIR")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.cmd == "list":
        print_messages(list_messages(limit=args.limit, mail_account=args.mail_account, mailbox=args.mailbox),
                       json_out=args.json)
    elif args.cmd == "read":
        msg = read_message(args.id, mail_account=args.mail_account, mailbox=args.mailbox)
        if msg is None:
            sys.exit(1)
        print_message(msg, json_out=args.json)
    elif args.cmd == "search":
        print_messages(search_messages(args.query, mail_account=args.mail_account,
                                       mailbox=args.mailbox, field=args.field), json_out=args.json)
    elif args.cmd == "find":
        if not args.account:
            print("Error: account email required. Pass --account=<email> or set KONTOR_MAIL_ACCOUNT.", file=sys.stderr)
            sys.exit(1)
        found = find_messages(args.account, args.imap_service, args.imap_host, args.mailbox,
                              sender=args.sender, subject=args.subject, since=args.since, limit=args.limit)
        if found is None:
            sys.exit(1)
        print_messages(found, json_out=args.json)
    elif args.cmd == "archive":
        if not args.account:
            print("Error: account email required. Pass --account=<email> or set KONTOR_MAIL_ACCOUNT.", file=sys.stderr)
            sys.exit(1)
        ok = archive_message(args.imap_uid, args.output, args.account, args.imap_service,
                             args.imap_host, args.mailbox, args.attachments_dir)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
