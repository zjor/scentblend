from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import suggest_classifications as suggestions


class SuggestionTests(unittest.TestCase):
    def row(self, **changes):
        row = dict(transaction_id="1", amount_czk="100", bank_type="Příchozí úhrada",
                   counterparty_name="Example s.r.o.", merchant_name="", description="")
        row.update(changes)
        return row

    def test_named_invoice_receipt_and_exact_existing_customer(self):
        guess = suggestions.suggest(self.row(), {"VS": "20260001"}, {})
        self.assertEqual(guess["guess_bucket"], "revenue")
        self.assertEqual(guess["guess_customer_name"], "Example s.r.o.")
        guess = suggestions.suggest(self.row(), {}, {"example s.r.o.": "Canonical customer"})
        self.assertEqual(guess["guess_customer_name"], "Canonical customer")

    def test_banks_processors_and_unknown_receipts_stay_unresolved(self):
        for name in ("COMMERZBANK AG", "STRIPE TECHNOLOGY EU"):
            guess = suggestions.suggest(self.row(counterparty_name=name), {"VS": "123"}, {})
            self.assertEqual(guess["guess_bucket"], "")
        self.assertEqual(suggestions.suggest(self.row(), {}, {})["guess_bucket"], "")

    def test_director_and_reversal_do_not_become_sales(self):
        row = self.row()
        self.assertEqual(suggestions.suggest(row, {"VS": "123"}, {}, {"example s.r.o."})["guess_bucket"], "")
        self.assertEqual(suggestions.suggest(row, {"VS": "123"}, {}, reversals={"1"})["guess_bucket"], "")

    def test_outgoing_contribution_label_is_not_incoming_funding(self):
        row = self.row(amount_czk="-1500", description="Vklad jednatele")
        self.assertEqual(suggestions.suggest(row, {}, {}, {"example s.r.o."})["guess_bucket"], "")
        row["amount_czk"] = "1500"
        self.assertEqual(suggestions.suggest(row, {}, {}, {"example s.r.o."})["guess_bucket"], "owner")

    def test_loan_type_precedes_same_company_transfer_rule(self):
        row = self.row(bank_type="Splátka jistiny po splatnosti", counterparty_name="Scent Blend s.r.o.", amount_czk="-100")
        self.assertEqual(suggestions.suggest(row, {}, {})["guess_bucket"], "financing")

    def test_tax_stock_and_shipping_need_evidence(self):
        for merchant, description in (("Finanční správa", "FÚ"), ("VZP", ""),
                                      ("Candle Shack", ""), ("PPL", "")):
            row = self.row(amount_czk="-100", merchant_name=merchant, description=description)
            self.assertEqual(suggestions.suggest(row, {}, {})["guess_bucket"], "")


if __name__ == "__main__":
    unittest.main()
