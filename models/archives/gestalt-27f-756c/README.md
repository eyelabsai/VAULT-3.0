# Model: gestalt-27f-756c

## Summary

Tight-chamber variant of the gestalt GradientBoosting model. Adds 3 new features targeting 12.1 lens size recall and uses balanced sample weights to counter class imbalance. Not promoted to production — available on the compare page.

## Performance

| Metric | Value |
|---|---|
| Lens size accuracy | 70.8% (5-fold CV, balanced weights) |
| Vault MAE | 128.9 um (5-fold CV) |
| Training cases | 756 |
| Trained | Feb 13, 2026 |
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
