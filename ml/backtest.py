"""
ml/backtest.py

The assignment's "Trading Logic" section, implemented: record LTP when
a crossover fires, hold the position open, and when the OPPOSITE
crossover fires, close it out and compute P/L. Every closed trade is
written to crossover_log.csv as one labeled training row (label=1 if
profitable, else 0). Run the live pipeline for a few days to
accumulate enough labeled rows, then train the model (see model.py).

CHANGE (day-wise train/validate workflow): each row now also records
- trade_date / entry_time / exit_time  -> lets us split rows by day
  (e.g. train on Day 1's rows, evaluate against Day 2's rows).
- predicted_decision / predicted_probability -> the ACCEPT/REJECT
  verdict and confidence the model (or heuristic) gave at the moment
  the trade was OPENED, so ml/evaluate.py can later check whether
  that prediction actually lined up with the real outcome (label).

If an older crossover_log.csv (without these columns) already exists,
it's renamed to crossover_log_legacy.csv on first run rather than
silently mixed with the new schema.
"""
import csv
import os
from datetime import datetime
from typing import Dict, Optional

from strategy.crossover import CrossoverEvent, SignalType
from ml.features import build_features, FEATURE_NAMES

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "crossover_log.csv")

ROW_COLUMNS = (
    FEATURE_NAMES
    + [
        "symbol",
        "trade_date",
        "entry_time",
        "exit_time",
        "predicted_decision",
        "predicted_probability",
        "entry_ltp",
        "exit_ltp",
        "pnl",
        "label",
    ]
)


class TradeLogger:
    def __init__(self, log_path: str = LOG_PATH):
        self.log_path = log_path
        self._open_trades: Dict[str, dict] = {}  # symbol -> open trade info
        self._ensure_header()

    def _ensure_header(self):
        if os.path.exists(self.log_path):
            with open(self.log_path, "r", newline="") as f:
                first_line = f.readline().strip()
            current_header = ",".join(ROW_COLUMNS)
            if first_line == current_header:
                return  # already the new schema, nothing to do
            # Old schema (pre predicted_decision/date columns) -- keep it
            # around for reference but don't mix it with the new rows.
            legacy_path = os.path.join(
                os.path.dirname(self.log_path), "crossover_log_legacy.csv"
            )
            if not os.path.exists(legacy_path):
                os.replace(self.log_path, legacy_path)
                print(f"[TradeLogger] Old-schema log preserved at {legacy_path}")

        with open(self.log_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(ROW_COLUMNS)

    def on_crossover(
        self, event: CrossoverEvent, state, verdict: Optional[dict] = None
    ) -> None:
        """verdict, if given, is the model/heuristic's ACCEPT/REJECT call
        made for THIS crossover (i.e. the prediction at entry time) --
        pass the dict returned by ml.model.evaluate_trade()."""
        symbol = event.symbol
        open_trade = self._open_trades.get(symbol)

        # Close an existing OPPOSITE-direction trade first
        if open_trade and open_trade["signal"] != event.signal:
            entry_ltp = open_trade["entry_ltp"]
            exit_ltp = event.ltp
            pnl = (
                (exit_ltp - entry_ltp)
                if open_trade["signal"] == SignalType.BUY
                else (entry_ltp - exit_ltp)
            )
            label = 1 if pnl > 0 else 0
            self._write_row(
                open_trade["features"],
                symbol,
                open_trade["trade_date"],
                open_trade["entry_time"],
                event.timestamp,
                open_trade["predicted_decision"],
                open_trade["predicted_probability"],
                entry_ltp,
                exit_ltp,
                pnl,
                label,
            )
            del self._open_trades[symbol]

        # Open a new trade on this crossover
        features = build_features(state, signal_is_buy=(event.signal == SignalType.BUY))
        entry_dt = datetime.fromtimestamp(event.timestamp)
        self._open_trades[symbol] = {
            "signal": event.signal,
            "entry_ltp": event.ltp,
            "features": features,
            "trade_date": entry_dt.strftime("%Y-%m-%d"),
            "entry_time": event.timestamp,
            "predicted_decision": (verdict or {}).get("decision", ""),
            "predicted_probability": (verdict or {}).get("probability", ""),
        }

    def _write_row(
        self,
        features,
        symbol,
        trade_date,
        entry_time,
        exit_time,
        predicted_decision,
        predicted_probability,
        entry_ltp,
        exit_ltp,
        pnl,
        label,
    ):
        with open(self.log_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [features[name] for name in FEATURE_NAMES]
                + [
                    symbol,
                    trade_date,
                    _fmt_time(entry_time),
                    _fmt_time(exit_time),
                    predicted_decision,
                    predicted_probability,
                    entry_ltp,
                    exit_ltp,
                    pnl,
                    label,
                ]
            )


def _fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")