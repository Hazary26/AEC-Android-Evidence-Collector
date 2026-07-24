"""
AEC - Phase 6: Communication Evidence (SMS, calls, contacts - no root needed)
"""

import os
from utils.adb_helper import adb_shell


def run(case_dir):
    print("[Phase 6] Communication Evidence...")
    out_dir = os.path.join(case_dir, "logs")
    os.makedirs(out_dir, exist_ok=True)

    queries = {
        "sms_messages.txt": "content query --uri content://sms/",
        "mms_messages.txt": "content query --uri content://mms/",
        "call_logs.txt": "content query --uri content://call_log/calls/",
        "contacts.txt": "content query --uri content://contacts/phones/",
        "calendar.txt": "content query --uri content://com.android.calendar/events/",
    }

    for filename, cmd in queries.items():
        adb_shell(cmd, output_file=os.path.join(out_dir, filename))

    print(f"[Phase 6] Done -> {out_dir}")
    return out_dir
