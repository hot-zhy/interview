#!/usr/bin/env python3
"""
Simulation evaluation for difficulty calibration (sliding-window / target-score control).

Simulates candidate with true ability θ ∈ {1,2,3,4,5}, generates response scores,
replays the calibration algorithm, and computes:
  - MAE(final_difficulty, θ)
  - Convergence round (first round where |d_t - d_{t-1}| < 0.5 for 2 consecutive)
  - Stability rate

Usage:
  python eval_modules/run_calibration_sim.py [--seed 42]
"""

import argparse
import numpy as np
from pathlib import Path

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def _simulate_response(true_ability: float, difficulty: float, noise: float = 0.2) -> float:
    """Simplified: higher ability + lower difficulty -> higher score."""
    # Score ~ ability - difficulty + noise, clipped to [0,1]
    raw = (true_ability - difficulty) / 5.0 + 0.5 + np.random.normal(0, noise)
    return float(np.clip(raw, 0, 1))


def run_simulation(seed: int, n_sessions: int = 100) -> dict:
    """Run calibration simulation."""
    np.random.seed(seed)
    target_score = 0.70
    kp, kd = 1.2, 0.6
    results = []

    for _ in range(n_sessions):
        theta = np.random.choice([1, 2, 3, 4, 5])
        theta_norm = theta / 5.0
        d = 3.0  # Start at middle difficulty
        converged_at = None
        prev_d = d
        stable_count = 0

        for round_idx in range(1, 21):
            score = _simulate_response(theta_norm, d / 5.0)
            error = target_score - score
            d_new = d + kp * error - kd * (d - prev_d) * 0.1
            d_new = np.clip(d_new, 1, 5)
            prev_d, d = d, d_new

            if abs(d - prev_d) < 0.5:
                stable_count += 1
                if stable_count >= 2 and converged_at is None:
                    converged_at = round_idx
            else:
                stable_count = 0

        mae = abs(d - theta)
        results.append({
            "theta": theta,
            "final_d": d,
            "mae": mae,
            "converged_at": converged_at or 20,
        })

    mae_mean = np.mean([r["mae"] for r in results])
    conv_mean = np.mean([r["converged_at"] for r in results])
    return {"mae_mean": mae_mean, "conv_mean": conv_mean, "n": n_sessions}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default=None, help="Output dir (default: reproduce_results/output)")
    args = parser.parse_args()

    out_dir = Path(args.output) if args.output else Path(__file__).parent.parent / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    res = run_simulation(args.seed)
    out_path = out_dir / "eval_calibration_sim.csv"
    with open(out_path, "w") as f:
        f.write("metric,value\n")
        f.write(f"mae_mean,{res['mae_mean']:.4f}\n")
        f.write(f"conv_mean,{res['conv_mean']:.2f}\n")
        f.write(f"n_sessions,{res['n']}\n")
    print(f"Calibration sim: MAE={res['mae_mean']:.4f}, conv={res['conv_mean']:.2f}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
