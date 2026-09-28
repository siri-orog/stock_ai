"""
ml/evaluate.py

Day-2 validation report: for a given trade_date, compares what the
model PREDICTED at entry time (predicted_decision / predicted_probability,
logged by ml/backtest.py) against what actually happened (label -- 1 if
the closed trade was profitable, 0 if not).

    python -m ml.evaluate --date 2026-08-17

Prints a report and (unless --no-save) writes it as JSON to
evaluation_report_<date>.json next to crossover_log.csv, so
ml/daily_performance.py and the dashboard analysis page can read it
back without recomputing.
"""
import argparse
import json
import os

from ml.backtest import LOG_PATH

REPORT_DIR = os.path.dirname(LOG_PATH)


def evaluate_day(trade_date: str, log_path: str = LOG_PATH) -> dict:
    import pandas as pd

    df = pd.read_csv(log_path)
    day_df = df[df.get("trade_date") == trade_date].copy()

    if day_df.empty:
        raise ValueError(f"No closed trades found for trade_date={trade_date}")

    # Only rows that actually carry a model verdict (older/legacy rows
    # or trades opened before a verdict existed won't have one).
    predicted_df = day_df[day_df["predicted_decision"].isin(["ACCEPT", "REJECT"])]

    total_trades = len(day_df)
    wins = int(day_df["label"].sum())
    losses = total_trades - wins
    win_rate = wins / total_trades if total_trades else 0.0
    total_pnl = float(day_df["pnl"].sum())
    avg_pnl = float(day_df["pnl"].mean()) if total_trades else 0.0

    report = {
        "trade_date": trade_date,
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 4),
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(avg_pnl, 2),
        "predictions_available": len(predicted_df),
    }

    if len(predicted_df) >= 1:
        from sklearn.metrics import (
            accuracy_score,
            precision_score,
            recall_score,
            f1_score,
            confusion_matrix,
        )

        y_true = predicted_df["label"].astype(int)
        y_pred = (predicted_df["predicted_decision"] == "ACCEPT").astype(int)

        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

        accepted = predicted_df[predicted_df["predicted_decision"] == "ACCEPT"]
        rejected = predicted_df[predicted_df["predicted_decision"] == "REJECT"]

        report.update(
            {
                "model_accuracy": round(accuracy_score(y_true, y_pred), 4),
                "model_precision": round(
                    precision_score(y_true, y_pred, zero_division=0), 4
                ),
                "model_recall": round(
                    recall_score(y_true, y_pred, zero_division=0), 4
                ),
                "model_f1": round(f1_score(y_true, y_pred, zero_division=0), 4),
                "confusion_matrix": {
                    "true_negative_correctly_rejected": int(tn),
                    "false_positive_accepted_but_lost": int(fp),
                    "false_negative_rejected_but_wouldve_won": int(fn),
                    "true_positive_correctly_accepted": int(tp),
                },
                "trades_accepted_by_model": len(accepted),
                "win_rate_when_accepted": round(accepted["label"].mean(), 4)
                if len(accepted)
                else None,
                "pnl_when_accepted": round(float(accepted["pnl"].sum()), 2)
                if len(accepted)
                else 0.0,
                "trades_rejected_by_model": len(rejected),
                "win_rate_when_rejected": round(rejected["label"].mean(), 4)
                if len(rejected)
                else None,
            }
        )
    else:
        report["note"] = (
            "No rows with a logged predicted_decision for this date -- "
            "run the live pipeline with the trained model active so "
            "predictions get recorded at entry time."
        )

    return report


def save_report(report: dict, report_dir: str = REPORT_DIR) -> str:
    path = os.path.join(report_dir, f"evaluation_report_{report['trade_date']}.json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    return path


def print_report(report: dict) -> None:
    print(f"=== Evaluation report: {report['trade_date']} ===")
    print(f"Total closed trades : {report['total_trades']}")
    print(f"Wins / Losses       : {report['wins']} / {report['losses']}")
    print(f"Win rate            : {report['win_rate']:.1%}")
    print(f"Total P/L           : {report['total_pnl']}")
    print(f"Avg P/L per trade   : {report['avg_pnl']}")
    if "model_accuracy" in report:
        print()
        print(f"Predictions logged  : {report['predictions_available']}")
        print(f"Model accuracy      : {report['model_accuracy']:.1%}")
        print(f"Model precision     : {report['model_precision']:.1%}")
        print(f"Model recall        : {report['model_recall']:.1%}")
        print(f"Model F1            : {report['model_f1']:.1%}")
        print(f"Confusion matrix    : {report['confusion_matrix']}")
        print(
            f"Accepted trades     : {report['trades_accepted_by_model']} "
            f"(win rate {report['win_rate_when_accepted']})"
        )
        print(
            f"Rejected trades     : {report['trades_rejected_by_model']} "
            f"(would-have win rate {report['win_rate_when_rejected']})"
        )
    else:
        print()
        print(report.get("note", ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate model predictions vs actual outcomes for one day."
    )
    parser.add_argument("--date", required=True, help="trade_date to evaluate, e.g. 2026-08-17")
    parser.add_argument("--no-save", action="store_true", help="Don't write the JSON report file")
    args = parser.parse_args()

    report = evaluate_day(args.date)
    print_report(report)
    if not args.no_save:
        path = save_report(report)
        print(f"\nSaved to {path}")