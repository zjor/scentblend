#!/usr/bin/env python3
"""Suggest classifications for newly imported rows, without confirming them."""

import argparse
from collections import Counter
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sys
import unicodedata

import process_transactions as process


PENDING = "New transaction; classification and customer need review."


def folded(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))


def suggest(row, raw, customers, directors=(), reversals=()):
    value = process.amount(row["amount_czk"])
    bank_type = folded(row["bank_type"])
    payer = folded(row["counterparty_name"])
    text = folded(" ".join(row.get(k, "") for k in ("merchant_name", "description")))

    def result(bucket, category, reason, customer=""):
        return dict(guess_bucket=bucket, guess_category=category,
                    guess_customer_name=customer, guess_reason=reason)

    if "jistiny" in bank_type:
        return result("financing", "loan_principal", "Bank transaction type identifies loan principal; not sales or an operating payment.")
    if bank_type == "konverze":
        return result("transfer", "currency_conversion", "Bank transaction type identifies a currency conversion; reconcile the other currency account.")
    if "vyber" in bank_type and "bankomatu" in bank_type:
        return result("transfer", "cash_withdrawal", "ATM withdrawal; spending from this cash requires separate records.")
    if "vklad jednatele" in text and value > 0:
        return result("owner", "director_contribution", "Incoming payment explicitly says director contribution; confirm equity versus director loan.")
    if payer in directors:
        return result("", "", "Director movement; confirm salary, reimbursement, funding, or loan settlement before classifying.")
    if "scent blend" in payer:
        return result("transfer", "own_account", "Counterparty name is the same company; reconcile the other account.")
    if "stripe" in payer:
        return result("", "", "Processor payout; obtain settlement detail for gross sales, fees, refunds, and customer allocation.")
    if row["transaction_id"] in reversals:
        return result("", "", "Equal opposite bank movement on the same counterparty account has a reversal note; reconcile the possible reversed payment before assigning a bucket.")
    if value > 0:
        if payer in customers:
            return result("revenue", "customer_receipt", "Same named payer as an existing suggested customer receipt; confirm invoice and VAT.", customers[payer])
        if raw.get("VS") and payer and "bank" not in payer:
            return result("revenue", "customer_receipt", f"Named payer and bank variable symbol {raw['VS']} suggest an invoice receipt; customer identity, invoice, and VAT remain unverified.", row["counterparty_name"])
        return result("", "", "Receipt has insufficient customer evidence; identify the original payer and invoice or other purpose.")
    if bank_type == "vedeni uctu":
        return result("opex", "bank_fees", "Bank transaction type identifies an account maintenance fee.")
    if "financni sprava" in text or "fú" in row.get("description", "").casefold():
        return result("", "", "Tax authority payment; identify tax type and period before choosing VAT, income tax, payroll withholding, or another treatment.")
    if any(term in text for term in ("socialni", "vzp", "sprava socialniho")):
        return result("", "", "Social or health insurance payment; payroll records must distinguish employer expense from withheld employee amounts and settlement of liabilities.")
    for term, category, reason in (
        ("ucetni", "accounting", "Payment note identifies accounting services; confirm invoice and service period."),
        ("spotrebu elektriny", "utilities", "Payment note identifies electricity; confirm invoice and consumption period."),
        ("fakturoid", "software", "Invoicing software merchant; confirm invoice and VAT."),
        ("t-mobile", "telecommunications", "Telecommunications merchant; confirm invoice and business allocation."),
        ("stehovaci sluzba", "moving", "Payment note identifies moving services; confirm business purpose and invoice."),
    ):
        if term in text:
            return result("opex", category, reason)
    if any(term in text for term in ("ppl", "dhl", "gls")):
        return result("", "shipping", "Shipping payment; identify the shipment and decide direct delivery cost versus general operations.")
    if any(term in text + " " + payer for term in (
        "candle shack", "alibaba", "flash style", "suroviny", "awgifts", "aroma global",
    )):
        return result("", "materials_review", "Possible production or stock purchase; invoice contents and inventory use are needed before assigning COGS, OPEX, or CAPEX.")
    if any(term in text for term in ("bolt", "easyjet", "omv", "shell", "tank ono", "orlen", "mol 678")):
        return result("", "travel_review", "Travel or fuel merchant; confirm business purpose, trip, receipts, and any private allocation.")
    return result("", "", "Bank description alone does not establish business purpose or accounting treatment; obtain receipt or invoice.")


def review_report(reviews, categories):
    counts = Counter()
    unresolved = []
    for row in reviews:
        manual = categories[row["transaction_id"]]
        bucket = manual.get("bucket") or row.get("guess_bucket") or "unresolved"
        counts[bucket] += 1
        if bucket == "unresolved":
            unresolved.append(row)
    lines = ["# Transaction classification review", "",
             "Suggestions use bank descriptions and existing customer suggestions. They are unconfirmed; manual classifications remain in `data/categories/transactions.csv`.",
             "Manual buckets override suggestions. Customer receipt amounts are gross bank amounts; no VAT or recognition-period adjustment has been made.", "",
             "| Bucket (manual or suggested) | Transactions |", "| --- | ---: |"]
    lines += [f"| {bucket} | {count} |" for bucket, count in sorted(counts.items())]
    lines += ["", "## Unresolved transactions", "",
              "A blank bucket keeps the transaction out of classified P&L lines. Review invoices, payroll, settlements, or cash records as specified below.", "",
              "| ID | Execution date | Amount CZK | Counterparty / merchant | Review needed |",
              "| --- | --- | ---: | --- | --- |"]
    for row in unresolved:
        label = row["counterparty_name"] or row["merchant_name"] or row["description"]
        cells = [row["transaction_id"], row["transaction_date"], row["amount_czk"], label, row["guess_reason"]]
        lines.append("| " + " | ".join(cell.replace("|", "/").replace("\n", " ") for cell in cells) + " |")
    lines += ["", "## Follow-up", "",
              "- Match new customer receipts to invoices before marking open invoices paid or changing forecast assumptions.",
              "- Keep different payer names separate unless invoices or the customer registry establish a shared entity.",
              "- Reconcile possible reversed payments in the table; equal bank amounts alone do not establish their original purpose.",
              "- Obtain tax account details, payroll records, and director movement explanations for unresolved settlements.", ""]
    return "\n".join(lines)


def prepare(root):
    reviews, fields = process.load_existing(root / "data/enriched/transactions.csv", process.REVIEW_FIELDS)
    categories, _ = process.load_existing(root / "data/categories/transactions.csv", process.CATEGORY_FIELDS)
    if not reviews or set(reviews) != set(categories):
        raise ValueError("Run process_transactions.py --write first; review and classification IDs must match")
    if "guess_category" not in fields:
        fields.append("guess_category")
    raw_by_id = {}
    # Validate raw duplicates and schema before consulting variable symbols.
    normalized, _, _ = process.load_raw(root / "data/raw")
    if {row['transaction_id'] for row in normalized} != set(reviews):
        raise ValueError("Raw export IDs differ from review IDs; run the import first")
    for path in sorted((root / "data/raw").glob("*.csv")):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            raw_by_id.update((row["Id transakce"], row) for row in csv.DictReader(handle, delimiter=";"))
    directors = {folded(row['counterparty_name']) for row in reviews.values()
                 if row['guess_bucket'] == 'owner' and row['counterparty_name']}
    reversals = set()
    for txid, raw in raw_by_id.items():
        if "storno" not in folded(raw.get("Zpráva", "") + " " + raw.get("Poznámka", "")):
            continue
        account = raw.get("Číslo protiúčtu")
        if not account:
            continue
        matches = [other_id for other_id, other in raw_by_id.items()
                   if other_id != txid and other.get("Číslo protiúčtu") == account
                   and process.amount(other["Zaúčtovaná částka"]) == -process.amount(raw["Zaúčtovaná částka"])]
        if len(matches) == 1:
            reversals.update((txid, matches[0]))
    names = {}
    for row in reviews.values():
        if row["guess_bucket"] == "revenue" and row["guess_customer_name"] and row["counterparty_name"]:
            key = folded(row["counterparty_name"])
            if key in names and names[key] != row["guess_customer_name"]:
                raise ValueError(f"Conflicting suggested customer identities for {key}")
            names[key] = row["guess_customer_name"]
    updated = 0
    for txid, row in reviews.items():
        row.setdefault("guess_category", "")
        if row["guess_reason"] == PENDING and not categories[txid]["bucket"]:
            row.update(suggest(row, raw_by_id[txid], names, directors, reversals))
            updated += 1
    rows = list(reviews.values())
    outputs = {
        root / "data/enriched/transactions.csv": process.csv_text(rows, fields),
        root / "data/enriched/customers.csv": process.csv_text(process.customer_rows(
            [categories[row["transaction_id"]] for row in rows], rows),
            ["customer_name", "transaction_count", "gross_bank_receipts_czk"]),
        root / "reports/classification_review.md": review_report(rows, categories),
    }
    return outputs, updated, Counter(row["guess_bucket"] or "unresolved" for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Apply suggestions; default is a dry run")
    parser.add_argument("--root", type=Path, default=process.ROOT)
    args = parser.parse_args()
    try:
        outputs, updated, counts = prepare(args.root.resolve())
        print(f"Reviewed {updated} newly imported rows. Suggested bucket totals: {dict(sorted(counts.items()))}")
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
