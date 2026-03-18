#!/usr/bin/env python3
"""
Evaluate resume parser on ResumeBench or custom labeled resumes.

Metrics: field-level F1, precision, recall (education, experience, skills)

Usage:
  python eval_modules/eval_resume_parser.py --data-dir data/resume_bench

Data format: JSON files with ground truth {education, experience, skills}
and raw text. Parser output compared to ground truth.
"""

import argparse
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def run(data_dir: Path, output_dir: Path) -> bool:
    """Run resume parser evaluation."""
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    labeled = list(data_dir.glob("*.json")) if data_dir.exists() else []
    if not labeled:
        out_path = output_dir / "eval_resume_parser.csv"
        with open(out_path, "w") as f:
            f.write("metric,value\n")
            f.write("f1,ILLUSTRATIVE\n")
            f.write("precision,ILLUSTRATIVE\n")
            f.write("recall,ILLUSTRATIVE\n")
        print("No labeled resumes found. Placeholder written. See EVALUATION_PLAN.md")
        return False

    # TODO: Load labeled resumes, run resume_parser, compute F1
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/resume_bench")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    out = Path(args.output) if args.output else Path(__file__).parent.parent / "output"
    run(Path(args.data_dir), out)
