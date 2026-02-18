#!/usr/bin/env python3
"""
Train gestalt-18f-756c — No-ACV fallback model.

Same architecture as gestalt-24f-756c (GradientBoosting) but trained
WITHOUT the 6 features that depend on ACV:
  Dropped: ACV, AC_shape_ratio, Shape_Bucket, Power_Density,
           Chamber_Tightness, Volume_Constraint

Kept: 7 base + 11 gestalt = 18 features.

Purpose: Compare page only — lets surgeons see predictions when their
Pentacam INI is missing ACV (common on SW v1.30 and earlier).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pickle
from sklearn.model_selection import cross_val_score, cross_val_predict, KFold
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
import warnings

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "training_data.csv"
ARCHIVE_DIR = PROJECT_ROOT / "models" / "archives" / "gestalt-18f-756c"

BASE_FEATURES = [
    "Age", "WTW", "ACD_internal", "ICL_Power",
    "SimK_steep", "TCRP_Km", "TCRP_Astigmatism",
]

ACV_DEPENDENT = {
    "ACV", "AC_shape_ratio", "Shape_Bucket",
    "Power_Density", "Chamber_Tightness", "Volume_Constraint",
}


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


def load_and_prepare():
    print("=" * 70)
    print("LOADING TRAINING DATA (No-ACV variant)")
    print("=" * 70)

    df = pd.read_csv(DATA_PATH)

    # Still require all 9 base features for training (we have ACV in training data,
    # we just don't use it as a feature)
    all_base = BASE_FEATURES + ["ACV", "AC_shape_ratio"]
    target_cols = ["Lens_Size", "Vault"]
    complete = df[all_base + target_cols].notna().all(axis=1)
    df_c = df[complete].copy()

    df_c["Lens_Size"] = df_c["Lens_Size"].abs()
    df_c = df_c[(df_c["Lens_Size"] > 0) & (df_c["Lens_Size"] < 20)].copy()

    # ── Engineer ALL gestalt features (same as production) ──
    df_c["WTW_Bucket"] = pd.cut(
        df_c["WTW"], bins=[0, 11.6, 11.9, 12.4, 20], labels=[0, 1, 2, 3]
    ).astype(int)
    df_c["ACD_Bucket"] = pd.cut(
        df_c["ACD_internal"], bins=[0, 3.1, 3.3, 10], labels=[0, 1, 2]
    ).astype(int)
    df_c["Shape_Bucket"] = pd.cut(
        df_c["AC_shape_ratio"], bins=[0, 58, 62.5, 68, 300], labels=[0, 1, 2, 3]
    ).astype(int)

    df_c["Space_Volume"] = df_c["WTW"] * df_c["ACD_internal"]
    df_c["Aspect_Ratio"] = df_c["WTW"] / df_c["ACD_internal"]
    df_c["Power_Density"] = abs(df_c["ICL_Power"]) / df_c["ACV"]

    df_c["High_Power_Deep_ACD"] = (
        (abs(df_c["ICL_Power"]) > 14) & (df_c["ACD_internal"] > 3.3)
    ).astype(int)
    df_c["Chamber_Tightness"] = df_c["ACV"] / df_c["WTW"]
    df_c["Curvature_Depth_Ratio"] = df_c["SimK_steep"] / df_c["ACD_internal"]

    df_c["Stability_Risk"] = (
        (df_c["TCRP_Astigmatism"] > 1.5) & (df_c["WTW"] > 12.0)
    ).astype(int)
    df_c["Age_Space_Ratio"] = df_c["Age"] / df_c["ACD_internal"]

    df_c["Nomogram_Size"] = df_c.apply(
        lambda r: get_nomogram_size(r["WTW"], r["ACD_internal"]), axis=1
    )
    df_c["Volume_Constraint"] = (
        (df_c["Nomogram_Size"] > 12.1) & (df_c["ACV"] < 170)
    ).astype(int)
    df_c["Steep_Eye_Adjustment"] = (
        (df_c["Nomogram_Size"] > 12.1) & (df_c["SimK_steep"] > 46.0)
    ).astype(int)
    df_c["Safety_Downsize_Flag"] = (
        (df_c["Nomogram_Size"] == 13.2) & (abs(df_c["ICL_Power"]) < 10.0)
    ).astype(int)

    # ── Build feature list: 24f minus the 6 ACV-dependent ones = 18 ──
    all_24 = BASE_FEATURES + ["ACV", "AC_shape_ratio"] + [
        "WTW_Bucket", "ACD_Bucket", "Shape_Bucket",
        "Space_Volume", "Aspect_Ratio", "Power_Density",
        "High_Power_Deep_ACD", "Chamber_Tightness", "Curvature_Depth_Ratio",
        "Stability_Risk", "Age_Space_Ratio", "Nomogram_Size",
        "Volume_Constraint", "Steep_Eye_Adjustment", "Safety_Downsize_Flag",
    ]
    feature_cols = [f for f in all_24 if f not in ACV_DEPENDENT]

    df_c["Lens_Size"] = df_c["Lens_Size"].astype(str)

    X = df_c[feature_cols].copy()
    y_lens = df_c["Lens_Size"].values
    y_vault = df_c["Vault"].values

    print(f"\nTotal cases: {len(df)}")
    print(f"Complete cases: {len(df_c)}")
    print(f"Features: {len(feature_cols)} (dropped {len(ACV_DEPENDENT)} ACV-dependent)")
    print(f"Dropped: {sorted(ACV_DEPENDENT)}")
    print(f"\nFeature list: {list(X.columns)}")
    print(f"Target distributions:")
    print(f"  Lens Size: {pd.Series(y_lens).value_counts().to_dict()}")
    print(f"  Vault: min={y_vault.min():.0f}, max={y_vault.max():.0f}, mean={y_vault.mean():.0f}")

    return X, y_lens, y_vault, df_c


def train_lens(X, y):
    print("\n" + "=" * 70)
    print("TRAINING LENS SIZE CLASSIFIER (No-ACV)")
    print("=" * 70)

    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)
    cv = KFold(n_splits=5, shuffle=True, random_state=42)

    models = {
        "Random Forest": RandomForestClassifier(
            n_estimators=150, max_depth=5, min_samples_split=5,
            class_weight="balanced", random_state=42,
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=150, max_depth=4, learning_rate=0.05,
            subsample=0.8, random_state=42,
        ),
    }

    best_model, best_score, best_name = None, 0, None
    print("\nCross-validation results:")
    for name, model in models.items():
        scores = cross_val_score(model, X_s, y, cv=cv, scoring="accuracy")
        m = scores.mean()
        print(f"  {name:20s}: {m:.3f} ± {scores.std():.3f}")
        if m > best_score:
            best_score, best_model, best_name = m, model, name

    print(f"\nBest: {best_name} ({best_score:.3f})")
    best_model.fit(X_s, y)

    y_pred = cross_val_predict(best_model, X_s, y, cv=cv)
    print("\nClassification Report:")
    print(classification_report(y, y_pred, zero_division=0))
    print("Confusion Matrix:")
    print(confusion_matrix(y, y_pred))

    if hasattr(best_model, "feature_importances_"):
        print("\nTop 10 Features:")
        imp = best_model.feature_importances_
        for i, idx in enumerate(np.argsort(imp)[::-1][:10], 1):
            print(f"  {i:2d}. {X.columns[idx]:25s}: {imp[idx]:.4f}")

    return best_model, scaler, best_name, best_score


def train_vault(X, y):
    print("\n" + "=" * 70)
    print("TRAINING VAULT REGRESSOR (No-ACV)")
    print("=" * 70)

    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)
    cv = KFold(n_splits=5, shuffle=True, random_state=42)

    models = {
        "Random Forest": RandomForestRegressor(
            n_estimators=100, max_depth=4, min_samples_split=5, random_state=42,
        ),
        "Gradient Boosting": GradientBoostingRegressor(
            n_estimators=50, max_depth=3, learning_rate=0.1, random_state=42,
        ),
        "Ridge": Ridge(alpha=1.0),
    }

    best_model, best_mae, best_name = None, float("inf"), None
    print("\nCross-validation results:")
    for name, model in models.items():
        scores = cross_val_score(model, X_s, y, cv=cv, scoring="neg_mean_absolute_error")
        mae = -scores.mean()
        r2 = cross_val_score(model, X_s, y, cv=cv, scoring="r2").mean()
        print(f"  {name:20s}: MAE={mae:.1f}µm, R²={r2:.3f}")
        if mae < best_mae:
            best_mae, best_model, best_name = mae, model, name

    print(f"\nBest: {best_name} (MAE: {best_mae:.1f}µm)")
    best_model.fit(X_s, y)

    y_pred = cross_val_predict(best_model, X_s, y, cv=cv)
    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2 = r2_score(y, y_pred)
    print(f"\n  MAE:  {mae:.1f} µm")
    print(f"  RMSE: {rmse:.1f} µm")
    print(f"  R²:   {r2:.3f}")

    within_100 = np.sum(np.abs(y - y_pred) <= 100)
    within_200 = np.sum(np.abs(y - y_pred) <= 200)
    print(f"\n  Within ±100µm: {within_100}/{len(y)} ({within_100/len(y)*100:.1f}%)")
    print(f"  Within ±200µm: {within_200}/{len(y)} ({within_200/len(y)*100:.1f}%)")

    if hasattr(best_model, "feature_importances_"):
        print("\nTop 10 Features:")
        imp = best_model.feature_importances_
        for i, idx in enumerate(np.argsort(imp)[::-1][:10], 1):
            print(f"  {i:2d}. {X.columns[idx]:25s}: {imp[idx]:.4f}")

    return best_model, scaler, best_name, best_mae


def main():
    print("\n" + "=" * 70)
    print("TRAINING: gestalt-18f-756c (No-ACV fallback)")
    print("=" * 70)

    X, y_lens, y_vault, df_c = load_and_prepare()
    if len(df_c) == 0:
        print("\nNo complete training cases!")
        return

    lens_model, lens_scaler, lens_name, lens_acc = train_lens(X, y_lens)
    vault_model, vault_scaler, vault_name, vault_mae = train_vault(X, y_vault)

    # Save to archive
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    pkls = {
        "lens_size_model.pkl": lens_model,
        "lens_size_scaler.pkl": lens_scaler,
        "vault_model.pkl": vault_model,
        "vault_scaler.pkl": vault_scaler,
        "feature_names.pkl": list(X.columns),
    }
    for fname, obj in pkls.items():
        with (ARCHIVE_DIR / fname).open("wb") as f:
            pickle.dump(obj, f)
        print(f"  ✓ {fname}")

    # Write README
    readme = f"""# gestalt-18f-756c

No-ACV fallback model. Same architecture as gestalt-24f-756c but trained WITHOUT the 6 features that depend on ACV. For compare page evaluation only — not used in production routing.

- **Algorithm:** {lens_name} (lens) + {vault_name} (vault)
- **Features:** 18 (7 base + 11 gestalt, no ACV-dependent features)
- **Training cases:** {len(df_c)}
- **Lens accuracy (CV):** {lens_acc:.1%}
- **Vault MAE (CV):** {vault_mae:.1f} µm
- **Date:** 2026-02-18

## Dropped Features (ACV-dependent)
- ACV
- AC_shape_ratio
- Shape_Bucket
- Power_Density
- Chamber_Tightness
- Volume_Constraint

## Kept Features ({len(X.columns)})
{chr(10).join(f"- {c}" for c in X.columns)}

## Parent
gestalt-24f-756c (same hyperparameters, fewer features)
"""
    (ARCHIVE_DIR / "README.md").write_text(readme)
    print(f"  ✓ README.md")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
    print(f"  Archive: {ARCHIVE_DIR}")
    print(f"  Lens accuracy: {lens_acc:.1%} (vs 73.2% with ACV)")
    print(f"  Vault MAE: {vault_mae:.1f}µm (vs 128.3µm with ACV)")
    print(f"  Features: {len(X.columns)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
