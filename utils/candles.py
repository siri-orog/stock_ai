"""
utils/candles.py

SMMA(20)/SMMA(120) are conventionally computed on a fixed timeframe
(e.g. 1-minute candle closes), not on every raw tick. This aggregator
buckets incoming ticks into 1-minute OHLC candles per symbol and
reports a finalized close price only when a candle completes -- that
close price is what should feed the SMMA trackers.
"""
import time


class CandleAggregator:
    """Buckets ticks into fixed-size (default 60s) candles for one symbol."""

    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self._bucket_start = None
        self._open = self._high = self._low = self._close = None
        self.closed_candles = []  # list of dicts, most recent last

    def add_tick(self, price: float, timestamp: float = None):
        """Returns the finalized candle dict if this tick closed the
        previous bucket, else None."""
        ts = timestamp or time.time()
        bucket = int(ts // self.interval_seconds) * self.interval_seconds

        finalized = None
        if self._bucket_start is None:
            self._bucket_start = bucket
            self._open = self._high = self._low = self._close = price
        elif bucket != self._bucket_start:
            finalized = {
                "start": self._bucket_start,
                "open": self._open,
                "high": self._high,
                "low": self._low,
                "close": self._close,
            }
            self.closed_candles.append(finalized)
            del self.closed_candles[:-500]  # cap memory

            self._bucket_start = bucket
            self._open = self._high = self._low = self._close = price
        else:
            self._high = max(self._high, price)
            self._low = min(self._low, price)
            self._close = price

        return finalized

    def closes(self):
        return [c["close"] for c in self.closed_candles]
