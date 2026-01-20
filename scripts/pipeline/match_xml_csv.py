#!/usr/bin/env python3
"""
Match XML files with CSV roster data
Finds which patients from XML files have lens size and vault data in CSV.
For exchanges, uses exchanged lens size and vault.
"""

import pandas as pd
import xml.etree.ElementTree as ET
import os
import sys
import difflib
from datetime import datetime


XML_OUTPUT_DIR = "XML files"
CSV_FILE = "data/excel/VAULT 3.0.csv"
OUTPUT_FILE = "data/processed/matched_patients.csv"


def extract_patient_info_from_xml(xml_file_path):
    """
    Extract patient information from XML file.
    
    Returns:
        dict with keys: name, surname, full_name, eye, dob, xml_filename
    """
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        info = {
            'name': '',
            'surname': '',
            'full_name': '',
            'eye': '',
            'dob': '',
            'xml_filename': os.path.basename(xml_file_path)
        }
        
        # Extract from Patient Data section
        for section in root.findall('section[@name="Patient Data"]'):
            for entry in section.findall('entry'):
                key = entry.get('key', '')
                value = entry.text or ''
                
                if key == 'Name':
                    info['name'] = value.strip()
                elif key == 'Surname':
                    info['surname'] = value.strip()
                elif key == 'DOB':
                    info['dob'] = value.strip()
        
        # Build full name (surname first, then name)
        parts = [info['surname'], info['name']]
        info['full_name'] = ' '.join([p for p in parts if p]).strip() or 'Unknown'
        
        # Extract eye laterality from Test Data sections
        for section in root.findall('section'):
            section_name = section.get('name', '')
            if 'Test Data' in section_name:
                for entry in section.findall('entry[@key="Eye"]'):
                    eye_value = entry.text or ''
                    if eye_value:
                        info['eye'] = eye_value.strip()
                        break
                if info['eye']:
                    break
        
        return info
    except Exception as e:
        print(f"Warning: Could not extract patient info from {xml_file_path}: {e}")
        return None


def normalize_name(name):
    """
    Normalize name for matching (remove extra spaces, handle hyphens, etc.)
    """
    if not name:
        return ''
    # Remove extra spaces, normalize hyphens
    name = ' '.join(name.split())
    # Fix hyphen spacing (e.g., "Gonzalez- Wooding" -> "Gonzalez-Wooding")
    name = name.replace('- ', '-').replace(' -', '-')
    # Convert to title case
    name = name.title()
    # Remove common suffixes for matching (Jr, Sr, II, III, etc.)
    # We'll add them back as variations
    return name.strip()


def remove_name_suffixes(name):
    """
    Remove common name suffixes and return base name and suffix.
    """
    suffixes = ['Jr', 'Jr.', 'Sr', 'Sr.', 'II', 'III', 'IV', 'V', '2Nd', '2Nd.']
    name_parts = name.split()
    base_name_parts = []
    suffix = None
    
    for part in name_parts:
        if part in suffixes or part.upper() in [s.upper() for s in suffixes]:
            suffix = part
        else:
            base_name_parts.append(part)
    
    return ' '.join(base_name_parts), suffix


def create_name_variations(name):
    """
    Create variations of a name for matching.
    Handles surname-first and first-name-first formats.
    Also handles common spelling variations.
    """
    if not name:
        return set()
    
    variations = set()
    name = normalize_name(name)
    variations.add(name)
    
    # Remove suffixes for base matching
    base_name, suffix = remove_name_suffixes(name)
    if suffix:
        # Add version without suffix
        variations.add(base_name)
        name = base_name
    
    # Common spelling variations - both directions
    spelling_variations = {
        'Russel': ['Russell', 'Russel'],  # Both spellings
        'Russell': ['Russell', 'Russel'],  # Both spellings
        'Micheal': ['Michael', 'Micheal'],
        'Michael': ['Michael', 'Micheal'],
        'Jon': ['John', 'Jon'],
        'John': ['John', 'Jon'],
        'Stephany': ['Stephanie', 'Stephany'],
        'Stephanie': ['Stephanie', 'Stephany'],
        'Roseanna': ['Rosanna', 'Roseanna'],  # Both spellings
        'Rosanna': ['Rosanna', 'Roseanna'],  # Both spellings
        'Jenifer': ['Jennifer', 'Jenifer'],  # Both spellings
        'Jennifer': ['Jennifer', 'Jenifer'],  # Both spellings
        'Brenton': ['Benton', 'Brenton'],  # Both spellings
        'Benton': ['Benton', 'Brenton'],  # Both spellings
        'Schwausch': ['Schwasuch', 'Schwausch'],  # Fix Blake Schwausch typo
        'Schwasuch': ['Schwasuch', 'Schwausch'],
    }
    
    # Apply spelling variations - create variations with all spellings
    for variant_key, variant_list in spelling_variations.items():
        if variant_key in name:
            for variant in variant_list:
                name_variant = name.replace(variant_key, variant)
                variations.add(name_variant)
            # Use the first (standard) spelling for further processing
            name = name.replace(variant_key, variant_list[0])
    
    # Split into parts
    parts = name.split()
    if len(parts) >= 2:
        # Original order
        variations.add(' '.join(parts))
        # Reverse order (surname first <-> first name first)
        variations.add(' '.join(reversed(parts)))
        
        # Also try with hyphenated names
        if len(parts) > 2:
            # Try different combinations for names with 3+ parts
            # e.g., "Gonzalez-Wooding Noah" vs "Noah Gonzalez-Wooding"
            if '-' in parts[0]:
                # First part is hyphenated surname
                variations.add(' '.join(parts))
                variations.add(' '.join([parts[1]] + [parts[0]] + parts[2:]))
            elif '-' in parts[1]:
                # Second part is hyphenated
                variations.add(' '.join([parts[1], parts[0]] + parts[2:]))
        
        # Also try with common spelling variations on individual parts
        for i, part in enumerate(parts):
            if part in spelling_variations:
                for variant in spelling_variations[part]:
                    new_parts = parts.copy()
                    new_parts[i] = variant
                    variations.add(' '.join(new_parts))
                    variations.add(' '.join(reversed(new_parts)))
    
    return variations


def normalize_dob(dob_str):
    """
    Normalize date of birth for matching.
    Handles various date formats including malformed dates.
    """
    if not dob_str:
        return ''
    
    # If it's a datetime object, convert to string
    if isinstance(dob_str, datetime):
        return dob_str.strftime('%Y-%m-%d')
    
    # If it's already a string, try to parse and normalize
    if isinstance(dob_str, str):
        # Remove time component if present
        dob_str = dob_str.split()[0]
        
        # Fix malformed dates like "6/27/0187" -> should be 1987
        # Check for 0187, 0188, etc. and fix to 1987, 1988
        if '018' in dob_str or '/018' in dob_str:
            dob_str = dob_str.replace('/018', '/198').replace('018', '198')
        
        # Try to parse common formats
        try:
            # Try YYYY-MM-DD format
            if len(dob_str) == 10 and dob_str.count('-') == 2:
                return dob_str
            # Try other formats if needed
            dt = pd.to_datetime(dob_str, errors='coerce')
            if pd.notna(dt):
                return dt.strftime('%Y-%m-%d')
        except:
            pass
    
    return str(dob_str).strip()


def load_csv_data():
    """
    Load CSV data and create lookup dictionaries.
    
    Returns:
        dict: Dictionary with key (name, dob, eye) -> row data
    """
    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file '{CSV_FILE}' not found.")
        return None
    
    try:
        df = pd.read_csv(CSV_FILE)
        
        # Create lookup dictionary
        lookup = {}
        
        for idx, row in df.iterrows():
            name = normalize_name(row.get('NAME', ''))
            dob = normalize_dob(row.get('DOB', ''))
            eye = str(row.get('Eye', '')).strip().upper()
            
            # Determine if exchange happened
            exchange = str(row.get('Exchange?', '')).strip().upper() == 'YES'
            
            # Get lens size and vault (use exchanged if exchange happened)
            if exchange:
                lens_size = row.get('Exchanged Size', '')
                vault = row.get('Exchanged Vault', '')
            else:
                lens_size = row.get('ICL Size', '')
                vault = row.get('Vault', '')
            
            # Create data entry
            data_entry = {
                'name': name,
                'dob': dob,
                'eye': eye,
                'lens_size': lens_size if pd.notna(lens_size) else '',
                'vault': vault if pd.notna(vault) else '',
                'exchange': exchange,
                'original_lens_size': row.get('ICL Size', ''),
                'original_vault': row.get('Vault', ''),
                'exchanged_lens_size': row.get('Exchanged Size', ''),
                'exchanged_vault': row.get('Exchanged Vault', ''),
                'dos': row.get('DOS', ''),
                'target': row.get('Target', ''),
                'icl_power': row.get('ICL Power', ''),
            }
            
            # Create name variations and add to lookup
            name_variations = create_name_variations(name)
            for name_var in name_variations:
                # Create key for lookup
                key = (name_var, dob, eye)
                lookup[key] = data_entry
        
        return lookup
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return None


def match_xml_to_csv():
    """
    Match XML files with CSV data and extract lens size and vault information.
    """
    # Load CSV data
    print("Loading CSV data...")
    csv_lookup = load_csv_data()
    if csv_lookup is None:
        return
    
    print(f"Loaded {len(csv_lookup)} entries from CSV.\n")
    
    # Process all XML files
    if not os.path.exists(XML_OUTPUT_DIR):
        print(f"Error: {XML_OUTPUT_DIR} directory not found.")
        return
    
    xml_files = [f for f in os.listdir(XML_OUTPUT_DIR) if f.lower().endswith('.xml')]
    
    if not xml_files:
        print(f"No XML files found in {XML_OUTPUT_DIR} directory.")
        return
    
    print(f"Processing {len(xml_files)} XML file(s)...\n")
    
    matched_results = []
    unmatched_results = []
    
    for xml_file in sorted(xml_files):
        xml_path = os.path.join(XML_OUTPUT_DIR, xml_file)
        
        # Extract patient info from XML
        xml_info = extract_patient_info_from_xml(xml_path)
        if xml_info is None:
            continue
        
        # Normalize for matching
        name = normalize_name(xml_info['full_name'])
        dob = normalize_dob(xml_info['dob'])
        eye = xml_info['eye'].upper()
        
        # Create name variations for matching
        name_variations = create_name_variations(xml_info['full_name'])
        
        # Try to match with variations
        matched = False
        csv_data = None
        matched_key = None
        
        # First try exact match
        for name_var in name_variations:
            key = (name_var, dob, eye)
            if key in csv_lookup:
                csv_data = csv_lookup[key]
                matched_key = key
                matched = True
                break
        
        # If no exact match, try matching by name+DOB (ignoring eye)
        if not matched:
            for name_var in name_variations:
                for csv_key, csv_data_candidate in csv_lookup.items():
                    csv_name, csv_dob, csv_eye = csv_key
                    if name_var == csv_name and dob == csv_dob:
                        csv_data = csv_data_candidate
                        matched_key = csv_key
                        matched = True
                        break
                if matched:
                    break
        
        # If still no match, try fuzzy matching by name only (for cases with DOB errors)
        # Only do this if we haven't found a match yet
        if not matched:
            for name_var in name_variations:
                for csv_key, csv_data_candidate in csv_lookup.items():
                    csv_name, csv_dob, csv_eye = csv_key
                    # Match by name only, if name is very similar
                    if name_var == csv_name:
                        csv_data = csv_data_candidate
                        matched_key = csv_key
                        matched = True
                        # Note: DOB mismatch - this will be flagged in the output
                        break
                if matched:
                    break
        
        # If still no match, try robust fuzzy matching using DOB as a verifier
        if not matched and dob:
            best_ratio = 0
            best_candidate = None
            
            # Look for candidates where DOB matches exactly
            for csv_key, csv_data_candidate in csv_lookup.items():
                csv_name, csv_dob, csv_eye = csv_key
                if dob == csv_dob:
                    # Check similarity between xml name and csv name
                    # We check all variations
                    for name_var in name_variations:
                        ratio = difflib.SequenceMatcher(None, name_var.upper(), csv_name.upper()).ratio()
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_candidate = (csv_key, csv_data_candidate)
            
            # If we found a very good match with same DOB, accept it
            # 0.8 is a high threshold for names with same DOB
            if best_ratio > 0.8:
                matched_key, csv_data = best_candidate
                matched = True
                # Note: This is a fuzzy match with verified DOB
        
        # If still no match, try fuzzy DOB matching (±7 days) for high-confidence name matches
        # This handles typos in DOB entry (e.g., 1993-07-06 vs 1993-07-09)
        if not matched and dob:
            best_ratio = 0
            best_candidate = None
            best_dob_diff = None
            
            try:
                xml_dob_date = datetime.strptime(dob, '%Y-%m-%d')
            except:
                xml_dob_date = None
            
            if xml_dob_date:
                for csv_key, csv_data_candidate in csv_lookup.items():
                    csv_name, csv_dob, csv_eye = csv_key
                    
                    # Try to parse CSV DOB
                    try:
                        csv_dob_date = datetime.strptime(csv_dob, '%Y-%m-%d')
                    except:
                        continue
                    
                    # Check if DOB is within 7 days
                    dob_diff = abs((xml_dob_date - csv_dob_date).days)
                    if dob_diff <= 7 and dob_diff > 0:  # Only for near-matches, not exact
                        # Check name similarity - require very high match (>0.9) for DOB tolerance
                        for name_var in name_variations:
                            ratio = difflib.SequenceMatcher(None, name_var.upper(), csv_name.upper()).ratio()
                            if ratio > best_ratio and ratio > 0.9:
                                best_ratio = ratio
                                best_candidate = (csv_key, csv_data_candidate)
                                best_dob_diff = dob_diff
                
                # Accept if we found a very high name match with DOB within tolerance
                if best_ratio > 0.9 and best_candidate:
                    matched_key, csv_data = best_candidate
                    matched = True
                    # Note: This is a fuzzy DOB match (will be flagged in output)
        
        # If still no match, try partial surname matching (for compound surnames)
        # e.g., "Calvetti Kirstin" matches "Kirstin Calvetti-Reyes"
        if not matched:
            for name_var in name_variations:
                name_parts = name_var.split()
                if len(name_parts) >= 2:
                    # Try both orders (surname first and first name first)
                    for order_reversed in [False, True]:
                        if order_reversed:
                            first_name = name_parts[-1]
                            surname = ' '.join(name_parts[:-1])
                        else:
                            first_name = name_parts[0]
                            surname = ' '.join(name_parts[1:])
                        
                        for csv_key, csv_data_candidate in csv_lookup.items():
                            csv_name, csv_dob, csv_eye = csv_key
                            csv_parts = csv_name.split()
                            if len(csv_parts) >= 2:
                                # Try both orders for CSV name too
                                for csv_order_reversed in [False, True]:
                                    if csv_order_reversed:
                                        csv_first_name = csv_parts[-1]
                                        csv_surname = ' '.join(csv_parts[:-1])
                                    else:
                                        csv_first_name = csv_parts[0]
                                        csv_surname = ' '.join(csv_parts[1:])
                                    
                                    # Match if first name matches and surname is contained
                                    if (first_name == csv_first_name and 
                                        (surname in csv_surname or csv_surname in surname or
                                         surname.split()[0] == csv_surname.split()[0])):
                                        csv_data = csv_data_candidate
                                        matched_key = csv_key
                                        matched = True
                                        break
                                if matched:
                                    break
                        if matched:
                            break
                if matched:
                    break
        
        if matched and csv_data:
            # Check if eye matches
            csv_eye = matched_key[2]
            csv_dob_matched = matched_key[1]
            eye_match = eye == csv_eye
            dob_match = dob == csv_dob_matched
            
            # Build match note
            match_notes = []
            if not dob_match:
                match_notes.append(f'DOB mismatch (XML: {dob}, CSV: {csv_dob_matched})')
            if not eye_match:
                match_notes.append(f'Eye mismatch (CSV: {csv_eye})')
            match_note = '; '.join(match_notes) if match_notes else 'Exact match'
            
            matched_results.append({
                'XML File': xml_info['xml_filename'],
                'Name': name,
                'DOB': dob,
                'Eye': eye,
                'Lens Size': csv_data['lens_size'] if eye_match else '',
                'Vault': csv_data['vault'] if eye_match else '',
                'Exchange': 'YES' if csv_data['exchange'] else 'NO',
                'Original Lens Size': csv_data['original_lens_size'],
                'Original Vault': csv_data['original_vault'],
                'Exchanged Lens Size': csv_data['exchanged_lens_size'],
                'Exchanged Vault': csv_data['exchanged_vault'],
                'DOS': csv_data['dos'],
                'Target': csv_data['target'],
                'ICL Power': csv_data['icl_power'],
                'Match Note': match_note
            })
        else:
            unmatched_results.append({
                'XML File': xml_info['xml_filename'],
                'Name': name,
                'DOB': dob,
                'Eye': eye,
            })
    
    # Create output DataFrame
    if matched_results:
        matched_df = pd.DataFrame(matched_results)
        
        # Save to CSV
        matched_df.to_csv(OUTPUT_FILE, index=False)
        
        print(f"\n{'='*60}")
        print(f"MATCHING RESULTS")
        print(f"{'='*60}")
        print(f"Matched: {len(matched_results)}/{len(xml_files)} XML files")
        print(f"Unmatched: {len(unmatched_results)}/{len(xml_files)} XML files")
        print(f"\nResults saved to: {OUTPUT_FILE}")
        
        # Show statistics
        with_data = matched_df[
            (matched_df['Lens Size'].notna()) & 
            (matched_df['Lens Size'] != '') &
            (matched_df['Vault'].notna()) & 
            (matched_df['Vault'] != '')
        ]
        print(f"\nXML files with lens size AND vault data: {len(with_data)}/{len(matched_results)}")
        
        exchanges = matched_df[matched_df['Exchange'] == 'YES']
        if len(exchanges) > 0:
            print(f"Patients with exchanges: {len(exchanges)}")
        
        # Show unmatched patients
        if unmatched_results:
            print(f"\n{'='*60}")
            print(f"UNMATCHED PATIENTS ({len(unmatched_results)}):")
            print(f"{'='*60}")
            for item in unmatched_results[:10]:  # Show first 10
                print(f"  {item['XML File']}: {item['Name']} ({item['DOB']}, {item['Eye']})")
            if len(unmatched_results) > 10:
                print(f"  ... and {len(unmatched_results) - 10} more")
    
    else:
        print("No matches found.")


def main():
    """Main function."""
    match_xml_to_csv()


if __name__ == '__main__':
    main()

