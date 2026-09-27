# Scent Blend finances

This project holds bank exports and a manual classification for a simple monthly management P&L. It is not an accounting ledger or a tax return.

## Files

- `data/raw/` — original bank CSV exports. Keep each export unchanged.
- `data/categories/transactions.csv` — one classification row per bank transaction, matched by `transaction_id` (`Id transakce` in the Raiffeisenbank export).
- `data/enriched/transactions.csv` — a separate review list with bank context and suggested `guess_bucket` and `guess_customer_name`. Empty suggestions need investigation. These guesses do not change the manual classification file.
- `data/enriched/customers.csv` — unique customer names derived from the suggested revenue transactions, with receipt counts and gross bank receipts.
- `data/enriched/customer-notes.md` — structured client profiles with current terms, opportunities, and open invoices from working notes.
- `data/enriched/customer-registry.csv` — legal names, Czech/Slovak IČO or Swiss UID where found, tax IDs, websites, source URLs, and match status for each client profile.
- `data/enriched/forecast-assumptions.csv` — current quarterly values and explicit optimistic scenario inputs by revenue stream.
- `data/enriched/forecast-quarterly.csv` — long-format quarterly results by client and revenue stream.
- `data/enriched/forecast-summary.csv` — one row per quarter with as-is and optimistic totals in separate CZK and EUR columns.
- `reports/pnl_provisional.md` — bank-based P&L proxy and the data gaps that prevent an accurate P&L.
- `reports/revenue-forecast.md` — quarterly customer revenue scenarios through 2027 and their assumptions.

All three data directories and generated reports contain private financial information and are excluded from Git.

## Classifying transactions

The classification file has these columns:

| Column | Meaning |
| --- | --- |
| `transaction_id` | Stable ID from the bank export. Do not edit. |
| `transaction_date` | Bank transaction date, in ISO format, for review. |
| `amount_czk` | Signed amount booked to the CZK account, for review. |
| `bucket` | One of the buckets below. Blank means not yet reviewed. |
| `category` | More specific label, such as `candles`, `materials`, `software`, or `rent`. |
| `customer_name` | Customer associated with a sale or refund, if known. Leave blank for other transactions. |
| `notes` | Explanation for uncertain or unusual treatment. |

Use these `bucket` values:

| Bucket | Treatment |
| --- | --- |
| `revenue` | Sales and service income; part of P&L. |
| `cogs` | Direct costs of goods sold or services delivered; part of P&L. Purchases held in inventory need separate timing information. |
| `opex` | Operating costs such as software, marketing, and rent; part of P&L. |
| `other_income` | Non-operating income; part of P&L. |
| `other_expense` | Non-operating expense, including interest; part of P&L. |
| `capex` | Equipment and other long-lived assets; exclude the full payment from immediate operating profit. Depreciation needs separate records. |
| `vat` | VAT payments or refunds; track separately from net revenue and costs. |
| `income_tax` | Income-tax payments or refunds; track separately until reconciled to the relevant period. |
| `financing` | Loan proceeds or principal repayments. Interest belongs in `other_expense`. |
| `owner` | Owner contributions or distributions. |
| `transfer` | Transfers between company accounts, currency conversions, or cash withdrawals. The later use of withdrawn cash needs its own evidence. |

Refunds or reversals normally use the same bucket as the original transaction and retain their signed amount. If a transaction contains several purposes, explain the split in `notes`; a later version can support multiple allocation rows.

## First report

A bank export supports a cash movement report immediately. A reliable P&L also needs invoices, VAT treatment, inventory or cost-of-goods information, unpaid bills, and any cash or other bank accounts. Until those are available, classify the bank transactions and label any resulting P&L as an estimate based on this account only.

The enriched file contains suggestions based on bank text, not verified accounting entries. In particular, a bank receipt can include VAT, and a purchase of stock is not necessarily a cost of goods sold in the payment month. Confirm customer names and P&L treatment against invoices before using the guesses in a report. Stripe payouts do not identify individual customers in this export.
