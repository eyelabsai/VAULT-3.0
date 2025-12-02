# Vault 3.0 - Vercel Deployment Guide

## 🚀 Quick Deploy to Vercel

### Step 1: Push to GitHub

```bash
git add -A
git commit -m "Add Vercel deployment support"
git push
```

### Step 2: Deploy on Vercel

1. Go to [vercel.com](https://vercel.com)
2. Click "New Project"
3. Import your GitHub repository
4. Vercel will auto-detect settings from `vercel.json`
5. Click "Deploy"

**That's it!** Your app will be live at `https://your-project.vercel.app`

---

## 📁 Project Structure

```
Vault 3.0/
├── api/
│   ├── predict.py          # FastAPI backend (serverless function)
│   └── requirements.txt    # Python dependencies for API
├── public/
│   └── index.html          # Frontend UI
├── vercel.json             # Vercel configuration
├── .vercelignore           # Files to exclude from deployment
├── *.pkl                   # ML model files (deployed with API)
└── feature_names.pkl       # Feature configuration
```

---

## 🔧 Local Testing

### Test the API:

```bash
python test_api.py
```

Then open: `http://localhost:8000/docs` to see API documentation

### Test the frontend:

Open `public/index.html` in your browser, or:

```bash
# Serve locally (install serve if needed: npm install -g serve)
serve public
```

---

## ⚙️ How It Works

### Backend (Serverless)
- **File:** `api/predict.py`
- **Framework:** FastAPI
- **Deployed as:** Vercel Serverless Function
- **Endpoint:** `https://your-app.vercel.app/api/predict`
- **Memory:** 1024MB (configured in vercel.json)
- **Timeout:** 10 seconds

### Frontend
- **File:** `public/index.html`
- **Tech:** Pure HTML + Tailwind CSS + JavaScript
- **Deployed as:** Static files
- **URL:** `https://your-app.vercel.app`

### Model Files
- The `.pkl` files (models, scalers) are included in deployment
- Loaded by the API function when making predictions
- Cached in memory for performance

---

## 🎨 Frontend Features

✅ Beautiful gradient background matching Streamlit style
✅ Two modes: Single Recommendation & Multiple Options
✅ Responsive design (works on mobile/tablet/desktop)
✅ Real-time API calls
✅ Clean, medical-grade UI

---

## 🔒 Security Notes

**What's deployed:**
- ✅ Model files (.pkl)
- ✅ API code
- ✅ Frontend code

**What's NOT deployed (.vercelignore):**
- ❌ Training data (training_data.csv)
- ❌ Patient Excel files
- ❌ XML files
- ❌ Source INI files
- ❌ Development scripts

**Privacy:**
- User inputs are sent to your API
- No data is stored (prediction happens in real-time)
- All data is ephemeral (cleared after request)

---

## 🎯 Environment Variables (Optional)

If you want to add API authentication:

1. Go to Vercel Dashboard → Project → Settings → Environment Variables
2. Add variables like `API_KEY`
3. Update `api/predict.py` to check the key

---

## 📊 Monitoring

Vercel provides:
- Real-time logs
- Function execution metrics
- Error tracking
- Deployment history

Access at: [vercel.com/dashboard](https://vercel.com/dashboard)

---

## 🔄 Updates & Redeployment

**Automatic:**
Every git push to main branch triggers auto-deployment

**Manual:**
Go to Vercel Dashboard → Deployments → Redeploy

**Update models:**
1. Retrain models locally: `./update_and_train.sh`
2. Commit new `.pkl` files
3. Push to GitHub
4. Vercel auto-deploys with new models

---

## 🐛 Troubleshooting

### API not working?
- Check Vercel Function logs
- Ensure all `.pkl` files are committed to git
- Verify `api/requirements.txt` has all dependencies

### Frontend not calling API?
- Check browser console for errors
- Ensure API endpoint is correct (/api/predict)
- Check CORS settings in api/predict.py

### Models not loading?
- Models must be in root directory (not in subdirectories)
- Check file paths in api/predict.py
- Ensure .pkl files are not in .gitignore

---

## 💡 Tips

1. **Use Vercel CLI for faster testing:**
   ```bash
   npm install -g vercel
   vercel dev  # Test locally with Vercel environment
   ```

2. **Check build logs:**
   Every deployment shows detailed logs in Vercel dashboard

3. **Custom domain:**
   Add your own domain in Vercel project settings

4. **Analytics:**
   Enable Vercel Analytics for usage insights

---

## 📞 Need Help?

- Vercel Docs: [vercel.com/docs](https://vercel.com/docs)
- FastAPI Docs: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- Check Vercel Function logs for errors

---

**Your app will be live at:** `https://vault-3-0.vercel.app` (or your custom URL)

🎉 **That's it! Your ML app is now deployed on Vercel!**

