#!/usr/bin/env python3
"""Build provisional financial reports using current manual and suggested treatment."""

import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sys

import process_transactions as process
from suggest_classifications import folded


ZERO = Decimal(0)
PNL_BUCKETS = {"revenue", "cogs", "opex", "other_income", "other_expense"}
EXCLUDED_BUCKETS = {"transfer", "owner", "financing", "capex", "vat", "income_tax"}


def effective_rows(reviews, categories):
    if set(reviews) != set(categories):
        raise ValueError("Transaction and classification IDs differ; run the import first")
    rows = []
    for txid, review in reviews.items():
        manual = categories[txid]
        if manual["transaction_date"] != review["transaction_date"] or process.amount(manual["amount_czk"]) != process.amount(review["amount_czk"]):
            raise ValueError(f"Classification date/amount differs for {txid}")
        is_manual = bool(manual["bucket"])
        bucket = manual["bucket"] if is_manual else review["guess_bucket"]
        if bucket and bucket not in PNL_BUCKETS | EXCLUDED_BUCKETS:
            raise ValueError(f"Unknown bucket {bucket!r} for {txid}")
        category = manual["category"] if is_manual else review.get("guess_category", "")
        # Older suggestions predate guess_category. Derive presentation labels only.
        if bucket == "opex" and not category:
            text = folded(review["merchant_name"] + " " + review["description"])
            for term, label in (("najem", "rent"), ("marketing", "marketing"),
                                ("zamkina", "marketing"), ("easypark", "parking"),
                                ("fakturoid", "software"), ("elektr", "utilities")):
                if term in text:
                    category = label
                    break
        rows.append(dict(
            transaction_id=txid, transaction_date=review["transaction_date"],
            booking_datetime=review["booking_datetime"], amount_czk=review["amount_czk"],
            bucket=bucket, category=category,
            customer_name=manual.get("customer_name") or review["guess_customer_name"],
            classification_source="manual" if is_manual else "suggested" if bucket else "unresolved",
            notes=manual["notes"] if is_manual else review["guess_reason"],
        ))
    return sorted(rows, key=lambda r: (r["transaction_date"], r["transaction_id"]))


def pnl_report(rows):
    months = sorted({r["transaction_date"][:7] for r in rows})
    sums = defaultdict(lambda: defaultdict(lambda: ZERO))
    for row in rows:
        month = row["transaction_date"][:7]
        value = process.amount(row["amount_czk"])
        bucket = row["bucket"] or ("unresolved_in" if value >= 0 else "unresolved_out")
        sums[bucket][month] += value
        sums["bank"][month] += value
        if bucket in PNL_BUCKETS:
            sums["subtotal"][month] += value
        if bucket == "opex":
            sums["opex:" + (row["category"] or "other")][month] += value
    for month in months:
        reconciled = sum((sums[k][month] for k in EXCLUDED_BUCKETS | {"subtotal", "unresolved_in", "unresolved_out"}), ZERO)
        if reconciled != sums["bank"][month]:
            raise ValueError(f"P&L reconciliation failed for {month}")
    sources = Counter(r["classification_source"] for r in rows)
    lines = ["# Provisional P&L view — Scent Blend", "",
             f"Source: {len(rows)} unique bank transactions, executed {rows[0]['transaction_date']}–{rows[-1]['transaction_date']}.",
             "Amounts are signed gross CZK bank movements grouped by execution month. Coverage is limited to supplied exports; first and last months may be incomplete.",
             f"Classification basis: {sources['manual']} manually classified rows, {sources['suggested']} suggested rows, and {sources['unresolved']} unresolved rows. Manual treatment takes precedence; manual notes retain provisional user assumptions.", "",
             "## Classified cash proxy", "",
             "| CZK | " + " | ".join(months) + " | Total |",
             "| --- | " + " | ".join(["---:"] * (len(months) + 1)) + " |"]

    def add(label, key):
        values = [sums[key][month] for month in months]
        lines.append("| " + label + " | " + " | ".join(f"{v:,.2f}" for v in values + [sum(values, ZERO)]) + " |")

    def pending(label):
        lines.append("| " + label + " | " + " | ".join(["pending"] * (len(months) + 1)) + " |")

    add("Customer / product receipts (`revenue`)", "revenue")
    pending("Complete COGS / inventory adjustment")
    if any(r["bucket"] == "cogs" for r in rows):
        add("Identified direct payments (`cogs`)", "cogs")
    pending("Gross profit")
    for key in sorted(k for k in sums if k.startswith("opex:")):
        add(key.split(":", 1)[1].replace("_", " ").capitalize(), key)
    add("**Identified operating payments (`opex`)**", "opex")
    add("Other income", "other_income")
    add("Other expense", "other_expense")
    for label in ("EBITDA", "Depreciation and amortization", "Operating profit", "Net profit"):
        pending(label)
    add("**Memo: classified cash subtotal**", "subtotal")
    lines += ["", "This subtotal is not profit. Unclassified purchases, payroll liabilities, VAT, inventory use, unpaid invoices, depreciation, and recognition periods remain unresolved. Salary lines show bank-paid amounts, not gross payroll expense.", "",
              "## Reconciliation to the bank account", "",
              "| CZK | " + " | ".join(months) + " | Total |",
              "| --- | " + " | ".join(["---:"] * (len(months) + 1)) + " |"]
    add("Classified cash subtotal", "subtotal")
    for bucket in sorted(EXCLUDED_BUCKETS):
        add(bucket.replace("_", " ").capitalize(), bucket)
    add("Unresolved incoming movements", "unresolved_in")
    add("Unresolved outgoing movements", "unresolved_out")
    add("**Net bank movement**", "bank")
    lines += ["", "Every month reconciles exactly to all imported bank movements. VAT and tax rows above represent classified cash settlements only; missing amounts remain unresolved.", "",
              "## Current assumptions and remaining work", "",
              "Manually classified transactions (including provisional user treatment):", "",
              "| ID | Date | CZK | Treatment | Basis |", "| --- | --- | ---: | --- | --- |"]
    for row in rows:
        if row["classification_source"] == "manual":
            notes = row["notes"].replace("|", "/").replace("\n", " ")
            lines.append(f"| {row['transaction_id']} | {row['transaction_date']} | {row['amount_czk']} | {row['bucket']} / {row['category']} | {notes} |")
    lines += ["", "The revenue line also includes tentative product-income suggestions. Named customer totals omit receipts with no customer assigned; see `customer_receipts.md` for this reconciliation.",
              "Review unresolved transactions in `classification_review.md`. Match invoices and processor settlements; identify tax and payroll liabilities, cash spending, other-account movements, purchase use, and the periods for revenue and costs.", "",
              "Generated by `python3 scripts/build_reports.py --write` using current classifications and suggestions.", ""]
    return "\n".join(lines)


def forecasts(root):
    with (root / "data/enriched/forecast-assumptions.csv").open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        periods = [field.removeprefix("optimistic_") for field in reader.fieldnames if field.startswith("optimistic_")]
        assumptions = list(reader)
    if not assumptions or not periods:
        raise ValueError("Forecast assumptions are empty or lack quarter columns")
    quarterly = []
    totals = defaultdict(lambda: defaultdict(lambda: ZERO))
    seen = set()
    for row in assumptions:
        identity = (row["customer_name"], row["stream"], row["currency"])
        if identity in seen or row["currency"] not in {"CZK", "EUR"}:
            raise ValueError(f"Duplicate forecast stream or unsupported currency: {identity}")
        seen.add(identity)
    for period in periods:
        for row in assumptions:
            pessimistic = process.amount(row["pessimistic_per_quarter"])
            optimistic = process.amount(row["optimistic_" + period])
            quarterly.append(dict(quarter=period, customer_name=row["customer_name"], stream=row["stream"],
                                  currency=row["currency"], pessimistic_amount=process.money(pessimistic), optimistic_amount=process.money(optimistic)))
            for scenario, value in (("pessimistic", pessimistic), ("optimistic", optimistic)):
                key = scenario + "_" + row["currency"].lower()
                totals[period][key] += value
    fields = ["pessimistic_czk", "optimistic_czk", "pessimistic_eur", "optimistic_eur"]
    summary = [dict(period=period, **{key: process.money(totals[period][key]) for key in fields}) for period in periods]
    for year in sorted({period[:4] for period in periods}):
        quarters = [period for period in periods if period.startswith(year)]
        if set(quarters) == {year + "Q" + str(q) for q in range(1, 5)}:
            summary.append(dict(period=year + "_TOTAL", **{key: process.money(sum((totals[q][key] for q in quarters), ZERO)) for key in fields}))
    return {
        root / "data/enriched/forecast-quarterly.csv": process.csv_text(quarterly, ["quarter", "customer_name", "stream", "currency", "pessimistic_amount", "optimistic_amount"]),
        root / "data/enriched/forecast-summary.csv": process.csv_text(summary, ["period"] + fields),
    }, assumptions


def customer_report(rows, assumptions):
    quarters = sorted({row["transaction_date"][:4] + "Q" + str((int(row["transaction_date"][5:7]) - 1) // 3 + 1) for row in rows})
    receipts = defaultdict(lambda: defaultdict(lambda: ZERO))
    for row in rows:
        if row["bucket"] == "revenue":
            quarter = row["transaction_date"][:4] + "Q" + str((int(row["transaction_date"][5:7]) - 1) // 3 + 1)
            receipts[row["customer_name"] or "[Unallocated product income]"][quarter] += process.amount(row["amount_czk"])
    forecast_names = {row["customer_name"] for row in assumptions}
    lines = ["# Customer receipt and forecast review", "",
             f"Bank execution coverage: {rows[0]['transaction_date']}–{rows[-1]['transaction_date']}. These are partial-quarter gross receipts, not recognized revenue or full-quarter results.",
             "Receipts use manual buckets first, otherwise suggestions. Forecast scenarios retain the existing commercial assumptions and stated currencies. They have not been fitted to bank receipts.", "",
             "| Customer / allocation | " + " | ".join(q + " CZK" for q in quarters) + " | Exact name in forecast assumptions |",
             "| --- | " + " | ".join(["---:"] * len(quarters)) + " | --- |"]
    for name, amounts in sorted(receipts.items()):
        lines.append("| " + name.replace("|", "/") + " | " + " | ".join(f"{amounts[q]:,.2f}" for q in quarters) + " | " + ("yes" if name in forecast_names else "no; verify identity or recurring terms") + " |")
    lines += ["| **Total classified receipts** | " + " | ".join(f"{sum((amounts[q] for amounts in receipts.values()), ZERO):,.2f}" for q in quarters) + " | |", "",
              "## Forecast treatment", "",
              "- New receipts do not establish a recurring contract, billing interval, net-of-VAT amount, or incremental forecast revenue.",
              "- Similar payer names remain separate pending invoice or registry confirmation. Exact-name matches show identity overlap only.",
              "- A receipt from a customer with an open invoice does not close that invoice until its reference and amount are reconciled.",
              "- Unallocated product income remains a tentative revenue suggestion and is omitted from named customer totals.",
              "- Forecast CSVs are rebuilt from `forecast-assumptions.csv`; commercial assumptions and customer profiles remain unchanged pending supporting evidence.", ""]
    return "\n".join(lines)


def prepare(root):
    reviews, _ = process.load_existing(root / "data/enriched/transactions.csv", process.REVIEW_FIELDS)
    categories, _ = process.load_existing(root / "data/categories/transactions.csv", process.CATEGORY_FIELDS)
    if not reviews:
        raise ValueError("No transactions to report; run the import first")
    # Catch newly added exports and changed bank facts before generating stale reports.
    imported, _ = process.prepare(root)
    review_path = root / "data/enriched/transactions.csv"
    with review_path.open(encoding="utf-8-sig", newline="") as handle:
        if imported[review_path] != handle.read():
            raise ValueError("Transaction review file needs refreshing; run the import first")
    rows = effective_rows(reviews, categories)
    outputs, assumptions = forecasts(root)
    outputs.update({
        root / "data/enriched/effective-transactions.csv": process.csv_text(rows, list(rows[0])),
        root / "reports/pnl_provisional.md": pnl_report(rows),
        root / "reports/customer_receipts.md": customer_report(rows, assumptions),
    })
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write reports; default is a dry run")
    parser.add_argument("--root", type=Path, default=process.ROOT)
    args = parser.parse_args()
    try:
        outputs = prepare(args.root.resolve())
        for path, contents in outputs.items():
            if args.write:
                process.atomic_write(path, contents)
            print(f"{'Wrote' if args.write else 'Would write'} {path}")
    except (ValueError, InvalidOperation, OSError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
