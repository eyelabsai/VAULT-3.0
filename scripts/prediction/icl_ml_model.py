"""
ICL Vault and Lens Size Prediction Model

Features from XML (Pentacam):
- ACD_internal, WTW, Pupil Diameter
- TCRP Km (3mm zone pupil), TCRP Astigmatism
- ACV, ACA_global, BAD-D (optional)

Features from CSV:
- Sphere, Cyl

Derived features:
- Age (from DOB and exam date)
- Chamber shape ratio (ACV / ACD if ACV present)

Targets: Vault and ICL Size (using exchanged values when available)
"""

import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
from pathlib import Path
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ML libraries
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib


class NameMatcher:
    """Implements fuzzy name matching with various strategies"""

    SPELLING_VARIATIONS = {
        'russel': 'russell', 'russell': 'russel',
        'jenifer': 'jennifer', 'jennifer': 'jenifer',
        'brenton': 'benton', 'benton': 'brenton',
        'roseanna': 'rosanna', 'rosanna': 'roseanna',
        'michael': 'micheal', 'micheal': 'michael',
    }

    @staticmethod
    def normalize_name(name: str) -> str:
        if pd.isna(name):
            return ""
        name = str(name).lower().strip()
        name = re.sub(r'\s*-\s*', '-', name)
        name = re.sub(r'\s+', ' ', name)
        return name

    @staticmethod
    def remove_suffix(name: str) -> str:
        suffixes = r'\b(jr|sr|ii|iii|iv|2nd|3rd)\b\.?'
        return re.sub(suffixes, '', name, flags=re.IGNORECASE).strip()

    @classmethod
    def get_name_variations(cls, name: str) -> List[str]:
        name = cls.normalize_name(name)
        name = cls.remove_suffix(name)
        variations = [name]

        parts = name.split()
        if len(parts) == 2:
            variations.append(f"{parts[1]} {parts[0]}")
        elif len(parts) > 2:
            variations.append(f"{parts[-1]} {' '.join(parts[:-1])}")

        for var in list(variations):
            words = var.split()
            for i, word in enumerate(words):
                if word in cls.SPELLING_VARIATIONS:
                    new_words = words.copy()
                    new_words[i] = cls.SPELLING_VARIATIONS[word]
                    variations.append(' '.join(new_words))

        return list(set(variations))

    @classmethod
    def match_names(cls, name1: str, name2: str) -> Tuple[bool, str]:
        name1_variations = cls.get_name_variations(name1)
        name2_variations = cls.get_name_variations(name2)

        for n1 in name1_variations:
            if n1 in name2_variations:
                return True, "exact"

        for n1 in name1_variations:
            for n2 in name2_variations:
                parts1 = n1.split()
                parts2 = n2.split()
                for p1 in parts1:
                    for p2 in parts2:
                        if len(p1) > 3 and len(p2) > 3:
                            if p1 in p2 or p2 in p1:
                                if any(part in n2 for part in parts1 if part != p1):
                                    return True, "partial"

        return False, "no_match"


class XMLParser:
    """Parse Pentacam XML files and extract ONLY specified clinical features"""

    def __init__(self, xml_path: str):
        self.xml_path = Path(xml_path)
        self.tree = ET.parse(xml_path)
        self.root = self.tree.getroot()

    def get_patient_info(self) -> Dict:
        """Extract patient name and DOB"""
        patient_section = self.root.find(".//section[@name='Patient Data']")
        if patient_section is None:
            return {}

        info = {}
        for entry in patient_section.findall('entry'):
            key = entry.get('key')
            value = entry.text
            info[key] = value

        surname = info.get('Surname', '')
        name = info.get('Name', '')
        full_name = f"{name} {surname}".strip() if name and surname else ""

        return {
            'full_name': full_name,
            'dob': info.get('DOB', ''),
        }

    def extract_eye_features(self, eye: str) -> Dict:
        """
        Extract specified clinical features for a specific eye

        Features:
        - From Test Data: WTW, Pupil Diameter
        - From Examination Data: TCRP Km, TCRP Asti, ACD (Int.), BAD D, ACA
        """
        features = {}

        # Determine section indices (OD=0, OS=1)
        eye_index = '0' if eye == 'OD' else '1'

        # Extract from Test Data section
        test_section = self.root.find(f".//section[@name='Test Data {eye} {eye_index}']")
        if test_section is not None:
            for entry in test_section.findall('entry'):
                key = entry.get('key')

                if key == 'Cornea Dia Horizontal':
                    try:
                        features['WTW'] = float(entry.text) if entry.text else None
                    except (ValueError, TypeError):
                        features['WTW'] = None

                elif key == 'Pupil diameter mm':
                    try:
                        features['Pupil_Diameter'] = float(entry.text) if entry.text else None
                    except (ValueError, TypeError):
                        features['Pupil_Diameter'] = None

                elif key == 'Test Date':
                    features['exam_date'] = entry.text

        # Extract from Examination Data section
        exam_section = self.root.find(f".//section[@name='Examination Data {eye_index}']")
        if exam_section is not None:
            for entry in exam_section.findall('entry'):
                key = entry.get('key')

                if key == 'TCRP 3mm zone pupil Km [D]':
                    try:
                        features['TCRP_Km'] = float(entry.text) if entry.text else None
                    except (ValueError, TypeError):
                        features['TCRP_Km'] = None

                elif key == 'TCRP 3mm zone pupil Asti [D]':
                    try:
                        features['TCRP_Asti'] = float(entry.text) if entry.text else None
                    except (ValueError, TypeError):
                        features['TCRP_Asti'] = None

                elif key == 'ACD (Int.) [mm]':
                    try:
                        features['ACD'] = float(entry.text) if entry.text else None
                    except (ValueError, TypeError):
                        features['ACD'] = None

                elif key == 'ACA (180°) [°]':
                    try:
                        features['ACA_180'] = float(entry.text) if entry.text else None
                    except (ValueError, TypeError):
                        features['ACA_180'] = None

        return features


def parse_all_xml_files(xml_dir: str) -> pd.DataFrame:
    """Parse all XML files and extract specified features"""
    xml_dir = Path(xml_dir)
    all_data = []

    xml_files = list(xml_dir.glob("*.xml"))
    print(f"Found {len(xml_files)} XML files")

    for xml_file in xml_files:
        try:
            parser = XMLParser(xml_file)
            patient_info = parser.get_patient_info()

            if not patient_info.get('full_name'):
                continue

            # Extract features for both eyes
            for eye in ['OD', 'OS']:
                features = parser.extract_eye_features(eye)
                if features:
                    record = {
                        'xml_file': xml_file.name,
                        'patient_name': patient_info['full_name'],
                        'dob_xml': patient_info.get('dob', ''),
                        'eye': eye,
                        **features
                    }
                    all_data.append(record)

        except Exception as e:
            print(f"Error parsing {xml_file.name}: {e}")
            continue

    df = pd.DataFrame(all_data)
    print(f"Extracted data for {len(df)} eye records from XML files")

    if len(df) > 0:
        print(f"\nXML Features extracted per record:")
        feature_cols = ['WTW', 'Pupil_Diameter', 'TCRP_Km', 'TCRP_Asti', 'ACD', 'ACA_180']
        for col in feature_cols:
            if col in df.columns:
                non_null = df[col].notna().sum()
                print(f"  {col}: {non_null}/{len(df)} records")

    return df


def load_csv_data(csv_path: str) -> pd.DataFrame:
    """Load CSV and extract Sphere, Cyl, and target variables"""
    df = pd.read_csv(csv_path)

    print(f"Loaded CSV with {len(df)} records")

    # Create final lens size and vault columns (use exchanged values if available)
    df['final_lens_size'] = df.apply(
        lambda row: row['Exchanged Size'] if row['Exchange?'] == 'YES' else row['ICL Size'],
        axis=1
    )

    df['final_vault'] = df.apply(
        lambda row: row['Exchanged Vault'] if row['Exchange?'] == 'YES' else row['Vault'],
        axis=1
    )

    df['patient_name'] = df['NAME'].str.strip()
    df['eye'] = df['Eye'].str.strip()

    # Remove records without final values
    df = df.dropna(subset=['final_lens_size', 'final_vault'])

    print(f"After cleaning: {len(df)} records with final vault and lens size")
    print(f"Exchanges used: {(df['Exchange?'] == 'YES').sum()}")

    return df


def merge_xml_and_csv(xml_df: pd.DataFrame, csv_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge XML features with CSV outcomes using fuzzy matching

    XML-DRIVEN APPROACH:
    - Start with XML files (patients with Pentacam data)
    - Find their surgical outcomes in CSV
    """

    matcher = NameMatcher()
    matches = []
    unmatched_xml = []

    print("\nMatching XML patients to CSV outcomes...")
    print(f"Starting with {len(xml_df)} XML eye records")

    # XML-driven: for each XML eye, find its outcome in CSV
    for idx, xml_row in xml_df.iterrows():
        xml_name = xml_row['patient_name']
        xml_eye = xml_row['eye']

        best_match = None
        match_type = "no_match"

        # Search CSV for matching patient and eye
        for csv_idx, csv_row in csv_df.iterrows():
            csv_name = csv_row['patient_name']
            csv_eye = csv_row['eye']

            # Eye must match
            if csv_eye != xml_eye:
                continue

            # Try name matching
            is_match, match_type_result = matcher.match_names(xml_name, csv_name)

            if is_match:
                best_match = csv_row
                match_type = match_type_result
                break

        if best_match is not None:
            merged = {
                'patient_name': xml_name,
                'eye': xml_eye,
                'match_type': match_type,

                # Targets from CSV (surgical outcomes)
                'final_lens_size': best_match['final_lens_size'],
                'final_vault': best_match['final_vault'],

                # CSV clinical features (pre-op)
                'Sphere': best_match.get('Sphere'),
                'Cyl': best_match.get('Cyl'),
                'DOS': best_match.get('DOS'),
                'DOB': best_match.get('DOB'),

                # XML clinical features (Pentacam)
                'WTW': xml_row.get('WTW'),
                'Pupil_Diameter': xml_row.get('Pupil_Diameter'),
                'TCRP_Km': xml_row.get('TCRP_Km'),
                'TCRP_Asti': xml_row.get('TCRP_Asti'),
                'ACD': xml_row.get('ACD'),
                'ACA_180': xml_row.get('ACA_180'),
                'exam_date': xml_row.get('exam_date'),
            }

            matches.append(merged)
        else:
            unmatched_xml.append((xml_name, xml_eye))

    print(f"\nMatched: {len(matches)} records ({len(matches)/len(xml_df)*100:.1f}% of XML)")
    print(f"Unmatched XML eyes (no surgery in CSV): {len(unmatched_xml)}")

    if unmatched_xml:
        print("\nSample XML patients without surgery outcomes (first 10):")
        for name, eye in unmatched_xml[:10]:
            print(f"  - {name} ({eye})")

    matched_df = pd.DataFrame(matches)

    if len(matched_df) > 0:
        print(f"\nMatch type distribution:")
        print(matched_df['match_type'].value_counts())

    return matched_df


def calculate_age(dob_str, exam_date_str):
    """Calculate age in years from DOB and exam date"""
    try:
        if pd.isna(dob_str) or pd.isna(exam_date_str):
            return None

        # Parse DOB
        dob_str = str(dob_str).split()[0]  # Remove time part
        dob = pd.to_datetime(dob_str)

        # Parse exam date
        exam_date_str = str(exam_date_str).split()[0]
        exam_date = pd.to_datetime(exam_date_str)

        # Calculate age
        age = (exam_date - dob).days / 365.25
        return age
    except:
        return None


def prepare_training_data(merged_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Prepare features and targets for training"""

    # Base feature columns
    feature_cols = [
        'Sphere',
        'Cyl',
        'WTW',
        'Pupil_Diameter',
        'TCRP_Km',
        'TCRP_Asti',
        'ACD',
    ]

    # Optional features
    optional_features = ['ACA_180']

    X = merged_df[feature_cols + optional_features].copy()

    # Convert all to numeric
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')

    # Derive Age
    merged_df['Age'] = merged_df.apply(
        lambda row: calculate_age(row['DOB'], row.get('exam_date')), axis=1
    )
    X['Age'] = merged_df['Age']

    # Handle missing values with median imputation
    print(f"\nFeature statistics:")
    for col in X.columns:
        missing = X[col].isna().sum()
        if missing > 0:
            median_val = X[col].median()
            if pd.notna(median_val):
                X[col].fillna(median_val, inplace=True)
                print(f"  {col}: {missing} missing → imputed with median {median_val:.2f}")
        else:
            print(f"  {col}: Complete ({len(X)} values)")

    # Target variables
    y_vault = merged_df['final_vault']
    y_lens_size = merged_df['final_lens_size']

    print(f"\n{'='*60}")
    print("TRAINING DATA SUMMARY")
    print(f"{'='*60}")
    print(f"\nFeatures: {list(X.columns)}")
    print(f"Samples: {len(X)}")
    print(f"Features: {X.shape[1]}")
    print(f"\nTarget ranges:")
    print(f"  Vault: {y_vault.min():.1f} - {y_vault.max():.1f} µm")
    print(f"  Lens Size: {y_lens_size.min():.1f} - {y_lens_size.max():.1f} mm")

    print(f"\nFeature Summary:")
    print(X.describe().round(2))

    return X, y_vault, y_lens_size


def train_models(X: pd.DataFrame, y_vault: pd.Series, y_lens_size: pd.Series):
    """Train ML models for vault and lens size prediction"""

    print("\n" + "="*60)
    print("TRAINING MODELS")
    print("="*60)

    X_train, X_test, y_vault_train, y_vault_test, y_lens_train, y_lens_test = train_test_split(
        X, y_vault, y_lens_size, test_size=0.2, random_state=42
    )

    print(f"\nTrain set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ========== VAULT MODEL ==========
    print("\n" + "-"*60)
    print("VAULT PREDICTION MODEL")
    print("-"*60)

    vault_model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        min_samples_split=5,
        min_samples_leaf=3,
        subsample=0.8,
        random_state=42
    )

    vault_model.fit(X_train_scaled, y_vault_train)

    y_vault_pred_train = vault_model.predict(X_train_scaled)
    y_vault_pred_test = vault_model.predict(X_test_scaled)

    print("\nTrain Performance:")
    print(f"  MAE: {mean_absolute_error(y_vault_train, y_vault_pred_train):.2f} µm")
    print(f"  RMSE: {np.sqrt(mean_squared_error(y_vault_train, y_vault_pred_train)):.2f} µm")
    print(f"  R²: {r2_score(y_vault_train, y_vault_pred_train):.3f}")

    print("\nTest Performance:")
    print(f"  MAE: {mean_absolute_error(y_vault_test, y_vault_pred_test):.2f} µm")
    print(f"  RMSE: {np.sqrt(mean_squared_error(y_vault_test, y_vault_pred_test)):.2f} µm")
    print(f"  R²: {r2_score(y_vault_test, y_vault_pred_test):.3f}")

    feature_importance_vault = pd.DataFrame({
        'feature': X.columns,
        'importance': vault_model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\nFeature Importance for Vault:")
    print(feature_importance_vault.to_string(index=False))

    # ========== LENS SIZE MODEL ==========
    print("\n" + "-"*60)
    print("LENS SIZE PREDICTION MODEL")
    print("-"*60)

    lens_model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        min_samples_split=5,
        min_samples_leaf=3,
        subsample=0.8,
        random_state=42
    )

    lens_model.fit(X_train_scaled, y_lens_train)

    y_lens_pred_train = lens_model.predict(X_train_scaled)
    y_lens_pred_test = lens_model.predict(X_test_scaled)

    print("\nTrain Performance:")
    print(f"  MAE: {mean_absolute_error(y_lens_train, y_lens_pred_train):.3f} mm")
    print(f"  RMSE: {np.sqrt(mean_squared_error(y_lens_train, y_lens_pred_train)):.3f} mm")
    print(f"  R²: {r2_score(y_lens_train, y_lens_pred_train):.3f}")

    print("\nTest Performance:")
    print(f"  MAE: {mean_absolute_error(y_lens_test, y_lens_pred_test):.3f} mm")
    print(f"  RMSE: {np.sqrt(mean_squared_error(y_lens_test, y_lens_pred_test)):.3f} mm")
    print(f"  R²: {r2_score(y_lens_test, y_lens_pred_test):.3f}")

    feature_importance_lens = pd.DataFrame({
        'feature': X.columns,
        'importance': lens_model.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\nFeature Importance for Lens Size:")
    print(feature_importance_lens.to_string(index=False))

    # Save models
    print("\n" + "="*60)
    print("SAVING MODELS")
    print("="*60)

    joblib.dump(vault_model, 'vault_model.pkl')
    joblib.dump(lens_model, 'lens_size_model.pkl')
    joblib.dump(scaler, 'feature_scaler.pkl')
    joblib.dump(X.columns.tolist(), 'feature_names.pkl')

    print("\nSaved:")
    print("  - vault_model.pkl")
    print("  - lens_size_model.pkl")
    print("  - feature_scaler.pkl")
    print("  - feature_names.pkl")

    return vault_model, lens_model, scaler, feature_importance_vault, feature_importance_lens


def main():
    """Main execution pipeline"""

    print("="*60)
    print("ICL VAULT & LENS SIZE PREDICTION MODEL")
    print("Using TCRP and Clinically Relevant Features")
    print("="*60)

    csv_path = "excel/VAULT 3.0.csv"
    xml_dir = "XML files"

    print("\n[1/5] Parsing XML files...")
    xml_df = parse_all_xml_files(xml_dir)

    print("\n[2/5] Loading CSV data...")
    csv_df = load_csv_data(csv_path)

    print("\n[3/5] Merging XML and CSV data...")
    merged_df = merge_xml_and_csv(xml_df, csv_df)

    merged_df.to_csv('merged_training_data.csv', index=False)
    print("\nSaved merged data to: merged_training_data.csv")

    if len(merged_df) < 20:
        print("\nWARNING: Very few matches found. Check name matching logic.")
        return

    print("\n[4/5] Preparing training data...")
    X, y_vault, y_lens_size = prepare_training_data(merged_df)

    print("\n[5/5] Training models...")
    vault_model, lens_model, scaler, feat_imp_vault, feat_imp_lens = train_models(
        X, y_vault, y_lens_size
    )

    print("\n" + "="*60)
    print("TRAINING COMPLETE!")
    print("="*60)
    print("\nModels are ready for prediction.")
    print("Use predict_new_patient.py to make predictions for new patients.")


if __name__ == "__main__":
    main()
