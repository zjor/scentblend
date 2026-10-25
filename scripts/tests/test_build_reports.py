import csv
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_reports as reports
import process_transactions as process


class ReportTests(unittest.TestCase):
    def fixture(self):
        reviews = {}
        categories = {}
        for txid, value, bucket in (("1", "100", "revenue"), ("2", "-30", "transfer"),
                                   ("3", "-20", ""), ("4", "10", ""),
                                   ("5", "-5", "financing")):
            row = dict.fromkeys(process.REVIEW_FIELDS, "")
            row.update(transaction_id=txid, transaction_date="2026-10-23", amount_czk=value,
                       booking_datetime="2026-10-24T12:00", guess_bucket=bucket)
            reviews[txid] = row
            category = dict.fromkeys(process.CATEGORY_FIELDS, "")
            category.update({k: row[k] for k in process.CATEGORY_FIELDS[:3]})
            categories[txid] = category
        categories["2"].update(bucket="opex", category="salary", notes="User provisional assumption")
        return reviews, categories

    def test_manual_override_and_reconciliation(self):
        reviews, categories = self.fixture()
        rows = reports.effective_rows(reviews, categories)
        self.assertEqual(rows[1]["bucket"], "opex")
        self.assertEqual(rows[1]["classification_source"], "manual")
        report = reports.pnl_report(rows)
        self.assertIn("| **Memo: classified cash subtotal** | 70.00 | 70.00 |", report)
        self.assertIn("| Unresolved incoming movements | 10.00 | 10.00 |", report)
        self.assertIn("| Unresolved outgoing movements | -20.00 | -20.00 |", report)
        self.assertIn("| **Net bank movement** | 55.00 | 55.00 |", report)
        self.assertIn("User provisional assumption", report)

    def test_unknown_bucket_cannot_disappear_from_reconciliation(self):
        reviews, categories = self.fixture()
        categories["2"]["bucket"] = "typo"
        with self.assertRaisesRegex(ValueError, "Unknown bucket"):
            reports.effective_rows(reviews, categories)

    def test_unallocated_income_reconciles_to_customer_totals(self):
        reviews, categories = self.fixture()
        reviews["1"]["guess_customer_name"] = "Example"
        reviews["4"]["guess_bucket"] = "revenue"
        rows = reports.effective_rows(reviews, categories)
        report = reports.customer_report(rows, [])
        self.assertIn("| Example | 100.00 |", report)
        self.assertIn("| [Unallocated product income] | 10.00 |", report)
        self.assertIn("| **Total classified receipts** | 110.00 |", report)

    def test_forecast_currency_separation_and_annual_totals(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "data/enriched/forecast-assumptions.csv"
            path.parent.mkdir(parents=True)
            fields = ["customer_name", "stream", "currency", "pessimistic_per_quarter"] + ["optimistic_2027Q" + str(q) for q in range(1, 5)]
            rows = []
            for currency, value in (("CZK", "100.25"), ("EUR", "20.10")):
                row = dict(customer_name="Example", stream="Service", currency=currency, pessimistic_per_quarter=value)
                row.update({field: value for field in fields if field.startswith("optimistic_")})
                rows.append(row)
            path.write_text(process.csv_text(rows, fields))
            outputs, _ = reports.forecasts(root)
            summary = list(csv.DictReader(io.StringIO(outputs[root / "data/enriched/forecast-summary.csv"])))
            self.assertEqual(summary[-1]["period"], "2027_TOTAL")
            self.assertEqual(summary[-1]["pessimistic_czk"], "401.00")
            self.assertEqual(summary[-1]["optimistic_eur"], "80.40")


if __name__ == "__main__":
    unittest.main()
