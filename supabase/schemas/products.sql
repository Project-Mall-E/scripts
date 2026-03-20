-- Combined declarative schema: normalized product catalog (tags normalized).
-- Place in supabase/schemas/ and use Supabase CLI to diff/generate migrations.
--
-- If `public.products` already existed without these columns, `CREATE TABLE IF NOT EXISTS`
-- skips DDL and migrations can fail on indexes; use migrations/20260319120100_repair_legacy_products_columns.sql.
--
-- Declarative apply order: users.sql → stores.sql → products.sql (upsert_product_from_json inserts into public.stores).

-- Extensions (trigram search on product names)
create extension if not exists pg_trgm;

-- Generated column expr must be immutable; core array_to_string / to_tsvector are stable.
-- plpgsql + immutable is accepted for the column; SQL-language functions would be auto-volatile.
create or replace function public.products_search_vector_from_row(
  item_name text,
  item_descriptions text[]
)
returns tsvector
language plpgsql
immutable
parallel safe
set search_path = public, pg_catalog
as $f$
begin
  return to_tsvector(
    'english'::regconfig,
    coalesce(item_name, '') || ' ' || coalesce(array_to_string(item_descriptions, ' '), '')
  );
end;
$f$;

-- 1) Tags
create table if not exists public.tags (
  id bigint generated always as identity primary key,
  name text not null unique,
  created_at timestamptz not null default now()
);

create index if not exists idx_tags_name on public.tags (lower(name));

-- 2) Products
create table if not exists public.products (
  id bigint generated always as identity primary key,
  store text not null,
  item_name text not null,
  item_image_link text,
  item_image_links text[] not null default array[]::text[],
  item_link text not null,
  price_text text,
  -- numeric parsed price (avoid column name "price": confuses some clients next to json key `price`)
  price_amount numeric(12, 2),
  item_descriptions text[] not null default array[]::text[],
  search_vector tsvector generated always as (
    public.products_search_vector_from_row(item_name, item_descriptions)
  ) stored,
  raw jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint products_item_link_key unique (item_link)
);

create index if not exists idx_products_store on public.products (store);
create index if not exists idx_products_item_name
  on public.products (lower(item_name) text_pattern_ops);
create index if not exists idx_products_item_name_trgm
  on public.products using gin (item_name gin_trgm_ops);
create index if not exists idx_products_item_descriptions
  on public.products using gin (item_descriptions);
create index if not exists idx_products_search_vector
  on public.products using gin (search_vector);

-- 3) Join table
create table if not exists public.product_tags (
  product_id bigint not null references public.products (id) on delete cascade,
  tag_id bigint not null references public.tags (id) on delete cascade,
  primary key (product_id, tag_id)
);

create index if not exists idx_product_tags_product on public.product_tags (product_id);
create index if not exists idx_product_tags_tag on public.product_tags (tag_id);

-- 4) updated_at trigger
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $body$
begin
  new.updated_at = now();
  return new;
end;
$body$;

drop trigger if exists trg_products_set_updated_at on public.products;

create trigger trg_products_set_updated_at
  before update on public.products
  for each row
  execute function public.set_updated_at();

-- 5) View (invoker: RLS on underlying tables applies)
drop view if exists public.products_with_tags;

create view public.products_with_tags
with (security_invoker = true) as
select
  p.id,
  p.store,
  p.item_name,
  p.item_image_link,
  p.item_image_links,
  p.item_link,
  p.price_text,
  p.price_amount as price,
  p.item_descriptions,
  p.search_vector,
  p.raw,
  p.created_at,
  p.updated_at,
  coalesce(
    jsonb_agg(
      jsonb_build_object('id', t.id, 'name', t.name)
      order by t.name
    ) filter (where t.id is not null),
    '[]'::jsonb
  ) as tags
from public.products p
left join public.product_tags pt on pt.product_id = p.id
left join public.tags t on t.id = pt.tag_id
group by
  p.id,
  p.store,
  p.item_name,
  p.item_image_link,
  p.item_image_links,
  p.item_link,
  p.price_text,
  p.price_amount,
  p.item_descriptions,
  p.search_vector,
  p.raw,
  p.created_at,
  p.updated_at;

-- 6) Upsert from JSON (matches Python Product asdict: item_image_links, item_descriptions, tags)
create or replace function public.upsert_product_from_json(p jsonb)
returns bigint
language plpgsql
security definer
set search_path = public
as $body$
declare
  v_product_id bigint;
  v_tag text;
  v_tag_id bigint;
  v_price_text text;
  v_price_numeric numeric(12, 2);
  v_item_link text;
  v_image_links text[];
  v_descriptions text[];
  v_primary_image text;
  v_store_name text;
begin
  v_item_link := nullif(trim(p ->> 'item_link'), '');
  if v_item_link is null then
    raise exception 'item_link is required';
  end if;

  v_store_name := nullif(trim(coalesce(p ->> 'store', '')), '');
  if v_store_name is not null then
    insert into public.stores (name)
    values (v_store_name)
    on conflict (name) do update
      set updated_at = now();
  end if;

  v_price_text := p ->> 'price';
  begin
    v_price_numeric := nullif(
      regexp_replace(coalesce(v_price_text, ''), '[^0-9\.]', '', 'g'),
      ''
    )::numeric;
  exception
    when others then
      v_price_numeric := null;
  end;

  select coalesce(
    array(
      select jsonb_array_elements_text
      from jsonb_array_elements_text(coalesce(p -> 'item_image_links', '[]'::jsonb))
    ),
    array[]::text[]
  )
  into v_image_links;

  select coalesce(
    array(
      select jsonb_array_elements_text
      from jsonb_array_elements_text(coalesce(p -> 'item_descriptions', '[]'::jsonb))
    ),
    array[]::text[]
  )
  into v_descriptions;

  v_primary_image := nullif(trim(p ->> 'item_image_link'), '');
  if v_primary_image is null and cardinality(v_image_links) > 0 then
    v_primary_image := v_image_links[1];
  end if;

  if coalesce(cardinality(v_image_links), 0) = 0 and v_primary_image is not null then
    v_image_links := array[v_primary_image];
  end if;

  insert into public.products (
    store,
    item_name,
    item_image_link,
    item_image_links,
    item_link,
    price_text,
    price_amount,
    item_descriptions,
    raw
  )
  values (
    coalesce(v_store_name, ''),
    coalesce(nullif(trim(p ->> 'item_name'), ''), ''),
    v_primary_image,
    v_image_links,
    v_item_link,
    v_price_text,
    v_price_numeric,
    v_descriptions,
    p
  )
  on conflict (item_link) do update set
    store = excluded.store,
    item_name = excluded.item_name,
    item_image_link = excluded.item_image_link,
    item_image_links = excluded.item_image_links,
    price_text = excluded.price_text,
    price_amount = excluded.price_amount,
    item_descriptions = excluded.item_descriptions,
    raw = excluded.raw
  returning id into v_product_id;

  delete from public.product_tags where product_id = v_product_id;

  if p ? 'tags' and jsonb_typeof(p -> 'tags') = 'array' then
    for v_tag in
      select jsonb_array_elements_text
      from jsonb_array_elements_text(p -> 'tags')
    loop
      if v_tag is null or length(trim(v_tag)) = 0 then
        continue;
      end if;

      insert into public.tags (name)
      values (v_tag)
      on conflict (name) do update set name = public.tags.name
      returning id into v_tag_id;

      insert into public.product_tags (product_id, tag_id)
      values (v_product_id, v_tag_id);
    end loop;
  end if;

  return v_product_id;
end;
$body$;

-- Privileges: catalog readable by signed-in clients; writes via service role (bypasses RLS) or Edge Functions
grant usage on schema public to anon, authenticated, service_role;

grant select on public.products to authenticated;
grant select on public.tags to authenticated;
grant select on public.product_tags to authenticated;
grant select on public.products_with_tags to authenticated;

grant execute on function public.upsert_product_from_json(jsonb) to service_role;

alter table public.products enable row level security;
alter table public.tags enable row level security;
alter table public.product_tags enable row level security;

drop policy if exists products_select_authenticated on public.products;
create policy products_select_authenticated
  on public.products
  for select
  to authenticated
  using (true);

drop policy if exists tags_select_authenticated on public.tags;
create policy tags_select_authenticated
  on public.tags
  for select
  to authenticated
  using (true);

drop policy if exists product_tags_select_authenticated on public.product_tags;
create policy product_tags_select_authenticated
  on public.product_tags
  for select
  to authenticated
  using (true);
