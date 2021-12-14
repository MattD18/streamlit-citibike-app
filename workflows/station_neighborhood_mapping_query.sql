
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
)

select 
    station_name,
    station_id,
    name as neighborhood,
    location,
    geometry as neighborhood_location
from stations s
cross join neighborhood_geometry_processed n
where ST_CONTAINS(n.geometry, s.location )

