# Inventory

Two CSV files. Stock on hand is never stored; it is the sum of `movements.qty` per `sku`.

## items.csv — catalog
| column | meaning |
|---|---|
| sku | stable id, use it in movements |
| name | supplier / product name |
| unit | base unit for qty: `ks` (pieces) or `kg` |
| pack_size | units per supplier pack (informational) |
| notes | free text |

## movements.csv — ledger
| column | meaning |
|---|---|
| date | YYYY-MM-DD |
| sku | from items.csv |
| qty | always in the item's base unit; positive for `in`, negative for `out` / `adjust` |
| type | `in` (purchase), `out` (used / sold), `adjust` (count correction) |
| document | invoice / order reference |
| counterparty | supplier or customer |
| unit_price_czk | net price per base unit, CZK (empty for out/adjust if unknown) |
| currency | currency of the source document |
| note | free text |

## Stock on hand
```
python3 scripts/inventory_stock.py
```
