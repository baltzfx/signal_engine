"""
Research: Model training pipeline.

Trains a LightGBM (or XGBoost) binary classifier and exports
the model in a format compatible with the production AI module.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

FEATURE_COLS = [
    "ema_slope",
    "vwap_distance",
    "atr",
    "range_expansion",
    "oi_delta",
    "funding_zscore",
    "liq_ratio",
    "liq_total_usd",
    "ob_imbalance",
]

LABEL_COL = "label"

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def split_data(
    df: pd.DataFrame,
    test_ratio: float = 0.2,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Time-aware split — no shuffling."""
    n = len(df)
    split_idx = int(n * (1 - test_ratio))
    return df.iloc[:split_idx].copy(), df.iloc[split_idx:].copy()


def train_lightgbm(
    df_train: pd.DataFrame,
    df_test: pd.DataFrame,
    params: Optional[Dict[str, Any]] = None,
    model_name: str = "model",
) -> Dict[str, Any]:
    """
    Train a LightGBM classifier and save it.
    Returns evaluation metrics.
    """
    import lightgbm as lgb

    X_train = df_train[FEATURE_COLS].values
    y_train = df_train[LABEL_COL].values
    X_test = df_test[FEATURE_COLS].values
    y_test = df_test[LABEL_COL].values

    default_params = {
        "objective": "binary",
        "metric": "auc",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
    }
    if params:
        default_params.update(params)

    dtrain = lgb.Dataset(X_train, label=y_train, feature_name=FEATURE_COLS)
    dtest = lgb.Dataset(X_test, label=y_test, reference=dtrain, feature_name=FEATURE_COLS)

    model = lgb.train(
        default_params,
        dtrain,
        num_boost_round=500,
        valid_sets=[dtest],
        callbacks=[lgb.early_stopping(30), lgb.log_evaluation(50)],
    )

    # Save model
    model_path = os.path.join(MODELS_DIR, f"{model_name}.json")
    model.save_model(model_path)
    print(f"Model saved → {model_path}")

    # Evaluate
    from sklearn.metrics import roc_auc_score, accuracy_score, classification_report

    preds = model.predict(X_test)
    auc = roc_auc_score(y_test, preds)
    acc = accuracy_score(y_test, (preds > 0.5).astype(int))
    report = classification_report(y_test, (preds > 0.5).astype(int), output_dict=True)

    metrics = {"auc": auc, "accuracy": acc, "report": report}
    metrics_path = os.path.join(MODELS_DIR, f"{model_name}_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"Metrics saved → {metrics_path}")

    return metrics


def train_xgboost(
    df_train: pd.DataFrame,
    df_test: pd.DataFrame,
    params: Optional[Dict[str, Any]] = None,
    model_name: str = "model_xgb",
) -> Dict[str, Any]:
    """Train XGBoost classifier and save."""
    import xgboost as xgb

    X_train = df_train[FEATURE_COLS].values
    y_train = df_train[LABEL_COL].values
    X_test = df_test[FEATURE_COLS].values
    y_test = df_test[LABEL_COL].values

    default_params = {
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "verbosity": 0,
    }
    if params:
        default_params.update(params)

    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=FEATURE_COLS)
    dtest = xgb.DMatrix(X_test, label=y_test, feature_names=FEATURE_COLS)

    model = xgb.train(
        default_params,
        dtrain,
        num_boost_round=500,
        evals=[(dtest, "test")],
        early_stopping_rounds=30,
        verbose_eval=50,
    )

    model_path = os.path.join(MODELS_DIR, f"{model_name}.json")
    model.save_model(model_path)
    print(f"Model saved → {model_path}")

    from sklearn.metrics import roc_auc_score, accuracy_score, classification_report

    preds = model.predict(dtest)
    auc = roc_auc_score(y_test, preds)
    acc = accuracy_score(y_test, (preds > 0.5).astype(int))
    report = classification_report(y_test, (preds > 0.5).astype(int), output_dict=True)

    metrics = {"auc": auc, "accuracy": acc, "report": report}
    metrics_path = os.path.join(MODELS_DIR, f"{model_name}_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    return metrics
