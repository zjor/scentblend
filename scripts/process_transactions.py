#!/usr/bin/env python3
"""Merge Raiffeisenbank exports and refresh local financial review files."""

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import io
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CATEGORY_FIELDS = [
    "transaction_id", "transaction_date", "amount_czk", "bucket", "category",
    "customer_name", "notes",
]
REVIEW_FIELDS = [
    "transaction_id", "transaction_date", "amount_czk", "bank_type",
    "counterparty_name", "merchant_name", "description", "guess_bucket",
    "guess_customer_name", "guess_reason", "booking_datetime",
]
NORMAL_FIELDS = [
    "transaction_id", "transaction_date", "booking_datetime", "amount_czk",
    "bank_type", "counterparty_name", "merchant_name", "description",
]
RAW_FIELDS = {
    "Id transakce", "Datum provedení", "Datum zaúčtování", "Zaúčtovaná částka",
    "Měna účtu", "Typ transakce", "Název protiúčtu", "Název obchodníka",
    "Zpráva", "Poznámka",
}


def amount(value):
    number = Decimal(value.replace("\u00a0", "").replace(" ", "").replace(",", "."))
    if not number.is_finite():
        raise ValueError(f"Invalid amount: {value!r}")
    return number


def money(number):
    return format(number, "f")


def load_raw(directory):
    transactions = {}
    originals = {}
    duplicate_count = 0
    files = sorted(directory.glob("*.csv"))
    if not files:
        raise ValueError(f"No CSV exports found in {directory}")
    for path in files:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter=";")
            missing = RAW_FIELDS - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
            for line, row in enumerate(reader, 2):
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"{path}:{line}: malformed CSV row")
                txid = row["Id transakce"].strip()
                if not txid:
                    raise ValueError(f"{path}:{line}: missing transaction ID")
                if txid in originals:
                    if originals[txid] != row:
                        raise ValueError(f"{path}:{line}: conflicting export rows for {txid}")
                    duplicate_count += 1
                    continue
                if row["Měna účtu"] != "CZK":
                    raise ValueError(f"{path}:{line}: expected CZK account currency")
                description = list(dict.fromkeys(
                    row[key] for key in ("Zpráva", "Poznámka") if row[key]
                ))
                transactions[txid] = {
                    "transaction_id": txid,
                    "transaction_date": datetime.strptime(row["Datum provedení"], "%d.%m.%Y").date().isoformat(),
                    "booking_datetime": datetime.strptime(row["Datum zaúčtování"], "%d.%m.%Y %H:%M").isoformat(timespec="minutes"),
                    "amount_czk": money(amount(row["Zaúčtovaná částka"])),
                    "bank_type": row["Typ transakce"],
                    "counterparty_name": row["Název protiúčtu"],
                    "merchant_name": row["Název obchodníka"],
                    "description": " | ".join(description),
                }
                originals[txid] = row
    ordered = sorted(transactions.values(), key=lambda row: (row["transaction_date"], row["transaction_id"]))
    return ordered, len(files), duplicate_count


def load_existing(path, defaults):
    if not path.exists():
        return {}, list(defaults)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        if not set(defaults[:3]).issubset(fields):
            raise ValueError(f"{path}: missing identity/date/amount columns")
        indexed = {}
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path}: malformed CSV row")
            txid = row["transaction_id"]
            if not txid or txid in indexed:
                raise ValueError(f"{path}: missing or duplicate transaction ID {txid!r}")
            indexed[txid] = row
    return indexed, fields + [field for field in defaults if field not in fields]


def csv_text(rows, fields):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def customer_rows(categories, reviews):
    totals = {}
    for category, review in zip(categories, reviews):
        # Any explicit manual bucket supersedes the suggested classification.
        manual = bool(category.get("bucket"))
        bucket = category.get("bucket") if manual else review.get("guess_bucket")
        name = category.get("customer_name") or review.get("guess_customer_name", "")
        if bucket != "revenue" or not name:
            continue
        count, total = totals.get(name, (0, Decimal(0)))
        totals[name] = count + 1, total + amount(review["amount_czk"])
    return [
        {"customer_name": name, "transaction_count": count, "gross_bank_receipts_czk": money(total)}
        for name, (count, total) in sorted(totals.items())
    ]


def cash_report(transactions):
    months = {}
    for row in transactions:
        month = row["transaction_date"][:7]
        count, incoming, outgoing = months.get(month, (0, Decimal(0), Decimal(0)))
        value = amount(row["amount_czk"])
        months[month] = (count + 1, incoming + max(value, Decimal(0)), outgoing + min(value, Decimal(0)))
    lines = [
        "# Bank cash movements", "",
        f"Source: {len(transactions)} unique transactions from all CSV exports in `data/raw/`.",
        f"Execution dates: {transactions[0]['transaction_date']}–{transactions[-1]['transaction_date']}.",
        f"Latest booking: {max(row['booking_datetime'] for row in transactions)}.", "",
        "Months use execution dates. Coverage is limited to the supplied exports; a month may be incomplete.",
        "These are signed gross bank movements, including transfers and funding. They do not measure profit.", "",
        "| Month | Transactions | Incoming CZK | Outgoing CZK | Net CZK |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for month, (count, incoming, outgoing) in sorted(months.items()):
        lines.append(f"| {month} | {count} | {incoming:,.2f} | {outgoing:,.2f} | {incoming + outgoing:,.2f} |")
    lines += ["", "Generated by `python3 scripts/process_transactions.py --write`.", ""]
    return "\n".join(lines)


def prepare(root):
    transactions, file_count, duplicate_count = load_raw(root / "data/raw")
    if not transactions:
        raise ValueError("Exports contain no transactions")
    category_path = root / "data/categories/transactions.csv"
    review_path = root / "data/enriched/transactions.csv"
    existing_categories, category_fields = load_existing(category_path, CATEGORY_FIELDS)
    existing_reviews, review_fields = load_existing(review_path, REVIEW_FIELDS)
    ids = {row["transaction_id"] for row in transactions}
    for path, existing in ((category_path, existing_categories), (review_path, existing_reviews)):
        orphans = set(existing) - ids
        if orphans:
            raise ValueError(f"{path}: {len(orphans)} IDs absent from raw exports; restore missing exports before processing")
    categories, reviews = [], []
    for tx in transactions:
        txid = tx["transaction_id"]
        for path, existing in ((category_path, existing_categories), (review_path, existing_reviews)):
            old = existing.get(txid)
            if old and (old["transaction_date"] != tx["transaction_date"] or amount(old["amount_czk"]) != amount(tx["amount_czk"])):
                raise ValueError(f"{path}: date or amount changed for {txid}; review before importing")
        category = dict.fromkeys(category_fields, "")
        category.update(existing_categories.get(txid, {}))
        category.update({key: tx[key] for key in CATEGORY_FIELDS[:3]})
        categories.append(category)
        review = dict.fromkeys(review_fields, "")
        review.update(existing_reviews.get(txid, {}))
        review.update(tx)
        if txid not in existing_reviews:
            review["guess_reason"] = "New transaction; classification and customer need review."
        reviews.append(review)
    outputs = {
        root / "data/enriched/normalized-transactions.csv": csv_text(transactions, NORMAL_FIELDS),
        category_path: csv_text(categories, category_fields),
        review_path: csv_text(reviews, review_fields),
        root / "data/enriched/customers.csv": csv_text(customer_rows(categories, reviews), [
            "customer_name", "transaction_count", "gross_bank_receipts_czk",
        ]),
        root / "reports/cash_movements.md": cash_report(transactions),
    }
    summary = (f"{file_count} exports; {len(transactions)} unique transactions; "
               f"{duplicate_count} duplicate rows; {len(ids - set(existing_categories))} new classification rows.\n"
               f"Execution dates: {transactions[0]['transaction_date']}–{transactions[-1]['transaction_date']}.\n"
               f"Unclassified manual rows: {sum(not row['bucket'] for row in categories)}.")
    return outputs, summary


def atomic_write(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(contents)
            handle.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write generated files; default is a dry run")
    parser.add_argument("--root", type=Path, default=ROOT, help="Project directory (default: script's parent project)")
    args = parser.parse_args()
    try:
        outputs, summary = prepare(args.root.resolve())
        print(summary)
        for path, contents in outputs.items():
            if args.write:
                atomic_write(path, contents)
            print(f"{'Wrote' if args.write else 'Would write'} {path}")
    except (ValueError, InvalidOperation, OSError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
