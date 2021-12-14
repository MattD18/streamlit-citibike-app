
with neighborhood_geometry_processed as (
    select
        name,
        ST_GEOGFROMTEXT(geometry_raw, make_valid => true) as geometry
    from reference_tables.neighborhood_geometry
), stations as (
    select 
        station_name, 
        station_id, 
        ST_GEOGPOINT(lng, lat) as location 
    from (
        select 
        distinct
            start_station_name as station_name,
            start_station_id as station_id,
            start_lat as lat,
            start_lng as lng,
        from citibike_data.rides
        union distinct 
        select 
        distinct
            end_station_name as station_name,
            end_station_id as station_id,
            end_lat as lat,
            end_lng as lng
        from citibike_data.rides
    )
), stations_with_neighborhood as (
    select 
        station_name,
        station_id,
        name as neighborhood,
        location,
        geometry as neighborhood_location
    from stations s
    cross join neighborhood_geometry_processed n
    where ST_CONTAINS(n.geometry, s.location )
), nyc_gov_neighborhoods_with_boroughs_processed as (
    select 
        ST_GEOGFROMTEXT(the_geom, make_valid => true) as geometry,
        Name as name,
        Borough as borough
    from reference_tables.nyc_gov_neighborhoods_with_boroughs
)

select 
    station_name,
    station_id,
    neighborhood, 
    neighborhood_two,
    borough,
    location as station_location,
    neighborhood_location,
from (
    select 
        *,
        RANK() OVER (PARTITION BY station_name ORDER BY station_to_neighborhood_dist asc) as rank
    from (
        select 
            s.*,
            n.geometry as neighborhood_location_two,
            n.name as neighborhood_two,
            n.borough,
            ST_DISTANCE(s.location, n.geometry) as station_to_neighborhood_dist  
        from nyc_gov_neighborhoods_with_boroughs_processed n
        cross join stations_with_neighborhood s
    )
) 
where rank = 1
and station_name is not null
order by station_name, rank