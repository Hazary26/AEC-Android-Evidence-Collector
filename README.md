# AEC — Android Evidence Collector

**AEC** is an automated, ADB-based Android forensic evidence collection tool. It runs a structured, 10-phase extraction pipeline against a connected Android device (physical or virtual), organizes the output into a hashed, auditable case folder, and generates a browsable HTML report — turning what would normally be dozens of manual `adb` commands into a single run.

AEC also ships with an optional analysis pipeline (`analysis/`) for research use: feature extraction, a Random Forest–based artifact relevance classifier, and SHAP-based explainability, intended for academic/experimental work on explainable mobile forensics.

> ⚠️ **For lawful, authorized, and educational use only.** See [Legal & Ethical Use](#legal--ethical-use) below.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
  - [CLI](#cli)
  - [GUI](#gui)
- [The 10 Phases](#the-10-phases)
- [Analysis Pipeline (Research / XAMF)](#analysis-pipeline-research--xamf)
- [Test Data Generation](#test-data-generation)
- [Known Limitations](#known-limitations)
- [Legal & Ethical Use](#legal--ethical-use)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **10-phase automated extraction** — device info, network state, installed apps, filesystem, databases, communications, system logs, screenshots, full backup, and integrity hashing.
- **Audit logging** — every ADB command AEC runs is logged with a timestamp (`aec_audit_log.txt`), so the collection process itself is reviewable.
- **Root-gated phases** — phases that require root (e.g. pulling app databases) detect root availability automatically and skip cleanly if unavailable, instead of crashing the run.
- **Case folder protection** — AEC refuses to overwrite an existing case folder, preventing accidental evidence loss.
- **Two interfaces** — a scriptable CLI (`main.py`) and a Tkinter GUI (`gui.py`) with live command log, progress bar, and one-click report opening.
- **Built-in hashing** — every extracted file is hashed (MD5 + SHA-256) as the final phase, always, regardless of which other phases were selected.
- **HTML report generation** — a single `AEC_report.html` summarizing the case is produced automatically.
- **Optional ML/XAI analysis layer** — feature extraction + Random Forest relevance scoring + SHAP explainability for research use cases.

---

## Architecture

```
AEC/
├── main.py                    # CLI entry point
├── gui.py                     # Tkinter GUI
├── seed_test_data.py          # Synthetic test data generator (contacts + call log)
├── generate_app_data.py       # Pushes sample photos/docs, opens browser URLs
├── modules/                   # One module per extraction phase
│   ├── device_info.py         # Phase 1
│   ├── network.py             # Phase 2
│   ├── apps.py                # Phase 3
│   ├── filesystem.py          # Phase 4
│   ├── databases.py           # Phase 5 (root)
│   ├── communications.py      # Phase 6
│   ├── logs.py                # Phase 7
│   ├── screenshots.py         # Phase 8
│   ├── backup.py              # Phase 9
│   └── hashing.py             # Phase 10
├── utils/
│   └── adb_helper.py          # Central ADB wrapper — every module goes through this
├── report/
│   └── generate_html.py       # Builds AEC_report.html at the end of a run
├── analysis/                  # Optional research/ML pipeline
│   ├── extract_features.py            # File/photo/document artifact → feature vector
│   ├── extract_calllog_features.py    # Call log artifact → feature vector
│   ├── merge_features.py              # Combines the two into one dataset
│   └── train_model.py                 # Random Forest + SHAP training & evaluation
├── sample_photos/             # Sample EXIF/GPS-tagged test images
├── sample_docs/                # Sample dummy documents
└── README.md
```

**Design principle:** `utils/adb_helper.py` is the *only* place that calls `adb`. Every phase module goes through it, which is what makes the single audit log possible and keeps the codebase easy to extend — adding a new phase means adding a new module, not touching the core.

---

## Requirements

- **Host:** Linux (tested on Ubuntu Desktop), with `adb` installed and on `PATH`.
- **Python:** 3.8+ (standard library only for the core tool — no third-party packages required to run `main.py` / `gui.py`).
- **Target device:** Any Android device/emulator reachable via ADB (USB or network), with USB/network debugging enabled and authorized.
- **For the GUI:** `python3-tk` (Tkinter) installed on the host.
- **For the analysis pipeline:** `pandas`, `scikit-learn`, `shap` (see [Analysis Pipeline](#analysis-pipeline-research--xamf)).

---

## Installation

```bash
git clone https://github.com/<your-username>/AEC.git
cd AEC

# No virtual environment is strictly required — the core tool uses only
# Python's standard library. A venv is still recommended for isolation:
python3 -m venv venv
source venv/bin/activate

# GUI dependency (skip if you only use the CLI)
sudo apt install -y python3-tk
```

Verify ADB can see your target device:

```bash
adb devices
```

You should see your device listed as `device` (not `unauthorized` or `offline`).

---

## Usage

### CLI

Run every phase against a new case:

```bash
python3 main.py --case case_001 --full
```

Run only specific phases (e.g. device info + installed apps):

```bash
python3 main.py --case case_002 --phases 1,3
```

List all available phases:

```bash
python3 main.py --list-phases
```

Output is written to `~/Desktop/<case_name>/`, including:

- `device_info/`, `apps/`, `extraction/`, `databases/`, `logs/` — raw extracted evidence, organized by phase
- `screenshot.png` — device screenshot at time of capture
- `full_backup.ab` / `backup_contents/` — raw and extracted `adb backup` data
- `md5_hashes.txt` / `sha256_hashes.txt` — integrity hashes for every extracted file
- `aec_audit_log.txt` — full command-level audit trail
- `AEC_report.html` — browsable summary report

### GUI

```bash
python3 gui.py
```

The GUI provides:

- A pre-filled, timestamped case name field
- A **Check Device** button to confirm ADB connectivity before running anything
- Checkboxes for each phase (Select All / Select None)
- A live scrolling log of every command executed
- A progress bar
- An **Open Report** button to launch `AEC_report.html` once the run finishes

The GUI runs extraction on a background thread, so the window stays responsive during long operations (e.g. the Phase 4 `/sdcard` pull), and it reuses the exact same phase modules as the CLI — results are identical either way.

---

## The 10 Phases

| # | Phase | What it collects | Root required? |
|---|-------|-------------------|-----------------|
| 1 | Device Identification | Model, Android version, manufacturer, build fingerprint | No |
| 2 | Network Investigation | Wi-Fi state, network config/logs | No |
| 3 | Installed Apps | Full package list, user-installed apps | No |
| 4 | File System Extraction | `/sdcard` — DCIM, Download, Documents | No |
| 5 | Database Extraction | App databases (contacts, messaging, browser, WhatsApp, Telegram, etc.) | **Yes** |
| 6 | Communication Evidence | Contacts, call log (and SMS, where the device's radio stack supports it) | No* |
| 7 | System Logs | Full `dumpsys` capture | No |
| 8 | Screenshot Evidence | Current device screen | No |
| 9 | Full Backup | `adb backup` (deprecated but still supported on many builds), extracted to tar | No** |
| 10 | Evidence Hashing | MD5 + SHA-256 of every file collected — always runs last | No |

\* Reading call log/contacts via `content query` may require root on some builds due to `READ_CALL_LOG`/`READ_SMS` permission enforcement on the `shell` UID — see [Known Limitations](#known-limitations).
\** Some devices require manual on-screen confirmation for `adb backup`.

Phase 5 checks for root automatically and skips cleanly (with a clear log message) if the device isn't rooted, rather than failing the whole run.

---

## Analysis Pipeline (Research / XAMF)

The `analysis/` folder implements an experimental **explainable relevance-scoring layer** on top of AEC's raw collection output — intended for research on explainable AI in mobile forensics (e.g. "which of these 200 artifacts should an investigator look at first, and why").

```bash
pip3 install pandas scikit-learn shap --user --break-system-packages

# 1. Extract features from file-based artifacts (photos, documents, etc.)
python3 analysis/extract_features.py --case ~/Desktop/case_001

# 2. Extract features from call log artifacts
python3 analysis/extract_calllog_features.py --case ~/Desktop/case_001

# 3. Merge both into one dataset
python3 analysis/merge_features.py --case ~/Desktop/case_001

# 4. Train + evaluate (Random Forest + SHAP)
python3 analysis/train_model.py --features ~/Desktop/case_001/combined_features.csv
```

`train_model.py` computes:

- **Table I** — Accuracy / Precision / Recall / F1 for a keyword baseline, Logistic Regression, SVM, and Random Forest
- **Table III** — an ablation study across feature categories (type / temporal / content / structural)
- **SHAP explainability** — per-artifact top contributing feature, saved to `shap_top_features.csv`

**Labeling:** artifact relevance ground truth is intended to come from a human-labeled `manual_label` column (added by you, the investigator/annotator, on top of the `auto_label` starting point produced during feature extraction). For multi-annotator studies, `sklearn.metrics.cohen_kappa_score` can be used to report inter-annotator agreement.

> This pipeline is a research prototype, not a production risk-scoring system. Results should be reported with dataset size and labeling methodology clearly stated (see [Known Limitations](#known-limitations)).

---

## Test Data Generation

For lab/research use where no real evidence is available, two helper scripts populate a **controlled, synthetic** dataset with a documented ground truth:

```bash
python3 seed_test_data.py       # Seeds contacts + call log entries (neutral + "scenario-relevant")
python3 generate_app_data.py    # Pushes sample GPS/EXIF photos + dummy documents, opens browser URLs
```

Both scripts print a ground-truth summary at the end (counts of neutral vs. relevant entries seeded) — save this output, since it's the answer key used for labeling agreement / Cohen's kappa in the analysis pipeline.

**This data is synthetic and clearly labeled as such in any resulting research output.** It should never be presented as real user data.

---

## Known Limitations

- **SMS on emulated/x86 Android builds:** On devices without a real or emulated RIL (Radio Interface Layer) — common on x86 LineageOS VMs and some emulator configurations — the SMS content provider's database is never lazily initialized, because Android only creates it once telephony hardware is detected. This is an **environment limitation, not an AEC bug**: `content insert`/`content query` against `content://sms/` will silently do nothing on such devices. AEC's Phase 6 falls back to Contacts + Call Log, which use separate, radio-independent content providers.
- **`content query` permission errors on some builds:** A handful of LineageOS builds restrict `READ_SMS`/`READ_CALL_LOG` for the `shell` UID. Running with `adb root` active resolves this where root access is available; on non-rooted target devices, this data may be inaccessible via `content query` and would require pulling the underlying SQLite databases directly instead (Phase 5, root required).
- **Legacy Android + modern apps:** Android 7.x devices/VMs cannot install current WhatsApp/Telegram/Chrome builds (which require Android 8+). Communication-app artifacts on such targets are limited to native SMS/Call Log/Contacts unless an older, compatible APK is sideloaded.
- **`adb backup` deprecation:** Phase 9 relies on `adb backup`, which Google has deprecated and removed on newer Android versions. It remains functional on many legacy/AOSP-derived builds (including LineageOS 14.1) but should not be relied upon for modern devices.
- **Small-sample studies:** If you're using the analysis pipeline for a research paper with a small, synthetically-seeded dataset, report this explicitly as a pilot study — it's a normal, accepted limitation in forensic tooling research, not a flaw to hide.

---

## Legal & Ethical Use

AEC is built for **authorized forensic research, digital forensics education, and testing on devices you own or have explicit written permission to examine** (e.g. your own lab VMs, a personally-owned test device, or a device you are contractually authorized to investigate).

- Do **not** use AEC against any device without the owner's informed consent or proper legal authority (e.g. a warrant, in a real investigative context).
- Extracting data from a device you do not own or are not authorized to access may violate computer misuse, wiretapping, and/or data protection laws in your jurisdiction.
- If you generate synthetic test data for research (via `seed_test_data.py`), clearly document it as synthetic/controlled data in any resulting paper or report — do not represent it as real user data.
- The maintainers of this project assume no liability for misuse of this tool.

---

## Contributing

Issues and pull requests are welcome. If you're adding a new extraction phase, please:

1. Add a new module under `modules/`, following the existing phase module pattern.
2. Route all `adb` calls through `utils/adb_helper.py` (do not call `adb` directly from a phase module).
3. Make the phase root-gated (with a clean skip) if it depends on root access.
4. Update the phase table in this README.

---

## License

*(Add your chosen license here — e.g. MIT, Apache 2.0. If unsure, [choosealicense.com](https://choosealicense.com/) is a good starting point.)*
