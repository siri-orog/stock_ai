"""
strategy/filters.py

Implements the assignment's actual screening rule:
  - LTP between Rs 30 and Rs 500
  - Bid quantity  > 10,00,000
  - Ask quantity  > 10,00,000

The original filter_stock(price) only checked price > 100 and ignored
liquidity entirely -- neither the price band nor the bid/ask condition
from the brief was enforced.
"""

PRICE_MIN, PRICE_MAX = 30, 500
MIN_BID_QTY, MIN_ASK_QTY = 1_000_000, 1_000_000  # 10,00,000


def filter_stock(price, bid_qty=None, ask_qty=None) -> bool:
    """Backward-compatible signature: bid_qty/ask_qty are optional so
    existing single-argument call sites don't crash, but the liquidity
    check is SKIPPED unless both are supplied. Always pass both in the
    live pipeline -- see symbol_state.py."""
    if price is None or not (PRICE_MIN <= price <= PRICE_MAX):
        return False
    if bid_qty is not None and bid_qty <= MIN_BID_QTY:
        return False
    if ask_qty is not None and ask_qty <= MIN_ASK_QTY:
        return False
    return True
