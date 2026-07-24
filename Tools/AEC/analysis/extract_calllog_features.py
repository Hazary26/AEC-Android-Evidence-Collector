#!/usr/bin/env python3
"""
Extract Call Log Features (companion to extract_features.py)
==============================================================
The original extract_features.py only understood text-based artifacts
(SMS body keyword matching). Call log records have no text body, so
they need separate, structurally-appropriate feature engineering:
  - duration (short calls are often flagged in real investigations)
  - call type (incoming/outgoing/missed)
  - recency
  - frequency of contact with the same number (repeated short calls
    to one number is a classic "burner contact" pattern)

Ground truth (auto_label) here is assigned based on which number list
the entry was seeded from (NEUTRAL_NUMBERS vs RELEVANT_NUMBERS below —
keep this in sync with seed_test_data.py). This is legitimate because
YOU are the one who planted the ground truth when seeding; it is not
the same as leaking the label into the classifier, since the ML model
in train_model.py will be trained on duration/type/recency/frequency
only — never on the phone number itself.

Usage:
    python3 analysis/extract_calllog_features.py --case ~/Desktop/lineageos_pilot_v3
"""

import subprocess
import re
import sys
import os
import csv
import argparse
from datetime import datetime
from collections import Counter

# Keep this in sync with seed_test_data.py's NEUTRAL_CALLS / RELEVANT_CALLS
NEUTRAL_NUMBER_PREFIX = "+880171100"
RELEVANT_NUMBER_PREFIX = "+880179900"


def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout


def parse_call_log_dump(raw_text):
    """Parse `adb shell content query --uri content://call_log/calls` output."""
    rows = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line.startswith("Row:"):
            continue
        fields = {}
        # split on ", " but values can't contain commas here (safe for this schema)
        parts = line.split(", ")
        for part in parts:
            if "=" not in part:
                continue
            key, _, value = part.partition("=")
            key = key.strip()
            # Row: 0 last_modified=... -> first token has "Row: 0 last_modified"
            if key.startswith("Row:"):
                key = key.split()[-1]
            fields[key.strip()] = value.strip()
        rows.append(fields)
    return rows


def label_for_number(number):
    if number.startswith(RELEVANT_NUMBER_PREFIX):
        return 1
    if number.startswith(NEUTRAL_NUMBER_PREFIX):
        return 0
    return 0  # unknown numbers (e.g. pre-existing device numbers) default neutral


def call_type_name(t):
    return {"1": "incoming", "2": "outgoing", "3": "missed"}.get(str(t), "unknown")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, help="Case folder path")
    args = ap.parse_args()

    case_dir = os.path.expanduser(args.case)
    os.makedirs(case_dir, exist_ok=True)
    out_path = os.path.join(case_dir, "calllog_features.csv")

    print("Querying call log via ADB...")
    raw = run("adb shell content query --uri content://call_log/calls")
    rows = parse_call_log_dump(raw)

    if not rows:
        print("No call log rows found. Is the device connected and seeded?")
        sys.exit(1)

    print(f"Parsed {len(rows)} call log rows.")

    # frequency of each number across the whole log
    numbers = [r.get("number", "UNKNOWN") for r in rows]
    freq = Counter(numbers)

    now_ms = int(datetime.now().timestamp() * 1000)

    out_rows = []
    for i, r in enumerate(rows):
        number = r.get("number", "UNKNOWN")
        duration = int(r.get("duration", 0) or 0)
        call_type_raw = r.get("type", "0")
        date_ms = int(r.get("date", now_ms) or now_ms)
        recency_days = max(0, round((now_ms - date_ms) / 86400000, 2))

        out_rows.append({
            "artifact_id": f"call_{i}_{number.replace('+','')}",
            "artifact_type": "call_log",
            "content_snippet": f"{number} [{call_type_name(call_type_raw)}, {duration}s]",
            "file_size": 0,
            "recency_days": recency_days,
            "deletion_state": "active",
            "storage_location": "call_log",
            "keyword_score": 0,
            "duration_seconds": duration,
            "call_type": call_type_name(call_type_raw),
            "call_frequency": freq[number],
            "is_short_call": 1 if duration < 30 else 0,
            "auto_label": label_for_number(number),
        })

    fieldnames = [
        "artifact_id", "artifact_type", "content_snippet", "file_size",
        "recency_days", "deletion_state", "storage_location", "keyword_score",
        "duration_seconds", "call_type", "call_frequency", "is_short_call",
        "auto_label",
    ]

    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    relevant_count = sum(1 for r in out_rows if r["auto_label"] == 1)
    print(f"\nSaved {len(out_rows)} call log feature rows -> {out_path}")
    print(f"Summary: {relevant_count} auto-labeled relevant, "
          f"{len(out_rows) - relevant_count} neutral.")
    print("\nNext: run merge_features.py to combine this with the existing")
    print("photo/document features.csv into one final dataset.")


if __name__ == "__main__":
    main()
