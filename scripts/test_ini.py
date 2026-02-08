#!/usr/bin/env python3
"""
Test INI Feature Extraction
Checks if an INI file has all required features for prediction.

Usage:
    python scripts/test_ini.py data/test_ini/yourfile.ini
    python scripts/test_ini.py data/test_ini/              # Test all INI files in folder
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from backend.app.supabase_client import parse_ini_strip_phi

REQUIRED_FEATURES = [
    "Age", "WTW", "ACD_internal", "ICL_Power", "AC_shape_ratio",
    "SimK_steep", "ACV", "TCRP_Km", "TCRP_Astigmatism",
]

FEATURE_LABELS = {
    "Age": "Age (from DOB)",
    "WTW": "WTW / Cornea Dia Horizontal",
    "ACD_internal": "ACD Internal [mm]",
    "ICL_Power": "ICL Power (user-provided)",
    "AC_shape_ratio": "AC Shape Ratio (ACV/ACD)",
    "SimK_steep": "SimK Steep D",
    "ACV": "ACV",
    "TCRP_Km": "TCRP 3mm Km [D]",
    "TCRP_Astigmatism": "TCRP 3mm Astigmatism [D]",
    "CCT": "Central Corneal Thickness",
    "Pupil_diameter": "Pupil Diameter",
    "ACA_global": "ACA (180deg)",
    "BAD_D": "BAD D",
    "Eye": "Eye (OD/OS)",
}


def test_ini_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    parsed = parse_ini_strip_phi(content)
    features = parsed["features"]
    eye = parsed["eye"]
    initials = parsed.get("initials", "??")

    filename = os.path.basename(filepath)

    print("")
    print("=" * 60)
    print("  File: " + filename)
    print("  Patient: " + str(initials) + "  |  Eye: " + eye)
    print("=" * 60)

    required_from_ini = [f for f in REQUIRED_FEATURES if f != "ICL_Power"]
    present = []
    missing = []

    header = "  {:<30} {:<10} {}".format("Feature", "Status", "Value")
    print(header)
    print("  " + "-" * 30 + " " + "-" * 10 + " " + "-" * 15)

    all_features = list(FEATURE_LABELS.keys())
    for feat in all_features:
        val = features.get(feat)
        label = FEATURE_LABELS.get(feat, feat)
        is_required = feat in required_from_ini

        if val is not None:
            status = "OK"
            val_str = "{:.2f}".format(val) if isinstance(val, float) else str(val)
            present.append(feat)
        elif feat == "ICL_Power":
            status = "INFO"
            val_str = "(user provides)"
        else:
            if is_required:
                status = "MISSING"
                missing.append(feat)
            else:
                status = "n/a"
            val_str = "-"

        req_marker = " *" if is_required else ""
        print("  {:<30} {:<10} {}{}".format(label, status, val_str, req_marker))

    total_required = len(required_from_ini)

    print("")
    print("  " + "-" * 55)
    if missing:
        print("  INCOMPLETE - Missing {}/{} required features:".format(len(missing), total_required))
        for m in missing:
            print("     - " + FEATURE_LABELS.get(m, m))
        print("")
        print("  Prediction will require manual entry of: " + ", ".join(missing))
    else:
        print("  COMPLETE - All {}/{} required features present".format(total_required, total_required))
        print("  Ready for prediction (user just needs to provide ICL Power)")

    return len(missing) == 0


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/test_ini.py <file.ini>")
        print("  python scripts/test_ini.py <folder/>")
        sys.exit(1)

    path = sys.argv[1]

    if os.path.isdir(path):
        ini_files = sorted([
            os.path.join(path, f) for f in os.listdir(path)
            if f.lower().endswith(".ini")
        ])
        if not ini_files:
            print("No .ini files found in " + path)
            sys.exit(1)

        print("Testing {} INI file(s) in {}".format(len(ini_files), path))
        complete = 0
        for f in ini_files:
            if test_ini_file(f):
                complete += 1

        print("")
        print("=" * 60)
        print("  SUMMARY: {}/{} complete".format(complete, len(ini_files)))
        print("=" * 60)
    else:
        if not os.path.exists(path):
            print("File not found: " + path)
            sys.exit(1)
        test_ini_file(path)


if __name__ == "__main__":
    main()