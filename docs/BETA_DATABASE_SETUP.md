# Beta Testing – Database Setup & PHI Handling

This guide covers choosing and setting up a database for beta testing with multiple doctors who upload INI files, and how to handle **patient names and DOB** (Protected Health Information / PHI) safely.

---

## Recommended database: **PostgreSQL**

| Requirement | Why PostgreSQL |
|-------------|----------------|
| Store uploads, outcomes, predictions | Strong relational model, JSONB for flexible payloads |
| Multi-user (doctors) | Row-level security (RLS), roles, concurrent access |
| PHI in INI files | Encrypt columns or separate PHI table; audit logging |
| HIPAA / compliance | Many managed providers offer BAA (e.g. AWS RDS, Supabase, Neon) |
| Works with FastAPI | Excellent async support via `asyncpg` + SQLAlchemy 2.0 |

Alternatives considered:
- **SQLite**: Simple but weak for multi-user concurrency and no built-in RLS; not ideal for PHI.
- **MySQL**: Fine, but PostgreSQL has better JSON and RLS for this use case.
- **MongoDB**: Possible but relational model fits “user → uploads → outcomes” better; compliance story is more work.

---

## PHI in INI files (names, DOB)

INI files from Pentacam contain **patient name and DOB**. That is PHI and must be handled with care (access control, encryption, audit, and—if applicable—HIPAA).

### Options (pick one and document it)

1. **Don’t store PHI (recommended for beta)**  
   - Store only **extracted measurements** (WTW, ACD, SimK, etc.) and **Age** (derived from DOB, less identifying).  
   - Do **not** persist raw INI content or FirstName/LastName/DOB.  
   - Doctors use the app for predictions; you get outcomes (vault, lens size) keyed by **upload id** or **anonymous case id**, not by patient identity.

2. **Store PHI encrypted, minimal and separate**  
   - If you must keep a link to “which patient” (e.g. for re-identification by the uploading doctor only):  
     - Put **only** the fields needed (e.g. first name, last name, DOB) in a **separate table** with **column-level or application-level encryption**.  
     - Restrict access (e.g. only the uploading doctor can see their own PHI).  
   - Store raw INI in **encrypted blob storage** (e.g. S3 with SSE) and keep only `(upload_id, storage_key)` in the DB.  
   - Log all access to PHI and to decrypted data.

3. **Store raw INI for reprocessing but strip PHI before DB**  
   - Save INI to encrypted blob storage.  
   - When extracting for DB: strip name/DOB; store only measurements + optional **anonymous** case id.  
   - No PHI in the database; INI in blob is encrypted and access-controlled.

For **beta**, option 1 (no PHI in DB) is simplest and safest. You can add option 2 or 3 later if you need audit or re-identification.

---

## Schema overview

- **users** – Beta doctors (id, email, name, created_at, etc.).
- **uploads** – One row per INI upload: `user_id`, `filename`, `uploaded_at`, optional `ini_storage_key` (if you store raw INI in blob storage). No PHI.
- **extracted_measurements** – Parsed values from INI (WTW, ACD, SimK, Age, etc.) keyed by `upload_id`. No names/DOB; Age is acceptable as non-identifying in many contexts.
- **predictions** – Model output at upload time: predicted lens size, vault, probabilities (keyed by `upload_id`).
- **outcomes** – Expected/actual results: actual vault, actual lens size, when recorded (keyed by `upload_id`).

Optional if you need PHI (use with encryption and strict access):

- **upload_phi** – `upload_id`, encrypted first_name, last_name, dob (or similar). Only used when you must support re-identification by the uploading doctor.

All tables use `user_id` (or `upload_id` → `user_id`) so you can enforce “doctors see only their own data” (e.g. via RLS or app-level checks).

---

## Hosting PostgreSQL (pick one)

1. **Local / dev**  
   - Docker: `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16`  
   - Or install Postgres 15+ locally and create a database.

2. **Supabase** (https://supabase.com)  
   - Managed Postgres + optional BAA; good for beta.  
   - Get connection string from project settings (use “Session mode” or “Transaction” for SQLAlchemy).

3. **Neon** (https://neon.tech)  
   - Serverless Postgres; supports BAAs.  
   - Copy the connection string (pooled or direct).

4. **AWS RDS**  
   - Full control and BAA; more ops work.  
   - Use RDS PostgreSQL and restrict access (security group, no public IP if possible).

Use a **single env var** for the URL, e.g.:

- `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname`  
  (for async FastAPI with SQLAlchemy)

Keep secrets in `.env` (and never commit `.env`).

---

## Setup steps (summary)

1. Create a PostgreSQL instance (local or managed).  
2. Create a database and a role with full access to that database.  
3. Set `DATABASE_URL` in `.env` (and in your deployment environment).  
4. Run migrations (Alembic) to create tables.  
5. In the app: connect with SQLAlchemy + `asyncpg`; add endpoints that create `uploads`, store extracted measurements and predictions, and (optionally) outcomes.  
6. Enforce “user can only see/edit own data” in API logic (and optionally with Postgres RLS).  
7. If you later store PHI: encrypt it, restrict access, and enable audit logging.

The rest of this repo implements the **schema and backend wiring** (models, migrations, and minimal API hooks) so you can plug in auth and your preferred hosting.
