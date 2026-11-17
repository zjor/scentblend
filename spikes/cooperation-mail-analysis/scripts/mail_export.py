#!/usr/bin/env python3
"""Export the cooperation mailbox over IMAP into a local SQLite file.

Read-only: uses BODY.PEEK and EXAMINE, so unread messages stay unread.
Resumable: messages already stored (same folder, UIDVALIDITY, UID) are skipped.

Usage:
    python3 scripts/mail_export.py [--folders INBOX Sent] [--db data/mail.sqlite]
"""

from __future__ import annotations

import argparse
import email
import email.policy
import email.utils
import imaplib
import os
import re
import sqlite3
import sys
from datetime import timezone
from html.parser import HTMLParser
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent.parent
BATCH = 50

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    folder        TEXT NOT NULL,
    uidvalidity   INTEGER NOT NULL,
    uid           INTEGER NOT NULL,
    message_id    TEXT,
    in_reply_to   TEXT,
    refs          TEXT,
    date_utc      TEXT,
    from_name     TEXT,
    from_addr     TEXT,
    to_addrs      TEXT,
    cc_addrs      TEXT,
    subject       TEXT,
    body_text     TEXT,
    attachments   TEXT,
    size          INTEGER,
    flags         TEXT,
    raw_headers   TEXT,
    PRIMARY KEY (folder, uidvalidity, uid)
);
CREATE INDEX IF NOT EXISTS ix_messages_mid ON messages(message_id);
CREATE INDEX IF NOT EXISTS ix_messages_from ON messages(from_addr);
CREATE INDEX IF NOT EXISTS ix_messages_date ON messages(date_utc);
"""


def load_env(path: Path) -> dict[str, str]:
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in ("br", "p", "div", "tr", "li"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = "".join(parser.parts)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def addresses(value: str | None) -> list[str]:
    if not value:
        return []
    return [addr.lower() for _, addr in email.utils.getaddresses([value]) if addr]


def parse_message(raw: bytes) -> dict:
    msg = email.message_from_bytes(raw, policy=email.policy.default)

    plain, html, attachments = None, None, []
    for part in msg.walk():
        if part.is_multipart():
            continue
        filename = part.get_filename()
        disposition = part.get_content_disposition()
        if filename or disposition == "attachment":
            attachments.append(filename or "(unnamed)")
            continue
        ctype = part.get_content_type()
        try:
            content = part.get_content()
        except Exception:
            content = (part.get_payload(decode=True) or b"").decode("utf-8", "replace")
        if ctype == "text/plain" and plain is None:
            plain = content
        elif ctype == "text/html" and html is None:
            html = content

    body = plain if plain else (html_to_text(html) if html else "")

    date_utc = None
    if msg["Date"]:
        try:
            dt = email.utils.parsedate_to_datetime(str(msg["Date"]))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            date_utc = dt.astimezone(timezone.utc).isoformat()
        except Exception:
            pass

    from_name, from_addr = email.utils.parseaddr(str(msg["From"] or ""))
    header_block = raw.split(b"\r\n\r\n", 1)[0].split(b"\n\n", 1)[0]

    return {
        "message_id": (str(msg["Message-ID"] or "").strip() or None),
        "in_reply_to": (str(msg["In-Reply-To"] or "").strip() or None),
        "refs": (" ".join(str(msg["References"] or "").split()) or None),
        "date_utc": date_utc,
        "from_name": from_name or None,
        "from_addr": from_addr.lower() or None,
        "to_addrs": ",".join(addresses(str(msg["To"] or ""))),
        "cc_addrs": ",".join(addresses(str(msg["Cc"] or ""))),
        "subject": str(msg["Subject"] or ""),
        "body_text": body,
        "attachments": "|".join(attachments),
        "raw_headers": header_block.decode("utf-8", "replace"),
    }


def export_folder(imap: imaplib.IMAP4_SSL, db: sqlite3.Connection, folder: str) -> None:
    typ, _ = imap.select(f'"{folder}"', readonly=True)
    if typ != "OK":
        print(f"{folder}: cannot open, skipped", file=sys.stderr)
        return
    uidvalidity = int(imap.response("UIDVALIDITY")[1][0])

    typ, data = imap.uid("SEARCH", None, "ALL")
    uids = [int(u) for u in data[0].split()]
    have = {
        row[0]
        for row in db.execute(
            "SELECT uid FROM messages WHERE folder=? AND uidvalidity=?", (folder, uidvalidity)
        )
    }
    todo = [u for u in uids if u not in have]
    print(f"{folder}: {len(uids)} on server, {len(have)} stored, {len(todo)} to fetch")

    for start in range(0, len(todo), BATCH):
        chunk = todo[start : start + BATCH]
        uid_set = ",".join(str(u) for u in chunk)
        typ, data = imap.uid("FETCH", uid_set, "(UID FLAGS RFC822.SIZE BODY.PEEK[])")
        if typ != "OK":
            print(f"{folder}: fetch failed for {uid_set}", file=sys.stderr)
            continue
        rows = []
        for item in data:
            if not isinstance(item, tuple):
                continue
            meta, raw = item[0].decode(), item[1]
            uid = int(re.search(r"UID (\d+)", meta).group(1))
            size = int(re.search(r"RFC822\.SIZE (\d+)", meta).group(1))
            flags_m = re.search(r"FLAGS \(([^)]*)\)", meta)
            flags = flags_m.group(1) if flags_m else ""
            try:
                parsed = parse_message(raw)
            except Exception as exc:  # keep going, record the failure
                print(f"{folder} uid {uid}: parse error {exc}", file=sys.stderr)
                continue
            rows.append({"folder": folder, "uidvalidity": uidvalidity, "uid": uid,
                         "size": size, "flags": flags, **parsed})
        db.executemany(
            """INSERT OR REPLACE INTO messages VALUES (
                :folder, :uidvalidity, :uid, :message_id, :in_reply_to, :refs, :date_utc,
                :from_name, :from_addr, :to_addrs, :cc_addrs, :subject, :body_text,
                :attachments, :size, :flags, :raw_headers)""",
            rows,
        )
        db.commit()
        print(f"{folder}: {min(start + BATCH, len(todo))}/{len(todo)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folders", nargs="+", default=["INBOX", "Sent"])
    parser.add_argument("--db", default=str(SPIKE_DIR / "data" / "mail.sqlite"))
    args = parser.parse_args()

    env = load_env(SPIKE_DIR / ".env")
    db = sqlite3.connect(args.db)
    db.executescript(SCHEMA)

    imap = imaplib.IMAP4_SSL(env["IMAP_HOST"], int(env.get("IMAP_PORT", "993")))
    imap.login(env["IMAP_USER"], env["IMAP_PASSWORD"])
    try:
        for folder in args.folders:
            export_folder(imap, db, folder)
    finally:
        imap.logout()
        db.close()


if __name__ == "__main__":
    main()
