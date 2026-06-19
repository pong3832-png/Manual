-- Ensure profile account fields used by the frontend exist.
-- Run in Supabase SQL Editor if profile save returns a schema/cache 400 error.

alter table public.profiles
  add column if not exists name text;

alter table public.profiles
  add column if not exists blog_url text;

alter table public.profiles
  add column if not exists level text not null default '브론즈';

alter table public.profiles
  add column if not exists points integer not null default 0;

alter table public.profiles
  add column if not exists created_at timestamptz not null default now();

alter table public.profiles
  add column if not exists updated_at timestamptz not null default now();

notify pgrst, 'reload schema';
