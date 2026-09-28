"""
strategy/crossover.py

get_signal() is kept for quick one-off comparisons, but the live
pipeline uses CrossoverDetector: it remembers whether SMMA20 was
last above or below SMMA120 and only fires an event on the actual
TRANSITION -- which is what "detect every SMMA crossover" in the
assignment means. Calling get_signal() every tick, as the original
dashboard did, reports the current relative position on every single
refresh (often for hours at a stretch), not the moment of crossing.
"""
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


def get_signal(smma20, smma120):
    if smma20 > smma120:
        return "BUY"
    elif smma20 < smma120:
        return "SELL"
    else:
        return "HOLD"


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class CrossoverEvent:
    symbol: str
    signal: SignalType
    timestamp: float
    ltp: float
    smma_fast: float
    smma_slow: float


class CrossoverDetector:
    """Per-symbol stateful crossover detector. Call update() every time
    a NEW candle-close SMMA pair is available; it returns a
    CrossoverEvent only on the tick where the relationship flips."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self._prev_state: Optional[str] = None  # "above" | "below"

    def update(self, smma_fast, smma_slow, ltp) -> Optional[CrossoverEvent]:
        if smma_fast is None or smma_slow is None:
            return None

        current_state = "above" if smma_fast > smma_slow else "below"
        event = None

        if self._prev_state is not None and current_state != self._prev_state:
            signal = SignalType.BUY if current_state == "above" else SignalType.SELL
            event = CrossoverEvent(
                symbol=self.symbol,
                signal=signal,
                timestamp=time.time(),
                ltp=ltp,
                smma_fast=smma_fast,
                smma_slow=smma_slow,
            )

        self._prev_state = current_state
        return event
