#!/usr/bin/env python3
"""
INI Feature Checker — Validate Pentacam INI files for Vault 3 readiness.

Scans every .ini file in data/inbox/, checks which of the 9 required model
metrics are present, and writes a report to data/inbox/output/.

Usage:
    python scripts/check_ini.py                   # process data/inbox/
    python scripts/check_ini.py /path/to/folder   # process custom folder

Output:
    data/inbox/output/ini_check_<timestamp>.txt   (human-readable report)
"""

import os
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from backend.app.supabase_client import parse_ini_strip_phi

# ── The 9 required model metrics and the INI keys they map to ──────────────

METRIC_MAP = [
    {
        "metric": "Age",
        "ini_key": "DOB  (in [Patient Data])",
        "ini_section": "[Patient Data]",
        "notes": "Calculated from DOB, not a direct value",
    },
    {
        "metric": "WTW",
        "ini_key": "Cornea Dia Horizontal",
        "ini_section": "[Test Data] or [Examination Data]",
        "notes": "Often empty on older Pentacam exports",
    },
    {
        "metric": "ACD_internal",
        "ini_key": "ACD (Int.) [mm]",
        "ini_section": "[Examination Data]",
        "notes": "Fallback: ACD external − CCT/1000",
    },
    {
        "metric": "ICL_Power",
        "ini_key": "(not in INI — user input)",
        "ini_section": "—",
        "notes": "Surgeon enters manually; never in Pentacam file",
    },
    {
        "metric": "AC_shape_ratio",
        "ini_key": "(calculated: ACV / ACD_internal)",
        "ini_section": "—",
        "notes": "Derived — requires both ACV and ACD_internal",
    },
    {
        "metric": "SimK_steep",
        "ini_key": "SimK steep D",
        "ini_section": "[Test Data]",
        "notes": "",
    },
    {
        "metric": "ACV",
        "ini_key": "ACV",
        "ini_section": "[Examination Data]",
        "notes": "Anterior chamber volume; most common missing field",
    },
    {
        "metric": "TCRP_Km",
        "ini_key": "TCRP 3mm zone pupil Km [D]",
        "ini_section": "[Examination Data]",
        "notes": "Total corneal refractive power, 3mm pupil zone mean K",
    },
    {
        "metric": "TCRP_Astigmatism",
        "ini_key": "TCRP 3mm zone pupil Asti [D]",
        "ini_section": "[Examination Data]",
        "notes": "Total corneal refractive power, 3mm pupil zone astigmatism",
    },
]

REQUIRED_FROM_INI = [
    m["metric"] for m in METRIC_MAP if m["metric"] != "ICL_Power"
]

BONUS_FIELDS = {
    "CCT": "Central Corneal Thickness",
    "Eye": "Eye (OD/OS)",
    "Pupil_diameter": "Pupil Diameter",
    "ACA_global": "ACA (180°)",
    "BAD_D": "BAD D",
    "Exam_Date": "Test Date",
}

SEP = "=" * 70


def check_one_ini(filepath: str) -> dict:
    """Parse one INI and return a result dict."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    parsed = parse_ini_strip_phi(content)
    features = parsed["features"]
    eye = parsed.get("eye", "?")
    initials = parsed.get("initials") or "??"
    first = parsed.get("first_name", "")
    last = parsed.get("last_name", "")

    present = {}
    missing = []

    for m in METRIC_MAP:
        key = m["metric"]
        if key == "ICL_Power":
            continue
        val = features.get(key)
        if val is not None:
            present[key] = val
        else:
            missing.append(key)

    bonus = {}
    for bk, bl in BONUS_FIELDS.items():
        val = features.get(bk)
        if val is not None:
            bonus[bk] = val

    return {
        "file": os.path.basename(filepath),
        "path": filepath,
        "initials": initials,
        "first_name": first,
        "last_name": last,
        "eye": eye,
        "present": present,
        "missing": missing,
        "bonus": bonus,
        "complete": len(missing) == 0,
    }


def format_value(val) -> str:
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def format_report(results: list[dict]) -> str:
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append(SEP)
    lines.append("  VAULT 3 — INI FEATURE CHECK REPORT")
    lines.append(f"  Generated: {ts}")
    lines.append(f"  Files scanned: {len(results)}")
    lines.append(SEP)

    # Key reference table
    lines.append("")
    lines.append("  INI KEY → MODEL METRIC REFERENCE")
    lines.append("  " + "-" * 66)
    lines.append(f"  {'Metric':<22} {'INI Key':<38} Notes")
    lines.append("  " + "-" * 66)
    for m in METRIC_MAP:
        note = m["notes"][:30] if m["notes"] else ""
        lines.append(f"  {m['metric']:<22} {m['ini_key']:<38} {note}")
    lines.append("  " + "-" * 66)
    lines.append("")

    # Per-file results
    complete_count = 0
    for r in results:
        if r["complete"]:
            complete_count += 1

        name_display = ""
        if r["last_name"] or r["first_name"]:
            name_display = f"{r['last_name']}, {r['first_name']}".strip(", ")
        else:
            name_display = r["initials"]

        lines.append(SEP)
        lines.append(f"  File:    {r['file']}")
        lines.append(f"  Patient: {name_display}  |  Eye: {r['eye']}")
        status = "COMPLETE" if r["complete"] else f"INCOMPLETE — missing {len(r['missing'])}"
        lines.append(f"  Status:  {status}")
        lines.append("  " + "-" * 66)

        lines.append(f"  {'Metric':<22} {'Status':<10} {'Value':<15} INI Key")
        lines.append(f"  {'-'*22} {'-'*10} {'-'*15} {'-'*30}")

        for m in METRIC_MAP:
            key = m["metric"]
            if key == "ICL_Power":
                lines.append(f"  {key:<22} {'INPUT':<10} {'(user enters)':<15} {m['ini_key']}")
                continue

            val = r["present"].get(key)
            if val is not None:
                lines.append(f"  {key:<22} {'OK':<10} {format_value(val):<15} {m['ini_key']}")
            else:
                lines.append(f"  {key:<22} {'MISSING':<10} {'—':<15} {m['ini_key']}")

        # Bonus fields
        if r["bonus"]:
            lines.append("")
            lines.append("  Extra fields found:")
            for bk, bv in r["bonus"].items():
                label = BONUS_FIELDS.get(bk, bk)
                lines.append(f"    {label:<30} {format_value(bv)}")

        # Missing summary
        if r["missing"]:
            lines.append("")
            lines.append("  *** MISSING FEATURES ***")
            for feat in r["missing"]:
                ini_key = next(
                    (m["ini_key"] for m in METRIC_MAP if m["metric"] == feat), "?"
                )
                lines.append(f"    - {feat} (INI key: {ini_key})")
            if "ACV" in r["missing"]:
                lines.append("")
                lines.append("    Note: Missing ACV also prevents AC_shape_ratio calculation.")
                lines.append("    The Pentacam may not have captured anterior chamber volume.")
                lines.append("    Check the scan quality — lid obstruction or poor fixation can cause this.")
            if "WTW" in r["missing"]:
                lines.append("")
                lines.append("    Note: WTW (Cornea Dia Horizontal) is often blank in older Pentacam exports.")
                lines.append("    The surgeon can measure this with a caliper or enter it manually.")

        lines.append("")

    # Summary
    lines.append(SEP)
    lines.append("  SUMMARY")
    lines.append(SEP)
    lines.append(f"  Total files:   {len(results)}")
    lines.append(f"  Complete:      {complete_count}")
    lines.append(f"  Incomplete:    {len(results) - complete_count}")
    lines.append("")

    if len(results) - complete_count > 0:
        lines.append("  Incomplete files:")
        for r in results:
            if not r["complete"]:
                lines.append(f"    {r['file']:<30} missing: {', '.join(r['missing'])}")
        lines.append("")

    lines.append("  To run predictions, all 8 INI-derived metrics + ICL Power must be present.")
    lines.append("  Missing values must be entered manually by the surgeon before calculating.")
    lines.append(SEP)

    return "\n".join(lines)


def main():
    # Determine input: single file or folder
    if len(sys.argv) > 1:
        target = os.path.abspath(sys.argv[1])
    else:
        target = os.path.join(ROOT, "data", "inbox")

    if os.path.isfile(target) and target.lower().endswith(".ini"):
        # Single file mode
        inbox = os.path.dirname(target)
        ini_files = [target]
    else:
        inbox = target
        ini_files = sorted([
            os.path.join(inbox, f)
            for f in os.listdir(inbox)
            if f.lower().endswith(".ini")
        ])

    output_dir = os.path.join(inbox, "output")

    # Create output folder if needed
    os.makedirs(output_dir, exist_ok=True)

    if not ini_files:
        print(f"\nNo .ini files found in: {inbox}")
        print(f"Drop INI files into that folder and re-run.\n")
        sys.exit(0)

    print(f"\nScanning {len(ini_files)} INI file(s) in: {inbox}\n")

    # Process each file
    results = []
    for fp in ini_files:
        result = check_one_ini(fp)
        results.append(result)

    # Build report
    report = format_report(results)

    # Print to console
    print(report)

    # Write to output file (single file, overwritten each run)
    out_path = os.path.join(output_dir, "ini_check.txt")
    with open(out_path, "w") as f:
        f.write(report)

    print(f"\nReport saved to: {out_path}\n")


if __name__ == "__main__":
    main()
