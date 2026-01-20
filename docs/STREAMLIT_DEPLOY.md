# Vault 3.0 - Streamlit Cloud Deployment

## 🚀 Deploy to Streamlit Cloud (FREE)

### Step 1: Go to Streamlit Cloud
Visit: [share.streamlit.io](https://share.streamlit.io)

### Step 2: Sign in with GitHub
- Click "Sign in with GitHub"
- Authorize Streamlit

### Step 3: Deploy New App
1. Click "New app"
2. **Repository:** `eyelabsai/VAULT-3.0`
3. **Branch:** `main`
4. **Main file path:** `app.py`
5. Click "Deploy!"

### Step 4: Wait ~2 minutes
Streamlit will:
- Install dependencies from `requirements.txt`
- Load your model files
- Deploy your app

### Step 5: Done! 🎉
Your app will be live at: `https://vault3.streamlit.app` (or similar)

---

## 📋 What Gets Deployed

✅ `app.py` - Your Streamlit interface
✅ `predict_icl.py` - Prediction logic
✅ `*.pkl` files - Your trained models
✅ `requirements.txt` - Python dependencies

❌ Training data, XML files, Excel files (not needed for predictions)

---

## 🔒 Privacy Options

**Public (Default):**
- Anyone with link can use it
- Great for demos, research

**Private (Change in Settings):**
- Add password protection
- Share only with specific people
- Still free!

---

## 🔄 Updates

Every time you push to GitHub main branch:
- Streamlit auto-redeploys
- Takes ~2 minutes
- Updates are live automatically

---

## 💡 Features Included

✅ Two modes: Single & Multiple recommendations
✅ Beautiful gradient background
✅ Real-time predictions
✅ Confidence scores & vault ranges
✅ Mobile responsive

---

## 🐛 Troubleshooting

**Build failed?**
- Check requirements.txt has all packages
- Ensure model files are in repo (not .gitignored)

**App crashes?**
- Check Streamlit logs (available in dashboard)
- Model files must be in root directory

**Slow to load?**
- First load takes ~10 seconds (model loading)
- Subsequent loads are fast

---

## 📞 Support

- Streamlit Docs: [docs.streamlit.io](https://docs.streamlit.io)
- Community: [discuss.streamlit.io](https://discuss.streamlit.io)

---

**Your link will be:** `https://vault3.streamlit.app` (or custom)

🎉 **Free forever!** No credit card needed.

