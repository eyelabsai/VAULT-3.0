# Current Production Model

## Active Model: `gestalt-24f-756c`

Deployed: Feb 8, 2026

| Metric | Value |
|---|---|
| Algorithm | GradientBoostingClassifier / GradientBoostingRegressor |
| Features | 24 (9 base + 15 gestalt) |
| Training cases | 756 |
| Lens accuracy | 73.2% (5-fold CV) |
| Vault MAE | 128.3 µm (5-fold CV) |

## Files

| File | Contents |
|---|---|
| `lens_size_model.pkl` | Trained GradientBoostingClassifier for lens size prediction |
| `lens_size_scaler.pkl` | StandardScaler fitted on lens training features |
| `vault_model.pkl` | Trained GradientBoostingRegressor for vault prediction |
| `vault_scaler.pkl` | StandardScaler fitted on vault training features |
| `feature_names.pkl` | Ordered list of 24 feature names the models expect |

## To Switch Models

```bash
cp models/archives/<new-model-tag>/*.pkl models/current/
# Update this README to reflect the new active model
git add models/current/
git commit -m "Deploy <new-model-tag> to production"
git push origin main
```

See `models/archives/gestalt-24f-756c/README.md` for full model details.
