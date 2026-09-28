"""
ml/train_day.py

Day-wise training entry point for the "Day 1 -> train -> Day 2
validate" workflow:

    python -m ml.train_day --date 2026-08-14

- Trains ONLY on crossover_log.csv rows whose trade_date matches
  --date (i.e. Day 1's closed trades), via ml.model.train().
- Saves the result to crossover_model.joblib (the file
  CrossoverPredictor loads live) AND a dated copy
  crossover_model_<date>.joblib, so each day's model is kept for
  later comparison instead of being silently overwritten.

Run this at the end of Day 1's trading session, then start the
server fresh on Day 2 -- ml/model.py's CrossoverPredictor will pick
up the newly trained crossover_model.joblib automatically.
"""
import argparse
import os
import shutil

from ml.model import train, MODEL_PATH


def train_day(trade_date: str, log_path: str = None):
    kwargs = {"trade_date": trade_date}
    if log_path:
        kwargs["log_path"] = log_path

    clf = train(model_path=MODEL_PATH, **kwargs)

    dated_path = os.path.join(
        os.path.dirname(MODEL_PATH), f"crossover_model_{trade_date}.joblib"
    )
    shutil.copyfile(MODEL_PATH, dated_path)
    print(f"Day-wise model also archived to {dated_path}")
    return clf


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train the crossover model on a single day's rows "
        "(Day 1) and save it as the live model for Day 2."
    )
    parser.add_argument(
        "--date", required=True, help="Day to train on, e.g. 2026-08-14 (trade_date)"
    )
    parser.add_argument(
        "--log-path", default=None, help="Override crossover_log.csv path"
    )
    args = parser.parse_args()
    train_day(args.date, log_path=args.log_path)