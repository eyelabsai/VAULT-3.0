#!/usr/bin/env python3
"""
Performance Tracking System
Logs model performance after each training run to track improvement over time.
"""

import pandas as pd
import json
import os
from datetime import datetime


HISTORY_FILE = "model_performance_history.json"


def load_history():
    """Load performance history from file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []


def save_run(num_cases, lens_accuracy, vault_mae, notes=""):
    """Save performance metrics from a training run."""
    history = load_history()
    
    run = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'training_cases': num_cases,
        'lens_size_accuracy': lens_accuracy,
        'vault_mae': vault_mae,
        'notes': notes
    }
    
    history.append(run)
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)
    
    print(f"\n✅ Logged training run: {num_cases} cases, {lens_accuracy:.1%} acc, {vault_mae:.1f}µm MAE")


def show_progress():
    """Display performance progress over time."""
    history = load_history()
    
    if not history:
        print("No training history yet. Run train_model.py first!")
        return
    
    print("\n" + "="*80)
    print("MODEL LEARNING PROGRESS")
    print("="*80)
    
    df = pd.DataFrame(history)
    
    print("\nAll Training Runs:")
    print("-"*80)
    for idx, row in df.iterrows():
        print(f"Run {idx+1}: {row['timestamp']}")
        print(f"  Cases: {row['training_cases']}")
        print(f"  Lens Size Accuracy: {row['lens_size_accuracy']:.1%}")
        print(f"  Vault MAE: {row['vault_mae']:.1f} µm")
        if row['notes']:
            print(f"  Notes: {row['notes']}")
        print()
    
    # Show improvement
    if len(df) > 1:
        first_run = df.iloc[0]
        last_run = df.iloc[-1]
        
        print("="*80)
        print("IMPROVEMENT SUMMARY")
        print("="*80)
        
        cases_added = last_run['training_cases'] - first_run['training_cases']
        acc_improvement = (last_run['lens_size_accuracy'] - first_run['lens_size_accuracy']) * 100
        mae_improvement = first_run['vault_mae'] - last_run['vault_mae']
        
        print(f"\nFrom first run ({first_run['timestamp']}) to now:")
        print(f"  📊 Data Growth:        +{cases_added} cases ({first_run['training_cases']} → {last_run['training_cases']})")
        print(f"  📈 Lens Accuracy:      {acc_improvement:+.1f}% ({first_run['lens_size_accuracy']:.1%} → {last_run['lens_size_accuracy']:.1%})")
        print(f"  📉 Vault MAE:          {mae_improvement:+.1f}µm ({first_run['vault_mae']:.1f} → {last_run['vault_mae']:.1f}µm)")
        
        if acc_improvement > 0 or mae_improvement > 0:
            print("\n✅ MODEL IS LEARNING! Performance improving with more data.")
        else:
            print("\n⚠️  Performance not improving yet. May need:")
            print("    - More diverse data (different patient types)")
            print("    - Better quality data (check flagged cases)")
            print("    - More cases (aim for 100+)")


def plot_progress():
    """Create a simple visualization of progress."""
    history = load_history()
    
    if len(history) < 2:
        print("\nNeed at least 2 training runs to show progress chart.")
        return
    
    df = pd.DataFrame(history)
    
    print("\n" + "="*80)
    print("PERFORMANCE TREND")
    print("="*80)
    print("\nLens Size Accuracy over time:")
    
    max_acc = df['lens_size_accuracy'].max()
    for idx, row in df.iterrows():
        acc = row['lens_size_accuracy']
        bar_length = int((acc / max_acc) * 50)
        bar = '█' * bar_length
        print(f"  Run {idx+1} ({row['training_cases']:3d} cases): {bar} {acc:.1%}")
    
    print("\nVault MAE over time (lower is better):")
    max_mae = df['vault_mae'].max()
    for idx, row in df.iterrows():
        mae = row['vault_mae']
        bar_length = int((mae / max_mae) * 50)
        bar = '█' * bar_length
        print(f"  Run {idx+1} ({row['training_cases']:3d} cases): {bar} {mae:.1f}µm")


if __name__ == '__main__':
    show_progress()
    plot_progress()










