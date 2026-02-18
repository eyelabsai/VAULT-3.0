# gestalt-18f-756c

No-ACV fallback model. Same architecture as gestalt-24f-756c but trained WITHOUT the 6 features that depend on ACV. For compare page evaluation only — not used in production routing.

- **Algorithm:** Gradient Boosting (lens) + Gradient Boosting (vault)
- **Features:** 18 (7 base + 11 gestalt, no ACV-dependent features)
- **Training cases:** 756
- **Lens accuracy (CV):** 72.6%
- **Vault MAE (CV):** 128.7 µm
- **Date:** 2026-02-18

## Dropped Features (ACV-dependent)
- ACV
- AC_shape_ratio
- Shape_Bucket
- Power_Density
- Chamber_Tightness
- Volume_Constraint

## Kept Features (18)
- Age
- WTW
- ACD_internal
- ICL_Power
- SimK_steep
- TCRP_Km
- TCRP_Astigmatism
- WTW_Bucket
- ACD_Bucket
- Space_Volume
- Aspect_Ratio
- High_Power_Deep_ACD
- Curvature_Depth_Ratio
- Stability_Risk
- Age_Space_Ratio
- Nomogram_Size
- Steep_Eye_Adjustment
- Safety_Downsize_Flag

## Parent
gestalt-24f-756c (same hyperparameters, fewer features)
