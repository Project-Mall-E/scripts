-- Declarative schema: user profiles linked to auth.users (id = auth.users.id).

-- 1) profiles: id matches auth.users, cascade on delete
create table if not exists public.profiles (
  id uuid not null references auth.users on delete cascade,
  username text,
  first_name text,
  last_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (id)
);

comment on table public.profiles is 'User profile data; id is auth.users.id';

-- Optional: unique username for display/handles (add after RLS if you want)
-- create unique index profiles_username_key on public.profiles (lower(username));
-- alter table public.profiles add constraint profiles_username_key unique using index profiles_username_key;

-- 2) Create profile from auth.users insert; reads from raw_user_meta_data
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $body$
begin
  insert into public.profiles (id, username, first_name, last_name, updated_at)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'username', ''),
    coalesce(new.raw_user_meta_data ->> 'first_name', ''),
    coalesce(new.raw_user_meta_data ->> 'last_name', ''),
    now()
  );
  return new;
end;
$body$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row
  execute function public.handle_new_user();

-- 3) RLS
alter table public.profiles enable row level security;

drop policy if exists "Users can read own profile" on public.profiles;
create policy "Users can read own profile"
  on public.profiles
  for select
  to authenticated
  using (id = auth.uid());

drop policy if exists "Users can update own profile" on public.profiles;
create policy "Users can update own profile"
  on public.profiles
  for update
  to authenticated
  using (id = auth.uid())
  with check (id = auth.uid());

-- No insert from client: trigger does it. If you ever need client insert (e.g. backfill), restrict:
-- create policy "Users can insert own profile" on public.profiles for insert to authenticated with check (id = auth.uid());

-- 4) Privileges
revoke all on public.profiles from anon;
revoke all on public.profiles from authenticated;
grant select, update on public.profiles to authenticated;
