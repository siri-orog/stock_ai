"""
ml/model.py

Replaces the previous stub:

    def predict(features):
        prob = random.uniform(0.4, 0.9)   # NOT a model

with an actual trained classifier. Train it once you've accumulated
labeled trades in crossover_log.csv (produced by ml/backtest.py):

    python -m ml.model          # trains and saves crossover_model.joblib

Until a trained model file exists, evaluate_trade() falls back to a
transparent RULE-BASED heuristic (clearly labeled as such in the
"reason" string) instead of silently returning random numbers -- so
the dashboard is always honest about whether it's showing a trained
prediction or a placeholder.
"""
import os
from typing import Dict

from ml.features import FEATURE_NAMES, build_features

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "crossover_model.joblib")
LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "crossover_log.csv")


def train(
    log_path: str = LOG_PATH,
    model_path: str = MODEL_PATH,
    trade_date: str = None,
    start_date: str = None,
    end_date: str = None,
):
    """Train on crossover_log.csv, optionally restricted to a single day
    (trade_date, e.g. "2026-08-14") or an inclusive date range
    (start_date/end_date). This is what makes the "Day 1 -> train ->
    Day 2 validate" workflow possible: run with trade_date=<Day 1's
    date> so the model never sees Day 2 rows before they're evaluated
    against it in ml/evaluate.py.
    """
    import joblib
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report

    df = pd.read_csv(log_path)

    if trade_date:
        df = df[df["trade_date"] == trade_date]
    elif start_date or end_date:
        if start_date:
            df = df[df["trade_date"] >= start_date]
        if end_date:
            df = df[df["trade_date"] <= end_date]

    if len(df) < 30 or df["label"].nunique() < 2:
        window = trade_date or f"{start_date or '...'}..{end_date or '...'}"
        raise ValueError(
            f"Only {len(df)} labeled trades found for {window} (need both "
            "profitable and losing examples, ~30+ minimum). Let the live "
            "pipeline run longer to accumulate crossovers before training."
        )

    X = df[FEATURE_NAMES]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    clf = RandomForestClassifier(
        n_estimators=300, max_depth=6, min_samples_leaf=5,
        class_weight="balanced", random_state=42,
    )
    clf.fit(X_train, y_train)

    print(classification_report(y_test, clf.predict(X_test)))
    joblib.dump(clf, model_path)
    print(f"Model saved to {model_path}")
    return clf


class CrossoverPredictor:
    """Loads the trained model if one exists; otherwise falls back to
    a transparent rule-based heuristic so the dashboard never shows
    fabricated confidence numbers."""

    def __init__(self, model_path: str = MODEL_PATH):
        self.model = None
        self.mode = "heuristic"
        if os.path.exists(model_path):
            try:
                import joblib
                self.model = joblib.load(model_path)
                self.mode = "trained"
            except Exception:
                self.model = None

    def predict(self, features: Dict[str, float]):
        if self.model is not None:
            import pandas as pd
            row = pd.DataFrame([[features[n] for n in FEATURE_NAMES]], columns=FEATURE_NAMES)
            proba = float(self.model.predict_proba(row)[0][1])
            verdict = "ACCEPT" if proba >= 0.55 else "REJECT"
            reason = self._explain(features)
            return proba, verdict, reason

        # --- heuristic fallback (no trained model yet) ---
        score = 0.5
        reasons = []
        if features["ltq_surge_ratio"] > 1.5:
            score += 0.15
            reasons.append(f"LTQ surged {features['ltq_surge_ratio']:.1f}x vs 5-min avg")
        elif features["ltq_surge_ratio"] < 0.8:
            score -= 0.1
            reasons.append("LTQ below normal -- weak participation")
        if abs(features["smma_gap_pct"]) > 1:
            score += 0.1
            reasons.append(f"strong SMMA separation ({features['smma_gap_pct']:.2f}%)")
        else:
            reasons.append("SMMAs close together -- weak crossover")
        if abs(features["bid_ask_imbalance"]) > 0.2:
            side = "buy" if features["bid_ask_imbalance"] > 0 else "sell"
            score += 0.05
            reasons.append(f"order book skewed toward {side} side")
        score = max(0.0, min(1.0, score))
        verdict = "ACCEPT" if score >= 0.55 else "REJECT"
        reason = "[heuristic, not yet trained] " + "; ".join(reasons)
        return score, verdict, reason

    def _explain(self, features):
        parts = []
        if features["ltq_surge_ratio"] > 1.5:
            parts.append(f"LTQ surged {features['ltq_surge_ratio']:.1f}x vs 5-min avg")
        elif features["ltq_surge_ratio"] < 0.8:
            parts.append("LTQ below normal -- weak participation")
        if abs(features["smma_gap_pct"]) > 1:
            parts.append(f"strong SMMA separation ({features['smma_gap_pct']:.2f}%)")
        else:
            parts.append("SMMAs close together -- weak crossover")
        if abs(features["bid_ask_imbalance"]) > 0.2:
            side = "buy" if features["bid_ask_imbalance"] > 0 else "sell"
            parts.append(f"order book skewed toward {side} side")
        return "; ".join(parts) if parts else "no strong signal either way"


_predictor = None


def evaluate_trade(state, signal_is_buy: bool) -> dict:
    """Wrapper used by the dashboard/server -- builds features from the
    symbol's live state and returns a verdict dict."""
    global _predictor
    if _predictor is None:
        _predictor = CrossoverPredictor()
    features = build_features(state, signal_is_buy)
    proba, verdict, reason = _predictor.predict(features)
    return {"probability": round(proba, 2), "decision": verdict, "reason": reason}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Train the crossover model, optionally restricted to "
        "one day's or a date range's rows in crossover_log.csv."
    )
    parser.add_argument(
        "--date", default=None, help="Train only on this trade_date, e.g. 2026-08-14"
    )
    parser.add_argument("--start-date", default=None, help="Inclusive range start")
    parser.add_argument("--end-date", default=None, help="Inclusive range end")
    args = parser.parse_args()

    train(trade_date=args.date, start_date=args.start_date, end_date=args.end_date)