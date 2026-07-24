#!/usr/bin/env python3
"""
AEC GUI - Android Evidence Collector (Graphical version)

A tkinter front-end over the same modules used by main.py (CLI).
No new pip packages required — tkinter ships with python3-tk,
which is already installed on your system.

Run:
    python3 gui.py
"""

import os
import sys
import queue
import threading
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from utils.adb_helper import check_device_connected, init_logger
from modules import (
    device_info,
    network,
    apps,
    filesystem,
    databases,
    communications,
    logs,
    screenshots,
    backup,
    hashing,
)
from report import generate_html

PHASES = [
    (1, "Device Identification", device_info.run),
    (2, "Network Investigation", network.run),
    (3, "Installed Apps", apps.run),
    (4, "File System Extraction", filesystem.run),
    (5, "Database Extraction (root required)", databases.run),
    (6, "Communication Evidence", communications.run),
    (7, "System Logs", logs.run),
    (8, "Screenshot Evidence", screenshots.run),
    (9, "Full Backup", backup.run),
    (10, "Evidence Hashing", hashing.run),
]

BASE_CASE_DIR = os.path.expanduser("~/Desktop")


class TextRedirector:
    """Redirects print()/stdout into a thread-safe queue the GUI polls."""

    def __init__(self, q):
        self.q = q

    def write(self, msg):
        if msg.strip():
            self.q.put(msg)

    def flush(self):
        pass


class AECApp:
    def __init__(self, root):
        self.root = root
        root.title("AEC — Android Evidence Collector")
        root.geometry("760x620")

        self.log_queue = queue.Queue()
        self.case_dir = None
        self.running = False

        self._build_ui()
        self._poll_log_queue()

    # ------------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # --- Top: case name + device status ---
        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)

        ttk.Label(top, text="Case name:").pack(side="left")
        self.case_entry = ttk.Entry(top, width=25)
        self.case_entry.insert(0, f"case_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}")
        self.case_entry.pack(side="left", padx=(6, 20))

        self.device_status = ttk.Label(top, text="Device: not checked", foreground="gray")
        self.device_status.pack(side="left", padx=(0, 10))

        ttk.Button(top, text="Check Device", command=self.check_device).pack(side="left")

        # --- Phase checkboxes ---
        phase_frame = ttk.LabelFrame(self.root, text="Phases to run")
        phase_frame.pack(fill="x", **pad)

        self.phase_vars = {}
        cols = 2
        for i, (num, name, _) in enumerate(PHASES):
            var = tk.BooleanVar(value=True)
            self.phase_vars[num] = var
            cb = ttk.Checkbutton(phase_frame, text=f"{num}. {name}", variable=var)
            cb.grid(row=i // cols, column=i % cols, sticky="w", padx=10, pady=2)

        btn_frame = ttk.Frame(phase_frame)
        btn_frame.grid(row=(len(PHASES) // cols) + 1, column=0, columnspan=2, pady=(6, 4))
        ttk.Button(btn_frame, text="Select All", command=lambda: self._set_all(True)).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Select None", command=lambda: self._set_all(False)).pack(side="left", padx=4)

        # --- Run controls ---
        run_frame = ttk.Frame(self.root)
        run_frame.pack(fill="x", **pad)

        self.run_btn = ttk.Button(run_frame, text="▶ Run AEC", command=self.start_run)
        self.run_btn.pack(side="left")

        self.progress = ttk.Progressbar(run_frame, mode="determinate", length=300)
        self.progress.pack(side="left", padx=12)

        self.report_btn = ttk.Button(run_frame, text="Open Report", command=self.open_report, state="disabled")
        self.report_btn.pack(side="left", padx=4)

        # --- Log output ---
        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)

        self.log_text = tk.Text(log_frame, wrap="word", bg="#111", fg="#0f0", font=("Courier", 10))
        self.log_text.pack(fill="both", expand=True, side="left")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def _set_all(self, value):
        for var in self.phase_vars.values():
            var.set(value)

    # ------------------------------------------------------------------
    def check_device(self):
        ok, info = check_device_connected()
        if ok:
            self.device_status.config(text=f"Device: {info}", foreground="green")
        else:
            self.device_status.config(text="Device: not connected", foreground="red")
            messagebox.showwarning("Device not found", info)

    # ------------------------------------------------------------------
    def start_run(self):
        if self.running:
            return

        case_name = self.case_entry.get().strip()
        if not case_name:
            messagebox.showerror("Error", "Enter a case name first.")
            return

        selected = [num for num, var in self.phase_vars.items() if var.get()]
        if not selected:
            messagebox.showerror("Error", "Select at least one phase.")
            return

        case_dir = os.path.join(BASE_CASE_DIR, case_name)
        if os.path.exists(case_dir):
            messagebox.showerror("Error", f"Case folder already exists:\n{case_dir}\nChoose a new case name.")
            return

        ok, info = check_device_connected()
        if not ok:
            messagebox.showerror("Device not connected", info)
            return

        self.log_text.delete("1.0", "end")
        self.progress["value"] = 0
        self.progress["maximum"] = len(selected) + 1  # +1 for report gen
        self.run_btn.config(state="disabled")
        self.report_btn.config(state="disabled")
        self.running = True
        self.case_dir = case_dir

        thread = threading.Thread(target=self._run_phases, args=(case_dir, case_name, selected), daemon=True)
        thread.start()

    def _run_phases(self, case_dir, case_name, selected):
        old_stdout = sys.stdout
        sys.stdout = TextRedirector(self.log_queue)
        try:
            os.makedirs(case_dir, exist_ok=True)
            init_logger(case_dir)
            print(f"Case folder: {case_dir}")

            phase_map = {num: (name, func) for num, name, func in PHASES}

            for num in sorted(selected):
                name, func = phase_map[num]
                print(f"\n{'='*50}\nPhase {num}: {name}\n{'='*50}")
                try:
                    func(case_dir)
                except Exception as e:
                    print(f"[!] Phase {num} failed: {e}")
                self.root.after(0, self._advance_progress)

            if 10 not in selected:
                print(f"\n{'='*50}\nPhase 10: Evidence Hashing (auto-run)\n{'='*50}")
                hashing.run(case_dir)

            print("\nGenerating report...")
            generate_html.generate(case_dir, case_name)
            self.root.after(0, self._advance_progress)

            print(f"\n✅ Done. Output: {case_dir}")
        except Exception as e:
            print(f"[!] Run failed: {e}")
        finally:
            sys.stdout = old_stdout
            self.root.after(0, self._run_finished)

    def _advance_progress(self):
        self.progress["value"] += 1

    def _run_finished(self):
        self.running = False
        self.run_btn.config(state="normal")
        self.report_btn.config(state="normal")

    # ------------------------------------------------------------------
    def open_report(self):
        if self.case_dir:
            report_path = os.path.join(self.case_dir, "AEC_report.html")
            if os.path.exists(report_path):
                webbrowser.open(f"file://{report_path}")
            else:
                messagebox.showinfo("Not found", "Report not generated yet.")

    # ------------------------------------------------------------------
    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert("end", msg)
                self.log_text.see("end")
        except queue.Empty:
            pass
        self.root.after(150, self._poll_log_queue)


def main():
    root = tk.Tk()
    app = AECApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
