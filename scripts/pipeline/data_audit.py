#!/usr/bin/env python3
"""
Comprehensive Data Audit for ICL Repository
Calculates and reports data pipeline statistics to ensure accuracy.
"""

import os
import re
import hashlib
import pandas as pd
from pathlib import Path
from feature_config import TRAINING_FEATURES

# Paths
XML_FOLDER = "XML files"
ROSTER_MD = "data/processed/roster.md"
MISSING_XML_IDS_FILE = "data/processed/missing_xml_ids.csv"
NONSTANDARD_XML_FILE = "data/processed/nonstandard_xml_filenames.csv"
DUPLICATE_XML_FILE = "data/processed/duplicate_xml_ids.csv"
MATCHED_CSV_CANDIDATES = [
    "data/processed/matched_patients.csv",
    "matched_patients.csv",
]
TRAINING_CSV_CANDIDATES = [
    "data/processed/training_data.csv",
    "training_data.csv",
]
EXCEL_CSV = "data/excel/VAULT 3.0.csv"
FLAGGED_CSV = "data/processed/flagged_incomplete_cases.csv"

def get_xml_count():
    if not os.path.exists(XML_FOLDER):
        return 0, []
    files = [f for f in os.listdir(XML_FOLDER) if f.lower().endswith('.xml')]
    return len(files), sorted(files)

def pick_latest_path(paths):
    existing = [p for p in paths if os.path.exists(p)]
    if not existing:
        return None
    return max(existing, key=os.path.getmtime)

def is_standard_filename(name):
    stem = os.path.splitext(name)[0]
    return re.fullmatch(r"\d{8}", stem) is not None

def file_sha256(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def analyze_xml_filenames(xml_list):
    numeric_ids = []
    invalid_names = []
    id_to_files = {}
    for name in xml_list:
        stem = os.path.splitext(name)[0]
        exact_match = re.fullmatch(r"\d{8}", stem)
        prefix_match = re.match(r"^(\d+)", stem)

        if exact_match:
            numeric_ids.append(int(stem))
        else:
            invalid_names.append(name)

        if prefix_match:
            num = int(prefix_match.group(1))
            id_to_files.setdefault(num, []).append(name)

    duplicates = {num: files for num, files in id_to_files.items() if len(files) > 1}
    return numeric_ids, invalid_names, duplicates

def audit():
    print("\n" + "="*80)
    print("ICL DATA PIPELINE AUDIT")
    print("="*80)
    
    # 1. XML Files on Disk
    total_xmls, xml_list = get_xml_count()
    
    # Determine range, missing, and filename issues
    if xml_list:
        numeric_ids, invalid_names, duplicates = analyze_xml_filenames(xml_list)
        if numeric_ids:
            min_num = min(numeric_ids)
            max_num = max(numeric_ids)
            all_possible = set(range(min_num, max_num + 1))
            missing = all_possible - set(numeric_ids)
        else:
            min_num, max_num, missing = 0, 0, []
    else:
        numeric_ids, invalid_names, duplicates = [], [], {}
        min_num, max_num, missing = 0, 0, []

    print(f"\n[XML FILES]")
    print(f"  Total XML files on disk: {total_xmls}")
    print(f"  Range: {min_num:08d}.xml to {max_num:08d}.xml")
    if missing:
        print(f"  Missing IDs in range ({len(missing)}): {sorted(list(missing))[:10]}...")
    if invalid_names:
        print(f"  Non-standard filenames ({len(invalid_names)}): {sorted(invalid_names)[:10]}...")
    if duplicates:
        print(f"  Duplicate numeric IDs ({len(duplicates)}): {sorted(list(duplicates.keys()))[:10]}...")

    os.makedirs("data/processed", exist_ok=True)
    missing_rows = [{"XML_ID": f"{num:08d}"} for num in sorted(missing)]
    pd.DataFrame(missing_rows).to_csv(MISSING_XML_IDS_FILE, index=False)
    if missing:
        print(f"  -> Details saved to: {MISSING_XML_IDS_FILE}")

    invalid_rows = [{"Filename": name} for name in sorted(invalid_names)]
    pd.DataFrame(invalid_rows).to_csv(NONSTANDARD_XML_FILE, index=False)
    if invalid_names:
        print(f"  -> Details saved to: {NONSTANDARD_XML_FILE}")

    dup_rows = []
    identical_groups = 0
    differing_groups = 0
    for num, files in sorted(duplicates.items()):
        file_hashes = {}
        for name in files:
            path = os.path.join(XML_FOLDER, name)
            if os.path.exists(path):
                file_hashes[name] = file_sha256(path)
            else:
                file_hashes[name] = "missing_on_disk"
        unique_hashes = set(file_hashes.values())
        group_status = "identical" if len(unique_hashes) == 1 else "different"
        if group_status == "identical":
            identical_groups += 1
        else:
            differing_groups += 1
        for name in sorted(files):
            dup_rows.append({
                "XML_ID": f"{num:08d}",
                "File": name,
                "SHA256": file_hashes.get(name, ""),
                "GroupStatus": group_status,
                "IsStandardName": is_standard_filename(name),
                "Recommended_Delete": group_status == "identical" and not is_standard_filename(name),
            })
    if identical_groups:
        print(f"  Duplicate groups with identical content: {identical_groups}")
    if differing_groups:
        print(f"  Duplicate groups with differing content: {differing_groups}")
    pd.DataFrame(dup_rows).to_csv(DUPLICATE_XML_FILE, index=False)
    if dup_rows:
        print(f"  -> Details saved to: {DUPLICATE_XML_FILE}")
    
    # 2. Matched Data
    matched_csv = pick_latest_path(MATCHED_CSV_CANDIDATES)
    if matched_csv:
        df_matched = pd.read_csv(matched_csv)
        matched_xmls = set(df_matched['XML File'].unique())
        unmatched_count = total_xmls - len(matched_xmls)
        
        print(f"\n[EXCEL MATCHING]")
        print(f"  Matched to Excel: {len(matched_xmls)}")
        print(f"  NOT matched to Excel: {unmatched_count}")
        
        unmatched_xmls = set(xml_list) - matched_xmls if unmatched_count > 0 else []
        # Save unmatched for reference (overwrite even if empty)
        unmatched_df = pd.DataFrame({'XML_File': sorted(list(unmatched_xmls))})
        unmatched_df.to_csv("data/processed/unmatched_xmls.csv", index=False)
        if unmatched_count > 0:
            print(f"  -> Details saved to: data/processed/unmatched_xmls.csv")
        else:
            print("  -> No unmatched XMLs; wrote empty unmatched_xmls.csv")
    else:
        print(f"\n[EXCEL MATCHING] Matched file not found.")

    # 3. Feature Extraction
    training_csv = pick_latest_path(TRAINING_CSV_CANDIDATES)
    if training_csv:
        df_train = pd.read_csv(training_csv)
        extracted_xmls = set(df_train['XML_File'].unique())
        failed_count = total_xmls - len(extracted_xmls)
        
        print(f"\n[FEATURE EXTRACTION]")
        print(f"  Successfully extracted: {len(extracted_xmls)}")
        print(f"  Failed extraction/Missing: {failed_count}")
        
        failed_xmls = set(xml_list) - extracted_xmls if failed_count > 0 else []
        failed_df = pd.DataFrame({'XML_File': sorted(list(failed_xmls))})
        failed_df.to_csv("data/processed/failed_extractions.csv", index=False)
        if failed_count > 0:
            print(f"  -> Details saved to: data/processed/failed_extractions.csv")
        else:
            print("  -> No failed extractions; wrote empty failed_extractions.csv")
            
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

        # Trainability check (configurable features)
        core_features = TRAINING_FEATURES
        df_train_outcomes = df_train[df_train['Lens_Size'].notna() & df_train['Vault'].notna()]
        available_features = [f for f in core_features if f in df_train_outcomes.columns]
        missing_features = [f for f in core_features if f not in df_train_outcomes.columns]
        trainable = df_train_outcomes[available_features].notna().all(axis=1) if available_features else pd.Series([], dtype=bool)
        
        print(f"\n[MODEL READINESS]")
        if missing_features:
            print(f"  Note: Missing core columns in training data: {missing_features}")
        if available_features:
            print(f"  Fully Trainable ({len(available_features)} features + outcomes): {trainable.sum()}")
            print(f"  Incomplete (outcomes exist, but features missing): {len(df_train_outcomes) - trainable.sum()}")
        else:
            print("  Fully Trainable: 0 (no core feature columns found)")
        
    else:
        print(f"\n[FEATURE EXTRACTION] Training data not found.")

    print("\n" + "="*80)
    print("AUDIT COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    audit()
