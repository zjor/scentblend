from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import project_valuation as valuation


class ValuationTests(unittest.TestCase):
    def settings(self):
        return dict(end_year=2030, eur_czk="25", annual_growth_after_base_year="0.20",
                    ebitda_margin="0.20", ebitda_multiple="3")

    def quarter(self):
        return dict(period="2027Q4", optimistic_czk="100", optimistic_eur="2")

    def test_annualise_convert_and_compound_exactly_three_years(self):
        rows = valuation.calculate(self.quarter(), self.settings())
        self.assertEqual(len(rows), 4)
        self.assertEqual(Decimal(rows[0]["combined_annualised_revenue_czk"]), Decimal("600"))
        last = rows[-1]
        self.assertEqual(last["year_end"], "2030")
        self.assertEqual(Decimal(last["combined_annualised_revenue_czk"]), Decimal("1036.8"))
        self.assertEqual(Decimal(last["annualised_ebitda_czk"]), Decimal("207.36"))
        self.assertEqual(Decimal(last["enterprise_value_czk"]), Decimal("622.08"))

    def test_zero_margin_has_no_earnings_based_value(self):
        settings = self.settings()
        settings["ebitda_margin"] = "0"
        self.assertTrue(all(Decimal(row["enterprise_value_czk"]) == 0
                            for row in valuation.calculate(self.quarter(), settings)))

    def test_invalid_inputs_fail(self):
        for field, value in (("eur_czk", "0"), ("annual_growth_after_base_year", "-1"),
                             ("ebitda_margin", "1.1"), ("ebitda_multiple", "0"),
                             ("end_year", 2026)):
            with self.subTest(field=field):
                settings = self.settings()
                settings[field] = value
                with self.assertRaises(ValueError):
                    valuation.calculate(self.quarter(), settings)


if __name__ == "__main__":
    unittest.main()
