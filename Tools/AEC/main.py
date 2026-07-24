#!/usr/bin/env python3
"""
AEC - Android Evidence Collector
Automated ADB-based forensic extraction tool.

Runs the same commands you'd type manually — just automated,
sequenced, logged, and organized into a case folder.

Usage:
    python3 main.py --case case_001 --full
    python3 main.py --case case_001 --phases 1,3,6
    python3 main.py --case case_001 --list-phases
"""

import argparse
import os
import sys
import datetime

from utils.adb_helper import check_device_connected, init_logger
from modules import (
    device_info,
    network,
    apps,
    filesystem,
    databases,
    communications,
    logs,
    screenshots,
    backup,
    hashing,
)
from report import generate_html

PHASES = {
    1: ("Device Identification", device_info.run),
    2: ("Network Investigation", network.run),
    3: ("Installed Apps", apps.run),
    4: ("File System Extraction", filesystem.run),
    5: ("Database Extraction (root)", databases.run),
    6: ("Communication Evidence", communications.run),
    7: ("System Logs", logs.run),
    8: ("Screenshot Evidence", screenshots.run),
    9: ("Full Backup", backup.run),
    10: ("Evidence Hashing", hashing.run),
}

BASE_CASE_DIR = os.path.expanduser("~/Desktop")


def list_phases():
    print("\nAEC available phases:")
    for num, (name, _) in PHASES.items():
        print(f"  {num}. {name}")
    print()


def make_case_dir(case_name):
    case_dir = os.path.join(BASE_CASE_DIR, case_name)
    if os.path.exists(case_dir):
        print(f"[!] Case folder already exists: {case_dir}")
        print("    AEC will not overwrite an existing case. Choose a new --case name.")
        sys.exit(1)
    os.makedirs(case_dir)
    return case_dir


def main():
    parser = argparse.ArgumentParser(description="AEC - Android Evidence Collector")
    parser.add_argument("--case", help="Case name, e.g. case_001")
    parser.add_argument("--full", action="store_true", help="Run all phases 1-10")
    parser.add_argument("--phases", help="Comma-separated phase numbers, e.g. 1,3,6")
    parser.add_argument("--list-phases", action="store_true", help="List available phases and exit")
    parser.add_argument("--skip-hash", action="store_true", help="Skip Phase 10 hashing (not recommended)")
    args = parser.parse_args()

    if args.list_phases:
        list_phases()
        return

    if not args.case:
        print("Error: --case NAME is required (e.g. --case case_001)")
        sys.exit(1)

    if not args.full and not args.phases:
        print("Error: specify --full or --phases 1,2,3,...")
        sys.exit(1)

    # 1. Check device before doing anything
    print("Checking device connection...")
    ok, info = check_device_connected()
    if not ok:
        print(f"[!] {info}")
        sys.exit(1)
    print(f"  Connected device: {info}\n")

    # 2. Set up case folder + audit log
    case_dir = make_case_dir(args.case)
    init_logger(case_dir)
    print(f"Case folder created: {case_dir}\n")

    # 3. Determine which phases to run
    if args.full:
        phase_nums = sorted(PHASES.keys())
    else:
        phase_nums = sorted(int(p.strip()) for p in args.phases.split(","))

    if args.skip_hash and 10 in phase_nums:
        phase_nums.remove(10)

    # 4. Run phases in order
    start_time = datetime.datetime.now()
    for num in phase_nums:
        if num not in PHASES:
            print(f"[!] Unknown phase {num}, skipping.")
            continue
        name, func = PHASES[num]
        print(f"\n{'='*60}\nPhase {num}: {name}\n{'='*60}")
        try:
            func(case_dir)
        except Exception as e:
            print(f"[!] Phase {num} ({name}) failed: {e}")
            print("    Continuing with remaining phases...")

    # 5. Always hash at the end unless explicitly skipped
    if 10 not in phase_nums and not args.skip_hash:
        print(f"\n{'='*60}\nPhase 10: Evidence Hashing (auto-run as final step)\n{'='*60}")
        hashing.run(case_dir)

    # 6. Generate summary report
    generate_html.generate(case_dir, args.case)

    elapsed = datetime.datetime.now() - start_time
    print(f"\n{'='*60}")
    print(f"AEC run complete. Case: {args.case}")
    print(f"Output: {case_dir}")
    print(f"Elapsed: {elapsed}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
