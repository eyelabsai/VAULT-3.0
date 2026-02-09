# lgb-24f-756c

LightGBM with balanced class weights. Regularized for real probability outputs.

- **Algorithm:** LightGBM (lens classifier + vault regressor)
- **Hyperparams:** n_estimators=150, max_depth=4, num_leaves=15, min_child_samples=20, lr=0.05
- **Features:** 24 (9 base + 15 clinical gestalts)
- **Training cases:** 756
- **Lens accuracy (CV):** 70.0%
- **12.1 recall (CV):** 46/81 (57%)
- **Vault MAE (CV):** 141.3 um
- **Class weights:** balanced (auto-computed inverse frequency)
- **Probability calibration:** Real spreads (mean max prob 0.69, <1% at 100%)
- **Date:** 2026-02-09

## Why not 500 trees?
The original 500-tree unlimited-depth config hit 77% accuracy but produced 100% probability
for every prediction (memorized training data). This regularized version trades ~7% accuracy
for clinically meaningful probability spreads that flag borderline cases.

## Parent
gestalt-24f-756c (foundation, untouched)
