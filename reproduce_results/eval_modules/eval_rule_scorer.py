#!/usr/bin/env python3
"""
Evaluate rule-based scorer against human evaluations.

Input: human_evaluations.csv (response_id, evaluator_id, correctness, depth, ...)
       + evaluations.csv (system scores)

Metrics: Cohen's κ, ICC, exact/adjacent agreement

Usage:
  python eval_modules/eval_rule_scorer.py --data-dir data
"""

import argparse
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def run(data_dir: Path, output_dir: Path) -> bool:
    """Run rule scorer evaluation."""
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    human_path = data_dir / "human_evaluations.csv"
    eval_path = data_dir / "evaluations.csv"

    if not human_path.exists() or not eval_path.exists():
        out_path = output_dir / "eval_rule_scorer.csv"
        with open(out_path, "w") as f:
            f.write("metric,value\n")
            f.write("kappa,ILLUSTRATIVE\n")
            f.write("icc,ILLUSTRATIVE\n")
        print("human_evaluations.csv or evaluations.csv not found. Placeholder written.")
        return False

    # TODO: Merge by response_id, compute κ and ICC
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    out = Path(args.output) if args.output else Path(__file__).parent.parent / "output"
    run(Path(args.data_dir), out)
