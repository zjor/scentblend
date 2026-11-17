# Spike: communication analysis of the cooperation mailbox

- **Status:** paused on 2026-11-17 (first full analysis done; see "Status and open items")
- **Started:** 2026-11-17
- **Mailbox:** cooperation@scentblend.cz
- **YouTrack:** [TM-25](https://scentblend.youtrack.cloud/issue/TM-25)

## Goal

Understand who writes to us, about what, and what happens to each conversation. Find lost leads, slow replies and follow-up candidates. Link email threads to real revenue.

## Data

Size on 2026-11-17 (from the mail MCP `list_folders`):

| Folder | Messages |
| --- | --- |
| INBOX | 2,267 (792 unread) |
| Sent | 2,517 |

Method: export the mailbox once over IMAP into SQLite (`data/mail.sqlite`), then run all questions locally. The mail MCP is too slow for this: search returns only metadata, 100 messages per page, and has no `Message-ID` / `In-Reply-To` headers for threading.

### Export

Run from the spike folder (needs `.env`, see `.env.example`):

```bash
python3 -I scripts/mail_export.py
```

The export is read-only: unread messages stay unread. A second run fetches only new messages.

First export on 2026-11-17: INBOX 2,267 and Sent 2,517 messages, dated 2025-12-07 to 2026-11-17.

## Questions

### Basics

- Full list of contacts.
- List of distinct domains.
- First and last message date per thread.
- Histogram of threads by duration and by number of messages.

### Cleanup (do first)

- Which messages are not clients: suppliers, platforms, newsletters, notifications, spam? Split them out before any statistics.

### Speed and missed leads

- How fast do we send the first reply to an inbound email? The website promises a reply within 24 hours.
- Which inbound threads never got a reply?
- In which threads did we write last, and the other side has been silent for more than N days? These are follow-up candidates.

### Funnel and outcome

- Who started the thread: the client (inbound) or us (outreach)?
- Reply rate on our outreach, by month and by industry.
- Stage each thread reached: enquiry, proposal, quote, sample, contract, order, or lost.
- Reasons for lost deals: price, timing, no budget, competitor.
- Which contacts also appear as payers in the bank export or in `data/enriched/customer-notes.md`?

### What clients ask for

- Service line of each thread: space scenting, private label, distribution, brand experiences.
- Products and volumes mentioned (diffusers, candles, refills, ...).
- Prices and discounts we quoted, and which quotes were accepted.

### Who the clients are

- Industry of each contact or client.
- Company domain vs free mail (gmail, seznam, ...).
- Country and language (domain TLD, email language).
- Repeat clients: threads per company over time.
- Number of people per company in the threads.

### Segmentation

- Cluster threads by industry.
- Cluster threads by state: alive, dead, waiting for our reply, waiting for their reply.

### Seasonality

- Inbound and outbound messages per week and per month. Peaks (for example before Christmas)?

### Handoff to sales (added 2026-11-17)

- When does a lead move from cooperation@ to the salesperson, and how long does it take?
- Which leads stop after the handoff?
- Which funnel stages happen in which channel (cooperation@, the salesperson's mailbox, WhatsApp)?

Only the cooperation@ side is visible (see Limits). We can see when the salesperson is put in copy or a lead is forwarded, but not what happens after that.

## Pipeline

Run from the spike folder:

```bash
python3 -I scripts/mail_export.py    # IMAP -> data/mail.sqlite (incremental)
python3 -I scripts/build_threads.py  # threads + per-message direction
python3 -I scripts/analyze.py        # reports/report.md, reports/*.csv, reports/overview.png
```

`data/labels.csv` maps domains and addresses to a role (noise, supplier, service, media, prospect), an industry and a paying customer. It covers all 275 domains that ever wrote to us. Outreach targets get their industry from the campaign template (subject line).

Stage, service line and decline reasons come from keyword rules on the message text without quoted parts. Treat them as estimates.

## Findings (2026-11-17)

Full tables: `reports/report.md`. Lists to act on: `reports/follow_up.csv`, `reports/unanswered_inbound.csv`.

### Mailbox composition

- 2,233 threads. Only about half are business: 1,156 prospect/client threads and 14 media threads.
- The rest is suppliers (510 threads), notifications and newsletters (459), and service providers (83).

### Outreach is most of the business mail, and it converts poorly

- 1,097 outreach threads. 45 bounced. 113 got a human reply, which is 10.7% of the delivered emails.
- CZ real estate got 543 emails (half of all outreach) and a 6.6% reply rate. Most replies are "not interested".
- The worst segments are EU car dealers (1.6%), French marketing agencies (3.6%) and Prague HoReCa (4.3%). CH real estate (21 emails) and AT/HU resorts (5 emails) got no replies.
- The best segments are small: fuel stations (3 of 8 replied), In-Cosmetics fair contacts (19%) and CZ car wash (10%, with several orders).
- Decline reasons in replies: not interested 23, forwarded or not the decision maker 17, "not now" 16, price 2, already have a supplier 1.

### Inbound leads are few but valuable

- 34 inbound prospect threads and 10 web form enquiries.
- When we reply, we are fast: median first reply 2.2 h, and 82% within 24 h. Web form enquiries get a median reply in 17 h.
- 14 inbound prospect threads have no reply from this mailbox. Some may have been answered by phone or from another address, so check them by hand.

### Link to revenue

- 11 of 16 paying customers in the bank export appear in the mailbox.
- At least 4 started from an inbound enquiry and 4 from our outreach. For 3 the origin is unclear.
- Of the 522 CZ real estate outreach emails, 1 thread became a paying customer.

### Thread state (business threads)

- 939 got no reply and 44 bounced.
- 60 are waiting for our reply. 13 of them had their last message in the last 30 days. Many older ones are probably closed in another channel.
- 10 are waiting for the other side and need a follow-up. 18 were declined. 47 are dead (no activity for more than 60 days).

### What people talk about (engaged threads)

- Space scenting 110, private label 97, gifts 44, brand experiences 39, distribution 7.
- 43 of 168 engaged threads are with free-mail addresses: small businesses and private persons. This group has the most "order" stage threads (18).
- Almost all engaged counterparties are Czech (.cz 101, .com 59). Outreach abroad produced almost nothing.

### Seasonality

- Outbound mail peaks in February–March (outreach to real estate) and July (resorts and car wash).
- Inbound business mail grows from about 35 per month in H1 to 70–80 per month in July–September.

### Limits

- **cooperation@ is the top of the funnel, not the whole funnel.** Team members also write from personal addresses. The salesperson handles invoices and contracts from a personal Gmail mailbox, and this mailbox will not be available. So conversion, order and contract counts, and the "waiting for us" lists are lower limits. Outreach reply rates, the segment ranking, bounce rates and first reply speed stay valid.
- The data covers one year (2025-12-07 to 2026-11-17).
- Replies made by phone, WhatsApp or from personal mailboxes are not visible. This includes the salesperson's own Gmail mailbox: we see only the 25 messages that went through this mailbox.
- Stage detection is keyword-based. "order" also matches invoices and payment talk.

## Status and open items

**2026-11-17 — paused.** First full analysis is done. Findings above are current.

Done:

- IMAP export, threading, rule-based classification, report (`reports/report.md`).
- Internal addresses confirmed with the owner and labeled in `data/labels.csv` (local only): the salesperson (1 Gmail address) and IT support (3 Gmail addresses). One supplier uses a Gmail address too.
- The salesperson's mailbox will not be shared, so the funnel stays a lower limit.

Open, when the spike resumes:

1. Team list: map each team member to all their addresses. Count a reply from any team address as "our reply" and a forward or copy to the salesperson as a handoff.
2. Find out why "waiting for us" stayed at 60 after the last IT address was marked internal (expected 59).
3. Measure the handoff from the cooperation@ side: leads forwarded or copied to the salesperson, and the time until then.
4. Re-run the export to add new mail (`scripts/mail_export.py` is incremental).
5. Decide which low-yield campaigns to stop (EU car dealers, FR agencies, CH real estate).
