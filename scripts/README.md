# Financial data tools

Keep repeatable imports and report generators here. Scripts use Python 3.9+ and the standard library; no dependencies or credentials are required. Run the commands below from the project root.

## Transaction workflow

1. Copy each unchanged bank export into `data/raw/`. Keep older exports: the importer needs the full history. Overlapping exports are supported.
2. Preview the import and validate all input files:

   ```sh
   python3 scripts/process_transactions.py
   ```

3. Apply the import:

   ```sh
   python3 scripts/process_transactions.py --write
   ```

4. Preview and apply suggestions for the newly imported rows:

   ```sh
   python3 scripts/suggest_classifications.py
   python3 scripts/suggest_classifications.py --write
   ```

   This separate stage uses bank transaction types, explicit descriptions, exact existing customer payer names, and invoice reference evidence. It preserves previous suggestions and skips rows with a manual bucket. Suggestions add `guess_category` and remain unconfirmed. Tax, payroll, director settlements, processor payouts, and purchases with unclear inventory or business use stay unresolved. Similar customer names are not combined. Possible reversals are flagged using an exact opposite amount on the same counterparty account with an explicit reversal note.

5. Review `reports/classification_review.md` and `data/enriched/transactions.csv`. Enter confirmed buckets, categories, customer names, and notes in `data/categories/transactions.csv` using supporting records.
6. Run both commands with `--write` again to update customer totals and the review report after classification changes. Suggestions are applied only to rows still marked as newly imported; reruns preserve prior review work.
7. Preview and rebuild reports and forecast CSVs with current assumptions:

   ```sh
   python3 scripts/build_reports.py
   python3 scripts/build_reports.py --write
   ```

   This generates `data/enriched/effective-transactions.csv` with the applied bucket, category, and manual/suggested/unresolved source for each row; `reports/pnl_provisional.md` with a monthly classified cash proxy and exact bank reconciliation; and `reports/customer_receipts.md` with partial-quarter customer receipts and forecast coverage. Manual buckets override suggestions. Unknown buckets or mismatched source data stop report generation.

   The forecast CSVs are rebuilt from `forecast-assumptions.csv`, retaining its commercial assumptions and separating CZK and EUR. Bank receipts do not automatically change contract prices, recurring terms, or forecast assumptions. Review customer profiles, invoice status, and the narrative forecast separately when new evidence supports changes. Complete profit metrics remain pending until invoices, VAT, inventory, payroll, and periods are reconciled.

8. Build the monthly cash-flow sensitivity estimate:

   ```sh
   python3 scripts/project_cashflow.py
   python3 scripts/project_cashflow.py --write
   ```

   Local private inputs live in `data/enriched/cashflow-assumptions.json`: `opening_balance_czk` (balance before the imported history), `expense_reference_month` (`YYYY-MM`), and `projection_end` (`YYYY-MM-DD`). The current zero opening balance was supplied by the user. The reference month and flat future spending budget are modeling assumptions.

   The script computes the historical balance from all imported movements, then projects from the next day. Quarterly revenue is spread evenly into monthly receipts; the monthly spending budget includes every negative reference-month payment except transfer, owner, and financing buckets, including unresolved payments and tax settlements. Partial months are prorated by calendar days. This is a sensitivity model, not an invoice payment schedule or profit forecast. EUR receipts remain separate, and no future funding or conversions are assumed. Outputs are `reports/cashflow-projection.md` and `data/enriched/cashflow-monthly.csv`. All source classifications and commercial assumptions are preserved.

9. Extend the optimistic scenario into a future operating-value sensitivity:

   ```sh
   python3 scripts/project_valuation.py
   python3 scripts/project_valuation.py --write
   ```

   Private assumptions live in `data/enriched/valuation-assumptions.json`: `base_quarter` (a Q4 in the existing optimistic forecast), `end_year`, `eur_czk`, `annual_growth_after_base_year`, `ebitda_margin`, and `ebitda_multiple`. The script annualises the base quarter, compounds the sales pace at each future year-end, and applies the margin and multiple. Outputs are `data/enriched/valuation-yearly.csv` and `reports/valuation-2030.md`.

   This models future enterprise value on a year-end earnings pace, not calendar-year sales, current sale proceeds, or shareholder net worth. VAT, market-rate owner compensation, growth costs, comparable sale multiples, net debt, and equity dilution require separate validation. It does not use the flat-spending cash sensitivity as EBITDA or change the existing 2027 forecast.

The importer produces:

| Output | Behavior |
| --- | --- |
| `data/enriched/normalized-transactions.csv` | One row per transaction ID across all exports, ordered by execution date and ID. Retains the booking timestamp separately. |
| `data/categories/transactions.csv` | Adds new transactions; preserves all existing manual fields and extra columns. |
| `data/enriched/transactions.csv` | Refreshes bank context, adds booking timestamps, and preserves existing suggestions and extra columns. |
| `data/enriched/customers.csv` | Rebuilds signed gross receipt totals for named revenue customers. Explicit manual buckets override suggestions; otherwise existing suggestions are used. Refunds reduce totals. Counts include all included revenue movements. |
| `reports/cash_movements.md` | Monthly incoming, outgoing, and net bank movements by execution date. Includes all buckets and does not measure profit. |

Exports must use the Raiffeisenbank UTF-8 semicolon CSV format with a CZK account currency. The script preserves the raw files. It rejects conflicting duplicate IDs, malformed data, changes to dates or amounts already in review files, and existing review IDs absent from raw exports. Restore or reconcile the source data before retrying.

All inputs are validated and output contents prepared before writing. Each file is replaced atomically; the five-file update is not a single transaction. If interrupted, rerun the command. Repeating an import with unchanged inputs produces identical file contents. Generated financial data and reports remain excluded from Git.

## Checks

```sh
python3 -m unittest discover -s scripts/tests -v
```

Tests use temporary synthetic exports and cover overlapping exports, conflicting IDs, preserving manual work, missing history, date/amount changes, exact decimal totals, and repeatable output.
Suggestion tests also cover payment direction, loan priority, exact customer matching, and retaining uncertainty for tax, stock, shipping, director movements, and reversals.
Report tests cover manual precedence, bank reconciliation including unresolved movements, unallocated receipts, currency separation, and annual forecast totals.
Cash-flow tests cover the opening balance, reference-month exclusions, unresolved spending, partial-month timing, missing quarters, funding gap calculations, and keeping EUR receipts outside CZK balances.
Valuation tests cover quarter annualisation, explicit currency conversion, growth compounding, zero-margin results, and rejecting invalid assumptions.
