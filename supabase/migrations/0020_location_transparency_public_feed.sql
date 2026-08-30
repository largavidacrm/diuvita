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
          'locations', case
            when jsonb_typeof(c.current_data -> 'locations') = 'array'
              then c.current_data -> 'locations'
            else null
          end,
          'maps_url', nullif(c.current_data ->> 'maps_url', ''),
          'google_maps_url', nullif(c.current_data ->> 'google_maps_url', ''),
          'google_reviews_url', nullif(c.current_data ->> 'google_reviews_url', ''),
          'reviews_url', nullif(c.current_data ->> 'reviews_url', ''),
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
          'years_in_practice', nullif(c.current_data ->> 'years_in_practice', ''),
          'specialists_count', c.current_data -> 'specialists_count',
          'team_credentialing_visible', nullif(c.current_data ->> 'team_credentialing_visible', ''),
          'public_pricing', nullif(c.current_data ->> 'public_pricing', ''),
          'pricing_url', nullif(c.current_data ->> 'pricing_url', ''),
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
