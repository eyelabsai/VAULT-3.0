#!/usr/bin/env python3
"""
ICL Vault Prediction - Model Training

Trains models to predict:
1. Lens Size (classification - discrete sizes like 12.6, 13.2, 13.7)
2. Vault (regression - continuous measurement)

Uses cross-validation due to small dataset size (56 cases).
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import cross_val_score, cross_val_predict, KFold
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import Ridge, Lasso
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    mean_absolute_error, mean_squared_error, r2_score
)
import pickle
import warnings
warnings.filterwarnings('ignore')

# Import performance tracking
from track_performance import save_run


def get_nomogram_size(wtw, acd):
    """Implementation of the sizing nomogram from the provided table."""
    if wtw < 10.5 or wtw >= 13.0:
        return 0.0
    
    if 10.5 <= wtw < 10.7:
        return 12.1 if acd > 3.5 else 0.0
    elif 10.7 <= wtw < 11.1:
        return 12.1
    elif 11.1 <= wtw < 11.2:
        return 12.6 if acd > 3.5 else 12.1
    elif 11.2 <= wtw < 11.5:
        return 12.6
    elif 11.5 <= wtw < 11.7:
        return 13.2 if acd > 3.5 else 12.6
    elif 11.7 <= wtw < 12.2:
        return 13.2
    elif 12.2 <= wtw < 12.3:
        return 13.7 if acd > 3.5 else 13.2
    elif 12.3 <= wtw < 13.0:
        return 13.7
    
    return 0.0


def load_and_prepare_data():
    """Load training data and prepare features/targets."""
    print("="*70)
    print("LOADING TRAINING DATA")
    print("="*70)
    
    df = pd.read_csv('data/processed/training_data.csv')
    
    # CORE FEATURES
    feature_cols = ['Age', 'WTW', 'ACD_internal', 'ICL_Power', 'AC_shape_ratio', 
                    'SimK_steep', 'ACV', 'TCRP_Km', 'TCRP_Astigmatism']
    target_cols = ['Lens_Size', 'Vault']
    
    # Filter complete cases
    complete = df[feature_cols + target_cols].notna().all(axis=1)
    df_complete = df[complete].copy()
    
    # Standardize Lens_Size (fix negative values like -12.6 -> 12.6)
    df_complete['Lens_Size'] = df_complete['Lens_Size'].abs()
    
    # Remove outliers in Lens_Size
    valid_lens = (df_complete['Lens_Size'] > 0) & (df_complete['Lens_Size'] < 20)
    df_complete = df_complete[valid_lens].copy()
    
    # --- ADD ADVANCED GESTALT CLINICAL FEATURES ---
    # 1. WTW Buckets (based on real patient distribution)
    df_complete['WTW_Bucket'] = pd.cut(df_complete['WTW'], 
                                     bins=[0, 11.6, 11.9, 12.4, 20], 
                                     labels=[0, 1, 2, 3]).astype(int)
    
    # 2. ACD Buckets
    df_complete['ACD_Bucket'] = pd.cut(df_complete['ACD_internal'], 
                                     bins=[0, 3.1, 3.3, 10], 
                                     labels=[0, 1, 2]).astype(int)
    
    # 3. Shape Ratio Buckets (Major decision point at 62.5)
    df_complete['Shape_Bucket'] = pd.cut(df_complete['AC_shape_ratio'],
                                       bins=[0, 58, 62.5, 68, 300],
                                       labels=[0, 1, 2, 3]).astype(int)
    
    # 4. Interaction Features
    df_complete['Space_Volume'] = df_complete['WTW'] * df_complete['ACD_internal']
    df_complete['Aspect_Ratio'] = df_complete['WTW'] / df_complete['ACD_internal']
    df_complete['Power_Density'] = abs(df_complete['ICL_Power']) / df_complete['ACV']
    
    # 5. NEW ADVANCED GESTALT FEATURES
    # User Nuance: High Power + Deep ACD often means 13.7
    df_complete['High_Power_Deep_ACD'] = ((abs(df_complete['ICL_Power']) > 14) & 
                                         (df_complete['ACD_internal'] > 3.3)).astype(int)
    
    # Chamber Tightness: Volume per mm of diameter (Excellent linear progression with size)
    df_complete['Chamber_Tightness'] = df_complete['ACV'] / df_complete['WTW']
    
    # Curvature-Depth Ratio: How steep is the cornea relative to the chamber depth
    df_complete['Curvature_Depth_Ratio'] = df_complete['SimK_steep'] / df_complete['ACD_internal']
    
    # 6. ROTATIONAL & AGE GESTALT
    # Stability Risk: High astigmatism in a larger eye often gets a larger lens to prevent rotation
    df_complete['Stability_Risk'] = ((df_complete['TCRP_Astigmatism'] > 1.5) & 
                                    (df_complete['WTW'] > 12.0)).astype(int)
    
    # Age-Space Constraint: Relative space loss due to crystalline lens thickening
    df_complete['Age_Space_Ratio'] = df_complete['Age'] / df_complete['ACD_internal']
    
    # 7. NOMOGRAM FEATURE (from user sizing table)
    df_complete['Nomogram_Size'] = df_complete.apply(
        lambda row: get_nomogram_size(row['WTW'], row['ACD_internal']), axis=1
    )
    
    # 8. NOMOGRAM DEVIATION GESTALT (Learning "Conservative Sizing")
    # Rule 1: Volume Constraint - Lower size if chamber volume is tight (<170)
    df_complete['Volume_Constraint'] = ((df_complete['Nomogram_Size'] > 12.1) & 
                                       (df_complete['ACV'] < 170)).astype(int)
    
    # Rule 2: Steep Eye Adjustment - Lower size if cornea is very steep (>46D)
    df_complete['Steep_Eye_Adjustment'] = ((df_complete['Nomogram_Size'] > 12.1) & 
                                          (df_complete['SimK_steep'] > 46.0)).astype(int)
    
    # Rule 3: Safety Downsize - Tendency to drop from 13.2 to 12.6 when power is moderate
    df_complete['Safety_Downsize_Flag'] = ((df_complete['Nomogram_Size'] == 13.2) & 
                                          (abs(df_complete['ICL_Power']) < 10.0)).astype(int)
    
    # Update feature list
    feature_cols += ['WTW_Bucket', 'ACD_Bucket', 'Shape_Bucket', 
                    'Space_Volume', 'Aspect_Ratio', 'Power_Density',
                    'High_Power_Deep_ACD', 'Chamber_Tightness', 'Curvature_Depth_Ratio',
                    'Stability_Risk', 'Age_Space_Ratio', 'Nomogram_Size',
                    'Volume_Constraint', 'Steep_Eye_Adjustment', 'Safety_Downsize_Flag']
    
    # Convert Lens_Size to string for classification
    df_complete['Lens_Size'] = df_complete['Lens_Size'].astype(str)
    
    print(f"\nTotal cases: {len(df)}")
    print(f"Complete cases: {len(df_complete)}")
    print(f"Features: {len(feature_cols)}")
    
    if len(df_complete) < 20:
        print("\n⚠️  WARNING: Very small dataset. Results may not be reliable.")
    
    # Prepare features
    X = df_complete[feature_cols].copy()
    
    # Targets
    y_lens = df_complete['Lens_Size'].values
    y_vault = df_complete['Vault'].values
    
    print(f"\nFeature matrix shape: {X.shape}")
    print(f"Target distributions:")
    print(f"  Lens Size: {pd.Series(y_lens).value_counts().to_dict()}")
    print(f"  Vault: min={y_vault.min():.0f}, max={y_vault.max():.0f}, mean={y_vault.mean():.0f}")
    
    return X, y_lens, y_vault, df_complete


def train_lens_size_model(X, y):
    """Train Lens Size prediction model (classification)."""
    print("\n" + "="*70)
    print("TRAINING LENS SIZE CLASSIFIER")
    print("="*70)
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Try multiple models
    models = {
        'Random Forest': RandomForestClassifier(
            n_estimators=150, 
            max_depth=5,
            min_samples_split=5,
            class_weight='balanced',
            random_state=42
        ),
        'Gradient Boosting': GradientBoostingClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42
        )
    }
    
    # Cross-validation (5-fold)
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    
    best_model = None
    best_score = 0
    best_name = None
    
    print("\nCross-validation results:")
    for name, model in models.items():
        scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='accuracy')
        mean_score = scores.mean()
        std_score = scores.std()
        
        print(f"  {name:20s}: {mean_score:.3f} ± {std_score:.3f}")
        
        if mean_score > best_score:
            best_score = mean_score
            best_model = model
            best_name = name
    
    # Train best model on full dataset
    print(f"\nBest model: {best_name} (Accuracy: {best_score:.3f})")
    best_model.fit(X_scaled, y)
    
    # Get predictions for detailed evaluation
    y_pred = cross_val_predict(best_model, X_scaled, y, cv=cv)
    
    print("\nDetailed Classification Report:")
    print(classification_report(y, y_pred, zero_division=0))
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y, y_pred))
    
    # Feature importance (if available)
    if hasattr(best_model, 'feature_importances_'):
        print("\nTop 5 Most Important Features:")
        importances = best_model.feature_importances_
        feature_names = X.columns
        indices = np.argsort(importances)[::-1][:5]
        
        for i, idx in enumerate(indices, 1):
            print(f"  {i}. {feature_names[idx]:20s}: {importances[idx]:.4f}")
    
    return best_model, scaler, best_name, best_score


def train_vault_model(X, y):
    """Train Vault prediction model (regression)."""
    print("\n" + "="*70)
    print("TRAINING VAULT REGRESSOR")
    print("="*70)
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Try multiple models
    models = {
        'Random Forest': RandomForestRegressor(
            n_estimators=100,
            max_depth=4,
            min_samples_split=5,
            random_state=42
        ),
        'Gradient Boosting': GradientBoostingRegressor(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.1,
            random_state=42
        ),
        'Ridge Regression': Ridge(alpha=1.0)
    }
    
    # Cross-validation (5-fold)
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    
    best_model = None
    best_mae = float('inf')
    best_name = None
    
    print("\nCross-validation results (MAE = Mean Absolute Error):")
    for name, model in models.items():
        # Negative MAE because sklearn maximizes scores
        scores = cross_val_score(model, X_scaled, y, cv=cv, 
                                 scoring='neg_mean_absolute_error')
        mae = -scores.mean()
        std = scores.std()
        
        # Also get R²
        r2_scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='r2')
        r2 = r2_scores.mean()
        
        print(f"  {name:20s}: MAE={mae:.1f}µm ± {std:.1f}, R²={r2:.3f}")
        
        if mae < best_mae:
            best_mae = mae
            best_model = model
            best_name = name
    
    # Train best model on full dataset
    print(f"\nBest model: {best_name} (MAE: {best_mae:.1f}µm)")
    best_model.fit(X_scaled, y)
    
    # Get predictions for detailed evaluation
    y_pred = cross_val_predict(best_model, X_scaled, y, cv=cv)
    
    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2 = r2_score(y, y_pred)
    
    print("\nDetailed Regression Metrics:")
    print(f"  Mean Absolute Error (MAE):  {mae:.1f} µm")
    print(f"  Root Mean Squared Error:    {rmse:.1f} µm")
    print(f"  R² Score:                   {r2:.3f}")
    
    # Clinical interpretation
    print("\nClinical Interpretation:")
    within_100 = np.sum(np.abs(y - y_pred) <= 100)
    within_200 = np.sum(np.abs(y - y_pred) <= 200)
    print(f"  Within ±100µm: {within_100}/{len(y)} ({within_100/len(y)*100:.1f}%)")
    print(f"  Within ±200µm: {within_200}/{len(y)} ({within_200/len(y)*100:.1f}%)")
    
    # Feature importance (if available)
    if hasattr(best_model, 'feature_importances_'):
        print("\nTop 5 Most Important Features:")
        importances = best_model.feature_importances_
        feature_names = X.columns
        indices = np.argsort(importances)[::-1][:5]
        
        for i, idx in enumerate(indices, 1):
            print(f"  {i}. {feature_names[idx]:20s}: {importances[idx]:.4f}")
    
    return best_model, scaler, best_name, best_mae


def save_models(lens_model, lens_scaler, vault_model, vault_scaler, feature_names):
    """Save trained models and scalers."""
    print("\n" + "="*70)
    print("SAVING MODELS")
    print("="*70)
    
    models_to_save = {
        'lens_size_model.pkl': lens_model,
        'lens_size_scaler.pkl': lens_scaler,
        'vault_model.pkl': vault_model,
        'vault_scaler.pkl': vault_scaler,
        'feature_names.pkl': list(feature_names)
    }
    
    for filename, obj in models_to_save.items():
        with open(filename, 'wb') as f:
            pickle.dump(obj, f)
        print(f"  ✓ {filename}")
    
    print("\n✅ Models saved successfully!")


def main():
    """Main training pipeline."""
    print("\n" + "="*70)
    print("ICL VAULT PREDICTION - MODEL TRAINING")
    print("="*70)
    
    # Load data
    X, y_lens, y_vault, df_complete = load_and_prepare_data()
    
    if len(df_complete) == 0:
        print("\n❌ No complete training cases found!")
        return
    
    # Train Lens Size model
    lens_model, lens_scaler, lens_name, lens_score = train_lens_size_model(X, y_lens)
    
    # Train Vault model
    vault_model, vault_scaler, vault_name, vault_mae = train_vault_model(X, y_vault)
    
    # Save models
    save_models(lens_model, lens_scaler, vault_model, vault_scaler, X.columns)
    
    # Final summary
    print("\n" + "="*70)
    print("TRAINING COMPLETE - SUMMARY")
    print("="*70)
    print(f"\nDataset: {len(df_complete)} complete training cases")
    print(f"Features: {X.shape[1]} (after encoding)")
    print()
    print(f"Lens Size Model: {lens_name}")
    print(f"  → Accuracy: {lens_score:.1%}")
    print()
    print(f"Vault Model: {vault_name}")
    print(f"  → MAE: {vault_mae:.1f} µm")
    print()
    print("Models saved and ready for prediction!")
    print("\nNext steps:")
    print("  1. Use predict_icl.py to make predictions on new patients")
    print("  2. Collect more data to improve model performance")
    print("  3. Consider feature selection if adding more data")
    print("="*70)
    
    # Log performance for tracking
    save_run(
        num_cases=len(df_complete),
        lens_accuracy=lens_score,
        vault_mae=vault_mae,
        notes=f"Lens: {lens_name}, Vault: {vault_name}"
    )


if __name__ == '__main__':
    main()

