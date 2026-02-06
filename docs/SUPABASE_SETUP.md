# Supabase Setup Guide - Vault 3.0 Beta

## Your Project Info
- **Project URL:** https://awdzlhqzubllaidhqsnw.supabase.co
- **Project:** VAULT3
- **Plan:** Pro (HIPAA add-on available later for $599/mo)

---

## Step 1: Run the Migration

1. Go to: https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/sql/new

2. Copy the entire contents of `supabase/migrations/001_initial_schema.sql`

3. Paste into the SQL Editor and click **Run**

4. You should see "Success. No rows returned" - that's correct!

---

## Step 2: Create Storage Bucket

1. Go to: https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/storage/buckets

2. Click **New bucket**

3. Settings:
   - **Name:** `ini-files`
   - **Public bucket:** OFF (unchecked)
   - **File size limit:** 10MB
   - **Allowed MIME types:** leave empty (allow all)

4. Click **Create bucket**

5. After creating, click on the bucket → **Policies** → **New policy**

6. Add these policies:

**Policy 1: Users can upload to their folder**
```sql
-- Name: Users can upload own files
-- Allowed operation: INSERT
-- Policy definition:
(bucket_id = 'ini-files' AND auth.uid()::text = (storage.foldername(name))[1])
```

**Policy 2: Users can read their own files**
```sql
-- Name: Users can read own files  
-- Allowed operation: SELECT
-- Policy definition:
(bucket_id = 'ini-files' AND auth.uid()::text = (storage.foldername(name))[1])
```

**Policy 3: Users can delete their own files**
```sql
-- Name: Users can delete own files
-- Allowed operation: DELETE
-- Policy definition:
(bucket_id = 'ini-files' AND auth.uid()::text = (storage.foldername(name))[1])
```

---

## Step 3: Get API Keys

1. Go to: https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/settings/api

2. Copy these values:
   - **Project URL:** `https://awdzlhqzubllaidhqsnw.supabase.co`
   - **anon public key:** (copy the long key)
   - **service_role key:** (copy - keep secret, for backend only)

3. Create `.env` file in project root (copy from `.env.example`):

```bash
cp .env.example .env
# Then edit .env with your actual keys
```

```env
# Supabase Configuration
SUPABASE_URL=https://awdzlhqzubllaidhqsnw.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here
```

⚠️ **Never commit `.env` to git!** (already in .gitignore)

---

## Step 4: Enable Auth Providers

1. Go to: https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/auth/providers

2. **Email** is enabled by default - good for beta

3. Optional: Enable **Google** or **GitHub** for easier login

---

## Step 5: Verify Setup

Run this in SQL Editor to verify tables exist:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';
```

Should return:
- profiles
- patients
- scans
- predictions
- outcomes

---

## Database Schema Overview

```
profiles (extends auth.users)
├── id (uuid, links to auth.users)
├── email
├── full_name
└── organization

patients
├── id (uuid)
├── user_id (FK → profiles)
├── anonymous_id ("Patient-001")
├── encrypted_name (NULL for beta)
└── encrypted_dob (NULL for beta)

scans
├── id (uuid)
├── patient_id (FK → patients)
├── user_id (FK → profiles)
├── eye (OD/OS)
├── ini_file_path (storage path)
├── features (jsonb) ← extracted from INI
└── extraction_status

predictions
├── id (uuid)
├── scan_id (FK → scans)
├── predicted_lens_size
├── lens_probabilities (jsonb)
├── predicted_vault
└── model_version

outcomes
├── id (uuid)
├── scan_id (FK → scans)
├── actual_lens_size
├── actual_vault
└── surgery_date
```

---

## Row Level Security

Every table has RLS enabled. Users can only see their own data:
- ✅ Doctor A uploads patient → only Doctor A sees it
- ✅ Doctor B uploads patient → only Doctor B sees it
- ✅ No cross-user data leakage

---

## Beta vs Production

### Beta (Now)
- PHI fields (name/DOB) stay NULL
- Strip patient info on upload
- Use anonymous_id like "Patient-001"

### Production (Later)
1. Upgrade to HIPAA add-on ($599/mo)
2. Sign BAA with Supabase
3. Enable encrypted_name / encrypted_dob columns
4. Add application-level encryption

---

## API Endpoints (Beta)

After setup, the backend exposes these endpoints:

### Upload & Predict
```bash
POST /beta/upload
# Upload INI file, strip PHI, extract features, get prediction
# Form data: file (INI), anonymous_id, icl_power
# Header: Authorization: Bearer <supabase_access_token>
```

### Record Outcome
```bash
POST /beta/scans/{scan_id}/outcome
# Record actual lens size and vault after surgery
# Body: { actual_lens_size, actual_vault, surgery_date, notes }
```

### List Data
```bash
GET /beta/patients      # List user's patients
GET /beta/scans         # List user's scans with predictions
GET /beta/scans/{id}    # Get scan detail
GET /beta/stats         # Get usage statistics
GET /beta/export        # Export data with outcomes
```

---

## Render Environment Variables

Add these to your Render service:

1. Go to Render Dashboard → Your Service → Environment
2. Add:
   - `SUPABASE_URL` = `https://awdzlhqzubllaidhqsnw.supabase.co`
   - `SUPABASE_ANON_KEY` = (your anon key)
   - `SUPABASE_SERVICE_KEY` = (your service role key)

---

## Frontend Environment Variables

For Vercel (Next.js frontend), add:

1. Go to Vercel Dashboard → Project → Settings → Environment Variables
2. Add:
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://awdzlhqzubllaidhqsnw.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = (your anon key)

---

## Exporting Beta Data

Use the export script to pull all data from Supabase into clean reports:

```bash
# Full report (summary + scans + features + probabilities)
python scripts/export_beta_data.py --all

# Save to CSV files (data/exports/)
python scripts/export_beta_data.py --csv

# Filter by doctor
python scripts/export_beta_data.py --user "Aaron" --all

# Just summary + scan table
python scripts/export_beta_data.py
```

### CSV Exports (saved to `data/exports/`)

| File | Contents |
|------|----------|
| `beta_export_*.csv` | All scans with features, predictions, outcomes |
| `outcomes_*.csv` | Only scans with recorded surgical outcomes |
| `training_ready_*.csv` | Features + outcomes, ready for model retraining |

### Creating Beta User Accounts

```bash
# Create accounts (no email sent to users)
python scripts/create_beta_users.py

# Or create a single account:
# Edit the BETA_USERS list in the script and re-run
```

---

## Useful Links

- **Dashboard:** https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw
- **SQL Editor:** https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/sql
- **Storage:** https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/storage
- **Auth:** https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/auth/users
- **API Docs:** https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/api
