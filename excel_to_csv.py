#!/usr/bin/env python3
"""
Excel to CSV Converter
Converts Excel (.xlsx) files to CSV format.
"""

import pandas as pd
import sys
import os
from pathlib import Path


def excel_to_csv(excel_file_path, csv_file_path=None, sheet_name=None):
    """
    Convert an Excel file to CSV format.
    
    Args:
        excel_file_path: Path to the input Excel file
        csv_file_path: Path to the output CSV file (optional)
        sheet_name: Name of the sheet to convert (optional, defaults to first sheet)
    
    Returns:
        Path to the created CSV file
    """
    if not os.path.exists(excel_file_path):
        print(f"Error: Excel file '{excel_file_path}' not found.")
        return None
    
    try:
        # Read the Excel file
        if sheet_name:
            df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
        else:
            # Read first sheet by default
            df = pd.read_excel(excel_file_path, sheet_name=0)
        
        # Set default output filename if not provided
        if csv_file_path is None:
            excel_basename = os.path.splitext(os.path.basename(excel_file_path))[0]
            csv_file_path = excel_basename + '.csv'
            # Save in the same directory as the Excel file
            excel_dir = os.path.dirname(excel_file_path)
            if excel_dir:
                csv_file_path = os.path.join(excel_dir, csv_file_path)
            else:
                csv_file_path = csv_file_path
        
        # Write to CSV
        df.to_csv(csv_file_path, index=False, encoding='utf-8')
        
        print(f"Successfully converted {os.path.basename(excel_file_path)} to {csv_file_path}")
        print(f"Rows: {len(df)}, Columns: {len(df.columns)}")
        
        return csv_file_path
        
    except Exception as e:
        print(f"Error converting Excel file: {e}")
        return None


def convert_all_sheets(excel_file_path, output_dir=None):
    """
    Convert all sheets in an Excel file to separate CSV files.
    
    Args:
        excel_file_path: Path to the input Excel file
        output_dir: Directory to save CSV files (optional, defaults to same as Excel file)
    """
    if not os.path.exists(excel_file_path):
        print(f"Error: Excel file '{excel_file_path}' not found.")
        return
    
    try:
        # Read all sheets
        excel_file = pd.ExcelFile(excel_file_path)
        
        # Set output directory
        if output_dir is None:
            output_dir = os.path.dirname(excel_file_path) or '.'
        
        excel_basename = os.path.splitext(os.path.basename(excel_file_path))[0]
        
        print(f"Found {len(excel_file.sheet_names)} sheet(s) in {os.path.basename(excel_file_path)}\n")
        
        converted_files = []
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
            
            # Create CSV filename from sheet name (sanitize it)
            safe_sheet_name = "".join(c for c in sheet_name if c.isalnum() or c in (' ', '-', '_')).strip()
            csv_filename = f"{excel_basename}_{safe_sheet_name}.csv"
            csv_path = os.path.join(output_dir, csv_filename)
            
            df.to_csv(csv_path, index=False, encoding='utf-8')
            print(f"  ✓ Sheet '{sheet_name}': {len(df)} rows × {len(df.columns)} columns → {csv_filename}")
            converted_files.append(csv_path)
        
        print(f"\nSuccessfully converted {len(converted_files)} sheet(s) to CSV.")
        return converted_files
        
    except Exception as e:
        print(f"Error converting Excel file: {e}")
        return None


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python excel_to_csv.py <excel_file>              # Convert first sheet to CSV")
        print("  python excel_to_csv.py <excel_file> <csv_file>   # Convert with custom output")
        print("  python excel_to_csv.py <excel_file> --all        # Convert all sheets to separate CSV files")
        print("\nExample:")
        print("  python excel_to_csv.py excel/VAULT 3.0.xlsx")
        print("  python excel_to_csv.py excel/VAULT 3.0.xlsx output.csv")
        print("  python excel_to_csv.py excel/VAULT 3.0.xlsx --all")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    
    if not os.path.exists(excel_file):
        print(f"Error: File '{excel_file}' not found.")
        sys.exit(1)
    
    # Check for --all flag
    if len(sys.argv) > 2 and sys.argv[2] == '--all':
        convert_all_sheets(excel_file)
    else:
        csv_file = sys.argv[2] if len(sys.argv) > 2 else None
        excel_to_csv(excel_file, csv_file)


if __name__ == '__main__':
    main()


