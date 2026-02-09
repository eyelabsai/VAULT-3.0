# Model: gestalt-24f-55c

## Summary

First gestalt-augmented model. Introduced all 15 engineered clinical features on top of 9 base measurements. Trained on a small early dataset (~55 cases) before the full data pipeline was built. Showed that gestalt features dramatically improve accuracy even with very limited data (~75% vs 65% on the base model). Superseded by `gestalt-24f-756c` once full training data was available.

## Performance

| Metric | Value |
|---|---|
| Lens size accuracy | ~75% (5-fold CV) |
| Vault MAE | Unknown |
| Training cases | ~55 |
| Trained | Jan 19, 2026 |
| Training script | `scripts/training/train_model.py` |
| Training data | Early subset (pre-pipeline) |

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

### Preprocessing
- `StandardScaler` fitted independently for lens and vault models

## Features (24)

### 9 Base Features

| # | Feature | Unit | Description |
|---|---|---|---|
| 1 | Age | years | Patient age |
| 2 | WTW | mm | White-to-white corneal diameter |
| 3 | ACD_internal | mm | Anterior chamber depth (internal) |
| 4 | ICL_Power | D | ICL lens power (negative for myopia) |
| 5 | AC_shape_ratio | — | Anterior chamber shape ratio |
| 6 | SimK_steep | D | Simulated keratometry, steep meridian |
| 7 | ACV | mm³ | Anterior chamber volume |
| 8 | TCRP_Km | D | Total corneal refractive power, mean K |
| 9 | TCRP_Astigmatism | D | Total corneal refractive power, astigmatism |

### 15 Gestalt Features

#### Bucketed Features (discretize continuous measurements)

| Feature | Formula | Cutoffs |
|---|---|---|
| WTW_Bucket | `pd.cut(WTW, [0, 11.6, 11.9, 12.4, 20])` → 0,1,2,3 | 0: ≤11.6, 1: 11.6–11.9, 2: 11.9–12.4, 3: >12.4 mm |
| ACD_Bucket | `pd.cut(ACD_internal, [0, 3.1, 3.3, 10])` → 0,1,2 | 0: ≤3.1, 1: 3.1–3.3, 2: >3.3 mm |
| Shape_Bucket | `pd.cut(AC_shape_ratio, [0, 58, 62.5, 68, 300])` → 0,1,2,3 | 0: ≤58, 1: 58–62.5, 2: 62.5–68, 3: >68 |

#### Continuous Ratios / Interactions

| Feature | Formula | Clinical Meaning |
|---|---|---|
| Space_Volume | `WTW × ACD_internal` | 2D approximation of anterior chamber space |
| Aspect_Ratio | `WTW / ACD_internal` | Width-to-depth proportion |
| Power_Density | `abs(ICL_Power) / ACV` | Refractive correction per unit chamber volume |
| Chamber_Tightness | `ACV / WTW` | Volume relative to horizontal diameter |
| Curvature_Depth_Ratio | `SimK_steep / ACD_internal` | Corneal steepness relative to chamber depth |
| Age_Space_Ratio | `Age / ACD_internal` | Age-adjusted chamber depth (lens thickening) |

#### Binary Clinical Flags

| Feature | Rule | Triggers When |
|---|---|---|
| High_Power_Deep_ACD | `abs(ICL_Power) > 14 AND ACD_internal > 3.3` | High myope with deep chamber |
| Stability_Risk | `TCRP_Astigmatism > 1.5 AND WTW > 12.0` | High astigmatism + wide eye → rotation risk |

#### Nomogram-Based Features

| Feature | Rule | Clinical Logic |
|---|---|---|
| Nomogram_Size | Manufacturer WTW/ACD lookup table | Maps WTW ranges to expected sizes (12.1–13.7), ACD >3.5 shifts up at boundary zones |
| Volume_Constraint | `Nomogram_Size > 12.1 AND ACV < 170` | Nomogram says bigger lens but chamber volume is small → crowding risk |
| Steep_Eye_Adjustment | `Nomogram_Size > 12.1 AND SimK_steep > 46.0` | Nomogram says bigger lens but cornea is steep → consider downsizing |
| Safety_Downsize_Flag | `Nomogram_Size == 13.2 AND abs(ICL_Power) < 10.0` | 13.2 suggested but low power → consider 12.6 to avoid over-vaulting |

#### Nomogram Lookup Table (`get_nomogram_size`)

```
WTW Range        ACD ≤ 3.5    ACD > 3.5
─────────────    ──────────   ──────────
10.5–10.7        0.0          12.1
10.7–11.1        12.1         12.1
11.1–11.2        12.1         12.6
11.2–11.5        12.6         12.6
11.5–11.7        12.6         13.2
11.7–12.2        13.2         13.2
12.2–12.3        13.2         13.7
12.3–13.0        13.7         13.7
```

## Key Limitations

- Very small dataset (~55 cases) — high variance, likely overfit
- Vault MAE was not tracked for this run
- Served as proof-of-concept that gestalt features work

## Deploy

```bash
cp models/archives/gestalt-24f-55c/*.pkl models/current/
git add models/current/*.pkl
git commit -m "Deploy gestalt-24f-55c to production"
git push origin main
```