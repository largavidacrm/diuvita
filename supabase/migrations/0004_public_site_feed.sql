begin;

create or replace function public.public_clinics_for_site()
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(
    jsonb_agg(
      jsonb_strip_nulls(
        jsonb_build_object(
          'slug', c.slug,
          'name', c.display_name,
          'city', c.city,
          'country', c.country,
          'region', c.region,
          'address', c.address,
          'web', c.website,
          'summary', c.summary,
          'services', case
            when jsonb_typeof(c.current_data -> 'services') = 'array'
              then c.current_data -> 'services'
            else '[]'::jsonb
          end,
          'specialties', case
            when jsonb_typeof(c.current_data -> 'specialties') = 'array'
              then c.current_data -> 'specialties'
            else '[]'::jsonb
          end,
          'cities_extra', case
            when jsonb_typeof(c.current_data -> 'cities_extra') = 'array'
              then c.current_data -> 'cities_extra'
            else null
          end,
          'profesionales', case
            when jsonb_typeof(c.current_data -> 'profesionales') = 'array'
              then c.current_data -> 'profesionales'
            else null
          end,
          'unidades', case
            when jsonb_typeof(c.current_data -> 'unidades') = 'array'
              then c.current_data -> 'unidades'
            else null
          end,
          'tech', nullif(c.current_data ->> 'tech', ''),
          'email', nullif(c.current_data ->> 'email', ''),
          'telefono', nullif(c.current_data ->> 'telefono', ''),
          'instagram', nullif(c.current_data ->> 'instagram', ''),
          'status', case c.status
            when 'published' then 'publicada'
            when 'preliminary' then 'preliminar'
            else c.status
          end
        )
      )
      order by c.display_name
    ),
    '[]'::jsonb
  )
  from public.clinics c
  where c.status in ('published', 'preliminary');
$$;

grant execute on function public.public_clinics_for_site() to anon, authenticated;

commit;
