#!/usr/bin/env python3
"""
Evaluate expression analyzer (DeepFace) on standard FER datasets.

Datasets: FER2013, RAF-DB, AffectNet (download separately)
Metrics: accuracy, confusion matrix

Usage:
  python eval_modules/eval_expression_fer.py --data-dir path/to/fer2013

Place FER2013 CSV or images in data-dir. If not found, outputs placeholder.
"""

import argparse
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def run(data_dir: Path, output_dir: Path) -> bool:
    """Run FER evaluation if data available."""
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    # Check for FER2013 fer2013.csv or similar
    fer_csv = data_dir / "fer2013.csv"
    if not fer_csv.exists():
        # Placeholder
        out_path = output_dir / "eval_expression_fer.csv"
        with open(out_path, "w") as f:
            f.write("metric,value\n")
            f.write("accuracy,ILLUSTRATIVE\n")
            f.write("dataset,FER2013 (not found)\n")
        print("FER2013 not found. Placeholder written. Download from Kaggle: FER2013")
        return False

    # TODO: Load FER2013, run DeepFace emotion detection, compute accuracy
    # from deepface import DeepFace
    # emotions = DeepFace.analyze(img_path, actions=["emotion"])
    # Compare with ground truth label
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/fer2013")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    out = Path(args.output) if args.output else Path(__file__).parent.parent / "output"
    run(Path(args.data_dir), out)
