"""
AEC - Phase 9: Full Backup (Logical Acquisition)
"""

import os
import subprocess
import zlib
import tarfile
from utils.adb_helper import _log


def run(case_dir):
    print("[Phase 9] Full Backup...")
    backup_path = os.path.join(case_dir, "full_backup.ab")
    tar_path = os.path.join(case_dir, "full_backup.tar")
    contents_dir = os.path.join(case_dir, "backup_contents")
    os.makedirs(contents_dir, exist_ok=True)

    print("  Running adb backup (confirm on device screen if prompted)...")
    # adb backup writes its own file; run it directly since it doesn't
    # follow the normal stdout-capture pattern (it prompts on-device).
    subprocess.run(
        ["adb", "backup", "-all", "-apk", "-shared", "-f", backup_path],
        timeout=600,
    )
    _log(f"RUN: adb backup -all -apk -shared -f {backup_path}")

    if not os.path.exists(backup_path) or os.path.getsize(backup_path) == 0:
        print("  [WARNING] Backup file empty or missing — likely not confirmed on-device.")
        return None

    # Convert .ab -> .tar (skip the 24-byte Android backup header, then zlib-decompress)
    print("  Converting backup to tar...")
    try:
        with open(backup_path, "rb") as f:
            f.seek(24)
            decompressed = zlib.decompress(f.read())
        with open(tar_path, "wb") as f:
            f.write(decompressed)

        with tarfile.open(tar_path) as tar:
            tar.extractall(contents_dir)
        print(f"  Extracted -> {contents_dir}")
    except Exception as e:
        print(f"  [WARNING] Could not auto-extract backup: {e}")
        print(f"  Raw backup still saved at {backup_path}")

    print(f"[Phase 9] Done -> {backup_path}")
    return backup_path
