#!/usr/bin/env python3
"""
AEC - analysis/extract_features.py

Reads an AEC case folder and turns every collected artifact into a
feature row for the relevance model. Also auto-labels artifacts
based on the ground truth from seed_test_data.py (which content
was seeded as "relevant" vs "neutral") — giving you an objective
baseline label set alongside your manual annotator labels.

Usage:
    python3 analysis/extract_features.py --case ~/Desktop/lineageos_pilot
"""

import os
import re
import csv
import argparse
import datetime

# Keywords that match the RELEVANT_SMS content seeded by seed_test_data.py.
# Edit this to match whatever mock scenario you configured there.
RELEVANT_KEYWORDS = [
    "transfer", "confirm receipt", "usual spot", "delete this message",
    "routing verified", "drop point", "agent", "unknown contact",
]


def keyword_score(text):
    text_l = text.lower()
    return sum(1 for kw in RELEVANT_KEYWORDS if kw in text_l)


def parse_sms_query_output(path):
    """
    Parses the output of:
      adb shell content query --uri content://sms/
    Each row looks like: Row: 0 _id=1, thread_id=2, address=..., body=..., date=...
    """
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", errors="ignore") as f:
        content = f.read()

    for line in content.splitlines():
        if not line.strip().startswith("Row:"):
            continue
        fields = {}
        # split on ", " but keep it simple/robust to odd formatting
        parts = re.split(r",\s+(?=[a-zA-Z_]+=)", line)
        for part in parts:
            if "=" in part:
                k, _, v = part.partition("=")
                fields[k.strip().split()[-1]] = v.strip()
        rows.append(fields)
    return rows


def extract_features_from_case(case_dir):
    """
    Returns a list of dict rows, one per artifact, with:
      artifact_id, artifact_type, content_snippet, file_size,
      recency_days, deletion_state, storage_location, keyword_score,
      auto_label (from ground truth keyword match)
    """
    rows = []
    now = datetime.datetime.now()

    # --- SMS artifacts ---
    sms_path = os.path.join(case_dir, "logs", "sms_messages.txt")
    sms_rows = parse_sms_query_output(sms_path)
    for i, sms in enumerate(sms_rows):
        body = sms.get("body", "")
        score = keyword_score(body)
        rows.append({
            "artifact_id": f"sms_{i}",
            "artifact_type": "sms",
            "content_snippet": body[:80],
            "file_size": len(body),
            "recency_days": 0,  # seeded today; adjust if you have real 'date' field parsing
            "deletion_state": "active",
            "storage_location": "content_provider",
            "keyword_score": score,
            "auto_label": 1 if score > 0 else 0,
        })

    # --- File-based artifacts (photos, documents) ---
    for subfolder, artifact_type in [("photos", "photo"), ("documents", "document"),
                                       ("downloads", "document"), ("extraction", "file")]:
        folder = os.path.join(case_dir, subfolder)
        if not os.path.isdir(folder):
            continue
        for root, _, files in os.walk(folder):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    stat = os.stat(fpath)
                    size = stat.st_size
                    mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
                    recency = (now - mtime).days
                except OSError:
                    size, recency = 0, -1

                score = keyword_score(fname)
                rows.append({
                    "artifact_id": f"{artifact_type}_{fname}",
                    "artifact_type": artifact_type,
                    "content_snippet": fname,
                    "file_size": size,
                    "recency_days": recency,
                    "deletion_state": "active",
                    "storage_location": subfolder,
                    "keyword_score": score,
                    "auto_label": 1 if score > 0 else 0,
                })

    # --- Contacts ---
    contacts_path = os.path.join(case_dir, "logs", "contacts.txt")
    if os.path.exists(contacts_path):
        with open(contacts_path, "r", errors="ignore") as f:
            content = f.read()
        for i, line in enumerate(content.splitlines()):
            if line.strip().startswith("Row:"):
                score = keyword_score(line)
                rows.append({
                    "artifact_id": f"contact_{i}",
                    "artifact_type": "contact",
                    "content_snippet": line[:80],
                    "file_size": len(line),
                    "recency_days": 0,
                    "deletion_state": "active",
                    "storage_location": "content_provider",
                    "keyword_score": score,
                    "auto_label": 1 if score > 0 else 0,
                })

    return rows


def save_csv(rows, out_path):
    if not rows:
        print("No artifacts found to write.")
        return
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} artifact feature rows -> {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, help="Path to AEC case folder")
    parser.add_argument("--out", default=None, help="Output CSV path (default: <case>/features.csv)")
    args = parser.parse_args()

    case_dir = os.path.expanduser(args.case)
    out_path = args.out or os.path.join(case_dir, "features.csv")

    rows = extract_features_from_case(case_dir)
    save_csv(rows, out_path)

    relevant_count = sum(1 for r in rows if r["auto_label"] == 1)
    print(f"\nSummary: {len(rows)} total artifacts, {relevant_count} auto-labeled relevant "
          f"(keyword match), {len(rows) - relevant_count} neutral.")
    print("\nNext step: manually review features.csv and add a 'manual_label' column")
    print("(you + one other annotator, independently) to compute Cohen's kappa,")
    print("then run train_model.py")


if __name__ == "__main__":
    main()
