#!/usr/bin/env python3
"""Forecast revenue, margin and marketer salary from meetings-to-hotel conversion."""

import argparse


def forecast(months, work_months, meetings_per_month, p_sale, income_per_hotel,
             margin_rate, salary_eur, eur_czk, pay_lag, investor_share, share_months):
    """Return per-month rows: active hotels, revenue, margin, salary, investor payout (CZK).

    The investor funds the salary and receives `investor_share` of the margin
    for the first `share_months` months.
    """
    hotels_per_month = meetings_per_month * p_sale
    salary_czk = salary_eur * eur_czk
    rows = []
    for m in range(1, months + 1):
        # Hotels signed in months 1..work_months start paying `pay_lag` months later.
        signing_months = [k for k in range(1, work_months + 1) if k + pay_lag <= m]
        active = hotels_per_month * len(signing_months)
        revenue = active * income_per_hotel
        margin = revenue * margin_rate
        salary = salary_czk if m <= work_months else 0.0
        investor = margin * investor_share if m <= share_months else 0.0
        rows.append({"month": m, "hotels": active, "revenue": revenue,
                     "margin": margin, "salary": salary, "investor": investor})
    return rows


def print_table(rows, horizons, share_months):
    print(f"{'month':>5} {'hotels':>6} {'revenue':>12} {'margin':>12} {'salary':>10} "
          f"{'investor':>10} {'company':>10} {'cum_margin':>12} {'cum_investor':>12}")
    cum_margin = cum_salary = cum_revenue = cum_investor = 0.0
    for r in rows:
        cum_revenue += r["revenue"]
        cum_margin += r["margin"]
        cum_salary += r["salary"]
        cum_investor += r["investor"]
        company = r["margin"] - r["investor"]
        print(f"{r['month']:>5} {r['hotels']:>6.1f} {r['revenue']:>12,.0f} {r['margin']:>12,.0f} "
              f"{r['salary']:>10,.0f} {r['investor']:>10,.0f} {company:>10,.0f} "
              f"{cum_margin:>12,.0f} {cum_investor:>12,.0f}")
        if r["month"] in horizons:
            print(f"--- {r['month']} months: revenue {cum_revenue:,.0f} | margin {cum_margin:,.0f} "
                  f"| salary {cum_salary:,.0f} | investor {cum_investor:,.0f} "
                  f"| company keeps {cum_margin - cum_investor:,.0f}")
    total_salary = sum(r["salary"] for r in rows)
    share_margin = sum(r["margin"] for r in rows if r["month"] <= share_months)
    print()
    print(f"Investor pays salary:        {total_salary:,.0f} CZK")
    print(f"Investor receives:           {cum_investor:,.0f} CZK "
          f"({cum_investor / total_salary:.2f}x) over {share_months} months")
    print(f"Margin in share window:      {share_margin:,.0f} CZK")
    print(f"Break-even share (1.0x):     {total_salary / share_margin:.1%}")
    print(f"Share for 1.5x return:       {1.5 * total_salary / share_margin:.1%}")
    print(f"Share for 2.0x return:       {2.0 * total_salary / share_margin:.1%}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", type=int, default=18, help="forecast horizon in months")
    ap.add_argument("--work-months", type=int, default=3, help="months the marketer works")
    ap.add_argument("--meetings", type=float, default=4, help="meetings per month (N)")
    ap.add_argument("--p-sale", type=float, default=0.5, help="probability of sale per meeting")
    ap.add_argument("--income", type=float, default=30000, help="monthly revenue per hotel, CZK")
    ap.add_argument("--margin", type=float, default=0.4, help="margin rate")
    ap.add_argument("--salary-eur", type=float, default=2100, help="marketer salary, EUR/month")
    ap.add_argument("--eur-czk", type=float, default=25.0, help="EUR to CZK rate")
    ap.add_argument("--pay-lag", type=int, default=1,
                    help="months between signing and first payment (0 = same month)")
    ap.add_argument("--investor-share", type=float, default=0.3,
                    help="share of margin paid to the investor who funds the salary")
    ap.add_argument("--share-months", type=int, default=12,
                    help="how many months (from month 1) the investor share applies")
    ap.add_argument("--horizons", type=int, nargs="*", default=[12, 18],
                    help="months at which to print cumulative totals")
    a = ap.parse_args()

    rows = forecast(a.months, a.work_months, a.meetings, a.p_sale, a.income,
                    a.margin, a.salary_eur, a.eur_czk, a.pay_lag,
                    a.investor_share, a.share_months)
    print_table(rows, set(a.horizons), a.share_months)


if __name__ == "__main__":
    main()
