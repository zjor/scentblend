#!/usr/bin/env python3
"""Project CZK cash sensitivity from bank history and existing revenue scenarios."""

import argparse
import calendar
import csv
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import io
import json
from pathlib import Path
import sys

import build_reports
import process_transactions as process


ZERO = Decimal(0)
CENT = Decimal("0.01")


def rounded(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def expense_reference(rows, month):
    """Budget all spending once, including unresolved amounts and tax settlements."""
    reference = [row for row in rows if row["transaction_date"].startswith(month)]
    if not reference:
        raise ValueError(f"No bank transactions in expense reference month {month}")
    return -sum((process.amount(row["amount_czk"]) for row in reference
                 if process.amount(row["amount_czk"]) < 0
                 and row["bucket"] not in {"transfer", "owner", "financing"}), ZERO)


def project(rows, revenue, assumptions):
    opening = process.amount(assumptions["opening_balance_czk"])
    cutoff = max(date.fromisoformat(row["transaction_date"]) for row in rows)
    actual_balance = opening + sum((process.amount(row["amount_czk"]) for row in rows), ZERO)
    monthly_expense = expense_reference(rows, assumptions["expense_reference_month"])
    end = date.fromisoformat(assumptions["projection_end"])
    if end <= cutoff:
        raise ValueError("Projection end must be after bank cutoff")
    balance = {scenario: rounded(actual_balance) for scenario in ("pessimistic", "optimistic")}
    start = cutoff + timedelta(days=1)
    result = []
    while start <= end:
        month_end = date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
        period_end = min(month_end, end)
        fraction = Decimal((period_end - start).days + 1) / Decimal(month_end.day)
        quarter = f"{start.year}Q{(start.month - 1) // 3 + 1}"
        if quarter not in revenue:
            raise ValueError(f"Missing revenue assumptions for {quarter}")
        for scenario in balance:
            incoming = rounded(process.amount(revenue[quarter][scenario + "_czk"]) / 3 * fraction)
            eur = rounded(process.amount(revenue[quarter][scenario + "_eur"]) / 3 * fraction)
            spending = rounded(monthly_expense * fraction)
            beginning = balance[scenario]
            net = incoming - spending
            balance[scenario] += net
            result.append(dict(
                period_start=start.isoformat(), period_end=period_end.isoformat(), scenario=scenario,
                opening_balance_czk=process.money(beginning), projected_receipts_czk=process.money(incoming),
                projected_outflows_czk=process.money(spending), projected_net_czk=process.money(net),
                closing_balance_czk=process.money(balance[scenario]),
                minimum_top_up_for_nonnegative_closing_czk=process.money(max(ZERO, -balance[scenario])),
                separate_projected_receipts_eur=process.money(eur),
            ))
        start = month_end + timedelta(days=1)
    return result, actual_balance, monthly_expense, cutoff


def report(rows, balance, expense, cutoff, assumptions):
    lines = ["# Monthly cash-flow sensitivity", "",
             f"User-confirmed opening balance before the imported history: **{process.amount(assumptions['opening_balance_czk']):,.2f} CZK**.",
             f"Calculated bank balance through **{cutoff.isoformat()}: {balance:,.2f} CZK**. This assumes the exports contain every movement since the zero opening balance; it is not a live bank balance.", "",
             "## Model assumptions", "",
             "- Uses the existing pessimistic/as-is and optimistic quarterly revenue scenarios as a receipt run rate, spread evenly across three months. This conversion to cash timing is an unverified modeling assumption; VAT basis and actual billing/collection schedules are unknown.",
             f"- Monthly outflows are fixed at **{expense:,.2f} CZK**, the gross negative bank payments in **{assumptions['expense_reference_month']}** excluding transfers, director funding, and loan principal. This includes unresolved purchases, taxes, and other payments without treating them as accounting expenses.",
             "- The same spending budget is used in both revenue cases. It is a sensitivity estimate: one-off purchases may overstate repeat spending, while expansion costs may be understated. Replace this budget with invoice, payroll, tax, and inventory plans when available.",
             "- Projection starts the day after the bank cutoff. Partial months prorate the monthly revenue and spending budgets by remaining calendar days; earlier actuals are already in the starting balance.",
             "- Future owner funding, loans, transfers, and currency conversions are zero in the model. Actual transfers remain included in the historical balance.",
             "- EUR projected receipts are shown separately with no conversion and no EUR opening balance assumed. The CZK path excludes them, so a negative CZK balance is a modeled CZK shortfall, not a complete business liquidity forecast.",
             "- No future receipts from the tentative other-product income are assumed beyond existing commercial revenue assumptions.", "",
             "## Projected CZK closing balances", "",
             "| Period | As-is CZK | Optimistic CZK | As-is receipts EUR | Optimistic receipts EUR |",
             "| --- | ---: | ---: | ---: | ---: |"]
    grouped = {}
    for row in rows:
        grouped.setdefault((row['period_start'], row['period_end']), {})[row['scenario']] = row
    for (start, end), scenarios in grouped.items():
        low, high = scenarios["pessimistic"], scenarios["optimistic"]
        values = [low['closing_balance_czk'], high['closing_balance_czk'], low['separate_projected_receipts_eur'], high['separate_projected_receipts_eur']]
        lines.append(f"| {start}–{end} | " + " | ".join(f"{process.amount(v):,.2f}" for v in values) + " |")
    lines += ["", "## Modeled funding gap", ""]
    for scenario in ("pessimistic", "optimistic"):
        scenario_rows = [row for row in rows if row['scenario'] == scenario]
        first = next((row for row in scenario_rows if process.amount(row['closing_balance_czk']) < 0), None)
        shortfall = max(process.amount(row['minimum_top_up_for_nonnegative_closing_czk']) for row in scenario_rows)
        lines.append(f"- {scenario.capitalize()}: " + (f"first negative projected closing balance at {first['period_end']}; maximum cumulative CZK gap **{shortfall:,.2f} CZK**." if first else "no negative projected closing balances."))
    lines += ["", "Funding gaps measure the minimum single opening top-up to keep modeled period-end CZK balances nonnegative, excluding EUR conversion. Intramonth payment timing may require more cash.", "",
              "Inputs: `cashflow-assumptions.json`, current transaction classifications, and `forecast-assumptions.csv`. Detailed period calculations are in `data/enriched/cashflow-monthly.csv`.",
              "Generated by `python3 scripts/project_cashflow.py --write`.", ""]
    return "\n".join(lines)


def prepare(root):
    assumptions = json.loads((root / "data/enriched/cashflow-assumptions.json").read_text())
    generated = build_reports.prepare(root)
    rows = list(csv.DictReader(io.StringIO(generated[root / "data/enriched/effective-transactions.csv"])))
    revenue_rows = csv.DictReader(io.StringIO(generated[root / "data/enriched/forecast-summary.csv"]))
    revenue = {row['period']: row for row in revenue_rows if "Q" in row['period']}
    projection, balance, expense, cutoff = project(rows, revenue, assumptions)
    return {
        root / "data/enriched/cashflow-monthly.csv": process.csv_text(projection, list(projection[0])),
        root / "reports/cashflow-projection.md": report(projection, balance, expense, cutoff, assumptions),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write projection; default is a dry run")
    parser.add_argument("--root", type=Path, default=process.ROOT)
    args = parser.parse_args()
    try:
        for path, contents in prepare(args.root.resolve()).items():
            if args.write:
                process.atomic_write(path, contents)
            print(f"{'Wrote' if args.write else 'Would write'} {path}")
    except (ValueError, InvalidOperation, OSError, KeyError, csv.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
