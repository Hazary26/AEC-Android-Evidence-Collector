"""
AEC - Phase 10: Evidence Integrity Hashing
Always run last. Hashes every file collected in the case folder.
"""

import os
import hashlib


def _hash_file(path, algo):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run(case_dir):
    print("[Phase 10] Evidence Integrity Hashing...")

    md5_out = os.path.join(case_dir, "md5_hashes.txt")
    sha256_out = os.path.join(case_dir, "sha256_hashes.txt")

    md5_lines = []
    sha256_lines = []

    for root, _, files in os.walk(case_dir):
        for fname in files:
            if fname in ("md5_hashes.txt", "sha256_hashes.txt"):
                continue  # don't hash our own output files
            fpath = os.path.join(root, fname)
            try:
                md5_lines.append(f"{_hash_file(fpath, 'md5')}  {fpath}")
                sha256_lines.append(f"{_hash_file(fpath, 'sha256')}  {fpath}")
            except Exception as e:
                md5_lines.append(f"ERROR hashing {fpath}: {e}")

    with open(md5_out, "w") as f:
        f.write("\n".join(md5_lines) + "\n")
    with open(sha256_out, "w") as f:
        f.write("\n".join(sha256_lines) + "\n")

    print(f"[Phase 10] Done -> {md5_out}, {sha256_out}")
    print(f"  {len(md5_lines)} files hashed.")
    return sha256_out
