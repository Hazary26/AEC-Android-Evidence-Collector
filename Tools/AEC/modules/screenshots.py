"""
AEC - Phase 8: Screenshot Evidence
"""

import os
from utils.adb_helper import adb_shell, adb_pull


def run(case_dir):
    print("[Phase 8] Screenshot Evidence...")
    out_dir = case_dir  # matches manual guide: saved to case root

    adb_shell("screencap /sdcard/aec_screenshot.png")
    adb_pull("/sdcard/aec_screenshot.png", os.path.join(out_dir, "screenshot.png"))

    print(f"[Phase 8] Done -> {out_dir}/screenshot.png")
    return out_dir


def record_screen(case_dir, seconds=10):
    """
    Optional: records the screen for a fixed duration (adb screenrecord
    has no built-in stop-after-N-seconds, so this uses a timeout).
    """
    import subprocess
    print(f"[Phase 8] Recording screen for {seconds}s...")
    try:
        subprocess.run(
            ["adb", "shell", "screenrecord", "--time-limit", str(seconds), "/sdcard/aec_recording.mp4"],
            timeout=seconds + 15,
        )
    except subprocess.TimeoutExpired:
        pass
    adb_pull("/sdcard/aec_recording.mp4", os.path.join(case_dir, "recording.mp4"))
    print(f"[Phase 8] Recording saved -> {case_dir}/recording.mp4")
