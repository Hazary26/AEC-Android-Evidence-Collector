#!/usr/bin/env python3
"""
Merge Features
===============
Combines the original features.csv (photo/document/file artifacts,
produced by extract_features.py) with calllog_features.csv (produced
by extract_calllog_features.py) into one final combined_features.csv
ready for train_model.py.

Usage:
    python3 analysis/merge_features.py --case ~/Desktop/lineageos_pilot_v3
"""

import argparse
import os
import sys

try:
    import pandas as pd
except ImportError:
    print("pandas not found. Run: pip3 install pandas --user --break-system-packages")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, help="Case folder path")
    args = ap.parse_args()

    case_dir = os.path.expanduser(args.case)
    features_path = os.path.join(case_dir, "features.csv")
    calllog_path = os.path.join(case_dir, "calllog_features.csv")
    out_path = os.path.join(case_dir, "combined_features.csv")

    if not os.path.exists(features_path):
        print(f"Missing: {features_path}")
        sys.exit(1)
    if not os.path.exists(calllog_path):
        print(f"Missing: {calllog_path}")
        print("Run extract_calllog_features.py first.")
        sys.exit(1)

    df_files = pd.read_csv(features_path)
    df_calls = pd.read_csv(calllog_path)

    print(f"Loaded {len(df_files)} file-based artifacts (photo/document/etc).")
    print(f"Loaded {len(df_calls)} call log artifacts.")

    # Union of columns; missing ones filled with sensible defaults
    combined = pd.concat([df_files, df_calls], ignore_index=True, sort=False)

    # Fill NaNs introduced by the concat for columns that only exist in one side
    numeric_fill_cols = ["duration_seconds", "call_frequency", "is_short_call"]
    for col in numeric_fill_cols:
        if col in combined.columns:
            combined[col] = combined[col].fillna(0)

    if "call_type" in combined.columns:
        combined["call_type"] = combined["call_type"].fillna("n/a")

    combined.to_csv(out_path, index=False)

    total = len(combined)
    relevant = int(combined["auto_label"].sum()) if "auto_label" in combined.columns else 0

    print(f"\nSaved combined dataset -> {out_path}")
    print(f"Total artifacts: {total}")
    print(f"Relevant (auto_label=1): {relevant}")
    print(f"Neutral  (auto_label=0): {total - relevant}")
    print("\nNext step: open combined_features.csv, add a 'manual_label' column")
    print("(copy auto_label as a starting point, then review each row yourself),")
    print("then run:")
    print(f"    python3 analysis/train_model.py --features {out_path}")


if __name__ == "__main__":
    main()
