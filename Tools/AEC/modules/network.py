"""
AEC - Phase 2: Network Investigation
"""

import os
from utils.adb_helper import adb_shell


def run(case_dir):
    print("[Phase 2] Network Investigation...")
    out_dir = os.path.join(case_dir, "logs")
    os.makedirs(out_dir, exist_ok=True)

    adb_shell("ip a", output_file=os.path.join(out_dir, "ip_addr.txt"))
    adb_shell("dumpsys wifi", output_file=os.path.join(out_dir, "wifi_info.txt"))
    adb_shell("netstat", output_file=os.path.join(out_dir, "network.txt"))
    adb_shell("cat /proc/net/arp", output_file=os.path.join(out_dir, "arp.txt"))

    dns1, _ = adb_shell("getprop net.dns1")
    dns2, _ = adb_shell("getprop net.dns2")
    with open(os.path.join(out_dir, "dns.txt"), "w") as f:
        f.write(f"dns1: {dns1.strip()}\ndns2: {dns2.strip()}\n")

    print(f"[Phase 2] Done -> {out_dir}")
    return out_dir
