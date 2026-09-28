"""
ml/features.py

Builds the feature vector used BOTH when logging a completed trade
for training (ml/backtest.py) and when predicting on a brand-new
crossover live (ml/model.py). Keeping them identical is essential --
a model trained on one feature set and served on another silently
gives garbage predictions.

The original create_features() only extracted raw price, matching
nothing from the assignment's actual hint: "compare average LTQ over
the last 2 minutes with average LTQ over the last 5 minutes."
"""
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from utils.symbol_state import SymbolState

FEATURE_NAMES = [
    "ltq_surge_ratio",
    "etq_5m",
    "etq_20m",
    "etq_60m",
    "smma_gap_pct",
    "bid_ask_imbalance",
    "price_vs_avg20m_pct",
    "signal_is_buy",
]


def build_features(state: "SymbolState", signal_is_buy: bool) -> Dict[str, float]:
    avg2 = state.ltq_2m.get_etq(2 * 60) / max(1, _count(state.ltq_2m, 2 * 60))
    avg5 = state.ltq_5m.get_etq(5 * 60) / max(1, _count(state.ltq_5m, 5 * 60))
    ltq_surge_ratio = (avg2 / avg5) if avg5 > 0 else 1.0

    smma_fast = state.smma_fast.value or 0.0
    smma_slow = state.smma_slow.value or 1e-6
    smma_gap_pct = (smma_fast - smma_slow) / smma_slow * 100

    q = state.last_quote or {}
    bid_qty = q.get("bidQty", 0) or 0
    ask_qty = q.get("askQty", 0) or 0
    total_qty = bid_qty + ask_qty
    bid_ask_imbalance = (bid_qty - ask_qty) / total_qty if total_qty > 0 else 0.0

    ltp = q.get("ltp", 0) or 0
    avg20 = state.avg_price_20m.get_avg(20 * 60)
    price_vs_avg20m_pct = ((ltp - avg20) / avg20 * 100) if avg20 > 0 else 0.0

    return {
        "ltq_surge_ratio": ltq_surge_ratio,
        "etq_5m": state.etq_5m.get_etq(5 * 60),
        "etq_20m": state.etq_20m.get_etq(20 * 60),
        "etq_60m": state.etq_60m.get_etq(60 * 60),
        "smma_gap_pct": smma_gap_pct,
        "bid_ask_imbalance": bid_ask_imbalance,
        "price_vs_avg20m_pct": price_vs_avg20m_pct,
        "signal_is_buy": 1.0 if signal_is_buy else 0.0,
    }


def _count(etq_calc, seconds):
    """ETQCalculator doesn't expose a count, so derive it from its
    internal data list filtered to the window (kept tiny, no perf issue)."""
    import time
    now = time.time()
    return sum(1 for t, _ in etq_calc.data if now - t <= seconds)
