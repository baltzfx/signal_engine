"""
AI inference module — Version 2 upgrade.

Loads a trained LightGBM / XGBoost model from disk and scores
feature vectors read from Redis.

Supports:
  • GPU / CPU auto-detection and fallback
  • Non-blocking inference via ``run_in_executor``
  • **Hot-reload** — automatically reloads the model when the file
    on disk changes (checked by mtime on every ``predict()`` call)

This module is OPTIONAL.  The engine works fully in rule-based mode
when settings.ai_enabled is False.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import os
from typing import Any, Dict, Optional

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

_model: Any = None
_model_mtime: float = 0.0          # last known mtime of the model file
_feature_order: list[str] = [
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


def _detect_gpu() -> bool:
    """Check if GPU acceleration is available for tree models."""
    try:
        import lightgbm as lgb
        # LightGBM GPU build check
        if "gpu" in lgb.Booster.__init__.__doc__.lower() if lgb.Booster.__init__.__doc__ else False:
            return True
    except Exception:
        pass
    try:
        import xgboost as xgb
        # XGBoost GPU check
        if xgb.build_info().get("USE_CUDA", False):
            return True
    except Exception:
        pass
    return False


_gpu_available: Optional[bool] = None


def _load_model() -> Any:
    """Load the serialised model once (or reload if file changed). Uses GPU if available."""
    global _model, _gpu_available, _model_mtime
    model_path = settings.ai_model_path

    if not os.path.exists(model_path):
        logger.error("AI model not found at %s", model_path)
        return None

    # Hot-reload check — if file changed on disk, force a reload
    try:
        current_mtime = os.path.getmtime(model_path)
    except OSError:
        current_mtime = 0.0

    if _model is not None and current_mtime == _model_mtime:
        return _model                       # no change, reuse cached model

    if _model is not None:
        logger.info("Model file changed (mtime %.0f → %.0f) — hot-reloading …",
                     _model_mtime, current_mtime)
        _model = None                       # force reload below
        
        # Track reload in Prometheus
        try:
            from app.core import prometheus_metrics as prom
            prom.ai_model_reloads_total.labels(model_type="lightgbm").inc()
        except Exception:
            pass

    if _gpu_available is None:
        _gpu_available = _detect_gpu()
        logger.info("GPU available: %s", _gpu_available)

    ext = os.path.splitext(model_path)[1].lower()
    try:
        if ext in (".json", ".txt"):
            # Try LightGBM first
            try:
                import lightgbm as lgb
                _model = lgb.Booster(model_file=model_path)
                if _gpu_available:
                    # Re-set parameters for GPU prediction
                    _model.reset_parameter({"device": "gpu", "gpu_platform_id": 0, "gpu_device_id": 0})
                    logger.info("LightGBM model loaded with GPU acceleration")
                else:
                    logger.info("LightGBM model loaded (CPU)")
                _model_mtime = current_mtime
                
                # Extract and record feature importance
                _record_feature_importance(_model, "lightgbm")
                
                return _model
            except Exception:
                pass
            # Fall back to XGBoost
            import xgboost as xgb
            _model = xgb.Booster()
            _model.load_model(model_path)
            if _gpu_available:
                _model.set_param({"predictor": "gpu_predictor"})
                logger.info("XGBoost model loaded with GPU acceleration")
            else:
                logger.info("XGBoost model loaded (CPU)")
            _model_mtime = current_mtime
            return _model
        elif ext == ".pkl":
            import joblib
            _model = joblib.load(model_path)
            logger.info("Loaded pickle model from %s", model_path)
            _model_mtime = current_mtime
            return _model
        else:
            logger.error("Unsupported model format: %s", ext)
            return None
    except Exception:
        logger.exception("Failed to load AI model")
        return None


def _build_feature_vector(features: Dict[str, str]) -> np.ndarray:
    """Convert Redis feature hash into ordered numpy vector."""
    vec = []
    for key in _feature_order:
        val = features.get(key, "0")
        try:
            vec.append(float(val))
        except (ValueError, TypeError):
            vec.append(0.0)
    return np.array([vec], dtype=np.float32)


def _sync_predict(model: Any, X: np.ndarray) -> Dict[str, float]:
    """
    Synchronous prediction — called via run_in_executor
    to avoid blocking the event loop.
    """
    # Attempt predict_proba (sklearn-style)
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X)[0]
    elif hasattr(model, "predict"):
        # LightGBM Booster / XGBoost Booster
        raw = model.predict(X)
        if isinstance(raw, np.ndarray) and raw.ndim == 2:
            probs = raw[0]
        else:
            p = float(raw[0]) if hasattr(raw, "__len__") else float(raw)
            probs = [1 - p, p]
    else:
        raise RuntimeError("Model has no predict API")

    p_short = float(probs[0])
    p_long = float(probs[1]) if len(probs) > 1 else 1 - p_short
    confidence = abs(p_long - p_short)

    return {
        "probability_long": round(p_long, 4),
        "probability_short": round(p_short, 4),
        "confidence": round(confidence, 4),
    }


async def predict(
    symbol: str,
    features: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """
    Run inference and return:
        {
            "probability_long": float,
            "probability_short": float,
            "confidence": float,
        }
    Returns None if model is unavailable.
    Runs blocking prediction in a thread executor to keep the event loop free.
    """
    model = _load_model()
    if model is None:
        return None

    X = _build_feature_vector(features)

    # Track inference in Prometheus
    try:
        from app.core import prometheus_metrics as prom
        import time
        start = time.perf_counter()
    except Exception:
        start = None

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            functools.partial(_sync_predict, model, X),
        )
        
        # Track inference latency
        if start is not None:
            try:
                from app.core import prometheus_metrics as prom
                import time
                duration = time.perf_counter() - start
                prom.ai_inference_duration_seconds.labels(model_type="lightgbm").observe(duration)
                prom.ai_inference_total.labels(model_type="lightgbm").inc()
            except Exception:
                pass
        
        logger.debug("AI prediction for %s: %s", symbol, result)
        return result
    except Exception:
        logger.exception("AI prediction error for %s", symbol)
        return None


def _record_feature_importance(model: Any, model_type: str) -> None:
    """Extract and record feature importance from a trained model."""
    try:
        import time
        from app.core import prometheus_metrics as prom
        
        importances = {}
        
        # Extract feature importance based on model type
        if hasattr(model, "feature_importance"):
            # LightGBM Booster
            importance_values = model.feature_importance(importance_type="gain")
            for i, val in enumerate(importance_values):
                if i < len(_feature_order):
                    feature_name = _feature_order[i]
                    importances[feature_name] = float(val)
        elif hasattr(model, "get_score"):
            # XGBoost Booster
            scores = model.get_score(importance_type="gain")
            for i, feature_name in enumerate(_feature_order):
                importances[feature_name] = scores.get(f"f{i}", 0.0)
        elif hasattr(model, "feature_importances_"):
            # Sklearn-style model
            for i, val in enumerate(model.feature_importances_):
                if i < len(_feature_order):
                    feature_name = _feature_order[i]
                    importances[feature_name] = float(val)
        
        if importances:
            # Normalize to sum to 1.0
            total = sum(importances.values())
            if total > 0:
                importances = {k: v / total for k, v in importances.items()}
            
            # Record to Prometheus
            for feature_name, importance in importances.items():
                prom.feature_importance.labels(
                    feature_name=feature_name,
                    model_type=model_type
                ).set(importance)
            
            # Record to database (async)
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                
                async def save_importance():
                    from app.storage.database import record_feature_importance
                    await record_feature_importance(model_type, importances)
                
                loop.create_task(save_importance())
            except Exception:
                pass
            
            logger.info("Recorded feature importance for %s model: top 3 = %s", 
                       model_type, 
                       sorted(importances.items(), key=lambda x: x[1], reverse=True)[:3])
    
    except Exception:
        logger.warning("Failed to extract feature importance from %s model", model_type, exc_info=True)

