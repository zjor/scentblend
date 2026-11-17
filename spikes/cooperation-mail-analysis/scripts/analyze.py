#!/usr/bin/env python3
"""Answer the spike questions from data/mail.sqlite (after build_threads.py).

Writes reports/*.csv, reports/*.png and reports/report.md.
Classification is rule-based (data/labels.csv + keyword rules), so treat
stage, service line and lost reasons as estimates.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

SPIKE = Path(__file__).resolve().parent.parent
DB = SPIKE / "data" / "mail.sqlite"
LABELS = SPIKE / "data" / "labels.csv"
OUT = SPIKE / "reports"
NOW = datetime(2026, 11, 17, tzinfo=timezone.utc)
FREE_MAIL = {"gmail.com", "seznam.cz", "email.cz", "centrum.cz", "icloud.com", "outlook.com",
             "hotmail.com", "post.cz", "tiscali.cz", "volny.cz", "atlas.cz", "yahoo.com",
             "mail.cz", "googlemail.com", "inbox.lv", "me.com", "live.com"}

NOISE_LOCAL = re.compile(r"^(no-?reply|noreply|mailer-daemon|postmaster|notif|notify|newsletter|"
                         r"novinky|news|info@newsletter|system|support@ppl|reviews|marketing@czechtrade)", re.I)

# Outreach campaigns: subject prefix -> (campaign, target segment)
CAMPAIGNS = [
    ("dotaz ke spolupráci – scent blend", "CZ real estate (Dotaz)", "real_estate"),
    ("nabídka spolupráce – scent blend", "CZ real estate (Nabídka)", "real_estate"),
    ("anfrage zur zusammenarbeit", "CH real estate", "real_estate"),
    ("collaboration opportunity", "EU car dealers", "automotive_dealer"),
    ("invitation: discover sensory marketing", "FR marketing agencies", "marketing_agency"),
    ("návrh spolupráce: aroma marketing pro váš resort", "CZ resorts & golf", "hotel_resort"),
    ("návrh spolupráce: aroma marketing pro váš hotel", "CZ resorts & golf", "hotel_resort"),
    ("a unique scent identity for your resort", "AT/HU resorts", "hotel_resort"),
    ("návrh spolupráce v oblasti aroma marketingu", "Prague HoReCa", "horeca"),
    ("speciální nabídka pro vaši značku", "CZ car wash", "car_wash"),
    ("great meeting at in-cosmetics", "In-Cosmetics contacts", "cosmetics_industry"),
    ("christmas with scent blend", "In-Cosmetics contacts", "cosmetics_industry"),
    ("nápad na spolupráci: vánoční dárky", "Fuel stations (gifts)", "fuel_retail"),
    ("nabídka spolupráce v oblasti eventů", "Events", "events"),
    ("vánoční nabídka", "Christmas offer", ""),
    ("vaše poptávka", "Reply to web enquiry", ""),
    ("difuzéry na míru", "Reply to web enquiry", ""),
    ("svíčky na míru", "Reply to web enquiry", ""),
    ("vaše objednávka – scent blend factory", "Reply to web enquiry", ""),
]

SERVICE_RULES = {
    "space_scenting": r"aroma ?marketing|aromatizac|difuz[ée]r|diffuser|scent marketing|sensory marketing|duftmarketing|vůn[ěí] (do|pro) prostor|náplň",
    "private_label": r"private label|vlastní značk|pod vaší značkou|white label|na míru|s logem|potisk|merch",
    "brand_experience": r"event|akce|veletrh|festival|activation|aktivac|konferenc",
    "gifts": r"vánoč|christmas|dárk|gift",
    "distribution": r"velkoobchod|wholesale|distribu|dealer|e-?shop|marketplace|reseller",
}
STAGE_RULES = [  # ordered low -> high
    ("meeting", r"schůzk|meeting|\bcall\b|zoom|teams|sejdeme|setkání|termín"),
    ("sample", r"vzor(ek|ky|ků)|sample|tester|muster"),
    ("quote", r"cenov[áé] nabídk|kalkulac|quote|quotation|price list|ceník|\b\d[\d  .,]*\s?(kč|czk|eur|€)"),
    ("contract", r"smlouv|contract|vertrag"),
    ("order", r"objednáv(ka|ku|ám)|\border\b|faktur|invoice|záloh|proforma|platb"),
]
LOST_RULES = {
    "not interested": r"nemáme zájem|nemám zájem|zájem nemáme|nemáme o .{0,30}zájem|nevyužijeme|neuvažujeme|nemáme potřeb|not interested|no,? thank|kein interesse|no interest|nebudeme mít zájem|^\s*(dobrý den,?)?\s*(není|ne)\.?\s",
    "already have / other supplier": r"již (máme|spolupracujeme)|už (máme|spolupracujeme)|stávající dodavatel|already (have|work)|jiného dodavatele",
    "budget / price": r"rozpočet|budget|příliš drah|too expensive|cena je vysok|finanční",
    "not now / timing": r"momentálně ne|v tuto chvíli|nyní ne|aktuálně (ne|není)|do budoucna|později|až poté|not at the moment|später|later|příští rok|next year",
    "not decision maker / forwarded": r"předám|předala|forward|kolegovi|kolegyni|nejsem kompetent",
}
QUOTE_CUT = re.compile(
    r"^(>|-{2,}\s*(original|původní|forwarded|přeposlan)|from:|od:|odesláno:|sent:|von:|"
    r".{0,40}odesílatel .{3,80} napsal|"
    r"on .{5,80} wrote:|dne .{5,80} napsal|le .{5,80} a écrit|am .{5,80} schrieb|"
    r"\d{1,2}\. ?\d{1,2}\. ?\d{4}.{0,40}(napsal|wrote))", re.I)
AUTO_SUBJ = re.compile(r"automatick|out of office|mimo kancel|dovolen|absen|abwesen|automatic reply|"
                       r"auto.?reply|autosvar|nepřítomn|undeliver|delivery status|returned to sender|delayed mail|"
                       r"failure notice|potvrzení přijetí|ticket", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def own_text(body: str | None) -> str:
    lines = []
    for line in (body or "").splitlines():
        if QUOTE_CUT.match(line.strip()):
            break
        lines.append(line)
    return "\n".join(lines)


def ts(iso: str | None) -> datetime | None:
    return datetime.fromisoformat(iso) if iso else None


def load_labels() -> dict[str, dict]:
    with LABELS.open() as f:
        rows = [r for r in csv.DictReader(line for line in f if not line.startswith("#"))]
    return {r["key"].lower(): r for r in rows}


def label_for(addr: str, labels: dict) -> dict:
    addr = (addr or "").lower()
    dom = addr.rsplit("@", 1)[-1]
    if addr in labels:
        return labels[addr]
    parts = dom.split(".")
    for i in range(len(parts) - 1):  # domain and its parents
        d = ".".join(parts[i:])
        if d in labels and not (d in FREE_MAIL):
            return labels[d]
    if NOISE_LOCAL.match(addr):
        return {"role": "noise", "industry": "", "customer": ""}
    return {}


def campaign_for(subject: str) -> tuple[str, str]:
    s = re.sub(r"^\s*((re|fw|fwd|aw)\s*:\s*)+", "", (subject or "").lower()).strip()
    s = re.sub(r"\s+", " ", s)
    for prefix, name, seg in CAMPAIGNS:
        if s.startswith(prefix):
            return name, seg
    return "", ""


def main() -> None:
    OUT.mkdir(exist_ok=True)
    labels = load_labels()
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    threads = [dict(r) for r in db.execute("SELECT * FROM threads")]
    msgs = defaultdict(list)
    for r in db.execute("SELECT * FROM msg ORDER BY date_utc"):
        msgs[r["thread_id"]].append(dict(r))

    # Bounced recipients: addresses named in bounce bodies that we wrote to.
    sent_to = {a for ms in msgs.values() for m in ms if m["direction"] == "out"
               for a in (m["to_addrs"] or "").split(",") if a}
    bounced = set()
    for ms in msgs.values():
        for m in ms:
            if m["direction"] == "in" and re.search(r"mailer-daemon|postmaster", m["from_addr"] or "", re.I):
                bounced |= {a.lower() for a in EMAIL_RE.findall(m["body_text"] or "")} & sent_to

    # Web form enquiries: the real sender is inside the body.
    form_leads = []
    for ms in msgs.values():
        for m in ms:
            if "web3forms" in (m["from_addr"] or "") and "inquiry" in (m["subject"] or "").lower():
                em = re.search(r"email\s*:\s*(\S+@\S+)", m["body_text"] or "")
                co = re.search(r"company\s*:\s*(.*)", m["body_text"] or "")
                form_leads.append({"date": m["date_utc"], "email": em.group(1).lower() if em else "",
                                   "company": co.group(1).strip() if co else ""})

    rows = []
    for t in threads:
        ms = msgs[t["thread_id"]]
        cp = t["counterparty"] or ""
        lab = label_for(cp, labels)
        campaign, seg = campaign_for(t["subject"]) if t["started_by"] == "out" else ("", "")
        role = lab.get("role") or ("prospect" if campaign or t["started_by"] == "out" else "unknown")
        if role == "unknown" and t["started_by"] == "in":
            role = "prospect"  # inbound mail from an unlisted sender: treat as a lead
        industry = lab.get("industry") or seg
        if not industry and cp.rsplit("@", 1)[-1] in FREE_MAIL:
            industry = "private_or_small"
        human_in = [m for m in ms if m["direction"] == "in" and not AUTO_SUBJ.search(m["subject"] or "")
                    and not NOISE_LOCAL.match(m["from_addr"] or "")]
        auto_in = [m for m in ms if m["direction"] == "in" and m not in human_in]
        text_all = "\n".join([t["subject"] or ""] + [own_text(m["body_text"]) for m in ms]).lower()
        text_in = "\n".join(own_text(m["body_text"]) for m in human_in).lower()
        stage = "none"
        if human_in or t["started_by"] == "in":
            stage = "conversation"
            for name, rx in STAGE_RULES:
                if re.search(rx, text_all):
                    stage = name
        services = [k for k, rx in SERVICE_RULES.items() if re.search(rx, text_all)]
        lost = [k for k, rx in LOST_RULES.items() if re.search(rx, text_in)]
        last = ts(t["last_utc"])
        age = (NOW - last).days if last else None
        last_human = max([m for m in ms if m["direction"] == "out"] + human_in,
                         key=lambda m: m["date_utc"] or "", default=None)
        last_by = last_human["direction"] if last_human else t["last_by"]
        last_in_text = own_text(human_in[-1]["body_text"]).lower() if human_in else ""
        negative = bool(re.search(LOST_RULES["not interested"], last_in_text))
        if (t["subject"] or "").lower().startswith("new order"):
            role = "eshop"
        if role in ("noise", "internal", "eshop"):
            state = "n/a"
        elif not human_in and t["n_out"] == 0:
            state = "auto-reply only"
        elif last_by == "in" and negative:
            state = "declined"
        elif t["started_by"] == "out" and not human_in:
            state = "bounced" if cp in bounced else "no reply"
        elif last_by == "in":
            state = "waiting for us"
        elif age is not None and age > 60:
            state = "dead"
        elif age is not None and age > 14:
            state = "waiting for them (follow-up)"
        else:
            state = "alive"
        rows.append({
            **{k: t[k] for k in ("thread_id", "subject", "counterparty", "cp_domain", "n_msgs", "n_in", "n_out",
                                 "first_utc", "last_utc", "duration_days", "started_by", "first_reply_hours")},
            "participants": len([p for p in (t["participants"] or "").split(",") if p]),
            "role": role, "industry": industry or "unknown", "customer": lab.get("customer", ""),
            "campaign": campaign, "human_replies": len(human_in), "auto_replies": len(auto_in),
            "stage": stage, "services": ",".join(services), "lost_reasons": ",".join(lost),
            "state": state, "days_since_last": age, "last_by": last_by,
            "free_mail": cp.rsplit("@", 1)[-1] in FREE_MAIL,
            "tld": cp.rsplit(".", 1)[-1] if "." in cp else "",
        })

    df = pd.DataFrame(rows)
    df["first_dt"] = pd.to_datetime(df["first_utc"], utc=True)
    df.to_csv(OUT / "threads.csv", index=False)
    biz = df[df.role.isin(["prospect", "media"])]
    report = []
    w = report.append

    # Basics
    contacts = (pd.read_sql("SELECT from_addr a, from_name n, date_utc d FROM msg WHERE direction='in'", db)
                .groupby("a").agg(name=("n", "first"), messages=("d", "size"), first=("d", "min"), last=("d", "max")))
    role_of = {a: (label_for(a, labels).get("role") or "prospect") for a in contacts.index}
    contacts["role"] = contacts.index.map(role_of)
    contacts.to_csv(OUT / "contacts.csv")
    out_only = {a for a in sent_to if a not in contacts.index and label_for(a, labels).get("role") != "internal"}
    dom = df.groupby("cp_domain").agg(threads=("thread_id", "size"), role=("role", "first"),
                                      industry=("industry", "first"), human_replies=("human_replies", "sum"),
                                      first=("first_utc", "min"), last=("last_utc", "max"))
    dom.sort_values("threads", ascending=False).to_csv(OUT / "domains.csv")

    w("# Cooperation mailbox analysis — report\n")
    w(f"Generated {NOW.date()}. Data: {len(df)} threads, {df.n_msgs.sum()} messages, "
      f"{df.first_utc.min()[:10]} to {df.last_utc.max()[:10]}.\n")
    w("Stage, service line and lost reasons come from keyword rules. Treat them as estimates.\n")
    w("## 1. Basics\n")
    w(f"- People who wrote to us: {len(contacts)} addresses; "
      f"{(contacts.role == 'prospect').sum()} of them are prospects or clients.")
    w(f"- Addresses we wrote to but who never wrote back: {len(out_only)}.")
    w(f"- Distinct counterparty domains: {df.cp_domain.nunique()}.\n")
    w("Threads by role:\n")
    w(df.role.value_counts().to_frame("threads").to_markdown() + "\n")
    w("Business threads (prospects, clients, media) by number of messages:\n")
    bins = pd.cut(biz.n_msgs, [0, 1, 2, 3, 5, 10, 1000], labels=["1", "2", "3", "4-5", "6-10", ">10"])
    w(bins.value_counts().sort_index().to_frame("threads").to_markdown() + "\n")
    w("Business threads with a human reply, by duration:\n")
    talk = biz[biz.human_replies > 0]
    dbins = pd.cut(talk.duration_days, [-1, 1, 7, 30, 90, 1000],
                   labels=["≤1 day", "2-7 days", "8-30 days", "31-90 days", ">90 days"])
    w(dbins.value_counts().sort_index().to_frame("threads").to_markdown() + "\n")

    # Cleanup
    w("## 2. Cleanup: who is not a client\n")
    w(df.groupby("role").agg(threads=("thread_id", "size"), messages=("n_msgs", "sum")).to_markdown() + "\n")
    w("`noise` = notifications, newsletters, carriers, bounces, SaaS. `supplier` = materials, packaging, print. "
      "`service` = accounting, logistics, vendor pitches.\n")

    # Outreach funnel
    w("## 3. Outreach (threads we started)\n")
    ob = df[(df.started_by == "out") & (df.role == "prospect")].copy()
    ob["replied"] = ob.human_replies > 0
    ob["bounced"] = ob.state == "bounced"
    camp = ob[ob.campaign != ""].groupby("campaign").agg(
        sent=("thread_id", "size"), bounced=("bounced", "sum"), replied=("replied", "sum"),
        first=("first_utc", "min"))
    camp["reply_rate_%"] = (100 * camp.replied / (camp.sent - camp.bounced)).round(1)
    camp["first"] = camp["first"].str[:10]
    camp = camp.sort_values("sent", ascending=False)
    camp.to_csv(OUT / "campaigns.csv")
    w(f"- Outreach threads: {len(ob)}, of them {ob.bounced.sum()} bounced, {ob.replied.sum()} got a human reply "
      f"({100 * ob.replied.sum() / max(1, len(ob) - ob.bounced.sum()):.1f}% of delivered).\n")
    w(camp.to_markdown() + "\n")
    seg_of = {name: seg for _, name, seg in CAMPAIGNS}
    ob["segment"] = ob.campaign.map(seg_of).fillna("")
    by_ind = ob[ob.segment != ""].groupby("segment").agg(sent=("thread_id", "size"), replied=("replied", "sum"))
    by_ind["reply_rate_%"] = (100 * by_ind.replied / by_ind.sent).round(1)
    w("Reply rate by target industry (campaign threads only):\n")
    w(by_ind.sort_values("sent", ascending=False).to_markdown() + "\n")
    ob["month"] = ob.first_dt.dt.strftime("%Y-%m")
    bym = ob.groupby("month").agg(sent=("thread_id", "size"), replied=("replied", "sum"))
    bym["reply_rate_%"] = (100 * bym.replied / bym.sent).round(1)
    w("Outreach by month:\n")
    w(bym.to_markdown() + "\n")

    # Inbound leads and speed
    w("## 4. Inbound leads and reply speed\n")
    ib = df[(df.started_by == "in") & (df.role == "prospect")].copy()
    ib = ib[~ib.subject.str.contains(AUTO_SUBJ.pattern, case=False, regex=True, na=False)]
    replied = ib.first_reply_hours.notna()
    w(f"- Inbound prospect threads: {len(ib)}. We replied in {replied.sum()} "
      f"({100 * replied.mean():.0f}%).")
    if replied.any():
        h = ib.first_reply_hours.dropna()
        w(f"- First reply time: median {h.median():.1f} h, 75th percentile {h.quantile(.75):.1f} h, "
          f"within 24 h: {100 * (h <= 24).mean():.0f}%.")
    w(f"- Web form enquiries (web3forms): {len(form_leads)}.")
    fl_rows = []
    out_msgs = pd.read_sql("SELECT to_addrs, date_utc FROM msg WHERE direction='out'", db)
    for fl in form_leads:
        later = out_msgs[(out_msgs.to_addrs.str.contains(re.escape(fl["email"]), na=False))
                         & (out_msgs.date_utc > fl["date"])] if fl["email"] else out_msgs.iloc[0:0]
        hrs = ((ts(later.date_utc.min()) - ts(fl["date"])).total_seconds() / 3600) if len(later) else None
        fl_rows.append({**fl, "first_reply_hours": None if hrs is None else round(hrs, 1)})
    fl_df = pd.DataFrame(fl_rows)
    fl_df.to_csv(OUT / "web_form_leads.csv", index=False)
    if len(fl_df):
        fr = fl_df.first_reply_hours.dropna()
        w(f"- Web form enquiries answered by email: {len(fr)} of {len(fl_df)}; "
          f"median first reply {fr.median():.1f} h." if len(fr) else "- No web form enquiry got an email reply.")
    unanswered = ib[~replied & ib.counterparty.ne("")][["thread_id", "first_utc", "counterparty", "subject", "n_msgs"]]
    unanswered.to_csv(OUT / "unanswered_inbound.csv", index=False)
    w(f"- Inbound prospect threads with no reply from us: {len(unanswered)} (list: `reports/unanswered_inbound.csv`).\n")

    # State
    w("## 5. Thread state (business threads)\n")
    w(biz.state.value_counts().to_frame("threads").to_markdown() + "\n")
    fu = biz[biz.state.isin(["waiting for them (follow-up)", "waiting for us"])].sort_values("last_utc", ascending=False)
    fu[["thread_id", "state", "last_utc", "days_since_last", "counterparty", "subject", "stage", "industry"]] \
        .to_csv(OUT / "follow_up.csv", index=False)
    w(f"Lists: `reports/follow_up.csv` ({len(fu)} threads).\n")

    # Funnel stages
    w("## 6. Funnel stage reached (threads with a human reply or inbound start)\n")
    eng = biz[biz.stage != "none"]
    order = ["conversation", "meeting", "sample", "quote", "contract", "order"]
    w(eng.stage.value_counts().reindex(order).fillna(0).astype(int).to_frame("threads").to_markdown() + "\n")
    lr = Counter(x for v in eng.lost_reasons for x in v.split(",") if x)
    w("Reasons given in their replies (a thread can have several):\n")
    w(pd.Series(lr).sort_values(ascending=False).to_frame("threads").to_markdown() + "\n")

    # Service lines
    w("## 7. What the conversations are about (engaged business threads)\n")
    sv = Counter(x for v in eng.services for x in v.split(",") if x)
    w(pd.Series(sv).sort_values(ascending=False).to_frame("threads").to_markdown() + "\n")

    # Who
    w("## 8. Who the counterparties are\n")
    ind = eng.groupby("industry").agg(threads=("thread_id", "size"),
                                      orders=("stage", lambda s: (s == "order").sum()))
    w("Engaged business threads by industry:\n")
    w(ind.sort_values("threads", ascending=False).to_markdown() + "\n")
    w(f"- Free-mail counterparties among engaged threads: {eng.free_mail.sum()} of {len(eng)}.")
    tld = eng.tld.value_counts().head(10)
    w("- Top TLDs (engaged): " + ", ".join(f"{k} {v}" for k, v in tld.items()) + ".")
    rep = eng.groupby("cp_domain").thread_id.size()
    rep = rep[(rep >= 2) & ~rep.index.isin(FREE_MAIL)]
    w(f"- Domains with 2+ engaged threads (repeat contacts): {len(rep)}.")
    w(f"- Engaged threads with 2+ external people: {(eng.participants >= 2).sum()}.\n")

    # Bank link
    w("## 9. Link to paying customers\n")
    cust = pd.read_csv(SPIKE.parent.parent / "data" / "enriched" / "customers.csv")
    linked = set(df.customer.dropna()) - {""}
    w(f"- Customers in the bank export: {len(cust)}. Found in the mailbox: {len(linked)}.")
    lk = df[df.customer.fillna("") != ""].groupby("customer").agg(
        threads=("thread_id", "size"), messages=("n_msgs", "sum"), first=("first_utc", "min"))
    lk["first"] = lk["first"].str[:10]
    lk = lk.join(cust.set_index("customer_name")["gross_bank_receipts_czk"], how="left")
    lk.to_csv(OUT / "customers_in_mail.csv")
    src = df[df.customer.fillna("") != ""].sort_values("first_utc").groupby("customer").started_by.first()
    w(f"- First thread started by the customer: {(src == 'in').sum()}, by us: {(src == 'out').sum()}.")
    w("- Per-customer detail: `reports/customers_in_mail.csv`.\n")

    # Seasonality
    w("## 10. Seasonality (business messages per month)\n")
    bm = pd.read_sql("SELECT thread_id, direction, date_utc FROM msg", db)
    bm = bm[bm.thread_id.isin(biz.thread_id)]
    bm["month"] = pd.to_datetime(bm.date_utc, utc=True).dt.strftime("%Y-%m")
    season = bm.pivot_table(index="month", columns="direction", values="thread_id", aggfunc="size").fillna(0).astype(int)
    w(season.to_markdown() + "\n")

    (OUT / "report.md").write_text("\n".join(report))

    # Charts
    fig, ax = plt.subplots(2, 2, figsize=(12, 8))
    season.plot(kind="bar", ax=ax[0, 0], title="Business messages per month")
    bins.value_counts().sort_index().plot(kind="bar", ax=ax[0, 1], title="Business threads by messages")
    c = camp.head(12).sort_values("reply_rate_%")
    ax[1, 0].barh(c.index, c["reply_rate_%"])
    ax[1, 0].set_title("Reply rate by campaign, %")
    biz.state.value_counts().plot(kind="barh", ax=ax[1, 1], title="Business thread state")
    fig.tight_layout()
    fig.savefig(OUT / "overview.png", dpi=110)
    print((OUT / "report.md").read_text())


if __name__ == "__main__":
    main()
