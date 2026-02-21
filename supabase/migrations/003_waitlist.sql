-- Migration: Waitlist signups (public form, no auth required)
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/sql/new

-- Table for /waitlist form submissions
create table public.waitlist (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  email text not null,
  practice_info text not null,
  created_at timestamptz default now()
);

create index idx_waitlist_created_at on public.waitlist(created_at desc);
create index idx_waitlist_email on public.waitlist(email);

alter table public.waitlist enable row level security;

-- Anyone (including anon) can insert a signup
create policy "Anyone can submit waitlist"
  on public.waitlist for insert
  with check (true);

-- Only service_role can read (no policy for anon/authenticated = no read from frontend)
-- Use Supabase Dashboard or backend with service key to view/export signups
