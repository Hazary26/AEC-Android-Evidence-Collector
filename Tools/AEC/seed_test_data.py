#!/usr/bin/env python3
"""
AEC Test Data Seeder (v2 - Contacts + Call Log)
================================================
NOTE: SMS seeding removed. On this LineageOS 14.1 x86 VM, the SMS
content provider database (mmssms.db) never gets created because
the VM has no RIL (Radio Interface Layer) - there is no emulated
modem/baseband. This is confirmed via:
  - adb shell ls -la /data/data/com.android.providers.telephony/databases/
    -> folder is empty
  - adb shell getprop | grep radio -> ro.radio.noril: yes
  - adb shell dumpsys telephony.registry -> mServiceState=1 (out of service)

This is an environment limitation, not a script bug. Contacts and
Call Log use separate content providers that do NOT depend on radio
hardware, so they work reliably on this VM (verified with adb root).

Run this with 'adb root' active first:
    adb root
    python3 seed_test_data.py
"""

import subprocess
import sys

DEVICE_ID = None  # auto-detect

# ---------------------------------------------------------------------
# Ground truth data - EDIT THESE to match your paper's mock scenario
# ---------------------------------------------------------------------

NEUTRAL_CONTACTS = [
    "Alice Rahman", "Bob Islam", "Carol Ahmed", "David Chowdhury",
    "Emma Sultana", "Frank Hossain", "Grace Akter", "Henry Molla",
]

RELEVANT_CONTACTS = [
    "Unknown Contact 1", "Agent X", "Delivery Contact",
]

# Neutral calls: normal, everyday, short/medium calls to known contacts
NEUTRAL_CALLS = [
    # (number, duration_seconds, call_type)  type: 1=incoming, 2=outgoing, 3=missed
    ("+8801711000001", 180, 1),
    ("+8801711000002", 340, 2),
    ("+8801711000003", 45, 3),
    ("+8801711000004", 600, 1),
    ("+8801711000005", 120, 2),
    ("+8801711000006", 90, 1),
    ("+8801711000007", 300, 2),
    ("+8801711000008", 15, 3),
    ("+8801711000001", 200, 1),
    ("+8801711000002", 60, 2),
    ("+8801711000009", 450, 1),
    ("+8801711000010", 30, 3),
    ("+8801711000003", 150, 2),
    ("+8801711000004", 220, 1),
    ("+8801711000011", 75, 2),
]

# Relevant calls: scenario-matched (short/suspicious calls to flagged numbers)
# Adjust the numbers/durations/pattern to fit whatever mock investigation
# scenario your paper is using (financial fraud shown here as an example).
RELEVANT_CALLS = [
    ("+8801799000001", 12, 2),   # very short outgoing call - "Agent X"
    ("+8801799000002", 8, 1),    # very short incoming call - "Unknown Contact 1"
    ("+8801799000001", 20, 2),
    ("+8801799000003", 5, 1),    # "Delivery Contact"
    ("+8801799000002", 15, 2),
    ("+8801799000001", 10, 1),
    ("+8801799000003", 25, 2),
    ("+8801799000002", 7, 1),
]

BASE_TIMESTAMP_MS = 1690000000000  # arbitrary base epoch ms; calls get offset


def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_device():
    print("=" * 55)
    print("AEC Test Data Seeder (v2 - Contacts + Call Log)")
    print("=" * 55)
    rc, out, err = run("adb devices")
    print(out)
    if "device" not in out.split("\n", 1)[-1]:
        print("No device detected. Connect your LineageOS VM first.")
        sys.exit(1)

    confirm = input("Confirm this is your OWN test device (LineageOS VM)? [y/N]: ")
    if confirm.strip().lower() != "y":
        print("Aborted.")
        sys.exit(0)

    # Check root, since call_log/contacts write reliably needs it on this build
    rc, out, err = run("adb shell id")
    if "uid=0" not in out:
        print()
        print("WARNING: adb is not running as root (uid=0 not detected).")
        print("Call log writes failed earlier without root due to a")
        print("READ_CALL_LOG/WRITE_CALL_LOG permission error.")
        print("Run 'adb root' in another terminal, then re-run this script.")
        proceed = input("Continue anyway? [y/N]: ")
        if proceed.strip().lower() != "y":
            sys.exit(1)


def seed_contacts():
    print("\nSeeding contacts (neutral)...")
    for name in NEUTRAL_CONTACTS:
        cmd = (
            'adb shell content insert --uri content://contacts/people '
            f'--bind name:s:"{name}"'
        )
        rc, out, err = run(cmd)
        status = "OK" if rc == 0 else f"FAIL ({err[:60]})"
        print(f"  [contact] {name} -> {status}")

    print("\nSeeding contacts (relevant/scenario)...")
    for name in RELEVANT_CONTACTS:
        cmd = (
            'adb shell content insert --uri content://contacts/people '
            f'--bind name:s:"{name}"'
        )
        rc, out, err = run(cmd)
        status = "OK" if rc == 0 else f"FAIL ({err[:60]})"
        print(f"  [contact] {name} -> {status}")


def seed_calls(call_list, label):
    print(f"\nSeeding {len(call_list)} {label} calls...")
    ok_count = 0
    for i, (number, duration, call_type) in enumerate(call_list):
        date_ms = BASE_TIMESTAMP_MS + i * 3600000  # 1 hour apart, arbitrary
        cmd = (
            "adb shell content insert --uri content://call_log/calls "
            f'--bind number:s:"{number}" '
            f"--bind duration:i:{duration} "
            f"--bind type:i:{call_type} "
            f'--bind date:s:"{date_ms}"'
        )
        rc, out, err = run(cmd)
        status = "OK" if rc == 0 and "Error" not in err else f"FAIL ({err[:80]})"
        if status == "OK":
            ok_count += 1
        print(f"  [call] {number} dur={duration}s type={call_type} -> {status}")
    return ok_count


def verify():
    print("\nVerifying seeded data...")
    rc, out, err = run("adb shell content query --uri content://contacts/people")
    contact_rows = out.count("Row:")
    print(f"  Contacts visible via query: {contact_rows}")

    rc, out, err = run("adb shell content query --uri content://call_log/calls")
    call_rows = out.count("Row:")
    print(f"  Call log rows visible via query: {call_rows}")

    if call_rows == 0:
        print("\n  WARNING: 0 call log rows found. If inserts above reported")
        print("  OK but query shows nothing, re-run with 'adb root' active:")
        print("      adb root && python3 seed_test_data.py")


def main():
    check_device()
    seed_contacts()
    neutral_ok = seed_calls(NEUTRAL_CALLS, "neutral")
    relevant_ok = seed_calls(RELEVANT_CALLS, "scenario-relevant")
    verify()

    print("\nDone. Ground-truth summary:")
    print(f"  Neutral contacts seeded:  {len(NEUTRAL_CONTACTS)}")
    print(f"  Relevant contacts seeded: {len(RELEVANT_CONTACTS)}")
    print(f"  Neutral calls seeded:     {neutral_ok}/{len(NEUTRAL_CALLS)}")
    print(f"  Relevant calls seeded:    {relevant_ok}/{len(RELEVANT_CALLS)}")
    print()
    print("Save these counts - this is your ground truth for labeling")
    print("agreement / Cohen's kappa comparison later.")
    print()
    print("NOTE: SMS was intentionally skipped on this device - see the")
    print("module docstring for why (no RIL/telephony hardware on this VM).")


if __name__ == "__main__":
    main()
