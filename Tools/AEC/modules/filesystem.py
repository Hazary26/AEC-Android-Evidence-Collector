"""
AEC - Phase 4: File System Extraction (sdcard, no root needed)
"""

import os
from utils.adb_helper import adb_shell, adb_pull


def run(case_dir):
    print("[Phase 4] File System Extraction...")
    extraction_dir = os.path.join(case_dir, "extraction")
    photos_dir = os.path.join(case_dir, "photos")
    downloads_dir = os.path.join(case_dir, "downloads")
    documents_dir = os.path.join(case_dir, "documents")

    for d in [extraction_dir, photos_dir, downloads_dir, documents_dir]:
        os.makedirs(d, exist_ok=True)

    # File listing first (fast, always useful even if pulls fail)
    adb_shell("find /sdcard/ -type f", output_file=os.path.join(extraction_dir, "all_files.txt"))

    # Full sdcard pull
    print("  Pulling /sdcard/ ... (can take a while)")
    adb_pull("/sdcard/", extraction_dir)

    # Targeted folders
    print("  Pulling DCIM, Download, Documents...")
    adb_pull("/sdcard/DCIM/", photos_dir)
    adb_pull("/sdcard/Download/", downloads_dir)
    adb_pull("/sdcard/Documents/", documents_dir)

    print(f"[Phase 4] Done -> {extraction_dir}")
    return extraction_dir
