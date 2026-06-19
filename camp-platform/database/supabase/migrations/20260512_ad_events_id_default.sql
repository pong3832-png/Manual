-- Make ad_events robust for clients that rely on database-generated ids.
-- The frontend now also sends id explicitly.

alter table public.ad_events
  alter column id set default gen_random_uuid()::text;

notify pgrst, 'reload schema';
