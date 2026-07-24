#!/usr/bin/env python3
"""
AEC - generate_app_data.py

Helper for populating the LineageOS VM with realistic app-generated
artifacts (browser history, downloaded files) that can't be scripted
via `content insert` the way SMS/contacts can. This script automates
the parts that CAN be automated (pushing sample files, triggering
browser visits via adb) and prints a checklist for the manual parts
(WhatsApp/Telegram — these require real UI interaction to generate
authentic msgstore.db / cache4.db content).

Usage:
    python3 generate_app_data.py
"""

import subprocess
import os
import time

SAMPLE_URLS = [
    "https://en.wikipedia.org/wiki/Digital_forensics",
    "https://en.wikipedia.org/wiki/Android_(operating_system)",
    "https://www.google.com/search?q=test+forensic+data",
]

SAMPLE_IMAGE_URLS = {
    "test_photo_1.jpg": "https://raw.githubusercontent.com/ianare/exif-samples/master/jpg/gps/DSCN0010.jpg",
    "test_photo_2.jpg": "https://raw.githubusercontent.com/ianare/exif-samples/master/jpg/gps/DSCN0012.jpg",
    "test_photo_3.jpg": "https://raw.githubusercontent.com/ianare/exif-samples/master/jpg/gps/DSCN0013.jpg",
    "test_photo_4.jpg": "https://raw.githubusercontent.com/ianare/exif-samples/master/jpg/gps/DSCN0018.jpg",
}


def adb_shell(cmd):
    return subprocess.run(["adb", "shell", cmd], capture_output=True, text=True)


def download_sample_photos(dest_dir="./sample_photos"):
    os.makedirs(dest_dir, exist_ok=True)
    print("Downloading sample GPS/EXIF photos to Ubuntu...")
    for fname, url in SAMPLE_IMAGE_URLS.items():
        path = os.path.join(dest_dir, fname)
        subprocess.run(["wget", "-q", "-O", path, url])
        print(f"  {fname} downloaded")
    return dest_dir


def push_photos_to_device(dest_dir):
    print("\nPushing photos to device DCIM folder...")
    for fname in os.listdir(dest_dir):
        local_path = os.path.join(dest_dir, fname)
        subprocess.run(["adb", "push", local_path, "/sdcard/DCIM/Camera/"])
        print(f"  pushed {fname}")


def push_dummy_documents():
    print("\nCreating and pushing dummy documents...")
    os.makedirs("./sample_docs", exist_ok=True)
    docs = {
        "meeting_notes.txt": "Meeting notes: discussed project timeline and budget.\n",
        "financial_summary.txt": "Q1 summary: revenue up 12%, expenses reviewed.\n",
        "contact_list_backup.txt": "Backup of contacts exported on request.\n",
    }
    for fname, content in docs.items():
        path = os.path.join("./sample_docs", fname)
        with open(path, "w") as f:
            f.write(content)
        subprocess.run(["adb", "push", path, "/sdcard/Download/"])
        print(f"  pushed {fname}")


def open_browser_urls():
    print("\nOpening sample URLs in device browser (generates history)...")
    for url in SAMPLE_URLS:
        adb_shell(f'am start -a android.intent.action.VIEW -d "{url}"')
        print(f"  opened {url}")
        time.sleep(3)  # give the page time to load before switching


def print_manual_checklist():
    print("\n" + "=" * 55)
    print("MANUAL STEPS (can't be scripted — need real UI interaction)")
    print("=" * 55)
    print("""
These generate authentic app databases and can't be faked via ADB
content-provider inserts. Use scrcpy to control the VM screen:

    scrcpy

Then, on the LineageOS VM:

[ ] Install WhatsApp (adb install whatsapp.apk, or via browser)
[ ] Sign up with a test/virtual number
[ ] Send/receive 10-15 messages across 2-3 contacts (mix of
    neutral chat + a couple "scenario-relevant" messages matching
    your paper's mock investigation theme)
[ ] Send/receive 2-3 media files (images) via WhatsApp

[ ] Install Telegram similarly
[ ] Repeat the same message pattern (10-15 messages)

[ ] Use the stock File Manager app: create a folder, move a
    couple of the pushed documents into it, rename one file
    (generates filesystem metadata changes worth extracting)

Once done, run:
    python3 main.py --case lineageos_case_01 --full

This pulls everything (WhatsApp/Telegram DBs via Phase 5 root
extraction, browser history via Phase 4/5, documents via Phase 4,
photos via Phase 4/8) into one organized, hashed case folder.
""")


if __name__ == "__main__":
    print("=" * 55)
    print("AEC — App Data Generator (LineageOS VM)")
    print("=" * 55)

    out = subprocess.run(["adb", "devices"], capture_output=True, text=True).stdout
    print(out)
    confirm = input("Confirm this is your LineageOS VM? [y/N]: ")
    if confirm.lower() != "y":
        print("Aborted.")
    else:
        photo_dir = download_sample_photos()
        push_photos_to_device(photo_dir)
        push_dummy_documents()
        open_browser_urls()
        print_manual_checklist()
