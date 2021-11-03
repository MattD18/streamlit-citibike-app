import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

## load test data ##
df = pd.read_csv('data/test_data.csv')
df['started_at'] = pd.to_datetime(df['started_at'])

### UI CODE ###

st.title('NYC Citibike Station Explorer')
timeperiod_start = df['started_at'].min()
timeperiod_end = df['started_at'].max()
timeperiod_num_days= (timeperiod_end.date() - timeperiod_start.date()).days
st.write(f'Data for {timeperiod_start.date()} through {timeperiod_end.date()}')
# specify station
station = st.selectbox(
    label='Select Station',
    options=df['start_station_name'].unique()
)

station_df = df.loc[df['start_station_name'] == station]

col1, col2 = st.columns(2)

with col1:

    # collect display stats
    avg_trips_per_day = station_df.groupby(station_df['started_at'].dt.date) \
        .apply(lambda x: x['ride_id'].count()).mean() #beware low trip count on first day of data file (9/1/21)

    avg_trip_length = station_df.loc[~station_df['end_station_name'].isnull()]['trip_duration_minutes'].mean() #remove trips missing end


    st.metric(label='Completed Trips', value=f'{int(np.round(avg_trips_per_day, 0))} per day (avg.)')
    st.metric(label='Average Trip Length', value=f'{np.round(avg_trip_length, 1)} minutes' )

    top_station_destinations_df = station_df.groupby('end_station_name') \
        .agg({'ride_id':lambda x: x.count(), 
            'trip_duration_minutes':'mean'}) \
        .sort_values(by = 'ride_id', ascending=False) \
        .reset_index() \
        .rename(columns={
            'end_station_name':'Station Name', 
            'ride_id':'# Trips', 
            'trip_duration_minutes': 'Avg. Trip Length (minutes)'
            })
    top_station_destinations_df['% of Total Trips'] = top_station_destinations_df['# Trips'] / top_station_destinations_df['# Trips'].sum()
    top_station_destinations_df = top_station_destinations_df[['Station Name',	'# Trips', '% of Total Trips',	'Avg. Trip Length (minutes)']]

    st.write(f'Top Destinations for {station}')
    st.table(top_station_destinations_df.head(5) \
        .style.format({
            '% of Total Trips' : '{:.1%}',
            'Avg. Trip Length (minutes)': '{:.1f}'
            })
    )

with col2:
    ## Chart 1
    num_rides_by_hour = station_df['started_at'].groupby(station_df['started_at'].dt.hour) \
        .apply(lambda x : x.count()) / timeperiod_num_days

    num_rides_by_hour_hist = go.Figure(
        go.Bar(
            x=pd.to_datetime(num_rides_by_hour.index, format='%H').time, 
            y=num_rides_by_hour
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

    station_start_time_hist = px.histogram(station_df, x="started_at", nbins=station_df['started_at'].dt.date.nunique())

    station_start_time_hist.update_layout(
        title='Station Ride History',
        yaxis_title='# Trips',
        xaxis_title='Date',
        title_font=dict(
            size=24
        )
    )

    st.plotly_chart(station_start_time_hist)



