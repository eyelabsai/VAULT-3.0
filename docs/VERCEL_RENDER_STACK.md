# Vercel + Render Deployment (Custom UI)

This guide deploys the new custom frontend on Vercel and the FastAPI backend on Render, while keeping Streamlit live during the build.

## Repo Structure Used

```
Vault 3.0/
├── backend/
│   ├── app/
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── app/
│   ├── package.json
│   └── .env.example
├── lens_size_model.pkl
├── lens_size_scaler.pkl
├── vault_model.pkl
├── vault_scaler.pkl
└── feature_names.pkl
```

---

## 1) Deploy the Backend on Render

1. Create a new **Web Service** on Render and connect your GitHub repo.
2. **Root Directory:** leave blank (repo root).
3. **Build Command:**
   ```
   pip install -r backend/requirements.txt
   ```
4. **Start Command:**
   ```
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```
5. Add an environment variable if needed:
   - `PYTHON_VERSION` (optional, e.g., `3.11.7`)
6. Deploy, then note your Render URL (e.g., `https://iclvault-api.onrender.com`).

### Optional: Custom API Domain
Add `api.iclvault.com` in Render → Settings → Custom Domains.

---

## 2) Deploy the Frontend on Vercel

1. Create a **New Project** on Vercel and import the repo.
2. **Root Directory:** `frontend`
3. **Framework Preset:** Next.js (auto-detected)
4. Add Environment Variable:
   - `NEXT_PUBLIC_API_BASE_URL` = `https://api.iclvault.com` (or your Render URL)
5. Deploy.

### Custom Domain
Add `iclvault.com` in Vercel → Project → Domains.

---

## 3) Keep Streamlit Live During Build

- Leave Streamlit running while you build and test the new stack.
- Use a staging domain while testing:
  - `staging.iclvault.com` → Vercel (staging frontend)
  - `api-staging.iclvault.com` → Render (staging backend)

When ready, switch `iclvault.com` to the Vercel frontend.

---

## 4) Quick API Test

Use Postman or curl to test the API:

```
curl -X POST https://api.iclvault.com/predict \
  -H "Content-Type: application/json" \
  -d '{
    "Age": 35,
    "WTW": 11.8,
    "ACD_internal": 3.2,
    "ICL_Power": -9.0,
    "AC_shape_ratio": 60.0,
    "SimK_steep": 44.0,
    "ACV": 180.0,
    "TCRP_Km": 44.0,
    "TCRP_Astigmatism": 1.0
  }'
```

---

## 5) Notes

- The backend loads model files from the repo root by default.
- Ensure `.pkl` files are committed and available to Render.
- Update `NEXT_PUBLIC_API_BASE_URL` on Vercel if the API URL changes.

