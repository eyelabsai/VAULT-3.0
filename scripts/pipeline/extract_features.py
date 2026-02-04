#!/usr/bin/env python3
"""
Feature Extraction for ICL Vault Prediction
Extracts core clinical features from XML files and matches with CSV outcomes.
"""

import pandas as pd
import xml.etree.ElementTree as ET
import os
import sys
from datetime import datetime
from match_xml_csv import (
    extract_patient_info_from_xml,
    normalize_name,
    normalize_dob,
    create_name_variations,
    load_csv_data
)
from feature_config import TRAINING_FEATURES


XML_DIR = "XML files"
CSV_FILE = "data/excel/VAULT 3.0.csv"
OUTPUT_FILE = "data/processed/training_data.csv"

# Clinical ranges for validation
FEATURE_RANGES = {
    'Age': (15, 70),
    'WTW': (10.0, 14.0),
    'ACD_internal': (2.0, 5.0),
    'ACV': (100, 400),
    'ACA_global': (20, 70),
    'Pupil_diameter': (2.0, 8.0),
    'TCRP_Km': (35, 55),
    'TCRP_Astigmatism': (0, 10),
    'AC_shape_ratio': (40, 200),  # ACV/ACD_internal
    'SEQ': (-25, 5),
    'SimK_steep': (38, 52),
    'CCT': (400, 700),
    'BAD_D': (-1, 15),
    'Vault': (50, 2000),  # Outcomes
    'Lens_Size': (11.0, 14.0)
}


def validate_value(value, feature_name):
    """
    Validate that a value falls within acceptable clinical range.
    Returns (is_valid, cleaned_value, warning_message)
    """
    try:
        val = float(value)
        
        # Check for missing value flags
        if val == -9999.0 or val == -9999.00:
            return False, None, f"{feature_name}: Invalid sentinel value -9999"
        
        if pd.isna(val):
            return False, None, f"{feature_name}: Missing value"
        
        # Check range
        if feature_name in FEATURE_RANGES:
            min_val, max_val = FEATURE_RANGES[feature_name]
            if val < min_val or val > max_val:
                return False, val, f"{feature_name}: {val} outside range [{min_val}, {max_val}]"
        
        return True, val, None
        
    except (ValueError, TypeError):
        return False, None, f"{feature_name}: Cannot convert to numeric"


def calculate_age(dob_str, exam_date_str):
    """Calculate age at time of exam."""
    try:
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        exam = datetime.strptime(exam_date_str, '%Y-%m-%d')
        age = (exam - dob).days / 365.25
        return age
    except:
        return None


def extract_xml_features(xml_file_path):
    """
    Extract core features from a single XML file.
    
    Returns dict with features or None if extraction fails.
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        features = {
            'XML_File': os.path.basename(xml_file_path),
            'Name': None,
            'DOB': None,
            'Eye': None,
            'Exam_Date': None,
            'Age': None,
            'WTW': None,
            'ACD_internal': None,
            'ACV': None,
            'ACA_global': None,
            'Pupil_diameter': None,
            'TCRP_Km': None,
            'TCRP_Astigmatism': None,
            'SimK_steep': None,
            'CCT': None,
            'BAD_D': None,
            'validation_warnings': []
        }
        
        # Extract patient info
        surname = ''
        first_name = ''
        
        for section in root.findall('section[@name="Patient Data"]'):
            for entry in section.findall('entry'):
                key = entry.get('key', '')
                value = entry.text or ''
                
                if key == 'Name':
                    first_name = value.strip()
                elif key == 'Surname':
                    surname = value.strip()
                elif key == 'DOB':
                    features['DOB'] = normalize_dob(value.strip())
        
        # Combine surname and first name (surname first for matching)
        if surname and first_name:
            features['Name'] = f"{surname} {first_name}"
        elif surname:
            features['Name'] = surname
        elif first_name:
            features['Name'] = first_name
        
        # Extract features from all sections
        # First pass: get eye-specific data from Test Data section
        for section in root.findall('section'):
            section_name = section.get('name', '')
            
            if 'Test Data' in section_name and ('OD' in section_name or 'OS' in section_name):
                # Extract eye, exam date, and measurements
                for entry in section.findall('entry'):
                    key = entry.get('key', '')
                    value = entry.text or ''
                    
                    if key == 'Eye':
                        features['Eye'] = value.strip()
                    elif key == 'Test Date':
                        features['Exam_Date'] = value.strip()
                    elif key == 'Central Corneal Thickness':
                        features['CCT'] = value.strip()
                    elif key == 'SimK steep D':
                        features['SimK_steep'] = value.strip()
                    elif key == 'Cornea Dia Horizontal':
                        features['WTW'] = value.strip()
                    elif key == 'Pupil diameter mm':
                        features['Pupil_diameter'] = value.strip()
                
                # Only process first test data section found
                if features['Eye']:
                    break
        
        # Second pass: get fields from General Overview section
        for section in root.findall('section'):
            for entry in section.findall('entry'):
                key = entry.get('key', '')
                value = entry.text or ''
                
                if key == 'ACV' and not features['ACV']:
                    features['ACV'] = value.strip()
                elif key == 'BAD D' and not features['BAD_D']:
                    features['BAD_D'] = value.strip()
                elif key == 'ACD (Int.) [mm]' and not features['ACD_internal']:
                    features['ACD_internal'] = value.strip()
                elif key == 'ACA (180°) [°]' and not features['ACA_global']:
                    features['ACA_global'] = value.strip()
                elif key == 'TCRP 3mm zone pupil Km [D]' and not features['TCRP_Km']:
                    features['TCRP_Km'] = value.strip()
                elif key == 'TCRP 3mm zone pupil Asti [D]' and not features['TCRP_Astigmatism']:
                    features['TCRP_Astigmatism'] = value.strip()
        
        # Calculate age
        if features['DOB'] and features['Exam_Date']:
            features['Age'] = calculate_age(features['DOB'], features['Exam_Date'])
        
        # Validate all numeric features
        numeric_features = ['Age', 'WTW', 'ACD_internal', 'ACV', 'ACA_global', 'Pupil_diameter',
                            'TCRP_Km', 'TCRP_Astigmatism', 'SimK_steep', 'CCT', 'BAD_D']
        
        for feat in numeric_features:
            if features[feat] is not None:
                is_valid, cleaned_val, warning = validate_value(features[feat], feat)
                features[feat] = cleaned_val
                if warning:
                    features['validation_warnings'].append(warning)
        
        # Calculate anterior chamber shape ratio (ACV / ACD_internal)
        if features['ACV'] is not None and features['ACD_internal'] is not None:
            try:
                acv_val = float(features['ACV'])
                acd_val = float(features['ACD_internal'])
                if acd_val > 0:
                    features['AC_shape_ratio'] = acv_val / acd_val
                    # Validate the ratio
                    is_valid, cleaned_val, warning = validate_value(features['AC_shape_ratio'], 'AC_shape_ratio')
                    if not is_valid:
                        features['AC_shape_ratio'] = None
                        if warning:
                            features['validation_warnings'].append(warning)
                else:
                    features['AC_shape_ratio'] = None
            except:
                features['AC_shape_ratio'] = None
        else:
            features['AC_shape_ratio'] = None
        
        return features
        
    except Exception as e:
        print(f"Error extracting from {xml_file_path}: {e}")
        return None


def merge_with_csv(xml_features, csv_lookup):
    """
    Merge XML features with CSV data (SEQ, Vault, Lens Size).
    
    Returns complete feature dict or None if no match.
    """
    name = xml_features['Name']
    dob = xml_features['DOB']
    eye = xml_features['Eye']
    
    if not all([name, dob, eye]):
        return None
    
    # Try to find match in CSV using same logic as match_xml_csv.py
    name_variations = create_name_variations(name, assume_surname_first=True)
    
    matched_data = None
    matched_key = None
    
    # Try exact match first
    for name_var in name_variations:
        key = (name_var, dob, eye.upper())
        if key in csv_lookup:
            matched_data = csv_lookup[key]
            matched_key = key
            break
    
    # Try matching by name+DOB only (ignoring eye)
    if not matched_data:
        for name_var in name_variations:
            for csv_key, csv_data in csv_lookup.items():
                csv_name, csv_dob, csv_eye = csv_key
                if name_var == csv_name and dob == csv_dob:
                    matched_data = csv_data
                    matched_key = csv_key
                    break
            if matched_data:
                break
    
    if not matched_data:
        return None
    
    # Merge CSV data
    result = xml_features.copy()
    result['SEQ'] = matched_data.get('name')  # Will fix this
    result['Lens_Size'] = matched_data.get('lens_size')
    result['Vault'] = matched_data.get('vault')
    result['Exchange'] = matched_data.get('exchange')
    
    # Get SEQ from CSV - need to add this to csv_lookup
    # For now, calculate from Sphere + Cyl if available
    
    return result


def load_csv_with_seq():
    """
    Load CSV and create lookup with SEQ included.
    Modified version of load_csv_data to include SEQ.
    """
    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file '{CSV_FILE}' not found.")
        return None
    
    try:
        df = pd.read_csv(CSV_FILE)
        
        lookup = {}
        
        for idx, row in df.iterrows():
            name = normalize_name(row.get('NAME', ''))
            dob = normalize_dob(row.get('DOB', ''))
            eye = str(row.get('Eye', '')).strip().upper()
            
            # Get exchange status
            exchange = str(row.get('Exchange?', '')).strip().upper() == 'YES'
            
            # Get lens size and vault (use exchanged if applicable)
            if exchange:
                lens_size = row.get('Exchanged Size', '')
                vault = row.get('Exchanged Vault', '')
            else:
                lens_size = row.get('ICL Size', '')
                vault = row.get('Vault', '')
            
            # Get Sphere and Cyl to calculate SEQ
            sphere = row.get('Sphere', '')
            cyl = row.get('Cyl', '')
            
            # Calculate SEQ = Sphere + (Cyl/2)
            seq = None
            if pd.notna(sphere) and pd.notna(cyl):
                try:
                    seq = float(sphere) + (float(cyl) / 2.0)
                except:
                    pass
            elif pd.notna(sphere) and not pd.notna(cyl):
                # If only sphere available, use it as SEQ
                try:
                    seq = float(sphere)
                except:
                    pass
            
            # Get ICL Power (use exchanged if applicable)
            if exchange:
                icl_power = row.get('Exchanged Power', '')
            else:
                icl_power = row.get('ICL Power', '')
            
            data_entry = {
                'name': name,
                'dob': dob,
                'eye': eye,
                'lens_size': lens_size if pd.notna(lens_size) else None,
                'vault': vault if pd.notna(vault) else None,
                'exchange': exchange,
                'seq': seq,
                'icl_power': float(icl_power) if pd.notna(icl_power) and icl_power != '' else None,
            }
            
            # Create name variations
            name_variations = create_name_variations(name)
            for name_var in name_variations:
                key = (name_var, dob, eye)
                lookup[key] = data_entry
        
        return lookup
        
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None


def extract_all_features():
    """
    Extract features from all XML files and merge with CSV data.
    """
    if not os.path.exists(XML_DIR):
        print(f"Error: {XML_DIR} directory not found.")
        return None
    
    # Load CSV lookup
    print("Loading CSV data...")
    csv_lookup = load_csv_with_seq()
    if not csv_lookup:
        return None
    
    print(f"Loaded CSV with {len(set([(v['name'], v['dob'], v['eye']) for v in csv_lookup.values()]))} unique patients\n")
    
    # Process all XML files
    xml_files = sorted([f for f in os.listdir(XML_DIR) if f.endswith('.xml')])
    
    print(f"Processing {len(xml_files)} XML files...\n")
    
    all_features = []
    warnings_list = []
    
    for xml_file in xml_files:
        xml_path = os.path.join(XML_DIR, xml_file)
        
        # Extract XML features
        features = extract_xml_features(xml_path)
        if not features:
            continue
        
        # Find CSV match
        name = features['Name']
        dob = features['DOB']
        eye = features['Eye']
        
        if not all([name, dob, eye]):
            print(f"⚠️  {xml_file}: Missing patient info")
            continue
        
        # Try to match using multiple strategies
        name_variations = create_name_variations(name, assume_surname_first=True)
        matched_data = None
        
        # Strategy 1: Exact match (name + DOB + eye)
        for name_var in name_variations:
            key = (name_var, dob, eye.upper())
            if key in csv_lookup:
                matched_data = csv_lookup[key]
                break
        
        # Strategy 2: Name + DOB only (ignore eye)
        if not matched_data:
            for name_var in name_variations:
                for csv_key, csv_data in csv_lookup.items():
                    csv_name, csv_dob, csv_eye = csv_key
                    if name_var == csv_name and dob == csv_dob:
                        matched_data = csv_data
                        break
                if matched_data:
                    break
        
        # Strategy 3: Fuzzy name match with exact DOB
        if not matched_data and dob:
            import difflib
            best_ratio = 0
            best_candidate = None
            
            for csv_key, csv_data in csv_lookup.items():
                csv_name, csv_dob, csv_eye = csv_key
                if dob == csv_dob:
                    for name_var in name_variations:
                        ratio = difflib.SequenceMatcher(None, name_var.upper(), csv_name.upper()).ratio()
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_candidate = csv_data
            
            if best_ratio > 0.8:
                matched_data = best_candidate
        
        # Strategy 4: Fuzzy DOB (±7 days) with high name similarity (>0.9)
        if not matched_data and dob:
            import difflib
            best_ratio = 0
            best_candidate = None
            
            try:
                xml_dob_date = datetime.strptime(dob, '%Y-%m-%d')
            except:
                xml_dob_date = None
            
            if xml_dob_date:
                for csv_key, csv_data in csv_lookup.items():
                    csv_name, csv_dob, csv_eye = csv_key
                    
                    try:
                        csv_dob_date = datetime.strptime(csv_dob, '%Y-%m-%d')
                    except:
                        continue
                    
                    dob_diff = abs((xml_dob_date - csv_dob_date).days)
                    if dob_diff <= 7 and dob_diff > 0:
                        for name_var in name_variations:
                            ratio = difflib.SequenceMatcher(None, name_var.upper(), csv_name.upper()).ratio()
                            if ratio > best_ratio and ratio > 0.9:
                                best_ratio = ratio
                                best_candidate = csv_data
                
                if best_ratio > 0.9 and best_candidate:
                    matched_data = best_candidate
        
        if not matched_data:
            print(f"⚠️  {xml_file}: No CSV match for {name}")
            continue
        
        # Merge CSV data (SEQ, ICL_Power, Vault, Lens_Size)
        features['SEQ'] = matched_data.get('seq')
        features['ICL_Power'] = matched_data.get('icl_power')
        features['Lens_Size'] = matched_data.get('lens_size')
        features['Vault'] = matched_data.get('vault')
        features['Exchange'] = matched_data.get('exchange')
        
        # Validate outcomes
        if features['Vault'] is not None:
            is_valid, cleaned_val, warning = validate_value(features['Vault'], 'Vault')
            features['Vault'] = cleaned_val
            if warning:
                features['validation_warnings'].append(warning)
        
        if features['Lens_Size'] is not None:
            is_valid, cleaned_val, warning = validate_value(features['Lens_Size'], 'Lens_Size')
            features['Lens_Size'] = cleaned_val
            if warning:
                features['validation_warnings'].append(warning)
        
        # Track validation warnings
        if features['validation_warnings']:
            warnings_list.append({
                'XML_File': xml_file,
                'Name': name,
                'Warnings': '; '.join(features['validation_warnings'])
            })
        
        all_features.append(features)
    
    print(f"\n{'='*60}")
    print(f"Extracted features from {len(all_features)} XML files")
    print(f"{'='*60}\n")
    
    # Convert to DataFrame
    df = pd.DataFrame(all_features)
    
    if len(df) == 0:
        print("\n❌ No features extracted. Check XML/CSV matching.")
        return None
    
    # Count complete cases
    # UPDATED: Using Top 6 feature set with ICL_Power instead of SEQ
    # ICL_Power is more consistently recorded than SEQ (from Sphere+Cyl)
    feature_cols_check = ['Age', 'WTW', 'ACD_internal', 'ICL_Power', 'AC_shape_ratio', 'SimK_steep']
    complete_features = df[feature_cols_check].notna().all(axis=1)
    complete_outcomes = df[['Vault', 'Lens_Size']].notna().all(axis=1)
    complete_cases = complete_features & complete_outcomes
    
    print(f"Complete cases (all features + outcomes): {complete_cases.sum()}/{len(df)}")
    print(f"  - With all features: {complete_features.sum()}/{len(df)}")
    print(f"  - With outcomes (Vault + Lens Size): {complete_outcomes.sum()}/{len(df)}")
    
    if warnings_list:
        print(f"\n⚠️  Validation warnings: {len(warnings_list)} files")
        warnings_df = pd.DataFrame(warnings_list)
        print(warnings_df.to_string(index=False))
    
    # Save complete training data
    output_columns = [
        'XML_File', 'Name', 'DOB', 'Eye', 'Exam_Date',
        'Age', 'WTW', 'ACD_internal', 'ACV', 'ACA_global', 'Pupil_diameter',
        'AC_shape_ratio', 'TCRP_Km', 'TCRP_Astigmatism', 'SEQ', 'ICL_Power',
        'SimK_steep', 'CCT', 'BAD_D',
        'Lens_Size', 'Vault', 'Exchange'
    ]
    
    df_output = df[output_columns].copy()
    df_output.to_csv(OUTPUT_FILE, index=False)
    
    print(f"\n✅ Training data saved to: {OUTPUT_FILE}")
    
    # Save flagged incomplete cases (have outcomes but missing features)
    both_outcomes = df[['Vault', 'Lens_Size']].notna().all(axis=1)
    # Flag based on configurable training feature list
    feature_cols = TRAINING_FEATURES
    all_features = df[feature_cols].notna().all(axis=1)
    incomplete = both_outcomes & ~all_features
    
    if incomplete.sum() > 0:
        flagged_file = "data/processed/flagged_incomplete_cases.csv"
        flagged_cols = ['XML_File', 'Name', 'DOB', 'Eye'] + feature_cols + ['Vault', 'Lens_Size']
        df_flagged = df[incomplete][flagged_cols].copy()
        
        # Add column showing which features are missing
        df_flagged['Missing_Features'] = df[incomplete].apply(
            lambda row: ', '.join([col for col in feature_cols if pd.isna(row[col])]), 
            axis=1
        )
        
        df_flagged.to_csv(flagged_file, index=False)
        print(f"⚠️  Flagged {incomplete.sum()} incomplete cases: {flagged_file}")
        print(f"    (Have outcomes but missing: {', '.join(df_flagged['Missing_Features'].unique())})")
    
    return df_output


def main():
    """Main function."""
    print("="*60)
    print("ICL Vault Prediction - Feature Extraction")
    print("="*60)
    print()
    
    df = extract_all_features()
    
    if df is not None:
        print("\n" + "="*60)
        print("Summary Statistics")
        print("="*60)
        stats_cols = ['Age', 'WTW', 'ACD_internal', 'ACV', 'ACA_global', 'Pupil_diameter', 
                      'AC_shape_ratio', 'TCRP_Km', 'TCRP_Astigmatism', 'SEQ', 
                      'SimK_steep', 'CCT', 'BAD_D', 'Vault', 'Lens_Size']
        print(df[stats_cols].describe())


if __name__ == '__main__':
    main()

