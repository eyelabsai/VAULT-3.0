# lgb-27f-756c

Tight chamber model. LightGBM on 27 features with balanced class weights. Auto-routes for patients with small ACD/ACV/WTW. Strongest 12.1 detection.

- **Algorithm:** LightGBM (lens classifier) + GradientBoosting (vault regressor)
- **Hyperparams:** n_estimators=150, max_depth=4, num_leaves=15, min_child_samples=20, lr=0.05
- **Features:** 27 (9 base + 15 clinical gestalts + 3 tight-chamber)
- **Training cases:** 756
- **Lens accuracy (CV):** 66.1%
- **Vault MAE (CV):** 128.9 um
- **Class weights:** balanced (auto-computed inverse frequency)
- **Date:** 2026-02-13

## New Features (vs lgb-24f-756c)

1. **Tight_Chamber_Score** — z-score distance from 12.1 medians, clipped at 0
2. **Volume_Per_Depth** — ACV / ACD^2, nonlinear shallow-chamber sensitivity
3. **Nomogram_Downsize_Pressure** — tension between nomogram and chamber capacity

## Parent
lgb-24f-756c (foundation, untouched)
