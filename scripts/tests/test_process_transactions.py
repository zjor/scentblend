import csv
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import process_transactions as process


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data/raw").mkdir(parents=True)

    def raw_row(self, txid="1", value="123,45", date="23.10.2026"):
        return {
            "Id transakce": txid, "Datum provedení": date,
            "Datum zaúčtování": "25.10.2026 15:53", "Zaúčtovaná částka": value,
            "Měna účtu": "CZK", "Typ transakce": "Příchozí úhrada",
            "Název protiúčtu": "Example", "Název obchodníka": "",
            "Zpráva": "Invoice", "Poznámka": "Invoice",
        }

    def export(self, name, rows):
        with (self.root / "data/raw" / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=sorted(process.RAW_FIELDS), delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

    def save_csv(self, relative, rows, fields):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(process.csv_text(rows, fields), encoding="utf-8")

    def test_overlap_dates_decimal_and_idempotence(self):
        self.export("first.csv", [self.raw_row()])
        self.export("second.csv", [self.raw_row(), self.raw_row("2", "-23,45")])
        outputs, summary = process.prepare(self.root)
        normalized = list(csv.DictReader(io.StringIO(outputs[self.root / "data/enriched/normalized-transactions.csv"])))
        self.assertEqual(len(normalized), 2)
        self.assertEqual(normalized[0]["transaction_date"], "2026-10-23")
        self.assertEqual(normalized[0]["booking_datetime"], "2026-10-25T15:53")
        self.assertEqual(normalized[0]["description"], "Invoice")
        self.assertIn("1 duplicate rows", summary)
        self.assertIn("| 2026-10 | 2 | 123.45 | -23.45 | 100.00 |", outputs[self.root / "reports/cash_movements.md"])
        for path, contents in outputs.items():
            process.atomic_write(path, contents)
        repeated, _ = process.prepare(self.root)
        self.assertEqual(outputs, repeated)

    def test_manual_classification_and_suggestions_survive(self):
        self.export("export.csv", [self.raw_row(), self.raw_row("2")])
        category = dict.fromkeys(process.CATEGORY_FIELDS, "")
        category.update(transaction_id="1", transaction_date="2026-10-23", amount_czk="123.45", bucket="transfer", notes="Confirmed internal transfer")
        self.save_csv("data/categories/transactions.csv", [category], process.CATEGORY_FIELDS)
        review = dict.fromkeys(process.REVIEW_FIELDS, "")
        review.update(transaction_id="1", transaction_date="2026-10-23", amount_czk="123.45", guess_bucket="revenue", guess_customer_name="Example", guess_reason="Existing suggestion")
        self.save_csv("data/enriched/transactions.csv", [review], process.REVIEW_FIELDS)
        outputs, _ = process.prepare(self.root)
        self.assertIn("Confirmed internal transfer", outputs[self.root / "data/categories/transactions.csv"])
        self.assertIn("Existing suggestion", outputs[self.root / "data/enriched/transactions.csv"])
        customers = list(csv.DictReader(io.StringIO(outputs[self.root / "data/enriched/customers.csv"])))
        self.assertEqual(customers, [])
        reviews = list(csv.DictReader(io.StringIO(outputs[self.root / "data/enriched/transactions.csv"])))
        self.assertEqual(reviews[1]["guess_bucket"], "")

    def test_conflicting_export_fails_before_writes(self):
        self.export("first.csv", [self.raw_row()])
        self.export("second.csv", [self.raw_row(value="999")])
        with self.assertRaisesRegex(ValueError, "conflicting export rows"):
            process.prepare(self.root)
        self.assertFalse((self.root / "data/categories").exists())

    def test_missing_export_does_not_drop_reviewed_rows(self):
        self.export("first.csv", [self.raw_row()])
        category = dict.fromkeys(process.CATEGORY_FIELDS, "")
        category.update(transaction_id="missing", transaction_date="2026-10-01", amount_czk="1")
        self.save_csv("data/categories/transactions.csv", [category], process.CATEGORY_FIELDS)
        with self.assertRaisesRegex(ValueError, "absent from raw exports"):
            process.prepare(self.root)

    def test_changed_amount_requires_review(self):
        self.export("first.csv", [self.raw_row()])
        category = dict.fromkeys(process.CATEGORY_FIELDS, "")
        category.update(transaction_id="1", transaction_date="2026-10-23", amount_czk="1")
        self.save_csv("data/categories/transactions.csv", [category], process.CATEGORY_FIELDS)
        with self.assertRaisesRegex(ValueError, "date or amount changed"):
            process.prepare(self.root)


if __name__ == "__main__":
    unittest.main()
