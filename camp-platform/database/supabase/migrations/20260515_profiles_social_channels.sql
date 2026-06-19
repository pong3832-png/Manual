-- Store user-managed channel links, public metrics, and application message templates.
-- Run in Supabase SQL Editor before deploying UI that saves these profile fields.

alter table public.profiles
  add column if not exists instagram_url text;

alter table public.profiles
  add column if not exists youtube_url text;

alter table public.profiles
  add column if not exists application_message_template text;

alter table public.profiles
  add column if not exists naver_blog_neighbor_count integer;

alter table public.profiles
  add column if not exists naver_blog_daily_visitor_count integer;

alter table public.profiles
  add column if not exists naver_blog_total_visitor_count bigint;

alter table public.profiles
  add column if not exists instagram_follower_count integer;

alter table public.profiles
  add column if not exists youtube_subscriber_count integer;

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'profiles_naver_blog_neighbor_count_nonnegative'
      and conrelid = 'public.profiles'::regclass
  ) then
    alter table public.profiles
      add constraint profiles_naver_blog_neighbor_count_nonnegative
      check (naver_blog_neighbor_count is null or naver_blog_neighbor_count >= 0);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conname = 'profiles_naver_blog_daily_visitor_count_nonnegative'
      and conrelid = 'public.profiles'::regclass
  ) then
    alter table public.profiles
      add constraint profiles_naver_blog_daily_visitor_count_nonnegative
      check (naver_blog_daily_visitor_count is null or naver_blog_daily_visitor_count >= 0);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conname = 'profiles_naver_blog_total_visitor_count_nonnegative'
      and conrelid = 'public.profiles'::regclass
  ) then
    alter table public.profiles
      add constraint profiles_naver_blog_total_visitor_count_nonnegative
      check (naver_blog_total_visitor_count is null or naver_blog_total_visitor_count >= 0);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conname = 'profiles_instagram_follower_count_nonnegative'
      and conrelid = 'public.profiles'::regclass
  ) then
    alter table public.profiles
      add constraint profiles_instagram_follower_count_nonnegative
      check (instagram_follower_count is null or instagram_follower_count >= 0);
  end if;

  if not exists (
    select 1 from pg_constraint
    where conname = 'profiles_youtube_subscriber_count_nonnegative'
      and conrelid = 'public.profiles'::regclass
  ) then
    alter table public.profiles
      add constraint profiles_youtube_subscriber_count_nonnegative
      check (youtube_subscriber_count is null or youtube_subscriber_count >= 0);
  end if;
end $$;

notify pgrst, 'reload schema';
