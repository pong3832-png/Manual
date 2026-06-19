-- Rename the comeplay platform label shown from Supabase-backed data.

update public.platforms
set
  name = '놀러와체험단',
  description = '놀러와체험단 public campaigns'
where id = 'comeplay';
