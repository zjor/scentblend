#!/usr/bin/env python3
"""Model future optimistic operating value from an annualised revenue pace."""

import argparse
import csv
from decimal import Decimal, InvalidOperation
import io
import json
from pathlib import Path
import sys

import build_reports
import process_transactions as process


def calculate(quarter, settings):
    fx = process.amount(settings["eur_czk"])
    growth = process.amount(settings["annual_growth_after_base_year"])
    margin = process.amount(settings["ebitda_margin"])
    multiple = process.amount(settings["ebitda_multiple"])
    base_year = int(quarter["period"][:4])
    end_year = int(settings["end_year"])
    if (not quarter["period"].endswith("Q4") or end_year < base_year or fx <= 0
            or growth <= -1 or not 0 <= margin <= 1 or multiple <= 0):
        raise ValueError("Invalid base quarter, horizon, exchange rate, growth, margin, or multiple")
    czk = process.amount(quarter["optimistic_czk"]) * 4
    eur = process.amount(quarter["optimistic_eur"]) * 4
    rows = []
    for year in range(base_year, end_year + 1):
        factor = (1 + growth) ** (year - base_year)
        revenue = (czk + eur * fx) * factor
        ebitda = revenue * margin
        rows.append(dict(
            year_end=str(year), annualised_revenue_czk=process.money(czk * factor),
            annualised_revenue_eur=process.money(eur * factor), assumed_eur_czk=process.money(fx),
            combined_annualised_revenue_czk=process.money(revenue),
            assumed_ebitda_margin=process.money(margin), annualised_ebitda_czk=process.money(ebitda),
            assumed_ebitda_multiple=process.money(multiple), enterprise_value_czk=process.money(ebitda * multiple),
        ))
    return rows


def report(rows, settings, actual_year):
    first, last = rows[0], rows[-1]
    final_revenue = process.amount(last["combined_annualised_revenue_czk"])
    fx = process.amount(settings["eur_czk"])
    actual_total = process.amount(actual_year["optimistic_czk"]) + process.amount(actual_year["optimistic_eur"]) * fx
    lines = ["# Optimistic business valuation through 2030", "",
             f"Central modeled operating value at the end of {last['year_end']}: **{process.amount(last['enterprise_value_czk']):,.0f} CZK**.",
             "This is a conditional future enterprise value based on annualised year-end earnings. It is not today's value, a guaranteed sale price, shareholder net worth, or a full-calendar-year revenue forecast.", "",
             "## Assumptions", "",
             f"- The existing optimistic {settings['base_quarter']} plan is fully achieved and sustainable. Annualising that quarter gives {process.amount(first['annualised_revenue_czk']):,.2f} CZK plus {process.amount(first['annualised_revenue_eur']):,.2f} EUR of annual revenue pace.",
             f"- Constant illustrative exchange rate: {fx} CZK/EUR. Combined annualised starting pace: **{process.amount(first['combined_annualised_revenue_czk']):,.2f} CZK**.",
             f"- Annual revenue pace grows {process.amount(settings['annual_growth_after_base_year']):.0%} per year after {first['year_end']}; this is a new modeling assumption, not a contracted sales plan.",
             f"- Sustainable EBITDA margin: {process.amount(settings['ebitda_margin']):.0%}, after materials, production, shipping, payroll (including market-rate replacement of owner work), rent, selling costs, and administration. Expansion costs must fit within this margin; no fixed historical spending budget is used.",
             f"- Earnings multiple: {settings['ebitda_multiple']} times annualised EBITDA. This is an illustrative assumption, not a verified Czech comparable-sale multiple. A buyer may instead price trailing earnings or apply a discount to the year-end run rate.",
             "- Commercial amounts have unresolved VAT treatment. For this sensitivity, input amounts are assumed to be usable net sales equivalents; remove VAT wherever included before treating the result as a valuation.",
             "- Values are nominal at each future year-end. Debt, excess cash, working-capital adjustments, future dilution, transaction costs, and shareholder taxes are not modeled.", "",
             "## Year-end operating value", "",
             "| Year-end | Annualised revenue pace CZK | Annualised EBITDA CZK | Enterprise value CZK |",
             "| --- | ---: | ---: | ---: |"]
    for row in rows:
        lines.append(f"| {row['year_end']} | " + " | ".join(f"{process.amount(row[key]):,.0f}" for key in ("combined_annualised_revenue_czk", "annualised_ebitda_czk", "enterprise_value_czk")) + " |")
    lines += ["", "## Relationship to the earlier 2027 estimate", "",
              f"The earlier optimistic 2027 estimate used full-calendar-year commercial revenue of {actual_total:,.2f} CZK at the same exchange-rate assumption. At the central margin and multiple it implies {actual_total * process.amount(settings['ebitda_margin']) * process.amount(settings['ebitda_multiple']):,.2f} CZK of operating value.",
              "This model starts from the higher Q4 annualised pace because the existing optimistic plan ramps up during 2027. The different starting basis, rather than a change in the earlier annual forecast, explains the higher end-2027 valuation.", "",
              "## 2030 margin and multiple sensitivity", "",
              "These are alternative assumptions, not a confidence interval. Revenue growth stays at the central assumption.", "",
              "| EBITDA margin | 2x EBITDA CZK | 3x EBITDA CZK | 4x EBITDA CZK |",
              "| --- | ---: | ---: | ---: |"]
    for margin in (Decimal("0.10"), Decimal("0.20"), Decimal("0.30")):
        lines.append(f"| {margin:.0%} | " + " | ".join(f"{final_revenue * margin * m:,.0f}" for m in (2, 3, 4)) + " |")
    lines += ["", "## 2030 growth sensitivity", "",
              "Central margin and earnings multiple are held constant.", "",
              "| Annual growth after base year | Enterprise value CZK |", "| --- | ---: |"]
    for growth in (Decimal("0"), Decimal("0.10"), Decimal("0.20"), Decimal("0.30")):
        value = process.amount(first["combined_annualised_revenue_czk"]) * (1 + growth) ** (int(last["year_end"]) - int(first["year_end"])) * process.amount(settings["ebitda_margin"]) * process.amount(settings["ebitda_multiple"])
        lines.append(f"| {growth:.0%} | {value:,.0f} |")
    lines += ["", "## Shareholder value and execution", "",
              "Equity value is enterprise value less debt and debt-like obligations plus excess cash and agreed working-capital adjustments. Normal operating inventory and equipment must not be added a second time to an earnings-based value. A shareholder's stake is their ownership percentage of equity value, subject to rights and dilution.",
              "No future debt or excess cash balances are established in the available data, so the model does not calculate equity value. A present-day valuation would also need execution-risk and time adjustments; the 2030 value is not a current asking price.",
              "The optimistic base depends heavily on sachet orders, branch expansion, and clinic upsells that remain unconfirmed. The 2030 extension also requires sustained customer retention, delivery capacity, funding, and the assumed margins. It is not yet supported by a detailed 2028–2030 customer or cost plan.", "",
              "## Method references", "",
              "[BDC: earnings-based valuation and the need for comparables](https://www.bdc.ca/en/articles-tools/start-buy-business/buy-business/how-value-business-youd-like-acquire). The source describes the method; the growth, margins, and multiple in this model are explicit assumptions.",
              "[BDC: enterprise value versus shareholder equity value](https://www.bdc.ca/en/articles-tools/entrepreneur-toolkit/templates-business-guides/glossary/enterprise-value).", "",
              "Generated by `python3 scripts/project_valuation.py --write` from the existing revenue assumptions and `data/enriched/valuation-assumptions.json`. Detailed calculations are in `data/enriched/valuation-yearly.csv`.", ""]
    return "\n".join(lines)


def prepare(root):
    settings = json.loads((root / "data/enriched/valuation-assumptions.json").read_text())
    generated, _ = build_reports.forecasts(root)
    summary = {row['period']: row for row in csv.DictReader(io.StringIO(generated[root / "data/enriched/forecast-summary.csv"]))}
    base = settings["base_quarter"]
    rows = calculate(summary[base], settings)
    return {
        root / "data/enriched/valuation-yearly.csv": process.csv_text(rows, list(rows[0])),
        root / "reports/valuation-2030.md": report(rows, settings, summary[base[:4] + "_TOTAL"]),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write valuation outputs; default is a dry run")
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
