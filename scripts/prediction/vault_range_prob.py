#!/usr/bin/env python3
"""
Estimate P(vault in [low, high]) using current model residuals.

This is a post-hoc probability estimate that does not retrain the model.
It assumes residuals are approximately normal and uses their standard deviation.
"""

import argparse
import math
import pickle

import numpy as np
import pandas as pd


def normal_cdf(x: float, mu: float, sigma: float) -> float:
    if sigma <= 0:
        return 0.0
    z = (x - mu) / (sigma * math.sqrt(2.0))
    return 0.5 * (1.0 + math.erf(z))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Estimate probability that vault falls within a range."
    )
    parser.add_argument("--vault_pred", type=float, required=True, help="Predicted vault (µm)")
    parser.add_argument("--low", type=float, default=250, help="Lower bound (µm)")
    parser.add_argument("--high", type=float, default=900, help="Upper bound (µm)")
    parser.add_argument(
        "--training_csv",
        default="data/processed/training_data.csv",
        help="Path to training data CSV",
    )
    parser.add_argument(
        "--vault_model",
        default="vault_model.pkl",
        help="Path to trained vault model",
    )
    parser.add_argument(
        "--vault_scaler",
        default="vault_scaler.pkl",
        help="Path to vault scaler",
    )
    parser.add_argument(
        "--feature_names",
        default="feature_names.pkl",
        help="Path to feature names",
    )
    args = parser.parse_args()

    # Load model + scaler + feature names
    with open(args.vault_model, "rb") as f:
        vault_model = pickle.load(f)
    with open(args.vault_scaler, "rb") as f:
        vault_scaler = pickle.load(f)
    with open(args.feature_names, "rb") as f:
        feature_names = pickle.load(f)

    # Load training data and compute residuals
    df = pd.read_csv(args.training_csv)
    df = df[df["Vault"].notna()].copy()
    X = df[feature_names].copy().fillna(0)
    X_scaled = vault_scaler.transform(X)
    preds = vault_model.predict(X_scaled)
    residuals = df["Vault"].values - preds

    sigma = float(np.std(residuals, ddof=1))
    mu = float(args.vault_pred)
    low = float(args.low)
    high = float(args.high)

    prob = max(0.0, normal_cdf(high, mu, sigma) - normal_cdf(low, mu, sigma))

    print(f"Predicted vault: {mu:.1f} µm")
    print(f"Range: {low:.1f}–{high:.1f} µm")
    print(f"Residual sigma (training): {sigma:.1f} µm")
    print(f"Estimated P(range): {prob:.3f}")


if __name__ == "__main__":
    main()

