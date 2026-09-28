"""
ml/daily_performance.py

Maintains daily_performance.csv -- one row per trading day, so the
dashboard's analysis page (and you, before submission) can see the
Day 1 -> Day 2 trend at a glance instead of re-reading crossover_log.csv
by hand each time.

    python -m ml.daily_performance --date 2026-08-17

Reuses ml.evaluate.evaluate_day() for the numbers, so run this AFTER
ml/evaluate.py (or just run this -- it computes the same report
internally). Re-running for a date that's already in the CSV replaces
that row instead of duplicating it.
"""
import argparse
import os

from ml.backtest import LOG_PATH
from ml.evaluate import evaluate_day

PERF_PATH = os.path.join(os.path.dirname(LOG_PATH), "daily_performance.csv")

COLUMNS = [
    "trade_date",
    "total_trades",
    "wins",
    "losses",
    "win_rate",
    "total_pnl",
    "avg_pnl",
    "predictions_available",
    "model_accuracy",
    "trades_accepted_by_model",
    "win_rate_when_accepted",
    "pnl_when_accepted",
]

def record_day(trade_date: str, perf_path: str = PERF_PATH):
    import pandas as pd

    report = evaluate_day(trade_date)
    row = {col: report.get(col) for col in COLUMNS}
    row["trade_date"] = trade_date

    if os.path.exists(perf_path):
        df = pd.read_csv(perf_path)
        df = df[df["trade_date"] != trade_date]  # drop any existing row for this date
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df = df.sort_values("trade_date").reset_index(drop=True)
    df.to_csv(perf_path, index=False)
    print(f"Recorded {trade_date} to {perf_path}")
    print(df.to_string(index=False))
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute and store one day's performance summary."
    )
    parser.add_argument("--date", required=True, help="trade_date, e.g. 2026-08-17")
    args = parser.parse_args()
    record_day(args.date)