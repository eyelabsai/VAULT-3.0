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
        'Excel roster': 'excel/VAULT 3.0.xlsx',
        'Images folder': 'images',
        'XML folder': 'XML files',
        'Virtual env': 'venv',
        'ini_to_xml.py': 'ini_to_xml.py',
        'match_xml_csv.py': 'match_xml_csv.py',
        'extract_features.py': 'extract_features.py',
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
    if os.path.exists('images'):
        ini_files = [f for f in os.listdir('images') if f.upper().endswith('.INI')]
        zip_files = [f for f in os.listdir('images') if f.lower().endswith('.zip')]
        print(f"\n  Found {len(zip_files)} ZIP file(s) and {len(ini_files)} INI file(s) in images/")
    
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
        "source venv/bin/activate && python excel_to_csv.py excel/VAULT\\ 3.0.xlsx",
        "Convert Excel roster to CSV"
    )
    if not success:
        print("\n❌ Pipeline failed at Excel conversion")
        sys.exit(1)
    
    # Step 2: Process INI files (unzip + convert to XML)
    # Check if there are any files to process
    has_zip = any(f.lower().endswith('.zip') for f in os.listdir('images') if os.path.isfile(os.path.join('images', f)))
    has_ini = any(f.upper().endswith('.INI') for f in os.listdir('images') if os.path.isfile(os.path.join('images', f)))
    
    if has_zip or has_ini:
        success = run_command(
            "source venv/bin/activate && python ini_to_xml.py --auto",
            "Process INI files (unzip + convert to XML)"
        )
        if not success:
            print("\n❌ Pipeline failed at INI processing")
            sys.exit(1)
    else:
        print("\n⚠️  No ZIP or INI files found in images/ - skipping INI processing")
    
    # Step 3: Match XML to CSV
    success = run_command(
        "source venv/bin/activate && python match_xml_csv.py",
        "Match XML files with CSV roster"
    )
    if not success:
        print("\n❌ Pipeline failed at XML-CSV matching")
        sys.exit(1)
    
    # Step 4: Extract features
    success = run_command(
        "source venv/bin/activate && python extract_features.py",
        "Extract features for ML training"
    )
    if not success:
        print("\n❌ Pipeline failed at feature extraction")
        sys.exit(1)
    
    # Step 5: Generate summary report
    print(f"\n{'='*70}")
    print("PIPELINE SUMMARY")
    print(f"{'='*70}")
    
    # Run summary analysis
    summary_cmd = """
import pandas as pd
import os

print()
print("Files generated:")
print("  ✓ excel/VAULT 3.0.csv - Roster in CSV format")
print("  ✓ roster.md - Quick reference of processed XMLs")
print("  ✓ matched_patients.csv - XML↔CSV crosswalk")
print("  ✓ training_data.csv - ML training dataset")

if os.path.exists('training_data.csv'):
    df = pd.read_csv('training_data.csv')
    
    both_outcomes = df[['Vault','Lens_Size']].notna().all(axis=1)
    # Check core features used in training (BAD_D removed - see feature_selection_analysis.py)
    all_features = df[['Age','WTW','ACD','ACV','SEQ','SimK_steep','CCT']].notna().all(axis=1)
    # all_features = df[['Age','WTW','ACD','ACV','SEQ','SimK_steep','CCT','BAD_D']].notna().all(axis=1)  # Uncomment to add BAD_D back
    complete = all_features & both_outcomes
    
    print()
    print(f"Total XML files processed: {len(df)}")
    print(f"  With Vault + Lens Size: {both_outcomes.sum()}")
    print(f"  With core 7 features: {all_features.sum()}")
    print()
    print(f"🎯 COMPLETE TRAINING CASES: {complete.sum()}/{len(df)}")
    
    # Flag incomplete cases
    incomplete = both_outcomes & ~all_features
    if incomplete.sum() > 0:
        print()
        print(f"⚠️  {incomplete.sum()} cases have outcomes but missing features:")
        incomplete_df = df[incomplete][['XML_File','Name','Eye','WTW','ACD','ACV','SEQ','Vault','Lens_Size']]
        incomplete_df.to_csv('flagged_incomplete_cases.csv', index=False)
        print("   → Saved to: flagged_incomplete_cases.csv")
        
        # Show what's missing
        for col in ['WTW','ACD','ACV','SEQ']:
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
    print("⚠️  training_data.csv not found")

print()
print("="*70)
print("✅ PIPELINE COMPLETE")
print("="*70)
print()
print("Next steps:")
print("  1. Review flagged_incomplete_cases.csv (if exists)")
print("  2. Use training_data.csv for ML model training")
print("  3. Re-run this pipeline when adding new INI batches")
"""
    
    subprocess.run(
        f"source venv/bin/activate && python3 -c \"{summary_cmd}\"",
        shell=True
    )
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == '__main__':
    main()

