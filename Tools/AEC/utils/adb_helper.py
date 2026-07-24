"""
AEC - Android Evidence Collector
utils/adb_helper.py

Core ADB wrapper. Every module calls these functions instead of
shelling out to `adb` directly, so logging/error-handling stays
in one place.
"""

import subprocess
import datetime
import os

# ---------------------------------------------------------------
# Audit log — every command AEC runs gets written here with a
# timestamp. Forensic tools need an audit trail; this is it.
# ---------------------------------------------------------------
_LOG_FILE = None


def init_logger(case_dir):
    """Call once at startup. Sets up the command audit log for this case."""
    global _LOG_FILE
    _LOG_FILE = os.path.join(case_dir, "aec_audit_log.txt")
    with open(_LOG_FILE, "a") as f:
        f.write(f"\n{'='*70}\nAEC session started: {datetime.datetime.now().isoformat()}\n{'='*70}\n")


def _log(line):
    if _LOG_FILE:
        with open(_LOG_FILE, "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] {line}\n")


def run_adb(args, output_file=None, timeout=60):
    """
    Run an adb command, exactly as you'd type it yourself.
    args: list of args after 'adb', e.g. ["shell", "getprop"]
    output_file: if given, stdout is written there (same bytes as
                 manually redirecting `adb ... > file`)
    Returns: (stdout_text, returncode)
    """
    cmd = ["adb"] + args
    cmd_str = " ".join(cmd)
    _log(f"RUN: {cmd_str}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        _log(f"TIMEOUT: {cmd_str}")
        return "", -1
    except FileNotFoundError:
        _log("ERROR: adb binary not found on PATH")
        return "", -1

    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            f.write(result.stdout)
        _log(f"  -> saved output to {output_file}")

    if result.returncode != 0 and result.stderr:
        _log(f"  stderr: {result.stderr.strip()}")

    return result.stdout, result.returncode


def adb_shell(shell_cmd, output_file=None, timeout=60):
    """Shortcut for `adb shell <shell_cmd>`."""
    return run_adb(["shell", shell_cmd], output_file, timeout)


def adb_pull(device_path, local_path, timeout=300):
    """Pull a file/folder from the device. File pulls can be slow — longer timeout."""
    os.makedirs(os.path.dirname(local_path) if os.path.dirname(local_path) else ".", exist_ok=True)
    return run_adb(["pull", device_path, local_path], timeout=timeout)


def check_device_connected():
    """
    Returns (True, serial) if exactly one authorized device is connected,
    (False, reason) otherwise. Always call this before running phases.
    """
    stdout, rc = run_adb(["devices"])
    lines = [l.strip() for l in stdout.splitlines() if l.strip() and "List of devices" not in l]

    if not lines:
        return False, "No device found. Is the LineageOS VM running and adb connect done?"

    devices = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            devices.append((parts[0], parts[1]))

    unauthorized = [d for d in devices if d[1] == "unauthorized"]
    authorized = [d for d in devices if d[1] == "device"]

    if unauthorized and not authorized:
        return False, f"Device {unauthorized[0][0]} is unauthorized. Check the RSA key / device popup."
    if not authorized:
        return False, f"No authorized device. Raw output: {stdout}"
    if len(authorized) > 1:
        return False, f"Multiple devices connected ({[d[0] for d in authorized]}). Connect only one."

    return True, authorized[0][0]


def check_root():
    """Returns True if `adb root` succeeds and shell runs as root."""
    run_adb(["root"])
    stdout, rc = adb_shell("id")
    return "uid=0" in stdout
