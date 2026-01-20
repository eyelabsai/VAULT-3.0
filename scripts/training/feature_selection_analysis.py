#!/usr/bin/env python3
"""
Feature Selection Analysis for ICL Prediction
Tests which features actually matter and finds optimal minimal set.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import cross_val_score, KFold
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
import warnings
warnings.filterwarnings('ignore')

# All 13 features
ALL_FEATURES = ['Age', 'WTW', 'ACD_internal', 'ACV', 'ACA_global', 
                'Pupil_diameter', 'AC_shape_ratio', 'TCRP_Km', 
                'TCRP_Astigmatism', 'SEQ', 'SimK_steep', 'CCT', 'BAD_D']

# Core features (anatomical + refractive - always needed)
CORE_FEATURES = ['Age', 'WTW', 'ACD_internal', 'SEQ']

# Optional features to test
OPTIONAL_FEATURES = ['ACV', 'ACA_global', 'Pupil_diameter', 
                     'AC_shape_ratio', 'TCRP_Km', 'TCRP_Astigmatism', 
                     'SimK_steep', 'CCT', 'BAD_D']


def load_data():
    """Load training data."""
    df = pd.read_csv('training_data.csv')
    
    # Filter complete cases
    complete = df[ALL_FEATURES + ['Lens_Size', 'Vault']].notna().all(axis=1)
    df = df[complete].copy()
    
    # Remove lens size outliers
    valid = (df['Lens_Size'] > 0) & (df['Lens_Size'] < 20)
    df = df[valid].copy()
    
    df['Lens_Size'] = df['Lens_Size'].astype(str)
    
    return df


def evaluate_feature_set(df, features, target, task='classification'):
    """
    Evaluate model performance with given feature set.
    
    Returns: (mean_score, std_score)
    """
    X = df[features].values
    y = df[target].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    
    if task == 'classification':
        model = GradientBoostingClassifier(n_estimators=50, max_depth=2, 
                                          learning_rate=0.1, random_state=42)
        scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='accuracy')
    else:  # regression
        model = GradientBoostingRegressor(n_estimators=50, max_depth=3, 
                                         learning_rate=0.1, random_state=42)
        scores = cross_val_score(model, X_scaled, y, cv=cv, 
                                scoring='neg_mean_absolute_error')
        scores = -scores  # Convert to positive MAE
    
    return scores.mean(), scores.std()


def ablation_study(df):
    """
    Remove one feature at a time and see impact.
    Tests which features can be removed without hurting performance.
    """
    print("="*80)
    print("ABLATION STUDY: Remove One Feature at a Time")
    print("="*80)
    
    # Baseline: all features
    print("\n📊 LENS SIZE MODEL (Accuracy)")
    print("-" * 80)
    baseline_lens, baseline_lens_std = evaluate_feature_set(
        df, ALL_FEATURES, 'Lens_Size', 'classification'
    )
    print(f"{'BASELINE (all 13 features)':<40} {baseline_lens:.3f} ± {baseline_lens_std:.3f}")
    
    results_lens = []
    for feature in ALL_FEATURES:
        features_without = [f for f in ALL_FEATURES if f != feature]
        score, std = evaluate_feature_set(df, features_without, 'Lens_Size', 'classification')
        diff = score - baseline_lens
        results_lens.append({
            'removed': feature,
            'accuracy': score,
            'std': std,
            'change': diff
        })
        
        symbol = "✓" if diff >= -0.01 else "✗"  # Minimal drop OK
        print(f"{symbol} Remove {feature:<25} → {score:.3f} ± {std:.3f} (Δ {diff:+.3f})")
    
    print("\n" + "="*80)
    print("📊 VAULT MODEL (MAE in µm)")
    print("-" * 80)
    baseline_vault, baseline_vault_std = evaluate_feature_set(
        df, ALL_FEATURES, 'Vault', 'regression'
    )
    print(f"{'BASELINE (all 13 features)':<40} {baseline_vault:.1f} ± {baseline_vault_std:.1f} µm")
    
    results_vault = []
    for feature in ALL_FEATURES:
        features_without = [f for f in ALL_FEATURES if f != feature]
        mae, std = evaluate_feature_set(df, features_without, 'Vault', 'regression')
        diff = mae - baseline_vault
        results_vault.append({
            'removed': feature,
            'mae': mae,
            'std': std,
            'change': diff
        })
        
        symbol = "✓" if diff <= 5 else "✗"  # <5µm increase OK
        print(f"{symbol} Remove {feature:<25} → {mae:.1f} ± {std:.1f} µm (Δ {diff:+.1f})")
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY: Features That Can Be Removed")
    print("="*80)
    
    lens_removable = [r for r in results_lens if r['change'] >= -0.01]
    vault_removable = [r for r in results_vault if r['change'] <= 5]
    
    both_removable = set([r['removed'] for r in lens_removable]) & \
                     set([r['removed'] for r in vault_removable])
    
    if both_removable:
        print("\n✅ Can remove WITHOUT hurting either model:")
        for feat in both_removable:
            lens_info = next(r for r in results_lens if r['removed'] == feat)
            vault_info = next(r for r in results_vault if r['removed'] == feat)
            print(f"   - {feat:<25} (Lens Δ{lens_info['change']:+.3f}, Vault Δ{vault_info['change']:+.1f}µm)")
    else:
        print("\n⚠️  All features contribute to at least one model")
    
    print("\n⚠️  Features that HURT performance when removed (keep these):")
    lens_critical = [r for r in results_lens if r['change'] < -0.02]
    vault_critical = [r for r in results_vault if r['change'] > 10]
    critical = set([r['removed'] for r in lens_critical + vault_critical])
    
    for feat in critical:
        lens_info = next((r for r in results_lens if r['removed'] == feat), None)
        vault_info = next((r for r in results_vault if r['removed'] == feat), None)
        print(f"   - {feat:<25} (Lens Δ{lens_info['change']:+.3f}, Vault Δ{vault_info['change']:+.1f}µm)")
    
    return results_lens, results_vault


def progressive_feature_addition(df):
    """
    Start with core features, add one at a time to see what helps most.
    """
    print("\n" + "="*80)
    print("PROGRESSIVE FEATURE ADDITION")
    print("Starting with core features, add one at a time")
    print("="*80)
    
    # Baseline with core features only
    print(f"\n📊 Starting with {len(CORE_FEATURES)} core features: {CORE_FEATURES}")
    
    current_features = CORE_FEATURES.copy()
    remaining_features = OPTIONAL_FEATURES.copy()
    
    lens_score, lens_std = evaluate_feature_set(df, current_features, 'Lens_Size', 'classification')
    vault_mae, vault_std = evaluate_feature_set(df, current_features, 'Vault', 'regression')
    
    print(f"Lens Size Accuracy: {lens_score:.3f} ± {lens_std:.3f}")
    print(f"Vault MAE:          {vault_mae:.1f} ± {vault_std:.1f} µm")
    
    history = [{
        'features': current_features.copy(),
        'count': len(current_features),
        'lens_acc': lens_score,
        'vault_mae': vault_mae
    }]
    
    # Try adding each remaining feature
    iteration = 0
    while remaining_features and iteration < 9:  # Max 9 additions (4 core + 9 = 13 total)
        iteration += 1
        print(f"\n--- Round {iteration}: Testing addition of remaining {len(remaining_features)} features ---")
        
        best_feature = None
        best_improvement = -999
        best_lens = lens_score
        best_vault = vault_mae
        
        for feature in remaining_features:
            test_features = current_features + [feature]
            new_lens, _ = evaluate_feature_set(df, test_features, 'Lens_Size', 'classification')
            new_vault, _ = evaluate_feature_set(df, test_features, 'Vault', 'regression')
            
            # Combined improvement score (normalize both)
            lens_improvement = (new_lens - lens_score) * 100  # Convert to percentage points
            vault_improvement = -(new_vault - vault_mae) / 5  # Lower MAE is better, normalize
            combined = lens_improvement + vault_improvement
            
            print(f"  + {feature:<20} → Lens: {new_lens:.3f} (Δ{new_lens-lens_score:+.3f}), "
                  f"Vault: {new_vault:.1f}µm (Δ{new_vault-vault_mae:+.1f}), Score: {combined:+.2f}")
            
            if combined > best_improvement:
                best_improvement = combined
                best_feature = feature
                best_lens = new_lens
                best_vault = new_vault
        
        # Add best feature if it helps
        if best_improvement > 0:
            current_features.append(best_feature)
            remaining_features.remove(best_feature)
            lens_score = best_lens
            vault_mae = best_vault
            
            print(f"\n✅ Added {best_feature} (improvement: {best_improvement:.2f})")
            print(f"   New performance → Lens: {lens_score:.3f}, Vault: {vault_mae:.1f}µm")
            
            history.append({
                'features': current_features.copy(),
                'count': len(current_features),
                'lens_acc': lens_score,
                'vault_mae': vault_mae
            })
        else:
            print(f"\n⛔ No remaining features improve performance. Stopping.")
            break
    
    # Print summary
    print("\n" + "="*80)
    print("FEATURE ADDITION HISTORY")
    print("="*80)
    
    for i, h in enumerate(history):
        print(f"\n{i+1}. With {h['count']} features:")
        print(f"   Features: {h['features']}")
        print(f"   Lens Accuracy: {h['lens_acc']:.3f}")
        print(f"   Vault MAE:     {h['vault_mae']:.1f} µm")
    
    return history


def minimal_feature_sets(df):
    """Test predefined minimal feature sets."""
    print("\n" + "="*80)
    print("TESTING MINIMAL FEATURE SETS")
    print("="*80)
    
    feature_sets = {
        'Ultra Minimal (4)': ['Age', 'WTW', 'ACD_internal', 'SEQ'],
        'Minimal (6)': ['Age', 'WTW', 'ACD_internal', 'ACV', 'SEQ', 'CCT'],
        'No BAD_D (12)': [f for f in ALL_FEATURES if f != 'BAD_D'],
        'Standard (8)': ['Age', 'WTW', 'ACD_internal', 'ACV', 'SEQ', 'SimK_steep', 'CCT', 'TCRP_Km'],
        'Full (13)': ALL_FEATURES
    }
    
    results = []
    
    for name, features in feature_sets.items():
        lens_acc, lens_std = evaluate_feature_set(df, features, 'Lens_Size', 'classification')
        vault_mae, vault_std = evaluate_feature_set(df, features, 'Vault', 'regression')
        
        results.append({
            'name': name,
            'count': len(features),
            'features': features,
            'lens_acc': lens_acc,
            'lens_std': lens_std,
            'vault_mae': vault_mae,
            'vault_std': vault_std
        })
        
        print(f"\n{name}")
        print(f"  Features ({len(features)}): {', '.join(features)}")
        print(f"  Lens Size: {lens_acc:.3f} ± {lens_std:.3f}")
        print(f"  Vault:     {vault_mae:.1f} ± {vault_std:.1f} µm")
    
    # Compare to full model
    print("\n" + "="*80)
    print("COMPARISON TO FULL MODEL")
    print("="*80)
    
    full_result = next(r for r in results if r['name'] == 'Full (13)')
    
    for r in results:
        if r['name'] != 'Full (13)':
            lens_diff = r['lens_acc'] - full_result['lens_acc']
            vault_diff = r['vault_mae'] - full_result['vault_mae']
            
            lens_symbol = "✓" if lens_diff >= -0.02 else "✗"
            vault_symbol = "✓" if vault_diff <= 5 else "✗"
            
            print(f"\n{r['name']}")
            print(f"  {lens_symbol} Lens Accuracy: {lens_diff:+.3f} vs full model")
            print(f"  {vault_symbol} Vault MAE: {vault_diff:+.1f}µm vs full model")
            print(f"  Reduces inputs from 13 to {r['count']} ({13-r['count']} fewer)")
    
    return results


def main():
    """Run complete feature selection analysis."""
    print("="*80)
    print("ICL PREDICTION - FEATURE SELECTION ANALYSIS")
    print("="*80)
    
    df = load_data()
    print(f"\nLoaded {len(df)} complete training cases")
    print(f"Testing {len(ALL_FEATURES)} features")
    
    # 1. Ablation study
    ablation_study(df)
    
    # 2. Progressive addition
    progressive_feature_addition(df)
    
    # 3. Test minimal sets
    minimal_feature_sets(df)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\n📋 RECOMMENDATIONS:")
    print("1. Check ablation study for features that can be removed")
    print("2. Review progressive addition for optimal feature count")
    print("3. Consider minimal feature sets for production deployment")
    print("4. Balance model performance with user input burden")


if __name__ == '__main__':
    main()





