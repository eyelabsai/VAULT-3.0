"""
Predict ICL vault and lens size for a new patient

Usage:
    python predict_new_patient.py --xml_file "XML files/patient.xml" --eye OD
"""

import argparse
import joblib
import pandas as pd
import numpy as np
from scripts.prediction.gestalt_postprocess import apply_gestalt_advice
from icl_ml_model import XMLParser


def load_models():
    """Load trained models and scaler"""
    try:
        vault_model = joblib.load('vault_model.pkl')
        lens_model = joblib.load('lens_size_model.pkl')
        scaler = joblib.load('feature_scaler.pkl')
        feature_names = joblib.load('feature_names.pkl')
        return vault_model, lens_model, scaler, feature_names
    except FileNotFoundError as e:
        print(f"Error: Model files not found. Please run icl_ml_model.py first to train the models.")
        print(f"Missing file: {e}")
        exit(1)


def extract_features_from_xml(xml_path: str, eye: str, feature_names: list) -> pd.DataFrame:
    """Extract features from XML file for prediction"""

    parser = XMLParser(xml_path)
    patient_info = parser.get_patient_info()

    print(f"\nPatient: {patient_info['full_name']}")
    print(f"DOB: {patient_info['dob']}")
    print(f"Eye: {eye}")

    # Extract XML features
    xml_features = parser.extract_eye_features(eye)

    if not xml_features:
        print(f"Warning: No features found for {eye} eye in XML file")
        return None

    # Create feature dictionary matching training features
    features = {}

    # Map XML features to training feature names
    xml_feature_mapping = {
        'xml_Central Corneal Thickness': 'Central Corneal Thickness',
        'xml_SimK flat D': 'SimK flat D',
        'xml_SimK steep D': 'SimK steep D',
        'xml_Pupil diameter mm': 'Pupil diameter mm',
        'xml_ACD external': 'ACD external',
        'xml_Cornea Dia Horizontal': 'Cornea Dia Horizontal',
        'xml_Anterior Rm': 'Anterior Rm',
        'xml_Posterior Rm': 'Posterior Rm',
        'xml_Sag K1 3.0mm, (D), Apex, Zone': 'Sag K1 3.0mm, (D), Apex, Zone',
        'xml_Sag K2 3.0mm, (D), Apex, Zone': 'Sag K2 3.0mm, (D), Apex, Zone',
        'xml_Sag Km 3.0mm, (D), Apex, Zone': 'Sag Km 3.0mm, (D), Apex, Zone',
    }

    for train_feature in feature_names:
        if train_feature.startswith('csv_'):
            # CSV features - we don't have these for new patients, will use median
            features[train_feature] = None
        elif train_feature.startswith('xml_'):
            # XML features
            xml_key = xml_feature_mapping.get(train_feature)
            if xml_key and xml_key in xml_features:
                features[train_feature] = xml_features[xml_key]
            else:
                features[train_feature] = None

    # Create DataFrame
    X = pd.DataFrame([features])

    # Show what features we have
    print("\nExtracted features:")
    for col in X.columns:
        val = X[col].iloc[0]
        if pd.notna(val):
            print(f"  {col}: {val}")

    return X


def predict(xml_path: str, eye: str, manual_features: dict = None):
    """Make prediction for a new patient"""

    print("="*60)
    print("ICL VAULT & LENS SIZE PREDICTION")
    print("="*60)

    # Load models
    print("\nLoading trained models...")
    vault_model, lens_model, scaler, feature_names = load_models()

    # Extract features
    print(f"\nExtracting features from XML file...")
    X = extract_features_from_xml(xml_path, eye, feature_names)

    if X is None:
        return

    # Add manual features if provided
    if manual_features:
        print("\nAdding manual features:")
        for key, val in manual_features.items():
            if key in X.columns:
                X[key] = val
                print(f"  {key}: {val}")

    # Handle missing values (use median from training)
    # For now, fill with 0 (will be handled by scaler)
    X_filled = X.fillna(0)

    # Scale features
    X_scaled = scaler.transform(X_filled)

    # Predict
    predicted_vault = vault_model.predict(X_scaled)[0]
    predicted_lens_size = lens_model.predict(X_scaled)[0]

    # Round lens size to nearest available size
    available_lens_sizes = [12.1, 12.6, 13.2, 13.7]
    predicted_lens_size_rounded = min(available_lens_sizes,
                                      key=lambda x: abs(x - predicted_lens_size))

    # Soft WTW+1 cap (non-absolute): report a conservative alternative
    soft_cap_size = None
    wtw_val = X.iloc[0].get('WTW') if 'WTW' in X.columns else None
    if wtw_val is not None and pd.notna(wtw_val) and not manual_features.get('toric', False):
        wtw_cap = float(wtw_val) + 1.0
        if predicted_lens_size_rounded > wtw_cap:
            eligible = [s for s in available_lens_sizes if s <= wtw_cap]
            if eligible:
                soft_cap_size = max(eligible)

    # Display results
    print("\n" + "="*60)
    print("PREDICTIONS")
    print("="*60)
    print(f"\nPredicted Vault: {predicted_vault:.0f} µm")
    print(f"Predicted Lens Size: {predicted_lens_size:.2f} mm")
    print(f"Recommended Lens Size (Model): {predicted_lens_size_rounded} mm")
    if soft_cap_size is not None:
        print(f"Recommended Lens Size (WTW+1 soft cap): {soft_cap_size} mm")

    # Gestalt advisory (post-processing)
    input_data = {
        'Age': X.iloc[0].get('Age'),
        'WTW': X.iloc[0].get('WTW'),
        'ACD_internal': X.iloc[0].get('ACD_internal'),
    }
    advice = apply_gestalt_advice(
        input_data=input_data,
        model_size=predicted_lens_size_rounded,
        model_prob=None,
        enabled=manual_features.get('gestalt', False),
        toric=manual_features.get('toric', False),
    )
    if advice:
        print("\nGestalt Advisory:")
        for item in advice:
            print(f"  - {item['recommendation']} — {item['reason']}")

    # Vault interpretation
    print("\nVault Interpretation:")
    if predicted_vault < 250:
        print("  ⚠️  LOW - Risk of contact with lens/cornea")
    elif predicted_vault < 400:
        print("  ✓ ACCEPTABLE - Lower end of optimal range")
    elif predicted_vault < 750:
        print("  ✓ OPTIMAL - Good clearance")
    elif predicted_vault < 1000:
        print("  ⚠️  HIGH - Upper end of acceptable range")
    else:
        print("  ⚠️  VERY HIGH - Risk of angle closure/pupil block")

    print("\nNote: These predictions are based on historical data.")
    print("Clinical judgment should always be used in final decision making.")

    return {
        'predicted_vault': predicted_vault,
        'predicted_lens_size': predicted_lens_size,
        'recommended_lens_size': predicted_lens_size_rounded,
        'wtw_plus_one_recommendation': soft_cap_size,
        'gestalt_advice': advice
    }


def main():
    parser = argparse.ArgumentParser(description='Predict ICL vault and lens size for new patient')
    parser.add_argument('--xml_file', required=True, help='Path to patient XML file')
    parser.add_argument('--eye', required=True, choices=['OD', 'OS'], help='Eye (OD or OS)')
    parser.add_argument('--sphere', type=float, help='Spherical refraction (optional)')
    parser.add_argument('--cyl', type=float, help='Cylindrical refraction (optional)')
    parser.add_argument('--k1', type=float, help='K1 value (optional)')
    parser.add_argument('--k2', type=float, help='K2 value (optional)')
    parser.add_argument('--acd', type=float, help='Anterior chamber depth (optional)')
    parser.add_argument('--wtw', type=float, help='White-to-white (optional)')
    parser.add_argument('--toric', action='store_true', help='Allow toric exception for WTW+1 soft cap')
    parser.add_argument('--gestalt', action='store_true', help='Enable gestalt advisory rules')

    args = parser.parse_args()

    # Collect manual features if provided
    manual_features = {}
    if args.sphere is not None:
        manual_features['csv_sphere'] = args.sphere
    if args.cyl is not None:
        manual_features['csv_cyl'] = args.cyl
    if args.k1 is not None:
        manual_features['csv_k1'] = args.k1
    if args.k2 is not None:
        manual_features['csv_k2'] = args.k2
    if args.acd is not None:
        manual_features['csv_acd'] = args.acd
    if args.wtw is not None:
        manual_features['csv_wtw'] = args.wtw
    if args.toric:
        manual_features['toric'] = True
    if args.gestalt:
        manual_features['gestalt'] = True

    predict(args.xml_file, args.eye, manual_features)


if __name__ == "__main__":
    main()
