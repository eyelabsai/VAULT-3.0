-- Migration: HIPAA Compliance Setup
-- Run this after upgrading to Supabase HIPAA plan and signing BAA
-- https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/sql/new

-- ============================================
-- 1. ADD AUDIT LOGGING FOR PHI ACCESS
-- ============================================

-- Table to track who accessed patient PHI
create table if not exists public.phi_access_logs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete cascade not null,
  patient_id uuid references public.patients(id) on delete cascade not null,
  action text not null check (action in ('view', 'update', 'delete', 'create')),
  accessed_at timestamptz default now(),
  ip_address text,
  user_agent text
);

-- Index for audit queries
create index idx_phi_access_logs_user_id on public.phi_access_logs(user_id);
create index idx_phi_access_logs_patient_id on public.phi_access_logs(patient_id);
create index idx_phi_access_logs_accessed_at on public.phi_access_logs(accessed_at desc);

-- Enable RLS on audit logs (only service role can modify)
alter table public.phi_access_logs enable row level security;

-- Users can only see their own access logs
create policy "Users can view own access logs"
  on public.phi_access_logs for select
  using (user_id = auth.uid());

-- ============================================
-- 2. ADD PLAIN TEXT PHI COLUMNS (for encrypted storage)
-- ============================================

-- These will store encrypted values at application level
-- Supabase HIPAA provides encryption at rest automatically
alter table public.patients 
add column if not exists first_name text,
add column if not exists last_name text,
add column if not exists dob date;

-- ============================================
-- 3. UPDATE RLS POLICIES FOR PHI
-- ============================================

-- Ensure strict access - users can only see their own patients
create policy if not exists "Users can view own patients"
  on public.patients for select
  using (user_id = auth.uid());

create policy if not exists "Users can insert own patients"
  on public.patients for insert
  with check (user_id = auth.uid());

create policy if not exists "Users can update own patients"
  on public.patients for update
  using (user_id = auth.uid());

create policy if not exists "Users can delete own patients"
  on public.patients for delete
  using (user_id = auth.uid());

-- ============================================
-- 4. FUNCTION TO LOG PHI ACCESS
-- ============================================

create or replace function public.log_phi_access(
  p_patient_id uuid,
  p_action text,
  p_ip_address text default null,
  p_user_agent text default null
)
returns void
language plpgsql
security definer
as $$
begin
  insert into public.phi_access_logs (
    user_id,
    patient_id,
    action,
    ip_address,
    user_agent
  ) values (
    auth.uid(),
    p_patient_id,
    p_action,
    p_ip_address,
    p_user_agent
  );
end;
$$;

-- ============================================
-- 5. COMPLIANCE NOTES
-- ============================================

-- After running this migration:
-- 1. Backend must encrypt PHI before storing
-- 2. All PHI access must call log_phi_access()
-- 3. Enable Supabase Audit Logs in dashboard
-- 4. Configure backup retention (7 years for HIPAA)
-- 5. Document your security procedures

comment on table public.patients is 'Patient records with PHI - HIPAA protected';
comment on table public.phi_access_logs is 'Audit trail for PHI access - required for HIPAA';
