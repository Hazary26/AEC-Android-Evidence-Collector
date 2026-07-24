# AEC — Android Evidence Collector

An automated ADB-based Android forensic extraction tool. Runs the same
commands you'd type manually across all 10 phases — device info, network,
apps, filesystem, databases, communications, logs, screenshots, backup,
and hashing — automatically, in sequence, with a full audit log.

**AEC does not reinvent ADB.** It runs the exact same `adb` commands you
already use, redirects output into an organized case folder, and logs
every command with a timestamp. The output text is identical to running
the commands yourself — the automation is in not typing 40 commands per case.

## Setup

```bash
# From your project folder
python3 -m venv venv
source venv/bin/activate
```

No extra pip packages are required — AEC only uses Python's standard
library (subprocess, hashlib, zlib, tarfile) plus the `adb` binary
already on your PATH.

## GUI version

A tkinter-based graphical interface is included (`gui.py`) — no extra
pip packages needed, just `python3-tk` (you already have this installed).

```bash
python3 gui.py
```

Features:
- Case name field (auto-fills with a timestamp)
- "Check Device" button — confirms ADB connection before you can run
- Checkboxes to pick which phases to run (or Select All / Select None)
- Live scrolling log output as each phase runs
- Progress bar
- "Open Report" button — opens `AEC_report.html` in your browser once done

## CLI Usage

Check your device is connected first:
```bash
adb devices
```

Run everything:
```bash
python3 main.py --case case_001 --full
```

Run specific phases only (e.g. device info + apps + comms):
```bash
python3 main.py --case case_001 --phases 1,3,6
```

List available phases:
```bash
python3 main.py --list-phases
```

Skip hashing (not recommended for real evidence handling):
```bash
python3 main.py --case case_001 --full --skip-hash
```

## Output structure

```
~/Desktop/case_001/
├── aec_audit_log.txt       # every command run, with timestamps
├── device_info/
├── logs/
├── apps/
├── extraction/
├── photos/ downloads/ documents/
├── databases/
├── full_backup.ab, full_backup.tar, backup_contents/
├── screenshot.png
├── md5_hashes.txt
├── sha256_hashes.txt
└── AEC_report.html          # summary of everything collected
```

## Notes

- Phase 5 (database extraction) needs root ADB. AEC checks automatically
  and skips gracefully with a message if the device isn't rooted.
- AEC will refuse to overwrite an existing case folder — use a new
  `--case` name for each run.
- For deep artifact parsing (turning raw databases into readable chat
  logs, browser history summaries, etc.), feed the case folder into
  **ALEAPP** afterward — AEC's job is clean, organized, hashed collection;
  ALEAPP's job is interpretation.
- Extend it: to add a new phase, create `modules/your_phase.py` with a
  `run(case_dir)` function, then register it in `PHASES` in `main.py`.
