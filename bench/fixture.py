"""Generates the benchmark repo: a small Python shop with a big data module, chatty tests and a noisy build.

Deterministic: same files every time. `python3 bench/fixture.py <dir>` writes it and prints the expected answers.
"""
import json
import os
import sys

CATS = ["kitchen", "garden", "office", "toys", "audio", "outdoor", "bath", "tools"]
PREFIX = {"kitchen": "KT", "garden": "GD", "office": "OF", "toys": "TY", "audio": "AU",
          "outdoor": "OD", "bath": "BT", "tools": "TL"}


def products():
    out = []
    for i in range(1, 601):
        cat = CATS[i % len(CATS)]
        out.append({
            "sku": f"{PREFIX[cat]}-{i:04d}",
            "name": f"{cat.title()} item {i}",
            "category": cat,
            "price_cents": 499 + (i * 173) % 9000,
            "weight_g": 120 + (i * 37) % 2600,
            "stock": (i * 7) % 40,
        })
    return out


CATALOG_TAIL = '''

_BY_SKU = {p["sku"]: p for p in PRODUCTS}


def by_sku(sku):
    """Product dict for a SKU, or None."""
    return _BY_SKU.get(sku)


def in_category(category):
    return [p for p in PRODUCTS if p["category"] == category]


def in_stock(min_units=1):
    return [p for p in PRODUCTS if p["stock"] >= min_units]
'''

SHIPPING = '''"""Shipping cost rules (cents). Thresholds come from the carrier contract, rev. 2024-03."""

LIGHT_MAX_G = 500
STANDARD_MAX_G = 1500


def ship_cost_light(weight_g):
    return 390


def ship_cost_standard(weight_g):
    return 590 + (weight_g - LIGHT_MAX_G) // 100 * 20


def ship_cost_heavy(weight_g):
    return 1290 + (weight_g - STANDARD_MAX_G) // 250 * 60


def ship_cost(product):
    """Pick the tariff for a product by its weight."""
    w = product["weight_g"]
    if w < LIGHT_MAX_G:
        return ship_cost_light(w)
    if w < STANDARD_MAX_G:
        return ship_cost_standard(w)
    return ship_cost_heavy(w)
'''

PRICING = '''"""Pricing: discounts, coupons, rounding."""
import logging

log = logging.getLogger("shopcart.pricing")

BULK_THRESHOLD = 10
BULK_RATE = 0.10
COUPONS = {"WELCOME5": 0.05, "SPRING10": 0.10, "VIP15": 0.15}


def bulk_discount(qty, unit_cents):
    """10% off the line when buying BULK_THRESHOLD units or more."""
    log.debug("bulk_discount qty=%s unit=%s threshold=%s", qty, unit_cents, BULK_THRESHOLD)
    if qty > BULK_THRESHOLD:
        return round(qty * unit_cents * BULK_RATE)
    return 0


def coupon_rate(code):
    code = (code or "").strip().upper()
    rate = COUPONS.get(code, 0.0)
    log.debug("coupon %r -> %s", code, rate)
    return rate


def line_total(qty, unit_cents):
    total = qty * unit_cents - bulk_discount(qty, unit_cents)
    log.debug("line_total qty=%s unit=%s -> %s", qty, unit_cents, total)
    return total


def apply_coupon(subtotal_cents, code):
    discounted = round(subtotal_cents * (1 - coupon_rate(code)))
    log.debug("apply_coupon %s %r -> %s", subtotal_cents, code, discounted)
    return discounted


def format_eur(cents):
    return f"{cents // 100},{cents % 100:02d} EUR"
'''

CART = '''"""Shopping cart."""
import logging

from . import catalog, pricing, shipping

log = logging.getLogger("shopcart.cart")


class Cart:
    def __init__(self):
        self.lines = {}
        self.coupon = None

    def add(self, sku, qty=1):
        product = catalog.by_sku(sku)
        if product is None:
            raise KeyError(sku)
        self.lines[sku] = self.lines.get(sku, 0) + qty
        log.debug("add %s x%s -> %s", sku, qty, self.lines[sku])

    def remove(self, sku):
        self.lines.pop(sku, None)
        log.debug("remove %s", sku)

    def subtotal(self):
        total = 0
        for sku, qty in self.lines.items():
            p = catalog.by_sku(sku)
            total += pricing.line_total(qty, p["price_cents"])
            log.debug("subtotal running %s after %s", total, sku)
        return total

    def shipping(self):
        cost = sum(shipping.ship_cost(catalog.by_sku(s)) for s in self.lines)
        log.debug("shipping %s", cost)
        return cost

    def total(self):
        t = pricing.apply_coupon(self.subtotal(), self.coupon) + self.shipping()
        log.debug("total %s", t)
        return t
'''

INIT = '''import logging
import sys

# Verbose by default: support asked for full traces in CI logs.
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format="%(asctime)s %(name)s %(levelname)s %(message)s")
'''

TEST_PRICING = '''import unittest

from shopcart import pricing


class PricingTest(unittest.TestCase):
    def test_no_bulk_discount_below_threshold(self):
        self.assertEqual(pricing.bulk_discount(9, 1000), 0)

    def test_bulk_discount_at_threshold(self):
        self.assertEqual(pricing.bulk_discount(10, 1000), 1000)

    def test_bulk_discount_above_threshold(self):
        self.assertEqual(pricing.bulk_discount(12, 1000), 1200)

    def test_coupon_case_insensitive(self):
        self.assertEqual(pricing.coupon_rate(" spring10 "), 0.10)

    def test_unknown_coupon(self):
        self.assertEqual(pricing.coupon_rate("NOPE"), 0.0)

    def test_format_eur(self):
        self.assertEqual(pricing.format_eur(1234), "12,34 EUR")


if __name__ == "__main__":
    unittest.main()
'''


def test_cart(prods):
    lines = ['import unittest', '', 'from shopcart import catalog, shipping', 'from shopcart.cart import Cart', '',
             '', 'class CartTest(unittest.TestCase):']
    for p in prods[::5]:
        sku = p["sku"]
        lines += [f'    def test_cart_{sku.replace("-", "_").lower()}(self):',
                  '        c = Cart()',
                  f'        c.add("{sku}", 2)',
                  f'        c.add("{sku}", 1)',
                  f'        self.assertEqual(c.lines["{sku}"], 3)',
                  f'        self.assertEqual(c.shipping(), shipping.ship_cost(catalog.by_sku("{sku}")))',
                  '        self.assertGreater(c.total(), 0)', '']
    lines += ['', 'if __name__ == "__main__":', '    unittest.main()', '']
    return "\n".join(lines)


LINT = '''"""Tiny house linter: every product needs a positive price and weight."""
from shopcart import catalog

bad = 0
for i, p in enumerate(catalog.PRODUCTS):
    ok = p["price_cents"] > 0 and p["weight_g"] > 0
    print(f"lint: PRODUCTS[{i}] {p['sku']:<8} price={p['price_cents']:>5} weight={p['weight_g']:>5} {'ok' if ok else 'BAD'}")
    bad += not ok
print(f"lint: {len(catalog.PRODUCTS)} products, {bad} problems")
raise SystemExit(1 if bad else 0)
'''

REPORT = '''"""Builds the weekly orders report (printed to stdout)."""
import csv
import sys

from shopcart import catalog, pricing, shipping


def main(path):
    n = revenue = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            product = catalog.by_sku(row["sku"])
            qty = int(row["qty"])
            line = pricing.line_total(qty, product["price_cents"])
            ship = shipping.ship_cost_for(product)
            revenue += line + ship
            n += 1
            print(f"report: order {row['order_id']} sku={row['sku']} qty={qty} line={line} ship={ship} running={revenue}")
    print(f"report: {n} orders, revenue {pricing.format_eur(revenue)}")


if __name__ == "__main__":
    main(sys.argv[1])
'''

BUILD = '''#!/usr/bin/env bash
# CI build: compile, lint, then generate the weekly report.
set -euo pipefail
cd "$(dirname "$0")"
echo "== compile"
python3 -m compileall -f shopcart tools
echo "== lint"
python3 -m tools.lint
echo "== report"
python3 -m tools.report data/orders.csv
echo "== build ok"
'''

README = '''# shopcart

Small shop backend: catalog, cart, pricing, shipping.

- Tests: `python3 -m unittest`
- Build: `./build.sh`
'''


def orders(prods):
    rows = ["order_id,sku,qty"]
    for i in range(1, 2401):
        p = prods[(i * 13) % len(prods)]
        rows.append(f"A{i:05d},{p['sku']},{1 + (i * 3) % 14}")
    return "\n".join(rows) + "\n"


def write(root):
    prods = products()
    files = {
        "README.md": README,
        "shopcart/__init__.py": INIT,
        "shopcart/catalog.py": '"""Product catalog. Generated from the merchandising export; do not edit by hand."""\n\nPRODUCTS = [\n'
                               + "".join(f"    {json.dumps(p)},\n" for p in prods) + "]\n" + CATALOG_TAIL,
        "shopcart/shipping.py": SHIPPING,
        "shopcart/pricing.py": PRICING,
        "shopcart/cart.py": CART,
        "tests/__init__.py": "",
        "tests/test_pricing.py": TEST_PRICING,
        "tests/test_cart.py": test_cart(prods),
        "tools/__init__.py": "",
        "tools/lint.py": LINT,
        "tools/report.py": REPORT,
        "build.sh": BUILD,
        "data/orders.csv": orders(prods),
    }
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
    os.chmod(os.path.join(root, "build.sh"), 0o755)
    by_cat = {}
    for i in range(1, 2401):
        cat = prods[(i * 13) % len(prods)]["category"]
        by_cat[cat] = by_cat.get(cat, 0) + 1
    return {"t2_count": sum(1 for p in prods if p["weight_g"] >= 1500 and p["stock"] == 0), "t4_toys": by_cat["toys"],
            "t4_by_cat": by_cat}


if __name__ == "__main__":
    print(json.dumps(write(sys.argv[1])))
