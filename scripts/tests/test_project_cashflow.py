from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import project_cashflow as cashflow


class CashflowTests(unittest.TestCase):
    def row(self, date, amount, bucket=""):
        return dict(transaction_date=date, amount_czk=amount, bucket=bucket)

    def test_expense_budget_includes_uncertainty_once_excludes_funding(self):
        rows = [self.row("2026-09-01", "-100", "opex"), self.row("2026-09-01", "-50"),
                self.row("2026-09-01", "-200", "transfer"), self.row("2026-09-01", "-20", "financing"),
                self.row("2026-09-01", "-30", "owner"), self.row("2026-09-01", "40", "revenue")]
        self.assertEqual(cashflow.expense_reference(rows, "2026-09"), Decimal("150"))

    def test_zero_opening_and_partial_month_no_actual_double_count(self):
        rows = [self.row("2026-09-01", "-31", "opex"), self.row("2026-10-23", "41", "revenue")]
        assumptions = dict(opening_balance_czk="0", expense_reference_month="2026-09", projection_end="2026-10-31")
        revenue = {"2026Q4": dict(pessimistic_czk="93", optimistic_czk="186", pessimistic_eur="93", optimistic_eur="186")}
        projection, balance, spending, cutoff = cashflow.project(rows, revenue, assumptions)
        self.assertEqual(balance, Decimal("10"))
        self.assertEqual(len(projection), 2)
        low, high = projection
        self.assertEqual(low["period_start"], "2026-10-24")
        self.assertEqual(low["projected_receipts_czk"], "8.00")
        self.assertEqual(low["projected_outflows_czk"], "8.00")
        self.assertEqual(low["closing_balance_czk"], "10.00")
        self.assertEqual(high["closing_balance_czk"], "18.00")
        # EUR cash is reported separately and does not increase CZK balances.
        self.assertEqual(high["separate_projected_receipts_eur"], "16.00")

    def test_missing_quarter_stops_projection(self):
        rows = [self.row("2026-09-01", "-10"), self.row("2026-10-23", "20")]
        assumptions = dict(opening_balance_czk="0", expense_reference_month="2026-09", projection_end="2026-11-30")
        with self.assertRaisesRegex(ValueError, "Missing revenue assumptions"):
            cashflow.project(rows, {}, assumptions)

    def test_negative_balance_top_up_is_not_repeated_funding(self):
        rows = [self.row("2026-09-01", "-30"), self.row("2026-10-31", "30")]
        assumptions = dict(opening_balance_czk="0", expense_reference_month="2026-09", projection_end="2026-12-31")
        revenue = {"2026Q4": dict(pessimistic_czk="0", optimistic_czk="0", pessimistic_eur="0", optimistic_eur="0")}
        projection, *_ = cashflow.project(rows, revenue, assumptions)
        low = [r for r in projection if r['scenario']=='pessimistic']
        self.assertEqual(low[0]['closing_balance_czk'], '-30.00')
        self.assertEqual(low[1]['closing_balance_czk'], '-60.00')
        self.assertEqual(low[1]['minimum_top_up_for_nonnegative_closing_czk'], '60.00')


if __name__ == "__main__":
    unittest.main()
