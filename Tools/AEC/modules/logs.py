"""
AEC - Phase 7: System Logs
"""

import os
from utils.adb_helper import run_adb, adb_shell


def run(case_dir):
    print("[Phase 7] System Logs...")
    out_dir = os.path.join(case_dir, "logs")
    os.makedirs(out_dir, exist_ok=True)

    # logcat uses run_adb directly (not "shell")
    run_adb(["logcat", "-d"], output_file=os.path.join(out_dir, "logcat.txt"), timeout=120)

    adb_shell("ps", output_file=os.path.join(out_dir, "processes.txt"))
    adb_shell("dumpsys battery", output_file=os.path.join(out_dir, "battery.txt"))
    adb_shell("dumpsys meminfo", output_file=os.path.join(out_dir, "memory.txt"))
    adb_shell("cat /proc/cpuinfo", output_file=os.path.join(out_dir, "cpuinfo.txt"))
    adb_shell("dumpsys account", output_file=os.path.join(out_dir, "accounts.txt"))
    adb_shell("dumpsys location", output_file=os.path.join(out_dir, "location.txt"))

    # Full dumpsys can be huge/slow — give it a longer timeout
    print("  Capturing full dumpsys (this can take a minute)...")
    adb_shell("dumpsys", output_file=os.path.join(out_dir, "dumpsys_full.txt"), timeout=180)

    print(f"[Phase 7] Done -> {out_dir}")
    return out_dir
