-- Vault 3.0 Beta Database Schema
-- Run this in Supabase SQL Editor: https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/sql

-- ============================================
-- TABLES
-- ============================================

-- Users (doctors/testers) - extends Supabase Auth
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique not null,
  full_name text,
  organization text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Patients (anonymous for beta, PHI-ready for later)
create table public.patients (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  anonymous_id text not null, -- "Patient-001" or user-provided label
  -- PHI fields (NULL for beta, encrypted later when HIPAA enabled)
  encrypted_name bytea,
  encrypted_dob bytea,
  notes text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(user_id, anonymous_id)
);

-- Scans (INI file uploads)
create table public.scans (
  id uuid primary key default gen_random_uuid(),
  patient_id uuid references public.patients(id) on delete cascade not null,
  user_id uuid references public.profiles(id) on delete cascade not null,
  eye text check (eye in ('OD', 'OS')) not null,
  ini_file_path text, -- Supabase Storage path (bucket/user_id/filename)
  original_filename text, -- Original filename for reference
  -- Extracted features (no PHI here)
  features jsonb, -- {"Age": 32, "WTW": 11.8, "ACD_internal": 3.2, ...}
  extraction_status text default 'pending' check (extraction_status in ('pending', 'success', 'failed')),
  extraction_error text,
  extracted_at timestamptz,
  created_at timestamptz default now()
);

-- Predictions (model outputs)
create table public.predictions (
  id uuid primary key default gen_random_uuid(),
  scan_id uuid references public.scans(id) on delete cascade not null,
  -- Lens size prediction
  predicted_lens_size text, -- "12.6"
  lens_probabilities jsonb, -- {"12.1": 0.02, "12.6": 0.71, "13.2": 0.25, "13.7": 0.02}
  -- Vault prediction  
  predicted_vault numeric,
  vault_mae numeric, -- Model's expected error (currently ~131µm)
  vault_range_low numeric, -- predicted - MAE
  vault_range_high numeric, -- predicted + MAE
  -- Model metadata
  model_version text not null,
  features_used jsonb, -- ["Age", "WTW", "ACD_internal", "SEQ", "CCT", "AC_shape_ratio"]
  created_at timestamptz default now()
);

-- Outcomes (ground truth from doctors after surgery)
create table public.outcomes (
  id uuid primary key default gen_random_uuid(),
  scan_id uuid references public.scans(id) on delete cascade not null,
  actual_lens_size text, -- What was actually implanted
  actual_vault numeric, -- Measured post-op vault in µm
  surgery_date date,
  notes text,
  recorded_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(scan_id) -- One outcome per scan
);

-- ============================================
-- INDEXES
-- ============================================

create index idx_patients_user_id on public.patients(user_id);
create index idx_scans_user_id on public.scans(user_id);
create index idx_scans_patient_id on public.scans(patient_id);
create index idx_predictions_scan_id on public.predictions(scan_id);
create index idx_outcomes_scan_id on public.outcomes(scan_id);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

alter table public.profiles enable row level security;
alter table public.patients enable row level security;
alter table public.scans enable row level security;
alter table public.predictions enable row level security;
alter table public.outcomes enable row level security;

-- Profiles: users can only see/edit their own profile
create policy "Users can view own profile" 
  on public.profiles for select 
  using (id = auth.uid());

create policy "Users can update own profile" 
  on public.profiles for update 
  using (id = auth.uid());

-- Patients: users can only access their own patients
create policy "Users can view own patients" 
  on public.patients for select 
  using (user_id = auth.uid());

create policy "Users can insert own patients" 
  on public.patients for insert 
  with check (user_id = auth.uid());

create policy "Users can update own patients" 
  on public.patients for update 
  using (user_id = auth.uid());

create policy "Users can delete own patients" 
  on public.patients for delete 
  using (user_id = auth.uid());

-- Scans: users can only access their own scans
create policy "Users can view own scans" 
  on public.scans for select 
  using (user_id = auth.uid());

create policy "Users can insert own scans" 
  on public.scans for insert 
  with check (user_id = auth.uid());

create policy "Users can update own scans" 
  on public.scans for update 
  using (user_id = auth.uid());

create policy "Users can delete own scans" 
  on public.scans for delete 
  using (user_id = auth.uid());

-- Predictions: users can access predictions for their scans
create policy "Users can view own predictions" 
  on public.predictions for select 
  using (scan_id in (select id from public.scans where user_id = auth.uid()));

create policy "Users can insert own predictions" 
  on public.predictions for insert 
  with check (scan_id in (select id from public.scans where user_id = auth.uid()));

-- Outcomes: users can access outcomes for their scans
create policy "Users can view own outcomes" 
  on public.outcomes for select 
  using (scan_id in (select id from public.scans where user_id = auth.uid()));

create policy "Users can insert own outcomes" 
  on public.outcomes for insert 
  with check (scan_id in (select id from public.scans where user_id = auth.uid()));

create policy "Users can update own outcomes" 
  on public.outcomes for update 
  using (scan_id in (select id from public.scans where user_id = auth.uid()));

create policy "Users can delete own outcomes" 
  on public.outcomes for delete 
  using (scan_id in (select id from public.scans where user_id = auth.uid()));

-- ============================================
-- FUNCTIONS
-- ============================================

-- Auto-create profile when user signs up
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', '')
  );
  return new;
end;
$$ language plpgsql security definer;

-- Trigger for new user signup
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Auto-update updated_at timestamp
create or replace function public.update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger update_profiles_updated_at
  before update on public.profiles
  for each row execute function public.update_updated_at();

create trigger update_patients_updated_at
  before update on public.patients
  for each row execute function public.update_updated_at();

create trigger update_outcomes_updated_at
  before update on public.outcomes
  for each row execute function public.update_updated_at();

-- ============================================
-- STORAGE BUCKET (run separately in Storage settings)
-- ============================================
-- Create bucket named "ini-files" with these settings:
-- - Public: OFF
-- - File size limit: 10MB
-- - Allowed MIME types: application/octet-stream, text/plain
