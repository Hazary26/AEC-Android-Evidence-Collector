"""
AEC - Phase 1: Device Identification
Same commands as the manual guide, just automated + logged.
"""

import os
from utils.adb_helper import run_adb, adb_shell


def run(case_dir):
    print("[Phase 1] Device Identification...")
    out_dir = os.path.join(case_dir, "device_info")
    os.makedirs(out_dir, exist_ok=True)

    fields = {
        "model": "ro.product.model",
        "android_version": "ro.build.version.release",
        "serial": "ro.serialno",
        "manufacturer": "ro.product.manufacturer",
        "brand": "ro.product.brand",
    }

    summary_lines = []
    for label, prop in fields.items():
        value, _ = adb_shell(f"getprop {prop}")
        value = value.strip()
        summary_lines.append(f"{label}: {value}")
        print(f"  {label}: {value}")

    # Screen size
    screen, _ = adb_shell("wm size")
    summary_lines.append(f"screen_size: {screen.strip()}")

    # Save summary
    with open(os.path.join(out_dir, "summary.txt"), "w") as f:
        f.write("\n".join(summary_lines) + "\n")

    # Full property dump (same as: adb shell getprop > device_info.txt)
    adb_shell("getprop", output_file=os.path.join(out_dir, "full_getprop.txt"))

    print(f"[Phase 1] Done -> {out_dir}")
    return out_dir
