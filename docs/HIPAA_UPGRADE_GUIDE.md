# HIPAA Compliance Upgrade Guide

This guide walks you through upgrading VAULT 3.0 from the current beta (non-HIPAA) to full HIPAA compliance.

## Overview

**Current State:**
- Supabase Pro Plan ($25/mo)
- No BAA signed
- Patient names stored in plain text (technically PHI, non-compliant)
- Showing initials in UI (good privacy practice)

**Target State:**
- Supabase Pro + HIPAA Add-on ($599/mo)
- BAA signed with Supabase
- PHI encrypted at application level + encrypted at rest by Supabase
- Full audit logging

---

## Step-by-Step Upgrade Process

### Step 1: Contact Supabase Support (Do This First)

**Email:** support@supabase.io

**Subject:** "HIPAA Compliance Upgrade Request - Project awdzlhqzubllaidhqsnw"

**Body:**
```
Hi Supabase Team,

We're upgrading our project to HIPAA compliance for production use.

Project Details:
- Project ID: awdzlhqzubllaidhqsnw
- Project Name: VAULT3
- Current Plan: Pro ($25/mo)
- Requested: Pro + HIPAA Add-on

We need:
1. HIPAA add-on enabled ($599/mo)
2. Business Associate Agreement (BAA) to sign
3. SOC 2 Type II documentation
4. Estimated timeline for upgrade

Our application handles patient health information (PHI) including names and dates of birth for eye surgery planning.

Please let us know next steps.

Thank you,
[Your Name]
```

**Expected Response:** 1-3 business days

---

### Step 2: Generate Encryption Key

Before running the migration, generate an encryption key for PHI:

```bash
# Run this locally to generate a key
cd /Users/gurpalvirdi/Vault\ 3.0
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Save this key** - you'll need it for the environment variables.

---

### Step 3: Run Database Migration

Once Supabase confirms HIPAA is enabled on your project:

1. **Go to Supabase Dashboard:**
   https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/sql/new

2. **Run the migration:**
   ```sql
   -- Run contents of supabase/migrations/004_hipaa_compliance.sql
   ```

This creates:
- `phi_access_logs` table for audit trail
- `first_name`, `last_name`, `dob` columns on patients table
- RLS policies for strict access control
- Audit logging function

---

### Step 4: Update Backend Environment Variables

**On Render.com (or your hosting platform):**

Add these environment variables:

```
# Existing variables (keep these)
SUPABASE_URL=https://awdzlhqzubllaidhqsnw.supabase.co
SUPABASE_SERVICE_KEY=your_service_key
SUPABASE_ANON_KEY=your_anon_key

# NEW: HIPAA Compliance
HIPAA_ENABLED=true
PHI_ENCRYPTION_KEY=your_generated_key_from_step_2
```

**Important:** 
- Keep `PHI_ENCRYPTION_KEY` secret - never commit it to git
- Rotate this key annually (you'll need to re-encrypt all PHI)
- Store it in a secure location (password manager, AWS Secrets Manager, etc.)

---

### Step 5: Deploy Backend Changes

1. **Commit the changes:**
   ```bash
   git add .
   git commit -m "Add HIPAA compliance: PHI encryption and audit logging"
   git push origin main
   ```

2. **Verify deployment on Render:**
   - Check build logs for errors
   - Verify environment variables are set
   - Test `/health` endpoint

---

### Step 6: Update Frontend to Show Full Names

Now that you have HIPAA compliance, you can show full names in the UI.

**Option A: Simple (Show names from database)**
Remove the `getInitials()` function calls in:
- `frontend/app/dashboard/page.tsx`
- `frontend/app/calculator/page.tsx`

**Option B: Secure (Decrypt names for authorized users only)**
Add a new API endpoint that returns decrypted names only for the authenticated user's own patients.

---

### Step 7: Enable Supabase Audit Logging

In Supabase Dashboard:

1. Go to **Database** → **Logs**
2. Enable **Detailed Logging**
3. Set retention to **7 years** (HIPAA requirement)
4. Configure log exports to secure storage

---

### Step 8: Document Your Security Procedures

Create a `SECURITY.md` file documenting:

```markdown
# Security & HIPAA Compliance

## Access Control
- Row-level security (RLS) ensures doctors only see their own patients
- Authentication via Supabase Auth with JWT tokens
- All PHI access is logged to `phi_access_logs` table

## Encryption
- PHI encrypted at application level using AES-256-GCM
- Database encrypted at rest by Supabase (HIPAA add-on)
- TLS 1.3 for all data in transit

## Audit Trail
- All PHI access logged with: user_id, patient_id, action, timestamp, IP
- Logs retained for 7 years
- Monthly audit reviews required

## Backup & Recovery
- Daily automated backups (Supabase manages)
- Point-in-time recovery available
- Backup encryption at rest

## Incident Response
- Report breaches within 24 hours
- Contact: [your email]
- Document all security incidents
```

---

### Step 9: Train Your Team

**Required for HIPAA:**
- Security awareness training for all team members
- Document who has access to PHI
- Annual security training
- Background checks for employees with PHI access

---

### Step 10: Ongoing Compliance Tasks

**Monthly:**
- Review `phi_access_logs` for suspicious activity
- Check for unauthorized access attempts
- Verify backups are working

**Annually:**
- Rotate `PHI_ENCRYPTION_KEY`
- Update security policies
- Risk assessment review
- Re-sign BAA with Supabase

---

## Cost Breakdown

| Item | Monthly Cost | Annual Cost |
|------|--------------|-------------|
| Supabase Pro + HIPAA | $599 | $7,188 |
| Render hosting (backend) | $7-25 | $84-300 |
| Vercel (frontend) | $0-20 | $0-240 |
| **Total** | **$606-644** | **$7,272-7,728** |

---

## Post-Upgrade Verification Checklist

- [ ] Supabase confirms HIPAA add-on is active
- [ ] BAA is signed and stored
- [ ] Database migration `004_hipaa_compliance.sql` is run
- [ ] `HIPAA_ENABLED=true` in backend environment
- [ ] `PHI_ENCRYPTION_KEY` is set and valid
- [ ] PHI is being encrypted in database (check a patient record)
- [ ] Audit logs are being written to `phi_access_logs`
- [ ] Frontend shows full names (not initials)
- [ ] RLS policies are working (users can't see other users' data)
- [ ] Backup retention is set to 7 years
- [ ] Security documentation is complete

---

## Emergency Contacts

| Issue | Contact |
|-------|---------|
| Supabase HIPAA questions | support@supabase.io |
| Security incident | [Your security email] |
| BAA questions | Supabase legal team |
| Data breach | HHS OCR: 1-800-368-1019 |

---

## Timeline Estimate

| Phase | Duration |
|-------|----------|
| Contact Supabase | 1-3 days |
| Sign BAA | 3-7 days |
| Run migration | 1 day |
| Deploy code changes | 1-2 days |
| Testing & verification | 3-5 days |
| Documentation | 2-3 days |
| **Total** | **1-2 weeks** |

---

## Questions?

- Review [Supabase HIPAA documentation](https://supabase.com/docs/guides/platform/compliance-overview)
- Consult a healthcare attorney for legal questions
- Hire a HIPAA compliance consultant if needed ($2,000-5,000 for initial setup)

---

**Disclaimer:** This guide is for technical implementation only. Consult a healthcare attorney to ensure full HIPAA compliance for your specific use case.
