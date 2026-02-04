#!/usr/bin/env python3
"""
ICL Vault Prediction - Master Pipeline
Automated end-to-end workflow from INI files to training dataset.

Usage:
    python run_pipeline.py

This will:
1. Convert Excel to CSV (canonical data/excel path)
2. Process ZIP/INI files → extract INIs → convert to XML
3. Run preprocessing audit and enforce XML integrity gates
4. Match XML files with CSV roster
5. Extract features for ML training
6. Run post-extraction audit and enforce feature gates
7. Generate summary report
"""

import subprocess
import sys
import os
import csv
from datetime import datetime

EXCEL_XLSX = "data/excel/VAULT 3.0.xlsx"
EXCEL_CSV = "data/excel/VAULT 3.0.csv"
PROCESSED_DIR = "data/processed"
TRAINING_CSV = f"{PROCESSED_DIR}/training_data.csv"
MATCHED_CSV = f"{PROCESSED_DIR}/matched_patients.csv"
FLAGGED_INCOMPLETE = f"{PROCESSED_DIR}/flagged_incomplete_cases.csv"
AUDIT_MISSING_XML = f"{PROCESSED_DIR}/missing_xml_ids.csv"
AUDIT_NONSTANDARD_XML = f"{PROCESSED_DIR}/nonstandard_xml_filenames.csv"
AUDIT_DUPLICATE_XML = f"{PROCESSED_DIR}/duplicate_xml_ids.csv"


def run_command(cmd, description):
    """Run a shell command and report status."""
    print(f"\n{'='*70}")
    print(f"STEP: {description}")
    print(f"{'='*70}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(result.stdout)
        print(f"✅ {description} - COMPLETE")
        return True
    else:
        print(f"❌ {description} - FAILED")
        print(result.stderr)
        return False

def csv_row_count(path):
    if not os.path.exists(path):
        return 0
    with open(path, newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)

def gate_on_csv_rows(path, reason):
    rows = csv_row_count(path)
    if rows > 0:
        print(f"\n❌ Preprocessing gate failed: {reason}")
        print(f"   -> {path} has {rows} row(s)")
        sys.exit(1)

def run_preprocessing_gates():
    gate_on_csv_rows(AUDIT_MISSING_XML, "Missing XML IDs in sequence")
    gate_on_csv_rows(AUDIT_NONSTANDARD_XML, "Non-standard XML filenames")
    gate_on_csv_rows(AUDIT_DUPLICATE_XML, "Duplicate XML numeric IDs")

def run_feature_gates():
    gate_on_csv_rows(FLAGGED_INCOMPLETE, "Incomplete cases missing required features")

def check_files():
    """Check for required files and directories."""
    print("\n" + "="*70)
    print("PRE-FLIGHT CHECK")
    print("="*70)
    
    checks = {
        'Excel roster': EXCEL_XLSX,
        'Images folder': 'data/images',
        'XML folder': 'XML files',
        'Virtual env': 'venv',
        'excel_to_csv.py': 'scripts/pipeline/excel_to_csv.py',
        'ini_to_xml.py': 'scripts/pipeline/ini_to_xml.py',
        'match_xml_csv.py': 'scripts/pipeline/match_xml_csv.py',
        'extract_features.py': 'scripts/pipeline/extract_features.py',
        'feature_config.py': 'scripts/pipeline/feature_config.py',
        'data_audit.py': 'scripts/pipeline/data_audit.py',
    }
    
    all_ok = True
    for name, path in checks.items():
        exists = os.path.exists(path)
        status = "✓" if exists else "✗"
        print(f"  [{status}] {name}: {path}")
        if not exists and name != 'Images folder':
            all_ok = False
    
    if not all_ok:
        print("\n❌ Missing required files. Cannot proceed.")
        return False
    
    # Count INI/ZIP files
    if os.path.exists('data/images'):
        ini_files = [f for f in os.listdir('data/images') if f.upper().endswith('.INI')]
        zip_files = [f for f in os.listdir('data/images') if f.lower().endswith('.zip')]
        print(f"\n  Found {len(zip_files)} ZIP file(s) and {len(ini_files)} INI file(s) in data/images/")
    
    print("\n✅ Pre-flight check passed")
    return True


def main():
    """Run the complete pipeline."""
    print("\n" + "="*70)
    print("ICL VAULT PREDICTION - AUTOMATED PIPELINE")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Pre-flight check
    if not check_files():
        sys.exit(1)
    
    # Step 1: Convert Excel to CSV (canonical path)
    os.makedirs("data/excel", exist_ok=True)
    success = run_command(
        f"source venv/bin/activate && python scripts/pipeline/excel_to_csv.py \"{EXCEL_XLSX}\" \"{EXCEL_CSV}\"",
        "Convert Excel roster to CSV"
    )
    if not success:
        print("\n❌ Pipeline failed at Excel conversion")
        sys.exit(1)
    
    # Step 2: Process INI files (unzip + convert to XML)
    # Check if there are any files to process
    if os.path.exists('data/images'):
        has_zip = any(f.lower().endswith('.zip') for f in os.listdir('data/images') if os.path.isfile(os.path.join('data/images', f)))
        has_ini = any(f.upper().endswith('.INI') for f in os.listdir('data/images') if os.path.isfile(os.path.join('data/images', f)))
    else:
        has_zip = False
        has_ini = False
    
    if has_zip or has_ini:
        success = run_command(
            "source venv/bin/activate && python scripts/pipeline/ini_to_xml.py --auto",
            "Process INI files (unzip + convert to XML)"
        )
        if not success:
            print("\n❌ Pipeline failed at INI processing")
            sys.exit(1)
    else:
        print("\n⚠️  No data/images folder or no ZIP/INI files found - skipping INI processing")
    
    # Step 3: Preprocessing audit (XML integrity gates)
    success = run_command(
        "source venv/bin/activate && python scripts/pipeline/data_audit.py",
        "Run preprocessing audit (XML integrity)"
    )
    if not success:
        print("\n❌ Pipeline failed at preprocessing audit")
        sys.exit(1)
    run_preprocessing_gates()

    # Step 4: Match XML to CSV
    success = run_command(
        "source venv/bin/activate && python scripts/pipeline/match_xml_csv.py",
        "Match XML files with CSV roster"
    )
    if not success:
        print("\n❌ Pipeline failed at XML-CSV matching")
        sys.exit(1)
    
    # Step 5: Extract features
    success = run_command(
        "source venv/bin/activate && python scripts/pipeline/extract_features.py",
        "Extract features for ML training"
    )
    if not success:
        print("\n❌ Pipeline failed at feature extraction")
        sys.exit(1)
    
    # Step 6: Post-extraction audit (outputs + readiness)
    success = run_command(
        "source venv/bin/activate && python scripts/pipeline/data_audit.py",
        "Run post-extraction data audit"
    )
    if not success:
        print("\n❌ Pipeline failed at data audit")
        sys.exit(1)
    run_feature_gates()

    # Step 7: Generate summary report
    print(f"\n{'='*70}")
    print("PIPELINE SUMMARY")
    print(f"{'='*70}")
    
    # Run summary analysis
    summary_cmd = """
import pandas as pd
import os
import importlib.util

def load_training_features():
    config_path = os.path.join(os.getcwd(), "scripts/pipeline/feature_config.py")
    spec = importlib.util.spec_from_file_location("feature_config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TRAINING_FEATURES

print()
print("Files generated:")
print("  ✓ data/excel/VAULT 3.0.csv - Roster in CSV format")
print("  ✓ data/processed/roster.md - Quick reference of processed XMLs")
print("  ✓ data/processed/matched_patients.csv - XML↔CSV crosswalk")
print("  ✓ data/processed/training_data.csv - ML training dataset")
print("  ✓ data/processed/flagged_incomplete_cases.csv - Outcomes but missing features")

if os.path.exists('data/processed/training_data.csv'):
    df = pd.read_csv('data/processed/training_data.csv')
    training_features = load_training_features()
    
    both_outcomes = df[['Vault','Lens_Size']].notna().all(axis=1)
    # Check configurable features used in training
    all_features = df[training_features].notna().all(axis=1)
    complete = all_features & both_outcomes
    
    print()
    print(f"Total XML files processed: {len(df)}")
    print(f"  With Vault + Lens Size: {both_outcomes.sum()}")
    print(f"  With {len(training_features)} training features: {all_features.sum()}")
    print()
    print(f"🎯 COMPLETE TRAINING CASES: {complete.sum()}/{len(df)}")
    
    # Flag incomplete cases (already saved by extract_features.py)
    incomplete = both_outcomes & ~all_features
    if incomplete.sum() > 0:
        print()
        print(f"⚠️  {incomplete.sum()} cases have outcomes but missing features:")
        print("   → Saved to: data/processed/flagged_incomplete_cases.csv")
        incomplete_df = df[incomplete]
        
        # Show what's missing
        for col in training_features:
            missing = incomplete_df[col].isnull().sum()
            if missing > 0:
                print(f"      {missing} missing {col}")
    
    # Flag validation warnings
    if 'validation_warnings' in df.columns:
        has_warnings = df['validation_warnings'].notna() & (df['validation_warnings'] != '')
        if has_warnings.sum() > 0:
            print()
            print(f"⚠️  {has_warnings.sum()} cases have validation warnings")
            print("   → Check extract_features.py output for details")
else:
    print("⚠️  data/processed/training_data.csv not found")

print()
print("="*70)
print("✅ PIPELINE COMPLETE")
print("="*70)
print()
print("Next steps:")
print("  1. Review data/processed/flagged_incomplete_cases.csv (if exists)")
print("  2. Use data/processed/training_data.csv for ML model training")
print("  3. Re-run this pipeline when adding new INI batches")
"""
    
    summary_cmd_escaped = summary_cmd.replace('"', '\\"')
    subprocess.run(
        f"source venv/bin/activate && python3 -c \"{summary_cmd_escaped}\"",
        shell=True
    )
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == '__main__':
    main()

