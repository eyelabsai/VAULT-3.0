# Model: base-5f-759c

## Summary

Baseline GradientBoosting model using only 5 raw Pentacam measurements. No gestalt features, no ICL Power, no corneal/astigmatism data. This was the first production model — serves as the performance floor that gestalt models must beat.

## Performance

| Metric | Value |
|---|---|
| Lens size accuracy | 65.1% (5-fold CV) |
| Vault MAE | 134.4 µm (5-fold CV) |
| Training cases | 759 |
| Trained | Feb 4, 2026 |
| Training script | `scripts/training/train_model.py` |
| Training data | `data/processed/training_data.csv` |

## Algorithm

### Lens Size Classifier
- **Type:** `GradientBoostingClassifier` (sklearn)
- **Hyperparameters:**
  - `n_estimators=150`
  - `max_depth=4`
  - `learning_rate=0.05`
  - `subsample=0.8`
  - `random_state=42`
- **Classes:** 12.1, 12.6, 13.2, 13.7 mm

### Vault Regressor
- **Type:** `GradientBoostingRegressor` (sklearn)
- **Hyperparameters:**
  - `n_estimators=50`
  - `max_depth=3`
  - `learning_rate=0.1`
  - `random_state=42`
- **Output:** Predicted vault in microns (µm)

### Cross-Validation
- 5-fold, `KFold(n_splits=5, shuffle=True, random_state=42)`
- Both models evaluated via `cross_val_score`, then trained on full dataset

### Preprocessing
- `StandardScaler` fitted independently for lens and vault models

## Features (5)

| # | Feature | Unit | Description |
|---|---|---|---|
| 1 | Age | years | Patient age |
| 2 | WTW | mm | White-to-white corneal diameter |
| 3 | ACD_internal | mm | Anterior chamber depth (internal) |
| 4 | ACV | mm³ | Anterior chamber volume |
| 5 | SimK_steep | D | Simulated keratometry, steep meridian |

**Not included:** ICL_Power, AC_shape_ratio, TCRP_Km, TCRP_Astigmatism, all 15 gestalt features.

## Gestalt Features

None — raw features only.

## Key Limitations

- No ICL Power input → cannot account for lens thickness differences across powers
- No astigmatism data → no awareness of rotational stability risk
- No gestalt engineering → no nomogram logic, no clinical flags
- Lower accuracy than gestalt models (65.1% vs 73.2%+)

## Deploy

```bash
cp models/archives/base-5f-759c/*.pkl models/current/
git add models/current/*.pkl
git commit -m "Deploy base-5f-759c to production"
git push origin main
```