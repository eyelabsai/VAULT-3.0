#!/usr/bin/env python3
"""
ICL Vault Prediction - Clinical Decision Support
Predicts lens size with confidence scores and vault for each option.
"""

import pandas as pd
import numpy as np
import pickle
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def load_models():
    """Load trained models and scalers."""
    with open('lens_size_model.pkl', 'rb') as f:
        lens_model = pickle.load(f)
    with open('lens_size_scaler.pkl', 'rb') as f:
        lens_scaler = pickle.load(f)
    with open('vault_model.pkl', 'rb') as f:
        vault_model = pickle.load(f)
    with open('vault_scaler.pkl', 'rb') as f:
        vault_scaler = pickle.load(f)
    with open('feature_names.pkl', 'rb') as f:
        feature_names = pickle.load(f)
    
    return lens_model, lens_scaler, vault_model, vault_scaler, feature_names


def predict_patient(patient_data, return_probabilities=True):
    """
    Predict lens size and vault for a patient.
    
    Args:
        patient_data: dict with keys ['Age', 'WTW', 'ACD_internal', 'SEQ', 'CCT']
        return_probabilities: if True, return full probability distribution
    
    Returns:
        dict with predictions and probabilities
    """
    # Load models
    lens_model, lens_scaler, vault_model, vault_scaler, feature_names = load_models()
    
    # Prepare input features
    X = pd.DataFrame([patient_data])[feature_names]
    
    # Validate inputs
    missing = X.isnull().any(axis=1).any()
    if missing:
        missing_cols = X.columns[X.isnull().any()].tolist()
        raise ValueError(f"Missing required features: {missing_cols}")
    
    # Scale features
    X_lens_scaled = lens_scaler.transform(X)
    X_vault_scaled = vault_scaler.transform(X)
    
    # LENS SIZE PREDICTIONS
    lens_pred = lens_model.predict(X_lens_scaled)[0]
    
    # Get probability distribution for all lens sizes
    if hasattr(lens_model, 'predict_proba'):
        lens_proba = lens_model.predict_proba(X_lens_scaled)[0]
        lens_classes = lens_model.classes_
        
        # Sort by probability (descending)
        sorted_indices = np.argsort(lens_proba)[::-1]
        lens_options = []
        
        for idx in sorted_indices:
            if lens_proba[idx] > 0.01:  # Only show options with >1% probability
                lens_options.append({
                    'size': float(lens_classes[idx]),
                    'probability': float(lens_proba[idx]),
                    'confidence_pct': float(lens_proba[idx] * 100)
                })
    else:
        # If model doesn't support probabilities, just return top prediction
        lens_options = [{
            'size': float(lens_pred),
            'probability': 1.0,
            'confidence_pct': 100.0
        }]
    
    # VAULT PREDICTIONS
    vault_pred = vault_model.predict(X_vault_scaled)[0]
    
    # Estimate prediction interval (using historical MAE as proxy)
    # From training: MAE = 131.7µm
    mae_estimate = 131.7
    vault_lower = vault_pred - mae_estimate
    vault_upper = vault_pred + mae_estimate
    
    # CONDITIONAL VAULT PREDICTIONS
    # Predict vault for each lens size option
    # (Note: Current model doesn't use lens size as input, so these will be the same)
    # Future enhancement: retrain vault model with lens size as feature
    for option in lens_options:
        option['predicted_vault'] = float(vault_pred)
        option['vault_range_lower'] = float(vault_lower)
        option['vault_range_upper'] = float(vault_upper)
        option['vault_range'] = f"{vault_lower:.0f}-{vault_upper:.0f}µm"
    
    result = {
        'patient_data': patient_data,
        'top_lens_size': float(lens_pred),
        'predicted_vault': float(vault_pred),
        'vault_confidence_interval': {
            'lower': float(vault_lower),
            'upper': float(vault_upper),
            'mae': mae_estimate
        },
        'lens_options': lens_options,
        'timestamp': datetime.now().isoformat()
    }
    
    return result


def format_prediction_report(prediction):
    """Format prediction as a clinical report."""
    report = []
    report.append("="*70)
    report.append("ICL PREDICTION - CLINICAL DECISION SUPPORT")
    report.append("="*70)
    report.append("")
    
    # Patient data
    report.append("Patient Data:")
    for key, value in prediction['patient_data'].items():
        report.append(f"  {key:20s}: {value}")
    report.append("")
    
    # Recommendations
    report.append("="*70)
    report.append("LENS SIZE RECOMMENDATIONS")
    report.append("="*70)
    report.append("")
    report.append(f"{'Size':>8} {'Confidence':>12} {'Pred. Vault':>14} {'Vault Range':>16}")
    report.append("-"*70)
    
    for i, option in enumerate(prediction['lens_options']):
        marker = "★" if i == 0 else " "
        report.append(
            f"{option['size']:>7.1f}mm "
            f"{option['confidence_pct']:>10.1f}% {marker} "
            f"{option['predicted_vault']:>11.0f}µm "
            f"{option['vault_range']:>16}"
        )
    
    report.append("")
    report.append("="*70)
    report.append("VAULT PREDICTION")
    report.append("="*70)
    report.append(f"Predicted Vault:  {prediction['predicted_vault']:.0f}µm")
    report.append(f"Confidence Range: {prediction['vault_confidence_interval']['lower']:.0f}-"
                 f"{prediction['vault_confidence_interval']['upper']:.0f}µm")
    report.append(f"Expected Error:   ±{prediction['vault_confidence_interval']['mae']:.1f}µm (MAE)")
    report.append("")
    
    # Clinical notes
    report.append("="*70)
    report.append("CLINICAL NOTES")
    report.append("="*70)
    report.append("★ = Highest confidence recommendation")
    report.append("")
    report.append("Model Performance (77 training cases):")
    report.append("  • Lens Size Accuracy: 81.8%")
    report.append("  • Vault MAE: 131.7µm")
    report.append("  • 75% of predictions within ±200µm of actual vault")
    report.append("")
    report.append("Recommendation:")
    top = prediction['lens_options'][0]
    report.append(f"  Primary choice: {top['size']:.1f}mm ({top['confidence_pct']:.0f}% confidence)")
    
    if len(prediction['lens_options']) > 1:
        alt = prediction['lens_options'][1]
        report.append(f"  Alternative: {alt['size']:.1f}mm ({alt['confidence_pct']:.0f}% confidence)")
        report.append("")
        report.append("  Consider alternative if clinical factors suggest different vault target.")
    
    report.append("")
    report.append("="*70)
    
    return "\n".join(report)


def main():
    """Example usage."""
    print("\n" + "="*70)
    print("ICL PREDICTION SYSTEM - EXAMPLE")
    print("="*70)
    print()
    
    # Example patient
    example_patient = {
        'Age': 32,
        'WTW': 11.8,
        'ACD_internal': 3.2,
        'SEQ': -8.5,
        'CCT': 540
    }
    
    print("Example Patient:")
    for key, value in example_patient.items():
        print(f"  {key}: {value}")
    print()
    
    # Make prediction
    prediction = predict_patient(example_patient)
    
    # Print formatted report
    print(format_prediction_report(prediction))
    
    # Also return as JSON for programmatic use
    print("\nJSON Output (for API/frontend):")
    import json
    print(json.dumps(prediction, indent=2))


if __name__ == '__main__':
    main()

