#!/usr/bin/env python3
"""
ICL Vault Prediction - Master Pipeline
Automated end-to-end workflow from INI files to training dataset.

Usage:
    python run_pipeline.py

This will:
1. Convert Excel to CSV (if needed)
2. Process any ZIP files → extract INIs → convert to XML
3. Match XML files with CSV roster
4. Extract features for ML training
5. Generate clean training data + flagged cases for review
"""

import subprocess
import sys
import os
from datetime import datetime


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


def check_files():
    """Check for required files and directories."""
    print("\n" + "="*70)
    print("PRE-FLIGHT CHECK")
    print("="*70)
    
    checks = {
        'Excel roster': 'data/excel/VAULT 3.0.xlsx',
        'Images folder': 'data/images',
        'XML folder': 'data/xml_files',
        'Virtual env': 'venv',
        'ini_to_xml.py': 'scripts/pipeline/ini_to_xml.py',
        'match_xml_csv.py': 'scripts/pipeline/match_xml_csv.py',
        'extract_features.py': 'scripts/pipeline/extract_features.py',
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
    
    # Step 1: Convert Excel to CSV
    success = run_command(
        "source venv/bin/activate && python scripts/pipeline/excel_to_csv.py data/excel/VAULT\\ 3.0.xlsx",
        "Convert Excel roster to CSV"
    )
    if not success:
        print("\n❌ Pipeline failed at Excel conversion")
        sys.exit(1)
    
    # Step 2: Process INI files (unzip + convert to XML)
    # Check if there are any files to process
    has_zip = any(f.lower().endswith('.zip') for f in os.listdir('data/images') if os.path.isfile(os.path.join('data/images', f)))
    has_ini = any(f.upper().endswith('.INI') for f in os.listdir('data/images') if os.path.isfile(os.path.join('data/images', f)))
    
    if has_zip or has_ini:
        success = run_command(
            "source venv/bin/activate && python scripts/pipeline/ini_to_xml.py --auto",
            "Process INI files (unzip + convert to XML)"
        )
        if not success:
            print("\n❌ Pipeline failed at INI processing")
            sys.exit(1)
    else:
        print("\n⚠️  No ZIP or INI files found in images/ - skipping INI processing")
    
    # Step 3: Match XML to CSV
    success = run_command(
        "source venv/bin/activate && python scripts/pipeline/match_xml_csv.py",
        "Match XML files with CSV roster"
    )
    if not success:
        print("\n❌ Pipeline failed at XML-CSV matching")
        sys.exit(1)
    
    # Step 4: Extract features
    success = run_command(
        "source venv/bin/activate && python scripts/pipeline/extract_features.py",
        "Extract features for ML training"
    )
    if not success:
        print("\n❌ Pipeline failed at feature extraction")
        sys.exit(1)
    
    # Step 5: Run Data Audit (Point 2, 3, 4, 5)
    success = run_command(
        "source venv/bin/activate && python scripts/pipeline/data_audit.py",
        "Run comprehensive data audit"
    )
    
    # Step 6: Generate summary report
    print(f"\n{'='*70}")
    print("PIPELINE SUMMARY")
    print(f"{'='*70}")
    
    # Run summary analysis
    summary_cmd = """
import pandas as pd
import os

print()
print("Key Files Updated:")
print("  ✓ data/processed/matched_patients.csv  - Primary matches")
print("  ✓ data/processed/training_data.csv     - Clean ML dataset")
print("  ✓ data/processed/unmatched_xmls.csv    - For manual naming fix")
print("  ✓ data/processed/failed_extractions.csv - Corrupt/format issues")
print("  ✓ data/processed/missing_outcomes.csv   - Pending surgery data")

if os.path.exists('data/processed/training_data.csv'):
    df = pd.read_csv('data/processed/training_data.csv')
    core_features = ['Age', 'WTW', 'ACD_internal', 'SEQ', 'CCT', 'AC_shape_ratio']
    complete = df[core_features + ['Lens_Size', 'Vault']].notna().all(axis=1)
    
    print()
    print(f"Total XMLs processed: {len(df)}")
    print(f"🎯 COMPLETE TRAINING CASES: {complete.sum()}")
else:
    print("⚠️  training_data.csv not found")

print()
print("="*70)
print("✅ PIPELINE COMPLETE")
print("="*70)
"""
    
    subprocess.run(
        f"source venv/bin/activate && python3 -c \"{summary_cmd}\"",
        shell=True
    )
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == '__main__':
    main()

