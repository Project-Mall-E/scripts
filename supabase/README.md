# Supabase schema (mall-e scripts)

SQL lives under [`schemas/`](schemas/) for reference and diffs; use [`migrations/`](migrations/) for incremental changes on a live project (Supabase CLI or SQL editor).

## Apply order (declarative)

1. [`schemas/users.sql`](schemas/users.sql) — `profiles` + auth trigger  
2. [`schemas/stores.sql`](schemas/stores.sql) — `stores`, `store_favorites` (requires `profiles`; defines `set_updated_at` so triggers work)  
3. [`schemas/products.sql`](schemas/products.sql) — catalog tables, `products_with_tags`, **`upsert_product_from_json`** (references `public.stores`)

If you apply `products.sql` before `stores.sql`, creating `upsert_product_from_json` will fail because the function references `public.stores`.

## Tables

| Object | Purpose |
|--------|---------|
| `products`, `tags`, `product_tags` | Normalized catalog |
| `products_with_tags` | Read view (`security_invoker`) |
| `stores` | One row per supported store (`name` PK); same string as `products.store` / `config/stores.json` `name` |
| `store_favorites` | `(user_id, store_name)` — authenticated users manage their own rows |

## Row level security

- **Catalog** (`products`, `tags`, `product_tags`, `products_with_tags`): `authenticated` may `SELECT` only (see `products.sql`).
- **`stores`**: `authenticated` may `SELECT` only. Rows are inserted/updated by **`upsert_product_from_json`** (service role / `security definer`), not by clients.
- **`store_favorites`**: `authenticated` may `SELECT`, `INSERT`, `DELETE` only where `user_id = auth.uid()`.

**Scraper:** use `SUPABASE_SERVICE_ROLE_KEY` on trusted runners only; it bypasses RLS and may call `upsert_product_from_json`.

**App:** use the anon or authenticated API key. End users insert/delete favorites with a signed-in session (`auth.uid()`). Do not ship the service role key in client apps.

## RPC: `upsert_product_from_json(p jsonb)`

- Granted to **`service_role`** only for `execute`.
- On each successful upsert, if `p->>'store'` is non-empty after trim, ensures a row in **`public.stores`** (`on conflict` bumps `updated_at`).

## Example queries (authenticated client)

List stores:

```sql
select name, domain, homepage, created_at from public.stores order by name;
```

Current user’s favorites:

```sql
select store_name, created_at from public.store_favorites where user_id = auth.uid();
```

Products from favorite stores (after loading favorite names in the app):

```sql
select * from public.products_with_tags
where store = any (:favorite_store_names);
```

## Migrations

[`migrations/20260319120200_stores_and_favorites.sql`](migrations/20260319120200_stores_and_favorites.sql) adds `stores`, `store_favorites`, RLS, and replaces `upsert_product_from_json`. It assumes `profiles` and the product catalog from earlier migrations already exist.
