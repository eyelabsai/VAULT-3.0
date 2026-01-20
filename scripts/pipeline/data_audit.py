#!/usr/bin/env python3
"""
Comprehensive Data Audit for ICL Repository
Calculates and reports data pipeline statistics to ensure accuracy.
"""

import os
import pandas as pd
from pathlib import Path

# Paths
XML_FOLDER = "XML files"
ROSTER_MD = "data/processed/roster.md"
MATCHED_CSV = "data/processed/matched_patients.csv"
TRAINING_CSV = "data/processed/training_data.csv"
EXCEL_CSV = "data/excel/VAULT 3.0.csv"
FLAGGED_CSV = "data/processed/flagged_incomplete_cases.csv"

def get_xml_count():
    if not os.path.exists(XML_FOLDER):
        return 0, []
    files = [f for f in os.listdir(XML_FOLDER) if f.lower().endswith('.xml')]
    return len(files), sorted(files)

def audit():
    print("\n" + "="*80)
    print("ICL DATA PIPELINE AUDIT")
    print("="*80)
    
    # 1. XML Files on Disk
    total_xmls, xml_list = get_xml_count()
    
    # Determine range and missing
    if xml_list:
        try:
            numbers = [int(f.split('.')[0]) for f in xml_list if f.split('.')[0].isdigit()]
            min_num = min(numbers)
            max_num = max(numbers)
            all_possible = set(range(min_num, max_num + 1))
            missing = all_possible - set(numbers)
        except:
            min_num, max_num = 0, 0
            missing = []
    else:
        min_num, max_num, missing = 0, 0, []

    print(f"\n[XML FILES]")
    print(f"  Total XML files on disk: {total_xmls}")
    print(f"  Range: {min_num:08d}.xml to {max_num:08d}.xml")
    if missing:
        print(f"  Missing IDs in range ({len(missing)}): {sorted(list(missing))[:10]}...")
    
    # 2. Matched Data
    if os.path.exists(MATCHED_CSV):
        df_matched = pd.read_csv(MATCHED_CSV)
        matched_xmls = set(df_matched['XML File'].unique())
        unmatched_count = total_xmls - len(matched_xmls)
        
        print(f"\n[EXCEL MATCHING]")
        print(f"  Matched to Excel: {len(matched_xmls)}")
        print(f"  NOT matched to Excel: {unmatched_count}")
        
        if unmatched_count > 0:
            unmatched_xmls = set(xml_list) - matched_xmls
            # Save unmatched for reference
            unmatched_df = pd.DataFrame({'XML_File': sorted(list(unmatched_xmls))})
            unmatched_df.to_csv("data/processed/unmatched_xmls.csv", index=False)
            print(f"  -> Details saved to: data/processed/unmatched_xmls.csv")
    else:
        print(f"\n[EXCEL MATCHING] Matched file not found.")

    # 3. Feature Extraction
    if os.path.exists(TRAINING_CSV):
        df_train = pd.read_csv(TRAINING_CSV)
        extracted_xmls = set(df_train['XML_File'].unique())
        failed_count = total_xmls - len(extracted_xmls)
        
        print(f"\n[FEATURE EXTRACTION]")
        print(f"  Successfully extracted: {len(extracted_xmls)}")
        print(f"  Failed extraction/Missing: {failed_count}")
        
        if failed_count > 0:
            failed_xmls = set(xml_list) - extracted_xmls
            failed_df = pd.DataFrame({'XML_File': sorted(list(failed_xmls))})
            failed_df.to_csv("data/processed/failed_extractions.csv", index=False)
            print(f"  -> Details saved to: data/processed/failed_extractions.csv")
            
        # Outcomes check
        has_outcomes = df_train[df_train['Lens_Size'].notna() & df_train['Vault'].notna()]
        missing_outcomes = len(df_train) - len(has_outcomes)
        
        print(f"\n[OUTCOMES]")
        print(f"  Cases with Outcomes (Lens+Vault): {len(has_outcomes)}")
        print(f"  Cases MISSING Outcomes: {missing_outcomes}")
        
        if missing_outcomes > 0:
            missing_df = df_train[df_train['Lens_Size'].isna() | df_train['Vault'].isna()][['XML_File', 'Name', 'Eye']]
            missing_df.to_csv("data/processed/missing_outcomes.csv", index=False)
            print(f"  -> Details saved to: data/processed/missing_outcomes.csv")

        # Trainability check (6 core features - Updated Jan 19, 2026)
        core_features = ['Age', 'WTW', 'ACD_internal', 'ICL_Power', 'AC_shape_ratio', 'SimK_steep']
        df_train_outcomes = df_train[df_train['Lens_Size'].notna() & df_train['Vault'].notna()]
        trainable = df_train_outcomes[core_features].notna().all(axis=1)
        
        print(f"\n[MODEL READINESS]")
        print(f"  Fully Trainable (6 features + outcomes): {trainable.sum()}")
        print(f"  Incomplete (outcomes exist, but features missing): {len(df_train_outcomes) - trainable.sum()}")
        
    else:
        print(f"\n[FEATURE EXTRACTION] Training data not found.")

    print("\n" + "="*80)
    print("AUDIT COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    audit()
