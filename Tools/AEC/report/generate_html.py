"""
AEC - Report Generator
Builds a simple HTML index summarizing what was collected.
For deep artifact parsing (chat messages, etc.), feed the case
folder into ALEAPP separately — AEC just organizes raw evidence.
"""

import os
import datetime


def generate(case_dir, case_name):
    out_path = os.path.join(case_dir, "AEC_report.html")

    rows = []
    for root, _, files in os.walk(case_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, case_dir)
            size = os.path.getsize(fpath)
            rows.append((rel, size))

    rows.sort()
    total_files = len(rows)
    total_size = sum(s for _, s in rows)

    rows_html = "\n".join(
        f"<tr><td>{rel}</td><td>{size:,} bytes</td></tr>" for rel, size in rows
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AEC Report — {case_name}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; margin: 40px; background: #f7f7f8; color: #222; }}
  h1 {{ font-size: 22px; }}
  .meta {{ color: #555; margin-bottom: 20px; }}
  table {{ border-collapse: collapse; width: 100%; background: white; }}
  th, td {{ text-align: left; padding: 6px 12px; border-bottom: 1px solid #eee; font-size: 13px; }}
  th {{ background: #eee; }}
</style>
</head>
<body>
<h1>AEC — Android Evidence Collector Report</h1>
<div class="meta">
  Case: <b>{case_name}</b><br>
  Generated: {datetime.datetime.now().isoformat()}<br>
  Total files collected: {total_files}<br>
  Total size: {total_size:,} bytes
</div>
<table>
<tr><th>File</th><th>Size</th></tr>
{rows_html}
</table>
</body>
</html>
"""
    with open(out_path, "w") as f:
        f.write(html)

    print(f"[Report] Generated -> {out_path}")
    return out_path
