#!/usr/bin/env python3
"""
Export Beta Data from Supabase
Joins all tables into clean, sortable reports for analysis.

Usage:
    python scripts/export_beta_data.py                  # Export all
    python scripts/export_beta_data.py --user gurpal    # Filter by user
    python scripts/export_beta_data.py --csv            # Save to CSV files
"""

import os
import sys
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
EXPORT_DIR = "data/exports"

HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
}


def query(table, select="*", filters=None):
    """Query Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"
    if filters:
        url += f"&{filters}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def fetch_all_data():
    """Fetch and join all tables."""
    profiles = {p["id"]: p for p in query("profiles")}
    patients = query("patients")
    scans = query("scans")
    predictions = query("predictions")
    outcomes = query("outcomes")

    pred_by_scan = {}
    for p in predictions:
        pred_by_scan.setdefault(p["scan_id"], []).append(p)

    outcome_by_scan = {o["scan_id"]: o for o in outcomes}
    patient_by_id = {p["id"]: p for p in patients}

    rows = []
    for scan in scans:
        patient = patient_by_id.get(scan["patient_id"], {})
        profile = profiles.get(scan["user_id"], {})
        preds = pred_by_scan.get(scan["id"], [])
        latest_pred = preds[-1] if preds else {}
        outcome = outcome_by_scan.get(scan["id"], {})
        features = scan.get("features") or {}

        probs = latest_pred.get("lens_probabilities", {})
        if isinstance(probs, str):
            probs = json.loads(probs)

        row = {
            "doctor": profile.get("full_name") or profile.get("email", "Unknown"),
            "doctor_email": profile.get("email", ""),
            "patient_id": patient.get("anonymous_id", ""),
            "eye": scan.get("eye", ""),
            "scan_date": scan.get("created_at", "")[:10],
            "age": features.get("Age"),
            "wtw": features.get("WTW"),
            "acd_internal": features.get("ACD_internal"),
            "acv": features.get("ACV"),
            "ac_shape_ratio": features.get("AC_shape_ratio"),
            "simk_steep": features.get("SimK_steep"),
            "tcrp_km": features.get("TCRP_Km"),
            "tcrp_astigmatism": features.get("TCRP_Astigmatism"),
            "icl_power": features.get("ICL_Power"),
            "cct": features.get("CCT"),
            "pupil_diameter": features.get("Pupil_diameter"),
            "predicted_lens_size": latest_pred.get("predicted_lens_size"),
            "predicted_vault": latest_pred.get("predicted_vault"),
            "vault_range_low": latest_pred.get("vault_range_low"),
            "vault_range_high": latest_pred.get("vault_range_high"),
            "prob_12.1": probs.get("12.1", 0),
            "prob_12.6": probs.get("12.6", 0),
            "prob_13.2": probs.get("13.2", 0),
            "prob_13.7": probs.get("13.7", 0),
            "model_version": latest_pred.get("model_version", ""),
            "actual_lens_size": outcome.get("actual_lens_size"),
            "actual_vault": outcome.get("actual_vault"),
            "surgery_date": outcome.get("surgery_date"),
            "outcome_notes": outcome.get("notes"),
            "lens_correct": None,
            "vault_error": None,
            "scan_id": scan["id"],
        }

        if row["actual_lens_size"] and row["predicted_lens_size"]:
            row["lens_correct"] = str(row["actual_lens_size"]) == str(row["predicted_lens_size"])
        if row["actual_vault"] is not None and row["predicted_vault"] is not None:
            row["vault_error"] = round(float(row["actual_vault"]) - float(row["predicted_vault"]), 1)

        rows.append(row)

    rows.sort(key=lambda r: (r["doctor_email"], r["scan_date"], r["patient_id"]))
    return rows


def print_summary(rows):
    """Print high-level summary."""
    print("=" * 70)
    print("ICL VAULT BETA — DATA EXPORT")
    print("Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 70)

    doctors = set(r["doctor_email"] for r in rows)
    with_outcomes = [r for r in rows if r["actual_lens_size"] or r["actual_vault"]]

    print("")
    print("SUMMARY".center(70))
    print("-" * 70)
    print(f"  Total scans:        {len(rows)}")
    print(f"  Total doctors:      {len(doctors)}")
    print(f"  With outcomes:      {len(with_outcomes)}")
    print(f"  Awaiting outcomes:  {len(rows) - len(with_outcomes)}")

    print("")
    print("SCANS BY DOCTOR".center(70))
    print("-" * 70)
    header = f"  {'Doctor':<35} {'Scans':>8} {'Outcomes':>10}"
    print(header)
    print(f"  {'─' * 35} {'─' * 8} {'─' * 10}")

    for doc in sorted(doctors):
        doc_rows = [r for r in rows if r["doctor_email"] == doc]
        doc_outcomes = [r for r in doc_rows if r["actual_lens_size"] or r["actual_vault"]]
        name = doc_rows[0]["doctor"] if doc_rows else doc
        print(f"  {name:<35} {len(doc_rows):>8} {len(doc_outcomes):>10}")

    if with_outcomes:
        lens_correct = [r for r in with_outcomes if r["lens_correct"] is True]
        vault_errors = [abs(r["vault_error"]) for r in with_outcomes if r["vault_error"] is not None]

        print("")
        print("MODEL ACCURACY (cases with outcomes)".center(70))
        print("-" * 70)
        lens_total = len([r for r in with_outcomes if r["lens_correct"] is not None])
        if lens_total > 0:
            pct = 100 * len(lens_correct) / lens_total
            print(f"  Lens size accuracy: {len(lens_correct)}/{lens_total} ({pct:.1f}%)")
        if vault_errors:
            mae = sum(vault_errors) / len(vault_errors)
            within_200 = len([e for e in vault_errors if e <= 200])
            pct = 100 * within_200 / len(vault_errors)
            print(f"  Vault MAE:          {mae:.1f}µm")
            print(f"  Within ±200µm:      {within_200}/{len(vault_errors)} ({pct:.1f}%)")


def print_scan_table(rows):
    """Print detailed scan table."""
    print("")
    print("SCAN DETAILS".center(70))
    print("-" * 70)
    print(f"  {'Date':<12} {'Doctor':<18} {'Patient':<15} {'Eye':<5} {'Pred Size':<10} {'Pred Vault':<12} {'Actual':<12}")
    print(f"  {'─' * 12} {'─' * 18} {'─' * 15} {'─' * 5} {'─' * 10} {'─' * 12} {'─' * 12}")

    for r in rows:
        doc_short = (r["doctor"] or "—")[:17]
        patient = (r["patient_id"] or "—")[:14]
        pred_size = f"{r['predicted_lens_size']}mm" if r["predicted_lens_size"] else "—"
        pred_vault = f"{r['predicted_vault']}µm" if r["predicted_vault"] else "—"

        actual = "—"
        if r["actual_lens_size"] or r["actual_vault"]:
            parts = []
            if r["actual_lens_size"]:
                parts.append(f"{r['actual_lens_size']}mm")
            if r["actual_vault"]:
                parts.append(f"{r['actual_vault']}µm")
            actual = " / ".join(parts)

        print(f"  {r['scan_date']:<12} {doc_short:<18} {patient:<15} {r['eye']:<5} {pred_size:<10} {pred_vault:<12} {actual:<12}")


def print_features_table(rows):
    """Print extracted features for each scan."""
    print("")
    print("EXTRACTED FEATURES".center(120))
    print("-" * 120)
    print(f"  {'Patient':<15} {'Eye':<4} {'Age':>5} {'WTW':>6} {'ACD':>6} {'ACV':>6} {'Shape':>7} {'SimK':>6} {'TCRP':>6} {'Astig':>6} {'ICL Pw':>7} {'CCT':>5}")
    print(f"  {'─' * 15} {'─' * 4} {'─' * 5} {'─' * 6} {'─' * 6} {'─' * 6} {'─' * 7} {'─' * 6} {'─' * 6} {'─' * 6} {'─' * 7} {'─' * 5}")

    for r in rows:
        def fmt(v, d=1):
            return f"{v:.{d}f}" if v is not None else "—"

        patient = (r["patient_id"] or "—")[:14]
        print(f"  {patient:<15} {r['eye']:<4} {fmt(r['age'], 0):>5} {fmt(r['wtw']):>6} {fmt(r['acd_internal'], 2):>6} {fmt(r['acv']):>6} {fmt(r['ac_shape_ratio']):>7} {fmt(r['simk_steep']):>6} {fmt(r['tcrp_km']):>6} {fmt(r['tcrp_astigmatism'], 2):>6} {fmt(r['icl_power']):>7} {fmt(r['cct'], 0):>5}")


def print_probabilities_table(rows):
    """Print lens size probabilities."""
    print("")
    print("LENS SIZE PROBABILITIES".center(70))
    print("-" * 70)
    print(f"  {'Patient':<15} {'Eye':<4} {'12.1':>8} {'12.6':>8} {'13.2':>8} {'13.7':>8} {'→ Pred':>8}")
    print(f"  {'─' * 15} {'─' * 4} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 8}")

    for r in rows:
        patient = (r["patient_id"] or "—")[:14]
        pred = r["predicted_lens_size"] or "—"
        print(f"  {patient:<15} {r['eye']:<4} {r['prob_12.1']:>7.1%} {r['prob_12.6']:>7.1%} {r['prob_13.2']:>7.1%} {r['prob_13.7']:>7.1%} {pred:>8}")


def save_csv(rows):
    """Save to CSV files."""
    import csv

    os.makedirs(EXPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    main_file = os.path.join(EXPORT_DIR, f"beta_export_{timestamp}.csv")
    if rows:
        keys = rows[0].keys()
        with open(main_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n✅ Saved: {main_file} ({len(rows)} rows)")

    outcomes_rows = [r for r in rows if r["actual_lens_size"] or r["actual_vault"]]
    if outcomes_rows:
        outcomes_file = os.path.join(EXPORT_DIR, f"outcomes_{timestamp}.csv")
        with open(outcomes_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(outcomes_rows)
        print(f"✅ Saved: {outcomes_file} ({len(outcomes_rows)} rows with outcomes)")

    training_rows = []
    for r in outcomes_rows:
        training_rows.append({
            "Age": r["age"],
            "WTW": r["wtw"],
            "ACD_internal": r["acd_internal"],
            "ACV": r["acv"],
            "AC_shape_ratio": r["ac_shape_ratio"],
            "SimK_steep": r["simk_steep"],
            "TCRP_Km": r["tcrp_km"],
            "TCRP_Astigmatism": r["tcrp_astigmatism"],
            "ICL_Power": r["icl_power"],
            "CCT": r["cct"],
            "Lens_Size": r["actual_lens_size"],
            "Vault": r["actual_vault"],
        })
    if training_rows:
        training_file = os.path.join(EXPORT_DIR, f"training_ready_{timestamp}.csv")
        with open(training_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=training_rows[0].keys())
            writer.writeheader()
            writer.writerows(training_rows)
        print(f"✅ Saved: {training_file} ({len(training_rows)} training-ready rows)")


def main():
    parser = argparse.ArgumentParser(description="Export ICL Vault beta data")
    parser.add_argument("--user", help="Filter by doctor name or email (partial match)")
    parser.add_argument("--csv", action="store_true", help="Save to CSV files")
    parser.add_argument("--features", action="store_true", help="Show extracted features table")
    parser.add_argument("--probs", action="store_true", help="Show lens probabilities table")
    parser.add_argument("--all", action="store_true", help="Show all tables")
    args = parser.parse_args()

    rows = fetch_all_data()

    if args.user:
        term = args.user.lower()
        rows = [r for r in rows if term in r["doctor"].lower() or term in r["doctor_email"].lower()]

    if not rows:
        print("No data found.")
        return

    print_summary(rows)
    print_scan_table(rows)

    if args.features or args.all:
        print_features_table(rows)

    if args.probs or args.all:
        print_probabilities_table(rows)

    if args.csv:
        save_csv(rows)

    print("")
    print("─" * 70)
    print("  Tip: Use --csv to export, --all for full detail, --user NAME to filter")
    print("─" * 70)


if __name__ == "__main__":
    main()