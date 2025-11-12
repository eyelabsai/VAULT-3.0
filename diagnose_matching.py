"""
Diagnose why XML files aren't matching to CSV
"""

import pandas as pd
from pathlib import Path
from icl_ml_model import XMLParser, parse_all_xml_files, load_csv_data

def diagnose():
    print("="*60)
    print("MATCHING DIAGNOSTIC")
    print("="*60)

    # Parse XML files
    xml_df = parse_all_xml_files("XML files")
    csv_df = load_csv_data("excel/VAULT 3.0.csv")

    print(f"\n1. XML FILE ANALYSIS")
    print(f"   Total XML files: 145")
    print(f"   Eye records extracted: {len(xml_df)}")
    print(f"   Expected (145 × 2 eyes): 290")
    print(f"   Missing: {290 - len(xml_df)} eye records")

    # Check which eyes are missing features
    xml_path = Path("XML files")
    xml_files = list(xml_path.glob("*.xml"))

    missing_features = []

    for xml_file in xml_files[:10]:  # Check first 10
        parser = XMLParser(xml_file)
        patient_info = parser.get_patient_info()

        for eye in ['OD', 'OS']:
            features = parser.extract_eye_features(eye)
            if not features:
                missing_features.append({
                    'file': xml_file.name,
                    'patient': patient_info.get('full_name', 'Unknown'),
                    'eye': eye,
                    'reason': 'No features extracted'
                })
            elif len(features) < 3:  # Very few features
                missing_features.append({
                    'file': xml_file.name,
                    'patient': patient_info.get('full_name', 'Unknown'),
                    'eye': eye,
                    'reason': f'Only {len(features)} features: {list(features.keys())}'
                })

    if missing_features:
        print(f"\n2. XML FILES WITH MISSING FEATURES (sample of {len(missing_features)}):")
        for item in missing_features[:20]:
            print(f"   {item['file']}: {item['patient']} ({item['eye']}) - {item['reason']}")

    # Check patient names
    print(f"\n3. PATIENT NAME COMPARISON")

    xml_patients = xml_df['patient_name'].unique()
    csv_patients = csv_df['patient_name'].unique()

    print(f"   Unique patients in XML: {len(xml_patients)}")
    print(f"   Unique patients in CSV: {len(csv_patients)}")

    # Find patients in CSV but not in XML
    csv_patient_set = set([name.lower().strip() for name in csv_patients])
    xml_patient_set = set([name.lower().strip() for name in xml_patients])

    csv_only = csv_patient_set - xml_patient_set
    xml_only = xml_patient_set - csv_patient_set
    both = csv_patient_set & xml_patient_set

    print(f"   In both: {len(both)}")
    print(f"   CSV only: {len(csv_only)}")
    print(f"   XML only: {len(xml_only)}")

    print(f"\n4. SAMPLE CSV PATIENTS WITHOUT XML (first 20):")
    for i, name in enumerate(sorted(csv_only)[:20], 1):
        original = [p for p in csv_patients if p.lower().strip() == name][0]
        count = len(csv_df[csv_df['patient_name'].str.lower().str.strip() == name])
        print(f"   {i:2d}. {original} ({count} records)")

    print(f"\n5. SAMPLE XML PATIENTS WITHOUT CSV (first 20):")
    for i, name in enumerate(sorted(xml_only)[:20], 1):
        original = [p for p in xml_patients if p.lower().strip() == name][0]
        count = len(xml_df[xml_df['patient_name'].str.lower().str.strip() == name])
        print(f"   {i:2d}. {original} ({count} records)")

    # Check specific missing patients from the training output
    print(f"\n6. CHECKING SPECIFIC UNMATCHED PATIENTS:")
    test_patients = [
        "Maxwell Jones",
        "Noah Gonzalez-Wooding",
        "Marina Lopez",
        "Tyne Cox"
    ]

    for patient in test_patients:
        in_csv = any(patient.lower() in name.lower() for name in csv_patients)
        in_xml = any(patient.lower() in name.lower() for name in xml_patients)

        print(f"   {patient}:")
        print(f"      In CSV: {in_csv}")
        print(f"      In XML: {in_xml}")

        if in_xml:
            # Show what features we extracted
            xml_records = xml_df[xml_df['patient_name'].str.contains(patient, case=False, na=False)]
            if len(xml_records) > 0:
                print(f"      XML records: {len(xml_records)}")
                for idx, row in xml_records.iterrows():
                    features = {k: v for k, v in row.items() if k not in ['xml_file', 'patient_name', 'dob_xml', 'eye', 'exam_date']}
                    non_null = sum(1 for v in features.values() if pd.notna(v))
                    print(f"        {row['eye']}: {non_null}/{len(features)} features present")

if __name__ == "__main__":
    diagnose()
