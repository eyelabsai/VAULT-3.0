-- Migration: Add multi-timepoint vault measurements to outcomes
-- Run in Supabase SQL Editor: https://supabase.com/dashboard/project/awdzlhqzubllaidhqsnw/sql/new

-- Rename existing vault column to vault_1day
ALTER TABLE public.outcomes RENAME COLUMN actual_vault TO vault_1day;

-- Add 1-week and 1-month vault columns
ALTER TABLE public.outcomes ADD COLUMN vault_1week numeric;
ALTER TABLE public.outcomes ADD COLUMN vault_1month numeric;

-- Remove the unique constraint on scan_id so we keep flexibility
-- (already unique via the existing constraint, keep it)
