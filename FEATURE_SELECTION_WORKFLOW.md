# Feature Selection Workflow

## Current Status (Last Updated: 68 cases)

**Active Feature Set:** 5 features  
- Age, WTW, ACD_internal, SEQ, CCT

**Performance:**
- Lens Size: 86.8% accuracy
- Vault: 141.9µm MAE

**All Features Still Extracted:** ✅  
The pipeline still extracts all 13 features into `training_data.csv`. We just train on the optimal 5.

---

## When to Re-Run Feature Analysis

### Run `feature_selection_analysis.py` when:

1. **Every 20-30 new cases added**
   - Small changes can shift optimal features
   - More data = can support more features without overfitting

2. **Milestones:**
   - ✅ 68 cases → **5 features optimal**
   - 🎯 100 cases → Re-analyze (may support 6-8 features)
   - 🎯 150 cases → Re-analyze (may support 8-10 features)
   - 🎯 200+ cases → Re-analyze (may support 10-13 features)

3. **If model performance degrades**
   - Accuracy drops by >5%
   - Vault MAE increases by >20µm

---

## How to Re-Run Analysis

```bash
# 1. After adding new data, extract features
./update_and_train.sh

# 2. Run feature analysis (takes ~2-3 minutes)
python feature_selection_analysis.py > feature_analysis_results.txt

# 3. Review results
cat feature_analysis_results.txt

# 4. Look at these sections:
#    - "PROGRESSIVE FEATURE ADDITION" → optimal count
#    - "TESTING MINIMAL FEATURE SETS" → compare to current
#    - "Can remove WITHOUT hurting either model" → features to drop

# 5. If optimal set changed, update train_model.py line 46
#    Then retrain:
python train_model.py
```

---

## Expected Evolution

As your dataset grows, expect these changes:

| Cases | Optimal Features | Expected Accuracy | Why |
|-------|------------------|-------------------|-----|
| 50-80 | 4-6 | 72-88% | Small data = simple model |
| 100-150 | 6-8 | 78-85% | Can add anatomical features |
| 150-200 | 8-10 | 80-88% | Can add corneal shape features |
| 200+ | 10-13 | 85-90% | Full feature set viable |

---

## Feature Hierarchy (Based on Importance)

**Tier 1 - Core (always needed):**
- SEQ (spherical equivalent)
- WTW (white-to-white)
- Age

**Tier 2 - Important (add at 80+ cases):**
- CCT (central corneal thickness)
- ACD_internal (anterior chamber depth)
- ACV (anterior chamber volume)

**Tier 3 - Helpful (add at 120+ cases):**
- SimK_steep
- TCRP_Km
- ACA_global

**Tier 4 - Situational (add at 200+ cases):**
- Pupil_diameter
- TCRP_Astigmatism
- AC_shape_ratio

**Tier 5 - Currently Unhelpful:**
- BAD_D (may help with 200+ cases)

---

## Important Notes

### ✅ You Don't Lose Features
- `extract_features.py` still extracts all 13 features
- They're all in `training_data.csv`
- You can test any combination anytime

### ✅ Quick Test of Different Sets
Want to try 8 features instead of 5? Just edit line 46 in `train_model.py`:

```python
# Try this:
feature_cols = ['Age', 'WTW', 'ACD_internal', 'ACV', 'SEQ', 'SimK_steep', 'CCT', 'TCRP_Km']
```

Then run:
```bash
python train_model.py
```

Compare the accuracy/MAE to decide which to use.

### ✅ Automation Idea
At 100+ cases, consider testing multiple feature sets automatically:

```bash
# Run analysis
python feature_selection_analysis.py

# It tests 5 different feature sets and shows which is best
# Use the "Minimal (6)" or "Standard (8)" recommendation
```

---

## Checklist for Next Re-Analysis

Current cases: 68  
Next analysis at: 90-100 cases

- [ ] Add new patient data
- [ ] Run `./update_and_train.sh`
- [ ] Check `training_data.csv` row count
- [ ] Run `python feature_selection_analysis.py`
- [ ] Compare "Progressive Addition" optimal count to current (5)
- [ ] If different, update `train_model.py` line 46
- [ ] Retrain with `python train_model.py`
- [ ] Update this file with new optimal set

---

## Quick Command Reference

```bash
# See current case count
wc -l training_data.csv

# Run full analysis (2-3 min)
python feature_selection_analysis.py

# Train with current features
python train_model.py

# Full pipeline (new data → train)
./update_and_train.sh
```

