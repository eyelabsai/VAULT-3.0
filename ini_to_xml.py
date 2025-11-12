#!/usr/bin/env python3
"""
INI to XML Converter with Roster Generation
Converts INI files to XML format and maintains a roster of processed files.
"""

import configparser
import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys
import os
import zipfile
import shutil
from pathlib import Path
from datetime import datetime


XML_OUTPUT_DIR = "XML files"
ROSTER_FILE = "roster.md"
IMAGES_DIR = "images"


def extract_patient_info(xml_file_path):
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
        
        # Build full name
        parts = [info['surname'], info['name']]
        info['full_name'] = ' '.join([p for p in parts if p]).strip() or 'Unknown'
        
        # Extract eye laterality from Test Data sections
        # Look for sections like "Test Data OD 0" or "Test Data OS 0"
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
        return {
            'full_name': 'Unknown',
            'eye': 'Unknown',
            'dob': 'Unknown',
            'xml_filename': os.path.basename(xml_file_path)
        }


def update_roster(xml_file_path):
    """
    Update the roster.md file with patient information from the XML file.
    """
    info = extract_patient_info(xml_file_path)
    
    # Read existing roster if it exists
    roster_entries = {}
    if os.path.exists(ROSTER_FILE):
        with open(ROSTER_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Skip header lines (title, empty line, table header, separator)
            for line in lines[4:]:  # Skip first 4 lines (header, blank, table header, separator)
                if line.strip() and '|' in line and not line.strip().startswith('|--'):
                    # Extract XML filename from the line to use as key
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 5:
                        xml_filename = parts[4].strip()
                        roster_entries[xml_filename] = line
    
    # Update or add entry
    xml_basename = os.path.basename(xml_file_path)
    roster_entries[xml_basename] = f"| {info['full_name']} | {info['eye']} | {info['dob']} | {xml_basename} |\n"
    
    # Sort entries by name
    sorted_entries = sorted(roster_entries.values(), key=lambda x: x.split('|')[1].strip() if '|' in x else x)
    
    # Write roster file
    with open(ROSTER_FILE, 'w', encoding='utf-8') as f:
        f.write("# Patient Roster\n\n")
        f.write("| Name | Eye | DOB | XML File |\n")
        f.write("|------|-----|-----|----------|\n")
        f.writelines(sorted_entries)
    
    print(f"Updated roster: {info['full_name']} ({info['eye']}) - {info['dob']}")


def ini_to_xml(ini_file_path, xml_file_path=None):
    """
    Convert an INI file to XML format.
    
    Args:
        ini_file_path: Path to the input INI file
        xml_file_path: Path to the output XML file (optional)
    
    Returns:
        Path to the created XML file
    """
    # Create XML output directory if it doesn't exist
    os.makedirs(XML_OUTPUT_DIR, exist_ok=True)
    
    # Set default output filename if not provided
    if xml_file_path is None:
        ini_basename = os.path.basename(ini_file_path)
        xml_basename = os.path.splitext(ini_basename)[0] + '.xml'
        xml_file_path = os.path.join(XML_OUTPUT_DIR, xml_basename)
    
    # Read the INI file
    config = configparser.ConfigParser()
    # Preserve case sensitivity
    config.optionxform = str
    
    # Try different encodings
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    read_success = False
    
    for encoding in encodings:
        try:
            config.read(ini_file_path, encoding=encoding)
            read_success = True
            print(f"Successfully read {os.path.basename(ini_file_path)} with {encoding} encoding")
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Error reading INI file with {encoding} encoding: {e}")
            continue
    
    if not read_success:
        print(f"Error: Could not read INI file {ini_file_path} with any supported encoding")
        return None
    
    # Create root XML element
    root = ET.Element('configuration')
    
    # Convert each section to XML
    for section_name in config.sections():
        section_elem = ET.SubElement(root, 'section', name=section_name)
        
        # Add all key-value pairs in this section
        for key, value in config.items(section_name):
            entry = ET.SubElement(section_elem, 'entry', key=key)
            entry.text = value
    
    # Also handle items not in any section (rare but possible)
    if config.defaults():
        default_section = ET.SubElement(root, 'section', name='DEFAULT')
        for key, value in config.defaults().items():
            entry = ET.SubElement(default_section, 'entry', key=key)
            entry.text = value
    
    # Create ElementTree and convert to string with pretty formatting
    tree = ET.ElementTree(root)
    
    # Pretty print the XML
    xml_string = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent="  ")
    
    # Write to file
    try:
        with open(xml_file_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        print(f"Successfully converted to {xml_file_path}")
        return xml_file_path
    except Exception as e:
        print(f"Error writing XML file: {e}")
        return None


def find_ini_files(directory):
    """
    Recursively find all INI files in a directory.
    
    Returns:
        List of full paths to INI files
    """
    ini_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.upper().endswith('.INI'):
                ini_files.append(os.path.join(root, file))
    return ini_files


def extract_zip_and_process(zip_file_path):
    """
    Extract a zip file, find all INI files, and process them.
    
    Args:
        zip_file_path: Path to the zip file
    """
    if not os.path.exists(zip_file_path):
        print(f"Error: Zip file '{zip_file_path}' not found.")
        return
    
    # Create a temporary extraction directory
    zip_basename = os.path.splitext(os.path.basename(zip_file_path))[0]
    extract_dir = os.path.join(IMAGES_DIR, f"_extracted_{zip_basename}")
    
    try:
        # Extract the zip file
        print(f"Extracting {os.path.basename(zip_file_path)}...")
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"Extracted to {extract_dir}\n")
        
        # Find all INI files in the extracted directory
        ini_files = find_ini_files(extract_dir)
        
        if not ini_files:
            print("No INI files found in the extracted zip archive.")
            # Clean up extraction directory
            shutil.rmtree(extract_dir, ignore_errors=True)
            return
        
        print(f"Found {len(ini_files)} INI file(s) in the zip archive.\n")
        
        # Process each INI file
        processed = 0
        for ini_path in sorted(ini_files):
            ini_filename = os.path.basename(ini_path)
            print(f"\nProcessing: {ini_filename}")
            
            xml_path = ini_to_xml(ini_path)
            if xml_path:
                update_roster(xml_path)
                processed += 1
        
        print(f"\n{'='*50}")
        print(f"Processing complete: {processed}/{len(ini_files)} files processed successfully")
        
        # Optionally clean up the extraction directory after processing
        # Uncomment the next line if you want to delete extracted files after processing
        # shutil.rmtree(extract_dir, ignore_errors=True)
        print(f"\nExtracted files are in: {extract_dir}")
        print("(You can delete this folder manually if needed)")
        
    except zipfile.BadZipFile:
        print(f"Error: '{zip_file_path}' is not a valid zip file.")
    except Exception as e:
        print(f"Error extracting zip file: {e}")
        # Clean up on error
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)


def process_all_ini_files():
    """
    Process all INI files in the images directory.
    """
    if not os.path.exists(IMAGES_DIR):
        print(f"Error: {IMAGES_DIR} directory not found.")
        return
    
    ini_files = [f for f in os.listdir(IMAGES_DIR) if f.upper().endswith('.INI')]
    
    if not ini_files:
        print(f"No INI files found in {IMAGES_DIR} directory.")
        return
    
    print(f"Found {len(ini_files)} INI file(s) to process.\n")
    
    processed = 0
    for ini_file in sorted(ini_files):
        ini_path = os.path.join(IMAGES_DIR, ini_file)
        print(f"\nProcessing: {ini_file}")
        
        xml_path = ini_to_xml(ini_path)
        if xml_path:
            update_roster(xml_path)
            processed += 1
    
    print(f"\n{'='*50}")
    print(f"Processing complete: {processed}/{len(ini_files)} files processed successfully")


def rebuild_roster():
    """
    Rebuild the roster from all XML files in the XML files directory.
    """
    if not os.path.exists(XML_OUTPUT_DIR):
        print(f"Error: {XML_OUTPUT_DIR} directory not found.")
        return
    
    xml_files = [f for f in os.listdir(XML_OUTPUT_DIR) if f.lower().endswith('.xml')]
    
    if not xml_files:
        print(f"No XML files found in {XML_OUTPUT_DIR} directory.")
        return
    
    print(f"Rebuilding roster from {len(xml_files)} XML file(s)...\n")
    
    roster_entries = {}
    for xml_file in sorted(xml_files):
        xml_path = os.path.join(XML_OUTPUT_DIR, xml_file)
        info = extract_patient_info(xml_path)
        roster_entries[xml_file] = f"| {info['full_name']} | {info['eye']} | {info['dob']} | {xml_file} |\n"
    
    # Sort entries by name
    sorted_entries = sorted(roster_entries.values(), key=lambda x: x.split('|')[1].strip() if '|' in x else x)
    
    # Write roster file
    with open(ROSTER_FILE, 'w', encoding='utf-8') as f:
        f.write("# Patient Roster\n\n")
        f.write("| Name | Eye | DOB | XML File |\n")
        f.write("|------|-----|-----|----------|\n")
        f.writelines(sorted_entries)
    
    print(f"Roster rebuilt successfully with {len(sorted_entries)} entries.")


def process_all_zip_files():
    """
    Find and process all zip files in the images directory.
    """
    if not os.path.exists(IMAGES_DIR):
        print(f"Error: {IMAGES_DIR} directory not found.")
        return
    
    # Find all zip files
    zip_files = [f for f in os.listdir(IMAGES_DIR) 
                 if f.lower().endswith(('.zip', '.ZIP'))]
    
    if not zip_files:
        print(f"No zip files found in {IMAGES_DIR} directory.")
        return
    
    print(f"Found {len(zip_files)} zip file(s) to process.\n")
    
    for zip_file in sorted(zip_files):
        zip_path = os.path.join(IMAGES_DIR, zip_file)
        print(f"{'='*60}")
        print(f"Processing zip file: {zip_file}")
        print(f"{'='*60}")
        extract_zip_and_process(zip_path)
        print()


def auto_process():
    """
    Automatically detect and process zip files and INI files in the images directory.
    """
    if not os.path.exists(IMAGES_DIR):
        print(f"Error: {IMAGES_DIR} directory not found.")
        return
    
    # First check for zip files
    zip_files = [f for f in os.listdir(IMAGES_DIR) 
                 if f.lower().endswith(('.zip', '.ZIP'))]
    
    if zip_files:
        print(f"Found {len(zip_files)} zip file(s). Processing...\n")
        process_all_zip_files()
    
    # Then check for INI files
    ini_files = [f for f in os.listdir(IMAGES_DIR) 
                 if f.upper().endswith('.INI')]
    
    if ini_files:
        print(f"\nFound {len(ini_files)} INI file(s). Processing...\n")
        process_all_ini_files()
    
    if not zip_files and not ini_files:
        print(f"No zip files or INI files found in {IMAGES_DIR} directory.")


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ini_to_xml.py <ini_file>              # Process single file")
        print("  python ini_to_xml.py <ini_file> <xml_file>   # Process with custom output")
        print("  python ini_to_xml.py --batch                 # Process all INI files in images/")
        print("  python ini_to_xml.py --unzip                 # Extract and process all zip files in images/")
        print("  python ini_to_xml.py --auto                  # Auto-detect and process zip/INI files")
        print("  python ini_to_xml.py --rebuild               # Rebuild roster from all XML files")
        print("\nExample:")
        print("  python ini_to_xml.py images/00000000.INI")
        print("  python ini_to_xml.py --batch")
        print("  python ini_to_xml.py --unzip")
        print("  python ini_to_xml.py --auto")
        sys.exit(1)
    
    # Check for batch mode
    if sys.argv[1] == '--batch' or sys.argv[1] == '-b':
        process_all_ini_files()
        return
    
    # Check for unzip mode
    if sys.argv[1] == '--unzip' or sys.argv[1] == '-u':
        process_all_zip_files()
        return
    
    # Check for auto mode
    if sys.argv[1] == '--auto' or sys.argv[1] == '-a':
        auto_process()
        return
    
    # Check for rebuild mode
    if sys.argv[1] == '--rebuild' or sys.argv[1] == '-r':
        rebuild_roster()
        return
    
    # Single file mode - check if it's a zip file
    input_file = sys.argv[1]
    if input_file.lower().endswith(('.zip', '.ZIP')):
        extract_zip_and_process(input_file)
        return
    
    # Single INI file mode
    xml_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)
    
    xml_path = ini_to_xml(input_file, xml_file)
    if xml_path:
        update_roster(xml_path)


if __name__ == '__main__':
    main()
