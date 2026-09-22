import sys
sys.path.insert(0, sys.argv[1])
from pricing import total
from api import checkout
from invoice import invoice_total
for cents, member, expected in [(1000, True, 900), (1000, False, 1000), (105, True, 95), (0, True, 0)]:
    assert total(cents, member) == expected
    assert checkout(cents, member) == {'total_cents': expected}
    assert invoice_total(cents, member) == expected
print('Shared pricing agrees across both public consumers, including rounding.')
# Reload consumers after replacing the canonical owner; copied formulas must fail.
import importlib
import pricing
pricing.total = lambda subtotal_cents, member=False: 713
api_module = importlib.reload(sys.modules['api'])
invoice_module = importlib.reload(sys.modules['invoice'])
assert api_module.checkout(1000, True) == {'total_cents': 713}
assert invoice_module.invoice_total(1000, True) == 713
