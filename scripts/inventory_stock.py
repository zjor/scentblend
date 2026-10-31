#!/usr/bin/env python3
"""Print current stock per SKU from data/inventory/movements.csv."""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data" / "inventory"

items = {r["sku"]: r for r in csv.DictReader(open(ROOT / "items.csv", encoding="utf-8"))}
stock = defaultdict(float)
for r in csv.DictReader(open(ROOT / "movements.csv", encoding="utf-8")):
    stock[r["sku"]] += float(r["qty"])

print(f"{'sku':<32} {'qty':>8} unit  name")
for sku, qty in sorted(stock.items()):
    it = items.get(sku, {})
    q = f"{qty:g}"
    print(f"{sku:<32} {q:>8} {it.get('unit', '?'):<4}  {it.get('name', '(unknown sku)')}")
