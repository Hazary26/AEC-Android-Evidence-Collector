"""
AEC - Phase 5: Database Extraction (ROOT REQUIRED)
Automatically skips gracefully if the device isn't rooted.
"""

import os
from utils.adb_helper import check_root, adb_pull

# package_path -> subfolder under case_dir/databases/
TARGETS = {
    "com.android.providers.contacts": "contacts",
    "com.android.providers.telephony": "sms",
    "com.android.messaging": "sms",
    "com.android.browser": "browser",
    "com.android.providers.calendar": "calendar",
    "com.whatsapp": "whatsapp",
    "org.telegram.messenger": "telegram",
    "com.google.android.gm": "gmail",
}


def run(case_dir):
    print("[Phase 5] Database Extraction (root required)...")
    is_root = check_root()

    if not is_root:
        print("  [SKIPPED] Device is not rooted (or root ADB not enabled).")
        print("  Enable via: Settings -> Developer options -> Root access -> ADB only")
        return None

    db_root = os.path.join(case_dir, "databases")
    for pkg, subfolder in TARGETS.items():
        dest = os.path.join(db_root, subfolder)
        os.makedirs(dest, exist_ok=True)
        print(f"  Pulling databases for {pkg} ...")
        adb_pull(f"/data/data/{pkg}/databases/", dest)

    print(f"[Phase 5] Done -> {db_root}")
    return db_root
