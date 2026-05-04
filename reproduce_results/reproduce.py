#!/usr/bin/env python3
"""
Reproduce all experimental results from raw data.

Usage:
  python reproduce.py [--data-dir PATH] [--seed N]

Output:
  output/tab_*.csv — Tables matching paper structure

Until raw data is provided, outputs placeholder files with "ILLUSTRATIVE" markers.
"""

import argparse
import os
import sys
from pathlib import Path

# Fixed random seed for reproducibility
SEED = int(os.environ.get("REPRODUCE_SEED", "42"))

# Ensure we can import sibling modules
sys.path.insert(0, str(Path(__file__).parent))

def main():
    parser = argparse.ArgumentParser(description="Reproduce paper results")
    parser.add_argument("--data-dir", default=os.environ.get("DATA_DIR", "data"), help="Path to data directory")
    parser.add_argument("--seed", type=int, default=SEED, help="Random seed")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    has_data = data_dir.exists() and any(data_dir.glob("*.csv"))

    if not has_data:
        print("WARNING: No data files found. Creating placeholder outputs.")
        print("See MISSING_DATA.md for required data files.")

    # Run modules
    modules = [
        ("calc_training_snapshot", "tab_training_snapshot.csv"),
        ("calc_calibration", "tab_calibration.csv"),
        ("calc_selection", "tab_selection.csv"),
        ("calc_bandit_policy", "tab_bandit_policy.csv"),
        ("calc_eval_policy", "tab_eval_policy.csv"),
        ("calc_eval_policy_ablation", "tab_eval_policy_ablation.csv"),
        ("calc_width_policy", "tab_width_policy.csv"),
        ("calc_subtask_policy", "tab_subtask_policy.csv"),
        ("calc_wideseek_baseline", "tab_wideseek_baseline.csv"),
        ("calc_evaluation", "tab_evaluation.csv"),
        ("calc_system_performance", "tab_system_performance.csv"),
        ("calc_interview_outcomes", "tab_interview_outcomes.csv"),
        ("calc_joint_ablation", "tab_joint_ablation.csv"),
        ("calc_joint_reward_sweep", "tab_joint_reward_sweep.csv"),
        ("calc_canary_abtest", "tab_canary_abtest.csv"),
        ("calc_go_nogo", "tab_go_nogo.csv"),
        ("calc_best_report", "tab_best_config.csv"),
    ]

    for mod_name, out_file in modules:
        try:
            mod = __import__(mod_name)
            result = mod.run(data_dir, output_dir, args.seed)
            if result:
                print(f"  {out_file}: OK")
            else:
                print(f"  {out_file}: placeholder (no data)")
        except ImportError as e:
            print(f"  {mod_name}: {e}")
        except Exception as e:
            print(f"  {mod_name}: {e}")

    print("\nDone. See output/ for generated tables.")

if __name__ == "__main__":
    main()
