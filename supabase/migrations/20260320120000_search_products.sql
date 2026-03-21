-- search_products: OR match (any token hits name / descriptions / store / tags / per-token FTS).
-- Order: 1) rows matching all query words, 2) rows matching only earlier words (e.g. "white" before "jeans"),
--        then phrase FTS rank, then overlap score.

create or replace function public.search_products(q text, result_limit int default 80)
returns table (
  id bigint,
  store text,
  item_name text,
  item_image_link text,
  item_image_links text[],
  item_link text,
  price_text text,
  price numeric,
  item_descriptions text[],
  tags jsonb,
  match_score numeric,
  rank_ts real
)
language plpgsql
stable
security invoker
set search_path = public, pg_catalog
as $func$
declare
  lim int := greatest(1, least(coalesce(result_limit, 80), 200));
  tsq tsquery;
begin
  begin
    if trim(coalesce(q, '')) = '' then
      tsq := null;
    else
      tsq := plainto_tsquery('english', trim(q));
    end if;
  exception
    when others then
      tsq := null;
  end;

  return query
  with tokens as (
    select array_remove(
      regexp_split_to_array(lower(trim(coalesce(q, ''))), '\s+'),
      ''
    ) as arr
  ),
  ntok as (
    select coalesce(cardinality(arr), 0) as n from tokens
  ),
  token_rows as (
    select
      p.id as product_id,
      u.idx,
      u.tok,
      (
        p.item_name ilike '%' || u.tok || '%'
        or lower(array_to_string(coalesce(p.item_descriptions, array[]::text[]), ' '))
           like '%' || u.tok || '%'
        or p.store ilike '%' || u.tok || '%'
        or exists (
          select 1
          from public.product_tags pt
          join public.tags tg on tg.id = pt.tag_id
          where pt.product_id = p.id
            and lower(tg.name) like '%' || u.tok || '%'
        )
        or (
          length(u.tok) >= 2
          and p.search_vector @@ plainto_tsquery('english', u.tok)
        )
      ) as tok_hit
    from public.products p
    cross join tokens t
    cross join lateral unnest(t.arr) with ordinality as u(tok, idx)
    where cardinality(t.arr) > 0
  ),
  stats as (
    select
      tr.product_id,
      (select ntok.n from ntok) as n_tok,
      count(*) filter (where tr.tok_hit)::int as match_count,
      case
        when count(*) filter (where tr.tok_hit) = 1
        then min(tr.idx) filter (where tr.tok_hit)
      end as only_token_idx
    from token_rows tr
    group by tr.product_id
    having count(*) filter (where tr.tok_hit) >= 1
  ),
  filtered as (
    select p.*
    from public.products p
    join stats s on s.product_id = p.id
  ),
  ranked as (
    select
      f.id,
      f.store,
      f.item_name,
      f.item_image_link,
      f.item_image_links,
      f.item_link,
      f.price_text,
      f.price_amount,
      f.item_descriptions,
      s.match_count,
      s.n_tok,
      s.only_token_idx,
      case
        when s.match_count = s.n_tok
          and s.n_tok = 2
          and lower(
            coalesce(f.item_name, '') || ' '
            || array_to_string(coalesce(f.item_descriptions, array[]::text[]), ' ')
          ) like '%'
            || (select t.arr[1] from tokens t)
            || '%'
            || (select t.arr[2] from tokens t)
            || '%'
        then 1
        else 0
      end as phrase_in_order,
      (
        select coalesce(
          sum(
            (case
              when lower(array_to_string(coalesce(f.item_descriptions, array[]::text[]), ' '))
                   like '%' || tok || '%'
              then 4 else 0 end)
            + (case when f.item_name ilike '%' || tok || '%' then 2 else 0 end)
            + (case
                when exists (
                  select 1
                  from public.product_tags pt
                  join public.tags tg on tg.id = pt.tag_id
                  where pt.product_id = f.id
                    and lower(tg.name) like '%' || tok || '%'
                )
                then 1 else 0 end)
            + (case when f.store ilike '%' || tok || '%' then 1 else 0 end)
          ),
          0
        )::numeric
        from unnest((select tokens.arr from tokens)) as tok
      ) as ms,
      case
        when tsq is not null and f.search_vector @@ tsq then ts_rank_cd(f.search_vector, tsq)
        else 0::float
      end as rts
    from filtered f
    join stats s on s.product_id = f.id
  )
  select
    r.id,
    r.store,
    r.item_name,
    r.item_image_link,
    r.item_image_links,
    r.item_link,
    r.price_text,
    r.price_amount as price,
    r.item_descriptions,
    coalesce(
      (
        select jsonb_agg(
          jsonb_build_object('id', tg.id, 'name', tg.name)
          order by tg.name
        )
        from public.product_tags pt
        join public.tags tg on tg.id = pt.tag_id
        where pt.product_id = r.id
      ),
      '[]'::jsonb
    ) as tags,
    r.ms as match_score,
    r.rts::real as rank_ts
  from ranked r
  order by
    r.match_count desc,
    r.phrase_in_order desc,
    r.rts desc nulls last,
    case when r.match_count = 1 then coalesce(r.only_token_idx, 999) else 0 end asc,
    r.ms desc,
    r.id desc
  limit lim;
end;
$func$;

comment on function public.search_products(text, int) is
  'OR token search: include if any word matches (ILIKE + per-token English FTS). Order: more words matched first, full query FTS rank, then single-token rows by word order (earlier query words first).';

grant execute on function public.search_products(text, int) to authenticated;

