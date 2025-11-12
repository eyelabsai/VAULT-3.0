#!/bin/bash
#
# ICL Vault Prediction - Complete Workflow
# 
# Run this script whenever you add new INI files or update the Excel roster.
# It will process everything and retrain the models.
#
# Usage: ./update_and_train.sh
#

set -e  # Exit on error

echo ""
echo "========================================================================"
echo "  ICL VAULT PREDICTION - COMPLETE UPDATE & TRAINING WORKFLOW"
echo "========================================================================"
echo ""

# Activate virtual environment
source venv/bin/activate

# Step 1: Run full pipeline
echo "🔄 STEP 1: Running data processing pipeline..."
echo ""
python run_pipeline.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Pipeline failed. Fix errors and try again."
    exit 1
fi

# Step 2: Train models
echo ""
echo "🤖 STEP 2: Training machine learning models..."
echo ""
python train_model.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Training failed. Check training data and try again."
    exit 1
fi

# Step 3: Summary
echo ""
echo "========================================================================"
echo "  ✅ WORKFLOW COMPLETE!"
echo "========================================================================"
echo ""
echo "Summary of generated files:"
echo "  📊 training_data.csv           - ML training dataset"
echo "  🚨 flagged_incomplete_cases.csv - Cases needing review"
echo "  🤖 lens_size_model.pkl         - Trained lens size classifier"
echo "  🤖 vault_model.pkl             - Trained vault regressor"
echo ""
echo "Quick stats:"
python3 <<EOF
import pandas as pd
import os

if os.path.exists('training_data.csv'):
    df = pd.read_csv('training_data.csv')
    complete = df.dropna()
    
    both_outcomes = df[['Vault', 'Lens_Size']].notna().all(axis=1)
    
    print(f"  Total XML files:        {len(df)}")
    print(f"  With outcomes:          {both_outcomes.sum()}")
    print(f"  Complete training cases: {len(complete)}")
    
    if os.path.exists('flagged_incomplete_cases.csv'):
        flagged = pd.read_csv('flagged_incomplete_cases.csv')
        print(f"  Flagged for review:      {len(flagged)}")
else:
    print("  No training data found")
EOF

echo ""
echo "Next: Review flagged_incomplete_cases.csv (if it exists)"
echo ""

