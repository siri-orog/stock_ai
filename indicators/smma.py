"""
indicators/smma.py

calculate_smma() is kept for backward compatibility (batch calculation
over an already-collected price list), but the live pipeline uses the
SMMA class below instead: an incremental, stateful tracker.

Why the class matters: SMMA(20) and SMMA(120) must be computed over
ONE symbol's price history through time. Feeding a cross-sectional
list (e.g. one LTP per different stock) into calculate_smma(), as the
original dashboard did, produces meaningless numbers. Each symbol
needs its OWN SMMA instance that persists across refresh cycles.
"""


def calculate_smma(prices, period):
    """Batch SMMA over a single list of sequential prices for ONE
    instrument. Kept for compatibility / offline analysis."""
    smma = []
    for i in range(len(prices)):
        if i < period:
            smma.append(prices[i])
        else:
            prev = smma[i - 1]
            value = (prev * (period - 1) + prices[i]) / period
            smma.append(value)
    return smma


class SMMA:
    """Incremental Smoothed Moving Average for a single symbol.

    SMMA_today = (SMMA_yesterday * (period - 1) + price_today) / period

    Feed it one new (finalized) price at a time via update(); it keeps
    its own running value between calls, so it works correctly across
    live polling cycles.
    """

    def __init__(self, period: int):
        self.period = period
        self._seed = []
        self.value = None

    def update(self, price: float):
        if self.value is None:
            self._seed.append(price)
            if len(self._seed) == self.period:
                self.value = sum(self._seed) / self.period
            return self.value
        self.value = (self.value * (self.period - 1) + price) / self.period
        return self.value

    @property
    def ready(self) -> bool:
        return self.value is not None
