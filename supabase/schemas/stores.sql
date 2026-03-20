-- Declarative schema: supported stores + per-user favorites.
-- Apply after users.sql (public.profiles). Apply before products.sql so public.upsert_product_from_json
-- can reference public.stores (duplicate set_updated_at here matches products.sql for a self-contained apply order).

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $body$
begin
  new.updated_at = now();
  return new;
end;
$body$;

-- 1) Catalog of store names; rows are also ensured by public.upsert_product_from_json.
create table if not exists public.stores (
  name text primary key,
  domain text,
  homepage text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

comment on table public.stores is 'Supported stores; name matches products.store and config stores.json name';

create index if not exists idx_stores_name_lower on public.stores (lower(name));

drop trigger if exists trg_stores_set_updated_at on public.stores;

create trigger trg_stores_set_updated_at
  before update on public.stores
  for each row
  execute function public.set_updated_at();

-- 2) User favorites (authenticated clients insert/delete their own rows)
create table if not exists public.store_favorites (
  user_id uuid not null references public.profiles (id) on delete cascade,
  store_name text not null references public.stores (name) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, store_name)
);

create index if not exists idx_store_favorites_user on public.store_favorites (user_id);

-- 3) RLS
alter table public.stores enable row level security;
alter table public.store_favorites enable row level security;

drop policy if exists stores_select_authenticated on public.stores;
create policy stores_select_authenticated
  on public.stores
  for select
  to authenticated
  using (true);

drop policy if exists store_favorites_select_own on public.store_favorites;
create policy store_favorites_select_own
  on public.store_favorites
  for select
  to authenticated
  using (user_id = auth.uid());

drop policy if exists store_favorites_insert_own on public.store_favorites;
create policy store_favorites_insert_own
  on public.store_favorites
  for insert
  to authenticated
  with check (user_id = auth.uid());

drop policy if exists store_favorites_delete_own on public.store_favorites;
create policy store_favorites_delete_own
  on public.store_favorites
  for delete
  to authenticated
  using (user_id = auth.uid());

-- 4) Privileges (writes to stores only via security definer RPC / service role)
revoke all on public.stores from anon;
revoke all on public.stores from authenticated;
grant select on public.stores to authenticated;

revoke all on public.store_favorites from anon;
revoke all on public.store_favorites from authenticated;
grant select, insert, delete on public.store_favorites to authenticated;
