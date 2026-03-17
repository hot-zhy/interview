#!/usr/bin/env python3
"""
Evaluate LLM scorer against human evaluations.

Same inputs as eval_rule_scorer. Compares rule-only vs LLM-only vs hybrid.

Metrics: κ, QWK, exact/adjacent agreement

Usage:
  python eval_modules/eval_llm_scorer.py --data-dir data
"""

import argparse
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def run(data_dir: Path, output_dir: Path) -> bool:
    """Run LLM scorer evaluation."""
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    human_path = data_dir / "human_evaluations.csv"
    eval_path = data_dir / "evaluations.csv"

    if not human_path.exists() or not eval_path.exists():
        out_path = output_dir / "eval_llm_scorer.csv"
        with open(out_path, "w") as f:
            f.write("metric,mode,value\n")
            f.write("kappa,rule,ILLUSTRATIVE\n")
            f.write("kappa,llm,ILLUSTRATIVE\n")
            f.write("kappa,hybrid,ILLUSTRATIVE\n")
        print("human_evaluations.csv or evaluations.csv not found. Placeholder written.")
        return False

    # TODO: Stratify by provenance, compute κ per mode
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    out = Path(args.output) if args.output else Path(__file__).parent.parent / "output"
    run(Path(args.data_dir), out)
