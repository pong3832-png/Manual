-- Ensure application activity fields used by the frontend exist.
-- Run in Supabase SQL Editor if application creation returns schema/cache 400 errors.

alter table public.applications
  add column if not exists campaign_url text;

alter table public.applications
  add column if not exists platform text;

alter table public.applications
  add column if not exists platform_id text;

alter table public.applications
  add column if not exists category text;

alter table public.applications
  add column if not exists d_day integer;

alter table public.applications
  add column if not exists created_at timestamptz not null default now();

alter table public.applications
  add column if not exists updated_at timestamptz not null default now();

alter table public.applications
  add column if not exists status text default '심사중';

update public.applications
set status = '심사중'
where status is null;

alter table public.applications
  alter column status set not null,
  alter column status set default '심사중';

alter table public.applications
  add column if not exists applied_at timestamptz default now();

update public.applications
set applied_at = coalesce(created_at, now())
where applied_at is null;

alter table public.applications
  alter column applied_at set not null,
  alter column applied_at set default now();

alter table public.applications
  add column if not exists selected_at timestamptz;

alter table public.applications
  add column if not exists completed_at timestamptz;

alter table public.applications
  add column if not exists memo text;

alter table public.applications
  add column if not exists review_url text;

create index if not exists idx_applications_status on public.applications(status);
create index if not exists idx_applications_platform_id on public.applications(platform_id);
create index if not exists idx_applications_applied_at on public.applications(applied_at desc);

notify pgrst, 'reload schema';
