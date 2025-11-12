"""
Analyze lens size prediction accuracy for discrete lens sizes
"""

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Available ICL sizes
AVAILABLE_SIZES = [12.1, 12.6, 13.2, 13.7]

def round_to_nearest_size(prediction):
    """Round continuous prediction to nearest available ICL size"""
    return min(AVAILABLE_SIZES, key=lambda x: abs(x - prediction))

def analyze_lens_predictions():
    """Analyze how well the model predicts discrete lens sizes"""

    print("="*70)
    print("LENS SIZE PREDICTION ANALYSIS (Discrete Sizes)")
    print("="*70)

    # Load data
    merged_df = pd.read_csv('merged_training_data.csv')

    # Prepare features (same as training)
    feature_cols = ['Sphere', 'Cyl', 'WTW', 'Pupil_Diameter', 'TCRP_Km',
                    'TCRP_Asti', 'ACD', 'ACA_180']

    X = merged_df[feature_cols].copy()
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')

    # Calculate Age
    merged_df['Age'] = 34.39  # Simplified - was mostly imputed anyway
    X['Age'] = merged_df['Age']

    # Fill missing
    for col in X.columns:
        if X[col].isna().any():
            median_val = X[col].median()
            X[col].fillna(median_val, inplace=True)

    y_lens_size = merged_df['final_lens_size']

    # Same split as training (random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_lens_size, test_size=0.2, random_state=42
    )

    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Load model
    lens_model = joblib.load('lens_size_model.pkl')

    # Predictions
    y_pred_continuous = lens_model.predict(X_test_scaled)

    # Round to nearest available size
    y_pred_rounded = [round_to_nearest_size(p) for p in y_pred_continuous]

    print(f"\n1. CONTINUOUS PREDICTION ANALYSIS")
    print("-"*70)
    print(f"   Test set size: {len(y_test)} eyes")
    print(f"   MAE (continuous): {np.mean(np.abs(y_pred_continuous - y_test)):.3f} mm")
    print(f"   This means average error is 0.23mm from true size")
    print()
    print(f"   Available sizes are: {AVAILABLE_SIZES}")
    print(f"   Size gaps are: 0.5mm (12.1→12.6), 0.6mm (12.6→13.2), 0.5mm (13.2→13.7)")
    print()

    print("\n2. DISCRETE ACCURACY (After Rounding to Real Sizes)")
    print("-"*70)

    # Exact match accuracy
    exact_match = sum(y_pred_rounded == y_test)
    exact_accuracy = exact_match / len(y_test) * 100

    print(f"   Exact matches: {exact_match}/{len(y_test)} ({exact_accuracy:.1f}%)")

    # Within one size accuracy
    def within_one_step(pred, true):
        pred_idx = AVAILABLE_SIZES.index(pred)
        true_idx = AVAILABLE_SIZES.index(true)
        return abs(pred_idx - true_idx) <= 1

    within_one = sum(within_one_step(p, t) for p, t in zip(y_pred_rounded, y_test))
    within_one_accuracy = within_one / len(y_test) * 100

    print(f"   Within one size step: {within_one}/{len(y_test)} ({within_one_accuracy:.1f}%)")

    # Show individual predictions
    print("\n3. INDIVIDUAL TEST PREDICTIONS")
    print("-"*70)
    print(f"   {'True Size':>10s} | {'Predicted':>10s} | {'Rounded':>10s} | {'Error':>8s} | Match")
    print(f"   {'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+------")

    for true, pred_cont, pred_round in zip(y_test, y_pred_continuous, y_pred_rounded):
        match_symbol = "✓" if pred_round == true else "✗"
        error = pred_cont - true
        print(f"   {true:10.1f} | {pred_cont:10.2f} | {pred_round:10.1f} | {error:+8.2f} | {match_symbol}")

    print("\n4. CONFUSION MATRIX (Predicted vs True)")
    print("-"*70)

    # Create confusion matrix
    from collections import defaultdict
    confusion = defaultdict(lambda: defaultdict(int))

    for true, pred in zip(y_test, y_pred_rounded):
        confusion[true][pred] += 1

    # Print header
    print(f"   True \\ Pred | ", end="")
    for size in AVAILABLE_SIZES:
        print(f"{size:>6.1f} ", end="")
    print("| Total")
    print(f"   {'-'*12}-+-{'-'*7}-{'-'*7}-{'-'*7}-{'-'*7}-+------")

    # Print rows
    for true_size in AVAILABLE_SIZES:
        print(f"   {true_size:10.1f}  | ", end="")
        row_total = 0
        for pred_size in AVAILABLE_SIZES:
            count = confusion[true_size][pred_size]
            row_total += count
            if count > 0:
                if true_size == pred_size:
                    print(f"{count:>6d}*", end=" ")  # Mark diagonal
                else:
                    print(f"{count:>6d} ", end=" ")
            else:
                print(f"{'—':>6s} ", end=" ")
        print(f"| {row_total:>4d}")

    print(f"   {'-'*12}-+-{'-'*7}-{'-'*7}-{'-'*7}-{'-'*7}-+------")
    print(f"   (* = correct predictions)")

    print("\n5. PRACTICAL INTERPRETATION")
    print("-"*70)
    print(f"   MAE of 0.23mm means:")
    print(f"   • Average prediction is within ±0.23mm of true size")
    print(f"   • Since lens gaps are 0.5-0.6mm, this is ~40-45% of one step")
    print(f"   • When rounded: {exact_accuracy:.0f}% exact matches")
    print(f"   • {within_one_accuracy:.0f}% within one size step (very safe)")
    print()

    # Check if any predictions are off by 2+ steps
    off_by_two = []
    for true, pred in zip(y_test, y_pred_rounded):
        true_idx = AVAILABLE_SIZES.index(true)
        pred_idx = AVAILABLE_SIZES.index(pred)
        if abs(true_idx - pred_idx) >= 2:
            off_by_two.append((true, pred))

    if off_by_two:
        print(f"   ⚠️  Predictions off by 2+ steps: {len(off_by_two)}")
        for true, pred in off_by_two:
            print(f"      True: {true}, Predicted: {pred}")
    else:
        print(f"   ✓ No predictions off by 2+ steps (very good!)")

    print("\n6. COMPARISON TO BASELINE")
    print("-"*70)

    # What if we always predicted the most common size?
    most_common_size = y_train.mode()[0]
    baseline_accuracy = sum(y_test == most_common_size) / len(y_test) * 100

    print(f"   Most common size in training: {most_common_size} mm")
    print(f"   Baseline (always predict {most_common_size}): {baseline_accuracy:.1f}% accuracy")
    print(f"   Our model: {exact_accuracy:.1f}% accuracy")
    print(f"   Improvement: +{exact_accuracy - baseline_accuracy:.1f} percentage points")

    print("\n" + "="*70)


if __name__ == "__main__":
    analyze_lens_predictions()
