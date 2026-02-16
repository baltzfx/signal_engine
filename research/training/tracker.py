"""
Research: Lightweight experiment tracking.

Records every training run with hyperparameters, metrics, and model path
to a local SQLite database + JSON log.  No external dependencies (MLflow etc).

Usage:
    tracker = ExperimentTracker("my_experiment")
    run_id = tracker.start_run(params={"lr": 0.05, "num_leaves": 31})
    ...train model...
    tracker.log_metrics(run_id, {"auc": 0.83, "accuracy": 0.76})
    tracker.finish_run(run_id, model_path="research/models/model.json")
    tracker.summary()
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

EXPERIMENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "experiments")
os.makedirs(EXPERIMENTS_DIR, exist_ok=True)
DB_PATH = os.path.join(EXPERIMENTS_DIR, "experiments.db")


class ExperimentTracker:
    """File-based experiment tracker backed by SQLite."""

    def __init__(self, experiment_name: str = "default") -> None:
        self.experiment_name = experiment_name
        self._db = sqlite3.connect(DB_PATH)
        self._db.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id          TEXT PRIMARY KEY,
                experiment      TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'running',
                params          TEXT,
                metrics         TEXT,
                model_path      TEXT,
                notes           TEXT,
                started_at      TEXT NOT NULL,
                finished_at     TEXT
            );
        """)
        self._db.commit()

    def start_run(
        self,
        params: Optional[Dict[str, Any]] = None,
        notes: str = "",
    ) -> str:
        """Begin a new run. Returns a unique run_id."""
        run_id = f"{self.experiment_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self._db.execute(
            "INSERT INTO runs (run_id, experiment, params, notes, started_at) VALUES (?, ?, ?, ?, ?)",
            (
                run_id,
                self.experiment_name,
                json.dumps(params or {}),
                notes,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._db.commit()
        print(f"[ExperimentTracker] Run started: {run_id}")
        return run_id

    def log_metrics(self, run_id: str, metrics: Dict[str, Any]) -> None:
        """Attach metrics to a run."""
        self._db.execute(
            "UPDATE runs SET metrics = ? WHERE run_id = ?",
            (json.dumps(metrics, default=str), run_id),
        )
        self._db.commit()

    def finish_run(
        self,
        run_id: str,
        model_path: Optional[str] = None,
        status: str = "completed",
    ) -> None:
        """Mark a run as finished."""
        self._db.execute(
            "UPDATE runs SET status = ?, model_path = ?, finished_at = ? WHERE run_id = ?",
            (status, model_path, datetime.now(timezone.utc).isoformat(), run_id),
        )
        self._db.commit()
        print(f"[ExperimentTracker] Run finished: {run_id} ({status})")

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        row = self._db.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_runs(
        self,
        experiment: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List runs, newest first."""
        if experiment:
            rows = self._db.execute(
                "SELECT * FROM runs WHERE experiment = ? ORDER BY started_at DESC LIMIT ?",
                (experiment, limit),
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def best_run(self, metric: str = "auc", experiment: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return the run with the highest value for the given metric."""
        runs = self.list_runs(experiment=experiment or self.experiment_name, limit=1000)
        best = None
        best_val = -float("inf")
        for run in runs:
            m = run.get("metrics", {})
            if isinstance(m, dict) and metric in m:
                val = float(m[metric])
                if val > best_val:
                    best_val = val
                    best = run
        return best

    def summary(self, experiment: Optional[str] = None) -> None:
        """Print a summary table of runs."""
        runs = self.list_runs(experiment=experiment or self.experiment_name)
        if not runs:
            print("No runs found.")
            return

        print(f"\n{'='*80}")
        print(f"Experiment: {experiment or self.experiment_name}  ({len(runs)} runs)")
        print(f"{'='*80}")
        print(f"{'Run ID':<45} {'Status':<12} {'AUC':<8} {'Acc':<8} {'Model'}")
        print(f"{'-'*80}")
        for r in runs:
            m = r.get("metrics", {}) or {}
            auc = m.get("auc", "—") if isinstance(m, dict) else "—"
            acc = m.get("accuracy", "—") if isinstance(m, dict) else "—"
            if isinstance(auc, float):
                auc = f"{auc:.4f}"
            if isinstance(acc, float):
                acc = f"{acc:.4f}"
            print(f"{r['run_id']:<45} {r['status']:<12} {auc:<8} {acc:<8} {r.get('model_path', '—')}")
        print()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for field in ("params", "metrics"):
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

    def close(self) -> None:
        self._db.close()
