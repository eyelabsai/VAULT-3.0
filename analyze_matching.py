"""
Analyze patient matching between XML and CSV files
Helps identify why some patients didn't match
"""

import pandas as pd
from icl_ml_model import parse_all_xml_files, load_csv_data, NameMatcher


def analyze_unmatched():
    """Analyze which patients didn't match and why"""

    print("="*60)
    print("PATIENT MATCHING ANALYSIS")
    print("="*60)

    # Load data
    print("\nLoading data...")
    xml_df = parse_all_xml_files("XML files")
    csv_df = load_csv_data("excel/VAULT 3.0.csv")

    print(f"\nXML: {len(xml_df)} eye records from {xml_df['patient_name'].nunique()} unique patients")
    print(f"CSV: {len(csv_df)} eye records from {csv_df['patient_name'].nunique()} unique patients")

    # Get unique patient names
    xml_patients = set(xml_df['patient_name'].str.lower().str.strip())
    csv_patients = set(csv_df['patient_name'].str.lower().str.strip())

    print(f"\n" + "="*60)
    print("PATIENT NAME ANALYSIS")
    print("="*60)

    # Patients only in CSV (not in XML)
    csv_only = csv_patients - xml_patients
    print(f"\nPatients in CSV but NOT in XML: {len(csv_only)}")

    if csv_only:
        print("\nSample patients without XML files (first 20):")
        for i, name in enumerate(sorted(csv_only)[:20], 1):
            # Get the original case
            original = csv_df[csv_df['patient_name'].str.lower().str.strip() == name]['patient_name'].iloc[0]
            count = len(csv_df[csv_df['patient_name'].str.lower().str.strip() == name])
            print(f"  {i:2d}. {original} ({count} eye records)")

    # Patients only in XML (not in CSV)
    xml_only = xml_patients - csv_patients
    print(f"\nPatients in XML but NOT in CSV: {len(xml_only)}")

    if xml_only:
        print("\nSample patients without outcomes (first 20):")
        for i, name in enumerate(sorted(xml_only)[:20], 1):
            original = xml_df[xml_df['patient_name'].str.lower().str.strip() == name]['patient_name'].iloc[0]
            count = len(xml_df[xml_df['patient_name'].str.lower().str.strip() == name])
            print(f"  {i:2d}. {original} ({count} eye records)")

    # Patients in both
    in_both = xml_patients & csv_patients
    print(f"\nPatients in BOTH XML and CSV: {len(in_both)}")

    print(f"\n" + "="*60)
    print("FUZZY MATCHING OPPORTUNITIES")
    print("="*60)

    # Try to find potential fuzzy matches
    matcher = NameMatcher()
    potential_matches = []

    print("\nSearching for potential fuzzy matches...")

    for csv_name in sorted(csv_only)[:50]:  # Check first 50 unmatched CSV patients
        csv_original = csv_df[csv_df['patient_name'].str.lower().str.strip() == csv_name]['patient_name'].iloc[0]

        for xml_name in xml_only:
            xml_original = xml_df[xml_df['patient_name'].str.lower().str.strip() == xml_name]['patient_name'].iloc[0]

            is_match, match_type = matcher.match_names(csv_original, xml_original)

            if is_match:
                potential_matches.append({
                    'csv_name': csv_original,
                    'xml_name': xml_original,
                    'match_type': match_type
                })

    if potential_matches:
        print(f"\nFound {len(potential_matches)} potential fuzzy matches:")
        for match in potential_matches[:20]:
            print(f"  CSV: {match['csv_name']:30s} <-> XML: {match['xml_name']:30s} ({match['match_type']})")
    else:
        print("\nNo additional fuzzy matches found.")

    print(f"\n" + "="*60)
    print("MATCHING SUMMARY")
    print("="*60)

    print(f"\nTotal unique patients:")
    print(f"  CSV: {len(csv_patients)}")
    print(f"  XML: {len(xml_patients)}")
    print(f"  Exact matches: {len(in_both)}")
    print(f"  Potential fuzzy: {len(potential_matches)}")
    print(f"  CSV without XML: {len(csv_only)}")
    print(f"  XML without CSV: {len(xml_only)}")

    print(f"\nMatching rate: {len(in_both) / len(csv_patients) * 100:.1f}%")

    # Save detailed report
    report = []

    # CSV patients without XML
    for name in sorted(csv_only):
        original = csv_df[csv_df['patient_name'].str.lower().str.strip() == name]['patient_name'].iloc[0]
        records = csv_df[csv_df['patient_name'].str.lower().str.strip() == name]
        report.append({
            'patient_name': original,
            'source': 'CSV only',
            'eye_records': len(records),
            'eyes': ', '.join(records['eye'].unique())
        })

    # XML patients without CSV
    for name in sorted(xml_only):
        original = xml_df[xml_df['patient_name'].str.lower().str.strip() == name]['patient_name'].iloc[0]
        records = xml_df[xml_df['patient_name'].str.lower().str.strip() == name]
        report.append({
            'patient_name': original,
            'source': 'XML only',
            'eye_records': len(records),
            'eyes': ', '.join(records['eye'].unique())
        })

    report_df = pd.DataFrame(report)
    report_df.to_csv('unmatched_patients_report.csv', index=False)
    print(f"\nDetailed report saved to: unmatched_patients_report.csv")


if __name__ == "__main__":
    analyze_unmatched()
