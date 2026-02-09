#!/usr/bin/env python3
"""
XGBoost + Optuna Training Script

Trains XGBoost models with Optuna hyperparameter optimization for:
1. Lens Size (classification)
2. Vault (regression)

Uses the same 24 gestalt features as the current GradientBoosting models.
Saves to models/archives/xgb-24f-756c/ without touching the live model.
"""

from pathlib import Path

import numpy as np
import optuna
import pandas as pd
import pickle
from sklearn.model_selection import cross_val_score, cross_val_predict, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from xgboost import XGBClassifier, XGBRegressor

optuna.logging.set_verbosity(optuna.logging.WARNING)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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


def engineer_gestalt_features(df):
    df = df.copy()
    df["WTW_Bucket"] = pd.cut(
        df["WTW"], bins=[0, 11.6, 11.9, 12.4, 20], labels=[0, 1, 2, 3]
    ).astype(int)
    df["ACD_Bucket"] = pd.cut(
        df["ACD_internal"], bins=[0, 3.1, 3.3, 10], labels=[0, 1, 2]
    ).astype(int)
    df["Shape_Bucket"] = pd.cut(
        df["AC_shape_ratio"], bins=[0, 58, 62.5, 68, 300], labels=[0, 1, 2, 3]
    ).astype(int)
    df["Space_Volume"] = df["WTW"] * df["ACD_internal"]
    df["Aspect_Ratio"] = df["WTW"] / df["ACD_internal"]
    df["Power_Density"] = abs(df["ICL_Power"]) / df["ACV"]
    df["High_Power_Deep_ACD"] = (
        (abs(df["ICL_Power"]) > 14) & (df["ACD_internal"] > 3.3)
    ).astype(int)
    df["Chamber_Tightness"] = df["ACV"] / df["WTW"]
    df["Curvature_Depth_Ratio"] = df["SimK_steep"] / df["ACD_internal"]
    df["Stability_Risk"] = (
        (df["TCRP_Astigmatism"] > 1.5) & (df["WTW"] > 12.0)
    ).astype(int)
    df["Age_Space_Ratio"] = df["Age"] / df["ACD_internal"]
    df["Nomogram_Size"] = df.apply(
        lambda row: get_nomogram_size(row["WTW"], row["ACD_internal"]), axis=1
    )
    df["Volume_Constraint"] = (
        (df["Nomogram_Size"] > 12.1) & (df["ACV"] < 170)
    ).astype(int)
    df["Steep_Eye_Adjustment"] = (
        (df["Nomogram_Size"] > 12.1) & (df["SimK_steep"] > 46.0)
    ).astype(int)
    df["Safety_Downsize_Flag"] = (
        (df["Nomogram_Size"] == 13.2) & (abs(df["ICL_Power"]) < 10.0)
    ).astype(int)
    return df


BASE_FEATURES = [
    "Age", "WTW", "ACD_internal", "ICL_Power", "AC_shape_ratio",
    "SimK_steep", "ACV", "TCRP_Km", "TCRP_Astigmatism",
]
GESTALT_FEATURES = [
    "WTW_Bucket", "ACD_Bucket", "Shape_Bucket",
    "Space_Volume", "Aspect_Ratio", "Power_Density",
    "High_Power_Deep_ACD", "Chamber_Tightness", "Curvature_Depth_Ratio",
    "Stability_Risk", "Age_Space_Ratio", "Nomogram_Size",
    "Volume_Constraint", "Steep_Eye_Adjustment", "Safety_Downsize_Flag",
]
ALL_FEATURES = BASE_FEATURES + GESTALT_FEATURES


def load_data():
    csv_path = PROJECT_ROOT / "data" / "processed" / "training_data.csv"
    df = pd.read_csv(csv_path)

    required_cols = [
        "Age", "WTW", "ACD_internal", "ICL_Power", "SimK_steep",
        "ACV", "TCRP_Km", "TCRP_Astigmatism", "Lens_Size", "Vault",
    ]
    df = df[df[required_cols].notna().all(axis=1)].copy()

    if "AC_shape_ratio" not in df.columns or df["AC_shape_ratio"].isna().any():
        df["AC_shape_ratio"] = df["ACV"] / df["ACD_internal"]

    df["Lens_Size"] = df["Lens_Size"].abs()
    df = df[(df["Lens_Size"] > 0) & (df["Lens_Size"] < 20)].copy()

    df = engineer_gestalt_features(df)

    X = df[ALL_FEATURES].copy()
    y_lens = df["Lens_Size"].astype(str).values
    y_vault = df["Vault"].values

    print(f"Training data: {len(df)} complete cases, {len(ALL_FEATURES)} features")
    print(f"Lens sizes: {pd.Series(y_lens).value_counts().to_dict()}")
    print(f"Vault: min={y_vault.min():.0f}, max={y_vault.max():.0f}, mean={y_vault.mean():.0f}um")
    return X, y_lens, y_vault


def tune_lens_classifier(X_scaled, y, cv):
    classes = sorted(set(y))
    label_map = {c: i for i, c in enumerate(classes)}
    y_int = np.array([label_map[c] for c in y])

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 500),
            "max_depth": trial.suggest_int("max_depth", 2, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0.0, 5.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        }
        model = XGBClassifier(
            **params, objective="multi:softprob", num_class=len(classes),
            random_state=42, verbosity=0, n_jobs=-1,
        )
        scores = cross_val_score(model, X_scaled, y_int, cv=cv, scoring="accuracy")
        return scores.mean()

    study = optuna.create_study(direction="maximize", study_name="lens_xgb")
    study.optimize(objective, n_trials=100, show_progress_bar=True)

    print(f"  Best lens accuracy: {study.best_value:.4f}")
    print(f"  Best params: {study.best_params}")

    best_model = XGBClassifier(
        **study.best_params, objective="multi:softprob", num_class=len(classes),
        random_state=42, verbosity=0, n_jobs=-1,
    )
    best_model.fit(X_scaled, y_int)
    best_model._vault_classes = np.array(classes, dtype=float)

    return best_model, study.best_value, study.best_params


def tune_vault_regressor(X_scaled, y, cv):
    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 500),
            "max_depth": trial.suggest_int("max_depth", 2, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0.0, 5.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        }
        model = XGBRegressor(
            **params, objective="reg:squarederror",
            random_state=42, verbosity=0, n_jobs=-1,
        )
        scores = cross_val_score(
            model, X_scaled, y, cv=cv, scoring="neg_mean_absolute_error"
        )
        return scores.mean()

    study = optuna.create_study(direction="maximize", study_name="vault_xgb")
    study.optimize(objective, n_trials=100, show_progress_bar=True)

    best_mae = -study.best_value
    print(f"  Best vault MAE: {best_mae:.1f}um")
    print(f"  Best params: {study.best_params}")

    best_model = XGBRegressor(
        **study.best_params, objective="reg:squarederror",
        random_state=42, verbosity=0, n_jobs=-1,
    )
    best_model.fit(X_scaled, y)

    return best_model, best_mae, study.best_params


def main():
    print("=" * 70)
    print("XGBoost + Optuna Training")
    print("=" * 70)

    X, y_lens, y_vault = load_data()
    cv = KFold(n_splits=5, shuffle=True, random_state=42)

    lens_scaler = StandardScaler()
    X_lens_scaled = lens_scaler.fit_transform(X)

    vault_scaler = StandardScaler()
    X_vault_scaled = vault_scaler.fit_transform(X)

    # --- Lens Size ---
    print()
    print("=" * 70)
    print("TUNING LENS SIZE CLASSIFIER (100 Optuna trials)")
    print("=" * 70)
    lens_model, lens_acc, lens_params = tune_lens_classifier(X_lens_scaled, y_lens, cv)

    # Detailed eval
    classes = sorted(set(y_lens))
    label_map = {c: i for i, c in enumerate(classes)}
    y_lens_int = np.array([label_map[c] for c in y_lens])
    y_pred_lens = cross_val_predict(
        XGBClassifier(
            **lens_params, objective="multi:softprob", num_class=len(classes),
            random_state=42, verbosity=0, n_jobs=-1,
        ),
        X_lens_scaled, y_lens_int, cv=cv,
    )
    y_pred_labels = [classes[i] for i in y_pred_lens]
    print()
    print("Classification Report:")
    print(classification_report(y_lens, y_pred_labels, zero_division=0))

    # --- Vault ---
    print()
    print("=" * 70)
    print("TUNING VAULT REGRESSOR (100 Optuna trials)")
    print("=" * 70)
    vault_model, vault_mae, vault_params = tune_vault_regressor(X_vault_scaled, y_vault, cv)

    # Detailed eval
    y_pred_vault = cross_val_predict(
        XGBRegressor(
            **vault_params, objective="reg:squarederror",
            random_state=42, verbosity=0, n_jobs=-1,
        ),
        X_vault_scaled, y_vault, cv=cv,
    )
    rmse = np.sqrt(mean_squared_error(y_vault, y_pred_vault))
    r2 = r2_score(y_vault, y_pred_vault)
    within_100 = np.sum(np.abs(y_vault - y_pred_vault) <= 100)
    within_200 = np.sum(np.abs(y_vault - y_pred_vault) <= 200)

    print()
    print("Detailed Vault Metrics:")
    print(f"  MAE:  {vault_mae:.1f}um")
    print(f"  RMSE: {rmse:.1f}um")
    print(f"  R2:   {r2:.3f}")
    print(f"  Within +/-100um: {within_100}/{len(y_vault)} ({within_100/len(y_vault)*100:.1f}%)")
    print(f"  Within +/-200um: {within_200}/{len(y_vault)} ({within_200/len(y_vault)*100:.1f}%)")

    # --- Save ---
    out_dir = PROJECT_ROOT / "models" / "archives" / "xgb-24f-756c"
    out_dir.mkdir(parents=True, exist_ok=True)

    artifacts = {
        "lens_size_model.pkl": lens_model,
        "lens_size_scaler.pkl": lens_scaler,
        "vault_model.pkl": vault_model,
        "vault_scaler.pkl": vault_scaler,
        "feature_names.pkl": list(X.columns),
    }
    for fname, obj in artifacts.items():
        with open(out_dir / fname, "wb") as f:
            pickle.dump(obj, f)
        print(f"  Saved {fname}")

    # README
    readme_text = (
        "# xgb-24f-756c\n\n"
        "XGBoost model with Optuna hyperparameter tuning.\n\n"
        "## Summary\n"
        f"- **Algorithm**: XGBoost (Classifier + Regressor)\n"
        f"- **Features**: 24 (9 base + 15 gestalts)\n"
        f"- **Training cases**: {len(y_lens)}\n"
        f"- **Lens accuracy**: {lens_acc:.1%} (5-fold CV)\n"
        f"- **Vault MAE**: {vault_mae:.1f}um (5-fold CV)\n"
        f"- **Tuning**: Optuna, 100 trials per model\n"
    )
    (out_dir / "README.md").write_text(readme_text)

    # --- Summary ---
    print()
    print("=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)
    print(f"  Cases:         {len(y_lens)}")
    print(f"  Features:      {len(ALL_FEATURES)}")
    print(f"  Lens Accuracy: {lens_acc:.1%}")
    print(f"  Vault MAE:     {vault_mae:.1f}um")
    print(f"  Saved to:      {out_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()