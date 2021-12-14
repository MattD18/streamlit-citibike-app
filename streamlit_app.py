import streamlit as st

from google.oauth2 import service_account
from google.cloud import bigquery

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)


### DEFINE QUERIES ###
station_info_query = """
    SELECT 
        *
    FROM  `streamlit-citibike-app.citibike_data.stations`
"""

timeperiod_query = """
SELECT  
        min(started_at) as timeperiod_start,
        max(started_at) as timeperiod_end
    FROM `streamlit-citibike-app.citibike_data.rides` 
"""

def generate_avg_trips_query(station_name):
    query =  f'''

    SELECT AVG(num_rides) as avg_num_rides FROM (
        SELECT  
            extract(date from started_at) as date_part,
            count(ride_id) as num_rides
        FROM `streamlit-citibike-app.citibike_data.rides` 
        WHERE start_station_name = "{station_name}"
        group by 1
    )
    
    '''
    return query

def generate_avg_trip_length_query(station_name):
    # warning, beware for long trips, may want to exclude
    query =  f'''
        SELECT  
            avg(
                (EXTRACT(DAY FROM ended_at - started_at) * (60*24)) +
                (EXTRACT(HOUR FROM ended_at - started_at) * 60) +
                (EXTRACT(MINUTE FROM ended_at - started_at)) +
                (EXTRACT(SECOND FROM ended_at - started_at) / 60)
            )
        FROM `streamlit-citibike-app.citibike_data.rides` 
        WHERE start_station_name = "{station_name}"
        and end_station_name is not null
    '''
    return query

def generate_top_destinations_query(station_name):
    query = f'''
    with station_destination_df as (
        SELECT  
            end_station_name,
            ride_id,
            (EXTRACT(DAY FROM ended_at - started_at) * (60*24)) +
                (EXTRACT(HOUR FROM ended_at - started_at) * 60) +
                (EXTRACT(MINUTE FROM ended_at - started_at)) +
                (EXTRACT(SECOND FROM ended_at - started_at) / 60) as trip_length_minutes
        FROM `streamlit-citibike-app.citibike_data.rides` 
        WHERE start_station_name = "{station_name}"
        and end_station_name is not null
    )

    select 
        end_station_name,
        count(ride_id) as num_rides,
        count(ride_id) / (select count(ride_id) from station_destination_df) as pct_total_rides,
        avg(trip_length_minutes) as avg_trip_length
    from station_destination_df 
    group by 1
    order by 2 desc
    limit 20
    '''
    return query

def generate_num_rides_by_hour_query(station_name):
    query = f'''
        SELECT 
            hour,
            num_rides / (select extract(day from max(started_at) - min(started_at) ) as num_days
            FROM `streamlit-citibike-app.citibike_data.rides` 
            WHERE start_station_name = "{station_name}"
            and end_station_name is not null) as daily_avg
        from (
        SELECT  
            EXTRACT(HOUR FROM started_at) AS hour,
            count(ride_id) as num_rides,
        FROM `streamlit-citibike-app.citibike_data.rides` 
        WHERE start_station_name = "{station_name}"
        and end_station_name is not null
        group by 1
        )
        order by 1
    '''
    return query

# Uses st.cache to only rerun when the query changes or after 15 min.
@st.cache(ttl=900)
def run_query(query):
    df = (
        client.query(query)
        .result()
        .to_dataframe()
    )
    return df

## INITIAL DATA LOAD ##

station_info_df = run_query(station_info_query)
timeperiod_df = run_query(timeperiod_query)

### UI CODE ###

st.title('NYC Citibike Station Explorer')
timeperiod_start = timeperiod_df.iloc[0][0]
timeperiod_end = timeperiod_df.iloc[0][1]
timeperiod_num_days= (timeperiod_end.date() - timeperiod_start.date()).days
st.write(f'Data for {timeperiod_start.date()} through {timeperiod_end.date()}')
# specify station
station_col1, station_col2, station_col3 = st.columns(3)

with station_col1:
    borough_list = np.sort(station_info_df['borough'].unique())
    borough = st.selectbox(
        label='Select Borough',
        options=borough_list
    )      
with station_col2:
    neighborhood_list = np.sort(
        station_info_df \
            .loc[station_info_df['borough']==borough]['neighborhood'].unique()
    )
    neighborhood = st.selectbox(
        label='Select Neighborhood',
        options=neighborhood_list
    )      
with station_col3:
    station_list = np.sort(
        station_info_df \
            .loc[(station_info_df['borough']==borough) \
                & (station_info_df['neighborhood']==neighborhood)] \
            ['station_name'].unique()
    )
    station = st.selectbox(
        label='Select Station',
        options=station_list
    )      



main_col1, main_col2 = st.columns(2)

with main_col1:

    # collect display stats
    avg_trips_per_day_query = generate_avg_trips_query(station)
    avg_trips_per_day_df = run_query(avg_trips_per_day_query)
    avg_trips_per_day = avg_trips_per_day_df.max()[0]

    avg_trip_length_query = generate_avg_trip_length_query(station)
    avg_trip_length_df = run_query(avg_trip_length_query)
    avg_trip_length = avg_trip_length_df.max()[0]

    st.metric(label='Completed Trips', value=f'{int(np.round(avg_trips_per_day, 0))} per day (avg.)')
    st.metric(label='Average Trip Length', value=f'{np.round(avg_trip_length, 1)} minutes' )

    top_destinations_query = generate_top_destinations_query(station)
    top_destinations_df = run_query(top_destinations_query)
    top_destinations_df = top_destinations_df.rename(columns={
            'end_station_name':'Station Name', 
            'num_rides':'# Trips', 
            'pct_total_rides': '% of Total Trips' ,
            'avg_trip_length': 'Avg. Trip Length (minutes)'
            })

    st.write(f'Top Destinations for {station}')
    st.table(top_destinations_df.head(5) \
        .style.format({
            '% of Total Trips' : '{:.1%}',
            'Avg. Trip Length (minutes)': '{:.1f}'
            })
    )

with main_col2:
    
    num_rides_by_hour_query = generate_num_rides_by_hour_query(station)
    num_rides_by_hour_df = run_query(num_rides_by_hour_query)
    num_rides_by_hour_hist = go.Figure(
        go.Bar(
            x=pd.to_datetime(num_rides_by_hour_df['hour'], format='%H').dt.time, 
            y=num_rides_by_hour_df['daily_avg']
        )
    )

    num_rides_by_hour_hist.update_layout(
        title='Hourly Ride Distribution',
        yaxis_title='# Trips (daily avg.)',
        xaxis_title='Time of Day',
        title_font=dict(
            size=24
        )
    )

    st.plotly_chart(num_rides_by_hour_hist)

# To Do organize queries, add better search to the station finder
