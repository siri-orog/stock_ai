"""
utils/symbol_state.py

The missing piece that ties your existing utilities together. Each
symbol gets ONE SymbolState that persists across polling cycles (this
is exactly what Streamlit's rerun-the-whole-script model fights
against, and why the FastAPI backend keeps this in memory instead).

Per poll, call state.on_quote(quote) where quote is one row from
data.fetch.get_live_data() -- it:
  1. Feeds the tick price into the 1-min candle aggregator
  2. On candle close, updates SMMA20/SMMA120 and checks for a crossover
  3. Derives this-interval traded quantity from the delta in cumulative
     `volume` (a valid ETQ proxy when only REST polling is available --
     see data/fetch.py) and folds it into the 5/20/60-min ETQ windows
  4. Updates rolling average LTP (20/60-min) and LTQ (2/5-min, used for
     the ML surge-ratio feature)
  5. Applies the price + liquidity screen
"""
import time
from typing import Optional

from indicators.smma import SMMA
from strategy.crossover import CrossoverDetector, CrossoverEvent
from strategy.filters import filter_stock
from utils.candles import CandleAggregator
from utils.etq import ETQCalculator
from utils.avg_price import AvgPrice


class SymbolState:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.candles = CandleAggregator(interval_seconds=60)
        self.smma_fast = SMMA(20)
        self.smma_slow = SMMA(120)
        self.detector = CrossoverDetector(symbol)

        self.etq_5m = ETQCalculator()
        self.etq_20m = ETQCalculator()
        self.etq_60m = ETQCalculator()
        self.avg_price_20m = AvgPrice()
        self.avg_price_60m = AvgPrice()
        self.ltq_2m = ETQCalculator()
        self.ltq_5m = ETQCalculator()

        self._prev_volume: Optional[int] = None
        self.last_quote: Optional[dict] = None

    def seed_history(self, closes: list) -> None:
        """Pre-warm SMMA20/SMMA120 with real historical 1-minute closes
        (oldest first) so they're ready immediately instead of waiting
        ~20min / ~2hrs for live ticks to build up. Call this once at
        startup, before on_quote() starts receiving live data."""
        for close in closes:
            self.smma_fast.update(close)
            self.smma_slow.update(close)
        # seed the candle aggregator's last close too, so the next
        # live tick continues the series correctly instead of starting
        # a fresh bucket with a jump
        if closes:
            self.candles._close = closes[-1]

    def on_quote(self, quote: dict) -> Optional[CrossoverEvent]:
        ltp = quote.get("ltp")
        volume = quote.get("volume", 0)
        now = time.time()

        # Traded quantity SINCE THE LAST POLL, derived from the change
        # in cumulative day volume -- this is the ETQ/LTQ proxy for a
        # polling-based (non-WebSocket) feed.
        interval_qty = 0
        if self._prev_volume is not None and volume >= self._prev_volume:
            interval_qty = volume - self._prev_volume
        self._prev_volume = volume

        if ltp is not None:
            self.avg_price_20m.add(ltp)
            self.avg_price_60m.add(ltp)

        self.etq_5m.add(interval_qty)
        self.etq_20m.add(interval_qty)
        self.etq_60m.add(interval_qty)
        self.ltq_2m.add(interval_qty)
        self.ltq_5m.add(interval_qty)

        self.last_quote = quote

        event = None
        if ltp is not None:
            finalized_candle = self.candles.add_tick(ltp, now)
            if finalized_candle is not None:
                self.smma_fast.update(finalized_candle["close"])
                self.smma_slow.update(finalized_candle["close"])
                if self.smma_fast.ready and self.smma_slow.ready:
                    event = self.detector.update(
                        self.smma_fast.value, self.smma_slow.value, ltp
                    )
        return event

    def passes_screen(self) -> bool:
        if not self.last_quote:
            return False
        return filter_stock(
            self.last_quote.get("ltp"),
            self.last_quote.get("bidQty"),
            self.last_quote.get("askQty"),
        )

    def signal_label(self) -> str:
        """Current SMMA relative position for display (HOLD until the
        first crossover has actually happened once)."""
        if not (self.smma_fast.ready and self.smma_slow.ready):
            return "HOLD"
        return "BUY" if self.smma_fast.value > self.smma_slow.value else "SELL"

    def to_row(self) -> dict:
        q = self.last_quote or {}
        return {
            "symbol": self.symbol,
            "ltp": q.get("ltp"),
            "smma20": round(self.smma_fast.value, 2) if self.smma_fast.ready else "building...",
            "smma120": round(self.smma_slow.value, 2) if self.smma_slow.ready else "building...",
            "bidQty": q.get("bidQty", 0),
            "askQty": q.get("askQty", 0),
            "bidPrice": q.get("bidPrice", 0),
            "askPrice": q.get("askPrice", 0),
            "etq_5m": self.etq_5m.get_etq(5 * 60),
            "etq_20m": self.etq_20m.get_etq(20 * 60),
            "etq_60m": self.etq_60m.get_etq(60 * 60),
            "avg_ltp_20m": round(self.avg_price_20m.get_avg(20 * 60), 2),
            "avg_ltp_60m": round(self.avg_price_60m.get_avg(60 * 60), 2),
        }
