-- Copy signup metadata into public.profiles.
-- Run this once in Supabase SQL Editor before production launch.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, name, blog_url)
  values (
    new.id,
    nullif(trim(coalesce(new.raw_user_meta_data ->> 'name', '')), ''),
    nullif(trim(coalesce(new.raw_user_meta_data ->> 'blog_url', '')), '')
  )
  on conflict (id) do update
  set
    name = coalesce(excluded.name, public.profiles.name),
    blog_url = coalesce(excluded.blog_url, public.profiles.blog_url),
    updated_at = now();
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_user();
