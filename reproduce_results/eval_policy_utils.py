"""Offline utilities for evaluation-routing policy training."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class EvalSampleRow:
    session_id: int
    round_number: int
    action: str
    reward: float
    features: List[float]


def build_eval_samples(data_dir: Path) -> List[EvalSampleRow]:
    path = data_dir / "eval_policy_trajectory.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    if df.empty:
        return []

    rows: List[EvalSampleRow] = []
    for _, row in df.iterrows():
        action = str(row.get("action", "") or "")
        if not action:
            continue
        features = [
            1.0,
            float(row.get("round", 1)) / max(float(df["round"].max() if "round" in df.columns else 1), 1.0),
            min(max(float(row.get("answer_length", 0)) / 1200.0, 0.0), 1.0),
            min(max(float(row.get("recent_avg_score", 0.5)), 0.0), 1.0),
            min(max(float(row.get("missing_points_count", 0)) / 6.0, 0.0), 1.0),
            min(max(float(row.get("fallback_count", 0)) / 6.0, 0.0), 1.0),
            min(max(float(row.get("llm_calls_used", 0)) / 8.0, 0.0), 1.0),
            min(max(float(row.get("multi_judge_used", 0)) / 3.0, 0.0), 1.0),
            1.0,
            1.0,
        ]
        rows.append(
            EvalSampleRow(
                session_id=int(row.get("session_id", 0)),
                round_number=int(row.get("round", 1)),
                action=action,
                reward=float(row.get("reward", 0.0) or 0.0),
                features=features,
            )
        )
    return rows


def train_linucb_eval(samples: List[EvalSampleRow], l2: float = 1.0) -> Dict:
    if not samples:
        return {"feature_dim": 0, "models": {}, "training_rows": 0}
    dim = len(samples[0].features)
    by_action: Dict[str, List[EvalSampleRow]] = {}
    for row in samples:
        by_action.setdefault(row.action, []).append(row)

    models: Dict[str, Dict] = {}
    for action, action_rows in by_action.items():
        a = np.eye(dim) * float(l2)
        b = np.zeros(dim, dtype=float)
        for sample in action_rows:
            x = np.array(sample.features, dtype=float)
            a += np.outer(x, x)
            b += float(sample.reward) * x
        models[action] = {
            "A_inv": np.linalg.inv(a).tolist(),
            "b": b.tolist(),
            "n": len(action_rows),
        }
    return {"feature_dim": dim, "models": models, "training_rows": len(samples)}


def evaluate_eval_policy(models_payload: Dict, samples: List[EvalSampleRow], alpha: float = 0.25) -> Dict[str, float]:
    models = models_payload.get("models", {})
    if not samples or not models:
        return {"avg_reward": 0.0, "avg_regret": 0.0, "top1_action_match": 0.0}
    matches = 0
    regrets = []
    rewards = []
    for row in samples:
        x = np.array(row.features, dtype=float)
        pred = []
        chosen_val = None
        for action, model in models.items():
            a_inv = np.array(model["A_inv"], dtype=float)
            b = np.array(model["b"], dtype=float)
            theta = a_inv @ b
            val = float(theta @ x + alpha * np.sqrt(max(float(x @ a_inv @ x), 0.0)))
            pred.append((action, val))
            if action == row.action:
                chosen_val = val
        if not pred:
            continue
        pred.sort(key=lambda t: t[1], reverse=True)
        if pred[0][0] == row.action:
            matches += 1
        best_val = pred[0][1]
        regrets.append(max(0.0, best_val - float(chosen_val if chosen_val is not None else pred[-1][1])))
        rewards.append(float(row.reward))
    n = max(1, len(rewards))
    return {
        "avg_reward": float(np.mean(rewards)) if rewards else 0.0,
        "avg_regret": float(np.mean(regrets)) if regrets else 0.0,
        "top1_action_match": 100.0 * float(matches) / float(n),
    }


def persist_eval_policy(output_dir: Path, payload: Dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "contextual_eval_policy.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
