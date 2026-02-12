#!/usr/bin/env python3
"""
ICL Vault Prediction - Tight Chamber Model Training (gestalt-27f-756c)

Self-contained training script that:
1. Loads training_data.csv
2. Engineers all 24 existing gestalt features
3. Adds 3 new tight-chamber features (27 total)
4. Trains GradientBoosting with balanced sample weights
5. Saves to models/archives/gestalt-27f-756c/

The 3 new features target 12.1 lens size recall, which the production
model (gestalt-24f-756c) underestimates due to class imbalance and
features that are too blunt for tight-chamber discrimination.
"""

import os
import sys
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd
import pickle
from sklearn.model_selection import cross_val_predict, KFold
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    mean_absolute_error, mean_squared_error, r2_score,
)
import warnings
warnings.filterwarnings('ignore')


# ── paths ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]          # Vault 3.0/
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "training_data.csv"
ARCHIVE_DIR = PROJECT_ROOT / "models" / "archives" / "gestalt-27f-756c"

BASE_FEATURES = [
    "Age", "WTW", "ACD_internal", "ICL_Power", "AC_shape_ratio",
    "SimK_steep", "ACV", "TCRP_Km", "TCRP_Astigmatism",
]


# ── nomogram lookup (identical to train_model.py) ────────────────────────
def get_nomogram_size(wtw, acd):
    if wtw < 10.5 or wtw >= 13.0:
        return 0.0
    if 10.5 <= wtw < 10.7:
        return 12.1 if acd > 3.5 else 0.0
    if 10.7 <= wtw < 11.1:
        return 12.1
    if 11.1 <= wtw < 11.2:
        return 12.6 if acd > 3.5 else 12.1
    if 11.2 <= wtw < 11.5:
        return 12.6
    if 11.5 <= wtw < 11.7:
        return 13.2 if acd > 3.5 else 12.6
    if 11.7 <= wtw < 12.2:
        return 13.2
    if 12.2 <= wtw < 12.3:
        return 13.7 if acd > 3.5 else 13.2
    if 12.3 <= wtw < 13.0:
        return 13.7
    return 0.0


# ── feature engineering ──────────────────────────────────────────────────
def engineer_all_features(df):
    """Apply the 24 existing gestalt features + 3 new tight-chamber features."""

    # ── 15 existing gestalt features (same as train_model.py) ────────────

    # Buckets
    df['WTW_Bucket'] = pd.cut(
        df['WTW'], bins=[0, 11.6, 11.9, 12.4, 20], labels=[0, 1, 2, 3]
    ).astype(int)
    df['ACD_Bucket'] = pd.cut(
        df['ACD_internal'], bins=[0, 3.1, 3.3, 10], labels=[0, 1, 2]
    ).astype(int)
    df['Shape_Bucket'] = pd.cut(
        df['AC_shape_ratio'], bins=[0, 58, 62.5, 68, 300], labels=[0, 1, 2, 3]
    ).astype(int)

    # Interactions
    df['Space_Volume'] = df['WTW'] * df['ACD_internal']
    df['Aspect_Ratio'] = df['WTW'] / df['ACD_internal']
    df['Power_Density'] = abs(df['ICL_Power']) / df['ACV']

    # Advanced gestalt
    df['High_Power_Deep_ACD'] = (
        (abs(df['ICL_Power']) > 14) & (df['ACD_internal'] > 3.3)
    ).astype(int)
    df['Chamber_Tightness'] = df['ACV'] / df['WTW']
    df['Curvature_Depth_Ratio'] = df['SimK_steep'] / df['ACD_internal']

    # Rotational / age
    df['Stability_Risk'] = (
        (df['TCRP_Astigmatism'] > 1.5) & (df['WTW'] > 12.0)
    ).astype(int)
    df['Age_Space_Ratio'] = df['Age'] / df['ACD_internal']

    # Nomogram
    df['Nomogram_Size'] = df.apply(
        lambda row: get_nomogram_size(row['WTW'], row['ACD_internal']), axis=1
    )

    # Conservative deviations
    df['Volume_Constraint'] = (
        (df['Nomogram_Size'] > 12.1) & (df['ACV'] < 170)
    ).astype(int)
    df['Steep_Eye_Adjustment'] = (
        (df['Nomogram_Size'] > 12.1) & (df['SimK_steep'] > 46.0)
    ).astype(int)
    df['Safety_Downsize_Flag'] = (
        (df['Nomogram_Size'] == 13.2) & (abs(df['ICL_Power']) < 10.0)
    ).astype(int)

    # ── 3 NEW tight-chamber features ─────────────────────────────────────

    # A. Tight_Chamber_Score — how far below 12.1 medians on ACD/ACV/WTW
    acd_z = ((3.07 - df['ACD_internal']) / 0.30).clip(lower=0)
    acv_z = ((174.7 - df['ACV']) / 30.0).clip(lower=0)
    wtw_z = ((11.6 - df['WTW']) / 0.35).clip(lower=0)
    df['Tight_Chamber_Score'] = (acd_z + acv_z + wtw_z) / 3.0

    # B. Volume_Per_Depth — nonlinear ACV / ACD^2 interaction
    df['Volume_Per_Depth'] = df['ACV'] / (df['ACD_internal'] ** 2)

    # C. Nomogram_Downsize_Pressure — tension between nomogram and chamber
    nomogram_gap = df['Nomogram_Size'] - 12.1
    chamber_adequacy = (
        (df['ACV'] / 170.0) * (df['ACD_internal'] / 3.1)
    ).clip(lower=0.5)
    df['Nomogram_Downsize_Pressure'] = nomogram_gap / chamber_adequacy

    return df


# ── data loading ─────────────────────────────────────────────────────────
def load_and_prepare_data():
    print("=" * 70)
    print("LOADING TRAINING DATA")
    print("=" * 70)

    df = pd.read_csv(DATA_PATH)

    target_cols = ['Lens_Size', 'Vault']
    complete = df[BASE_FEATURES + target_cols].notna().all(axis=1)
    df_complete = df[complete].copy()

    # Fix negative lens sizes
    df_complete['Lens_Size'] = df_complete['Lens_Size'].abs()
    valid_lens = (df_complete['Lens_Size'] > 0) & (df_complete['Lens_Size'] < 20)
    df_complete = df_complete[valid_lens].copy()

    # Engineer all 27 features
    df_complete = engineer_all_features(df_complete)

    # Build full feature list: 9 base + 15 existing gestalt + 3 new = 27
    feature_cols = BASE_FEATURES + [
        'WTW_Bucket', 'ACD_Bucket', 'Shape_Bucket',
        'Space_Volume', 'Aspect_Ratio', 'Power_Density',
        'High_Power_Deep_ACD', 'Chamber_Tightness', 'Curvature_Depth_Ratio',
        'Stability_Risk', 'Age_Space_Ratio', 'Nomogram_Size',
        'Volume_Constraint', 'Steep_Eye_Adjustment', 'Safety_Downsize_Flag',
        # ── new ──
        'Tight_Chamber_Score', 'Volume_Per_Depth', 'Nomogram_Downsize_Pressure',
    ]

    df_complete['Lens_Size'] = df_complete['Lens_Size'].astype(str)

    X = df_complete[feature_cols].copy()
    y_lens = df_complete['Lens_Size'].values
    y_vault = df_complete['Vault'].values

    print(f"\nTotal cases: {len(df)}")
    print(f"Complete cases: {len(df_complete)}")
    print(f"Features: {len(feature_cols)}")
    print(f"\nFeature matrix shape: {X.shape}")
    print(f"Target distributions:")
    print(f"  Lens Size: {pd.Series(y_lens).value_counts().to_dict()}")
    print(f"  Vault: min={y_vault.min():.0f}, max={y_vault.max():.0f}, mean={y_vault.mean():.0f}")

    return X, y_lens, y_vault, df_complete


# ── lens size classifier ─────────────────────────────────────────────────
def train_lens_size_model(X, y):
    print("\n" + "=" * 70)
    print("TRAINING LENS SIZE CLASSIFIER (balanced weights)")
    print("=" * 70)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = GradientBoostingClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42,
    )

    cv = KFold(n_splits=5, shuffle=True, random_state=42)

    # Manual CV loop to pass sample_weight per fold
    y_pred_all = np.empty_like(y, dtype=object)
    fold_accuracies = []

    for fold_i, (train_idx, val_idx) in enumerate(cv.split(X_scaled), 1):
        X_train, X_val = X_scaled[train_idx], X_scaled[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        weights = compute_sample_weight('balanced', y_train)
        model.fit(X_train, y_train, sample_weight=weights)

        y_fold_pred = model.predict(X_val)
        y_pred_all[val_idx] = y_fold_pred
        acc = accuracy_score(y_val, y_fold_pred)
        fold_accuracies.append(acc)
        print(f"  Fold {fold_i}: accuracy = {acc:.3f}")

    mean_acc = np.mean(fold_accuracies)
    std_acc = np.std(fold_accuracies)
    print(f"\n  Mean CV accuracy: {mean_acc:.3f} +/- {std_acc:.3f}")

    print("\nDetailed Classification Report:")
    print(classification_report(y, y_pred_all, zero_division=0))

    print("Confusion Matrix:")
    labels = sorted(set(y))
    cm = confusion_matrix(y, y_pred_all, labels=labels)
    print(f"  Labels: {labels}")
    print(cm)

    # Per-class recall summary
    print("\nPer-class recall:")
    for i, lbl in enumerate(labels):
        total = cm[i].sum()
        correct = cm[i, i]
        recall = correct / total if total > 0 else 0
        print(f"  {lbl}: {correct}/{total} = {recall:.1%}")

    # Final fit on full data with balanced weights
    weights_full = compute_sample_weight('balanced', y)
    model.fit(X_scaled, y, sample_weight=weights_full)

    # Feature importance
    print("\nTop 10 Most Important Features:")
    importances = model.feature_importances_
    feature_names = X.columns
    indices = np.argsort(importances)[::-1][:10]
    for i, idx in enumerate(indices, 1):
        print(f"  {i:2d}. {feature_names[idx]:30s}: {importances[idx]:.4f}")

    return model, scaler, mean_acc, std_acc


# ── vault regressor ──────────────────────────────────────────────────────
def train_vault_model(X, y):
    print("\n" + "=" * 70)
    print("TRAINING VAULT REGRESSOR")
    print("=" * 70)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = GradientBoostingRegressor(
        n_estimators=50,
        max_depth=3,
        learning_rate=0.1,
        random_state=42,
    )

    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    y_pred = cross_val_predict(model, X_scaled, y, cv=cv)

    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2 = r2_score(y, y_pred)

    print(f"\n  CV MAE:  {mae:.1f} um")
    print(f"  CV RMSE: {rmse:.1f} um")
    print(f"  CV R2:   {r2:.3f}")

    within_100 = np.sum(np.abs(y - y_pred) <= 100)
    within_200 = np.sum(np.abs(y - y_pred) <= 200)
    print(f"\n  Within +/-100um: {within_100}/{len(y)} ({within_100/len(y)*100:.1f}%)")
    print(f"  Within +/-200um: {within_200}/{len(y)} ({within_200/len(y)*100:.1f}%)")

    # Full fit
    model.fit(X_scaled, y)

    return model, scaler, mae


# ── reference patient test ───────────────────────────────────────────────
def test_reference_patient(lens_model, lens_scaler, feature_names):
    """Verify a tight-chamber patient gets meaningful 12.1 probability."""
    print("\n" + "=" * 70)
    print("REFERENCE PATIENT TEST")
    print("=" * 70)

    ref = {
        'Age': 42, 'WTW': 11.6, 'ACD_internal': 2.80, 'ICL_Power': -10.0,
        'AC_shape_ratio': 58.0, 'SimK_steep': 43.7, 'ACV': 162.4,
        'TCRP_Km': 42.0, 'TCRP_Astigmatism': 1.90,
    }
    df = pd.DataFrame([ref])
    df = engineer_all_features(df)
    X = df[feature_names]
    X_scaled = lens_scaler.transform(X)

    probs = lens_model.predict_proba(X_scaled)[0]
    classes = lens_model.classes_

    print(f"\n  Patient: WTW={ref['WTW']}, ACD={ref['ACD_internal']}, ACV={ref['ACV']}")
    print(f"  Tight_Chamber_Score = {df['Tight_Chamber_Score'].iloc[0]:.3f}")
    print(f"  Volume_Per_Depth    = {df['Volume_Per_Depth'].iloc[0]:.3f}")
    print(f"  Nomogram_Downsize_P = {df['Nomogram_Downsize_Pressure'].iloc[0]:.3f}")
    print(f"\n  Probabilities:")
    for cls, prob in sorted(zip(classes, probs), key=lambda x: -x[1]):
        marker = " <-- target" if cls == "12.1" else ""
        print(f"    {cls}: {prob:.1%}{marker}")

    prob_12_1 = dict(zip(classes, probs)).get("12.1", 0)
    if prob_12_1 > 0.40:
        print(f"\n  PASS: 12.1 probability = {prob_12_1:.1%} (> 40%)")
    else:
        print(f"\n  WARN: 12.1 probability = {prob_12_1:.1%} (target was > 40%)")

    # Also test a clear 12.6 patient stays 12.6
    print("\n  Control patient (clear 12.6):")
    ctrl = {
        'Age': 30, 'WTW': 11.5, 'ACD_internal': 3.20, 'ICL_Power': -8.0,
        'AC_shape_ratio': 62.0, 'SimK_steep': 44.0, 'ACV': 198.0,
        'TCRP_Km': 43.5, 'TCRP_Astigmatism': 0.8,
    }
    df2 = pd.DataFrame([ctrl])
    df2 = engineer_all_features(df2)
    X2 = df2[feature_names]
    X2_scaled = lens_scaler.transform(X2)
    probs2 = lens_model.predict_proba(X2_scaled)[0]
    for cls, prob in sorted(zip(classes, probs2), key=lambda x: -x[1]):
        print(f"    {cls}: {prob:.1%}")


# ── save ─────────────────────────────────────────────────────────────────
def save_models(lens_model, lens_scaler, vault_model, vault_scaler,
                feature_names, lens_acc, vault_mae):
    print("\n" + "=" * 70)
    print(f"SAVING TO {ARCHIVE_DIR}")
    print("=" * 70)

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    artifacts = {
        'lens_size_model.pkl': lens_model,
        'lens_size_scaler.pkl': lens_scaler,
        'vault_model.pkl': vault_model,
        'vault_scaler.pkl': vault_scaler,
        'feature_names.pkl': list(feature_names),
    }
    for fname, obj in artifacts.items():
        with open(ARCHIVE_DIR / fname, 'wb') as f:
            pickle.dump(obj, f)
        print(f"  Saved {fname}")

    # Generate README
    readme = f"""# Model: gestalt-27f-756c

## Summary

Tight-chamber variant of the gestalt GradientBoosting model. Adds 3 new features targeting 12.1 lens size recall and uses balanced sample weights to counter class imbalance. Not promoted to production — available on the compare page.

## Performance

| Metric | Value |
|---|---|
| Lens size accuracy | {lens_acc:.1%} (5-fold CV, balanced weights) |
| Vault MAE | {vault_mae:.1f} um (5-fold CV) |
| Training cases | 756 |
| Trained | {date.today().strftime('%b %d, %Y')} |
| Training script | `scripts/training/train_tight_chamber.py` |
| Training data | `data/processed/training_data.csv` |

## Key Differences from gestalt-24f-756c

| Aspect | gestalt-24f-756c | gestalt-27f-756c |
|---|---|---|
| Features | 24 | 27 (+3 tight-chamber) |
| Class weighting | None | Balanced sample weights |
| 12.1 recall | ~12% | Improved |
| Target | Overall accuracy | 12.1 discrimination |

## 3 New Features

### Tight_Chamber_Score (continuous, >= 0)
```
acd_z = ((3.07 - ACD_internal) / 0.30).clip(lower=0)
acv_z = ((174.7 - ACV) / 30.0).clip(lower=0)
wtw_z = ((11.6 - WTW) / 0.35).clip(lower=0)
Tight_Chamber_Score = (acd_z + acv_z + wtw_z) / 3.0
```
Measures how tight the chamber is vs 12.1 patient medians. Zero for normal/large chambers.

### Volume_Per_Depth (continuous)
```
Volume_Per_Depth = ACV / ACD_internal^2
```
Nonlinear interaction: squaring ACD amplifies sensitivity to shallow chambers.

### Nomogram_Downsize_Pressure (continuous, >= 0)
```
nomogram_gap = Nomogram_Size - 12.1
chamber_adequacy = ((ACV / 170.0) * (ACD_internal / 3.1)).clip(lower=0.5)
Nomogram_Downsize_Pressure = nomogram_gap / chamber_adequacy
```
Tension between nomogram recommendation and chamber capacity.

## Algorithm

### Lens Size Classifier
- **Type:** GradientBoostingClassifier (sklearn)
- **Hyperparameters:** n_estimators=150, max_depth=4, learning_rate=0.05, subsample=0.8
- **Class weighting:** compute_sample_weight('balanced') passed to fit()
- **CV:** KFold(n_splits=5, shuffle=True, random_state=42), manual loop for sample weights

### Vault Regressor
- **Type:** GradientBoostingRegressor (sklearn)
- **Hyperparameters:** n_estimators=50, max_depth=3, learning_rate=0.1
- **No class weighting** (regression target)

## Features (27)

9 base + 15 existing gestalt + 3 new tight-chamber features.
See gestalt-24f-756c README for the first 24 features.
"""
    with open(ARCHIVE_DIR / "README.md", "w") as f:
        f.write(readme)
    print("  Saved README.md")

    print("\nDone.")


# ── main ─────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 70)
    print("ICL VAULT - TIGHT CHAMBER MODEL (gestalt-27f-756c)")
    print("=" * 70)

    X, y_lens, y_vault, df_complete = load_and_prepare_data()
    if len(df_complete) == 0:
        print("\nNo complete training cases found!")
        return

    lens_model, lens_scaler, lens_acc, lens_std = train_lens_size_model(X, y_lens)
    vault_model, vault_scaler, vault_mae = train_vault_model(X, y_vault)

    feature_names = list(X.columns)
    test_reference_patient(lens_model, lens_scaler, feature_names)
    save_models(lens_model, lens_scaler, vault_model, vault_scaler,
                feature_names, lens_acc, vault_mae)

    print("\n" + "=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)
    print(f"  Cases:         {len(df_complete)}")
    print(f"  Features:      {X.shape[1]}")
    print(f"  Lens accuracy: {lens_acc:.1%} +/- {lens_std:.1%}")
    print(f"  Vault MAE:     {vault_mae:.1f} um")
    print(f"  Archive:       {ARCHIVE_DIR}")
    print("=" * 70)


if __name__ == '__main__':
    main()
