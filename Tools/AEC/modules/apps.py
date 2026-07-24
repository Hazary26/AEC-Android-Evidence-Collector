"""
AEC - Phase 3: Installed Apps Investigation
"""

import os
from utils.adb_helper import adb_shell


def run(case_dir):
    print("[Phase 3] Installed Apps Investigation...")
    out_dir = os.path.join(case_dir, "apps")
    os.makedirs(out_dir, exist_ok=True)

    adb_shell("pm list packages", output_file=os.path.join(out_dir, "all_apps.txt"))
    adb_shell("pm list packages -3", output_file=os.path.join(out_dir, "user_apps.txt"))
    adb_shell("pm list packages -s", output_file=os.path.join(out_dir, "system_apps.txt"))
    adb_shell("pm list packages -f", output_file=os.path.join(out_dir, "apps_with_paths.txt"))
    adb_shell("dumpsys usagestats", output_file=os.path.join(out_dir, "app_usage.txt"))

    print(f"[Phase 3] Done -> {out_dir}")
    return out_dir


def get_app_details(case_dir, package_name):
    """Optional: detailed dump for one specific package, e.g. com.whatsapp"""
    out_dir = os.path.join(case_dir, "apps")
    os.makedirs(out_dir, exist_ok=True)
    safe_name = package_name.replace(".", "_")
    adb_shell(
        f"dumpsys package {package_name}",
        output_file=os.path.join(out_dir, f"pkg_{safe_name}.txt"),
    )
