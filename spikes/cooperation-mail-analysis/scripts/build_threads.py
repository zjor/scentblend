#!/usr/bin/env python3
"""Group exported messages into threads and derive per-thread facts.

Reads data/mail.sqlite (table messages) and writes tables:
  msg      one row per unique message (INBOX + Sent copies merged), with direction
  threads  one row per thread

Threading: union-find over Message-ID, In-Reply-To and References.
Fallback for messages without links: same normalized subject + same counterparty.
"""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent.parent
DB = SPIKE_DIR / "data" / "mail.sqlite"

OUR_DOMAINS = {"scentblend.cz", "scent-blend.com"}
SUBJECT_PREFIX = re.compile(r"^\s*((re|fw|fwd|aw|wg|odp|tr|sv|vs|r)\s*(\[\d+\])?\s*:\s*)+", re.I)
MSGID = re.compile(r"<[^>]+>")


def domain(addr: str | None) -> str:
    return addr.rsplit("@", 1)[-1].lower() if addr and "@" in addr else ""


def is_ours(addr: str | None) -> bool:
    return domain(addr) in OUR_DOMAINS


def norm_subject(s: str) -> str:
    s = SUBJECT_PREFIX.sub("", s or "")
    return re.sub(r"\s+", " ", s).strip().lower()


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def main() -> None:
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT * FROM messages ORDER BY date_utc").fetchall()

    # Merge duplicates (same Message-ID in INBOX and Sent).
    msgs: dict[str, dict] = {}
    for r in rows:
        key = r["message_id"] or f"{r['folder']}:{r['uid']}"
        if key in msgs:
            continue
        m = dict(r)
        m["key"] = key
        out = is_ours(m["from_addr"])
        m["direction"] = "out" if out else "in"
        if out:
            others = [a for a in (m["to_addrs"] or "").split(",") + (m["cc_addrs"] or "").split(",")
                      if a and not is_ours(a)]
            m["counterparty"] = others[0] if others else ""
        else:
            m["counterparty"] = m["from_addr"] or ""
        msgs[key] = m

    dsu = DSU()
    for k, m in msgs.items():
        dsu.find(k)
        for ref in MSGID.findall(" ".join(filter(None, [m["in_reply_to"], m["refs"]]))):
            dsu.union(k, ref)

    # Fallback: unlinked messages with the same subject and counterparty.
    by_subj = {}
    for k, m in msgs.items():
        s = norm_subject(m["subject"])
        if not s or not m["counterparty"]:
            continue
        sk = (s, m["counterparty"])
        if sk in by_subj:
            dsu.union(by_subj[sk], k)
        else:
            by_subj[sk] = k

    groups = defaultdict(list)
    for k, m in msgs.items():
        groups[dsu.find(k)].append(m)

    db.executescript("""
        DROP TABLE IF EXISTS msg;
        CREATE TABLE msg (key TEXT PRIMARY KEY, thread_id INTEGER, folder TEXT, uid INTEGER,
            date_utc TEXT, direction TEXT, from_addr TEXT, from_name TEXT, to_addrs TEXT,
            cc_addrs TEXT, counterparty TEXT, cp_domain TEXT, subject TEXT, body_text TEXT,
            attachments TEXT, flags TEXT, raw_headers TEXT);
        DROP TABLE IF EXISTS threads;
        CREATE TABLE threads (thread_id INTEGER PRIMARY KEY, subject TEXT, counterparty TEXT,
            cp_domain TEXT, participants TEXT, n_msgs INTEGER, n_in INTEGER, n_out INTEGER,
            first_utc TEXT, last_utc TEXT, duration_days REAL, started_by TEXT, last_by TEXT,
            first_reply_hours REAL, unread_in INTEGER);
    """)

    tid = 0
    for members in groups.values():
        members.sort(key=lambda m: m["date_utc"] or "")
        tid += 1
        cps = [m["counterparty"] for m in members if m["counterparty"]]
        cp = max(set(cps), key=cps.count) if cps else ""
        participants = sorted({a for m in members
                               for a in [m["from_addr"]] + (m["to_addrs"] or "").split(",")
                               + (m["cc_addrs"] or "").split(",")
                               if a and not is_ours(a)})
        first, last = members[0], members[-1]
        n_in = sum(m["direction"] == "in" for m in members)
        reply_h = None
        if first["direction"] == "in":
            for m in members[1:]:
                if m["direction"] == "out" and m["date_utc"] and first["date_utc"]:
                    reply_h = (_ts(m["date_utc"]) - _ts(first["date_utc"])) / 3600
                    break
        unread = sum(m["direction"] == "in" and "\\Seen" not in (m["flags"] or "") for m in members)
        dur = (_ts(last["date_utc"]) - _ts(first["date_utc"])) / 86400 if first["date_utc"] and last["date_utc"] else 0
        db.execute("INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            tid, first["subject"], cp, domain(cp), ",".join(participants), len(members), n_in,
            len(members) - n_in, first["date_utc"], last["date_utc"], round(dur, 2),
            first["direction"], last["direction"], None if reply_h is None else round(reply_h, 2), unread))
        for m in members:
            db.execute("INSERT INTO msg VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                m["key"], tid, m["folder"], m["uid"], m["date_utc"], m["direction"], m["from_addr"],
                m["from_name"], m["to_addrs"], m["cc_addrs"], m["counterparty"], domain(m["counterparty"]),
                m["subject"], m["body_text"], m["attachments"], m["flags"], m["raw_headers"]))
    db.commit()
    n = db.execute("SELECT count(*), sum(n_msgs) FROM threads").fetchone()
    print(f"{n[0]} threads, {n[1]} unique messages")


def _ts(iso: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(iso).timestamp()


if __name__ == "__main__":
    main()
