# ICL Vault — Agent Instructions

Read this before making any changes to the codebase.

## What This Project Is

Clinical decision support for ICL (Implantable Collamer Lens) surgery. Predicts:
1. **Lens Size** (classification: 12.1, 12.6, 13.2, 13.7 mm)
2. **Post-operative Vault** (regression: microns)

From Pentacam eye measurements (INI files) uploaded by surgeons.

## Production Stack

| Layer | Tech | Hosted | Path |
|---|---|---|---|
| **Frontend** | Next.js + Supabase Auth | Vercel | `frontend/` |
| **Backend API** | FastAPI + Uvicorn | Render | `backend/app/main.py` |
| **Database** | PostgreSQL (Supabase) | Supabase | `supabase/migrations/` |
| **ML Models** | sklearn, LightGBM, XGBoost | Bundled with backend | `models/` |

**NOT in production**: `legacy/streamlit_app.py` (old Streamlit app, kept for reference only). Nothing imports from it.

## Key Endpoints (backend/app/main.py)

- `POST /predict` — Single prediction using routed model (gestalt-24f or lgb-27f based on chamber tightness)
- `POST /predict-compare` — Run all archived models side by side (used by /compare page)
- `GET /models` — List all archived models with metadata
- `POST /parse-ini` — Extract measurements from Pentacam INI file
- `POST /beta/upload` — Upload INI, store in Supabase, return prediction (routes_beta.py)

## Model Architecture

### Production Models
- **gestalt-24f-756c** — GradientBoosting, 24 features, 73.2% accuracy. Best for 12.6/13.2/13.7.
- **lgb-27f-756c** — LightGBM, 27 features, 66.1% accuracy. Best for 12.1 (tight-chamber patients).

### Routing Logic
`Tight_Chamber_Score` (computed from WTW, ACD, ACV) determines which model handles `/predict`:
- Score > 0 (tight chamber) → lgb-27f-756c
- Score = 0 (normal/large) → gestalt-24f-756c

### Model Archives (`models/archives/`)
Each folder contains 5 PKL files + README.md. Auto-discovered by `load_all_models()` for the compare page. Folders starting with `.` are hidden.

### Feature Engineering
`engineer_features()` in `backend/app/main.py` produces 27 columns from 9 base Pentacam measurements. Every model selects only its own features from this DataFrame — extra columns are safely ignored.

9 base features: Age, WTW, ACD_internal, ICL_Power, AC_shape_ratio, SimK_steep, ACV, TCRP_Km, TCRP_Astigmatism

### Training Scripts
| Script | Model |
|---|---|
| `scripts/training/train_model.py` | gestalt-24f-756c (production GB) |
| `scripts/training/train_tight_chamber.py` | gestalt-27f-756c |
| `scripts/training/train_tight_chamber_lgb.py` | lgb-27f-756c |
| `scripts/training/train_xgb.py` | xgb-24f-756c |

Training data: `data/processed/training_data.csv` (756 complete cases)

## Critical Rules

1. **Never modify files in `models/current/` or root PKL files** without explicit instruction — these are the live production models
2. **Never modify `scripts/training/train_model.py`** — it's the source of truth for the production gestalt-24f model
3. **`legacy/` is dead code** — don't import from it, don't update it, don't reference it as current
4. **`engineer_features()` must stay in sync** between backend/app/main.py and all training scripts. If you add a feature, add it everywhere
5. **Model archives are append-only** — create new folders, don't modify existing archives
6. **PHI handling** — patient data in INI files contains protected health information. Never log, commit, or expose patient names/DOBs. The beta system uses anonymous_id
7. **Backend changes require Render redeploy** — push to main triggers auto-deploy. `@lru_cache` on model loaders means restart needed for new models

## File Map

```
Vault 3.0/
  backend/
    app/
      main.py            # FastAPI app — ALL prediction logic lives here
      routes_beta.py     # Beta test routes (Supabase integration)
  frontend/              # Next.js app (deployed on Vercel)
  models/
    current/             # Production model PKLs (gestalt-24f-756c)
    archives/            # All model versions (auto-discovered)
  scripts/
    training/            # Model training scripts
    pipeline/            # Feature config, data pipeline
  data/
    processed/           # training_data.csv, matched_patients.csv
    images/              # Raw INI/ZIP files (not committed)
    excel/               # Source Excel with outcomes
  supabase/
    migrations/          # Database schema
  docs/                  # Project documentation
  legacy/                # Retired Streamlit app (not in production)
  agents.md              # This file
```

## Deployment

- **Frontend (Vercel)**: Auto-deploys from `frontend/` on push to main
- **Backend (Render)**: Build: `pip install -r backend/requirements.txt`, Start: `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
- **Supabase**: Migrations in `supabase/migrations/`, project URL in `.env`

## Common Tasks

### Add a new model
1. Create training script in `scripts/training/`
2. Save 5 PKL files + README.md to `models/archives/<tag>/`
3. Add any new features to `engineer_features()` in `backend/app/main.py`
4. Push to main — model auto-appears on compare page after restart

### Update training data
1. Add INI files to `data/images/`
2. Run `python run_pipeline.py`
3. Run training script
4. Copy PKLs to `models/current/` if promoting to production

### Test a prediction locally
```bash
cd "Vault 3.0"
python -c "
from backend.app.main import engineer_features, load_all_models
import numpy as np

data = {'Age': 35, 'WTW': 11.8, 'ACD_internal': 3.2, 'ICL_Power': -9.0,
        'AC_shape_ratio': 60.0, 'SimK_steep': 44.0, 'ACV': 190.0,
        'TCRP_Km': 43.5, 'TCRP_Astigmatism': 1.0}
df = engineer_features(data)
models = load_all_models()
for tag, m in models.items():
    X = df[m['feature_names']]
    probs = m['lens_model'].predict_proba(m['lens_scaler'].transform(X))[0]
    print(f'{tag}: {dict(zip(m[\"lens_model\"].classes_, [f\"{p:.1%}\" for p in probs]))}')
"
```
