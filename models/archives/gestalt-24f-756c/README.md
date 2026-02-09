# Model: gestalt-24f-756c

## Summary
Fresh retrain with full gestalts on all available data

## Details
- **Trained:** Feb 8, 2026
- **Training cases:** 756
- **Lens accuracy:** 73.2%
- **Vault MAE:** 128.3 um
- **Lens model:** GradientBoostingClassifier
- **Vault model:** GradientBoostingRegressor

## Features (24)
- Age
- WTW
- ACD_internal
- ICL_Power
- AC_shape_ratio
- SimK_steep
- ACV
- TCRP_Km
- TCRP_Astigmatism
- WTW_Bucket
- ACD_Bucket
- Shape_Bucket
- Space_Volume
- Aspect_Ratio
- Power_Density
- High_Power_Deep_ACD
- Chamber_Tightness
- Curvature_Depth_Ratio
- Stability_Risk
- Age_Space_Ratio
- Nomogram_Size
- Volume_Constraint
- Steep_Eye_Adjustment
- Safety_Downsize_Flag

## Gestalt Features Included
- WTW_Bucket
- ACD_Bucket
- Shape_Bucket
- Space_Volume
- Aspect_Ratio
- Power_Density
- High_Power_Deep_ACD
- Chamber_Tightness
- Curvature_Depth_Ratio
- Stability_Risk
- Age_Space_Ratio
- Nomogram_Size
- Volume_Constraint
- Steep_Eye_Adjustment
- Safety_Downsize_Flag

## How to deploy
```bash
cp models/archives/gestalt-24f-756c/*.pkl .
git add *.pkl && git commit -m "Deploy gestalt-24f-756c" && git push origin main
```
