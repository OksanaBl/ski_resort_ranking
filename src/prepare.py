import json
import os
import numpy as np
import pandas as pd

from haversine import haversine_vector

from utils import (
    load_resorts_full_data,
    load_resort_locations,
    save_df_to_csv
)

CLOSED_RESORTS = ['R015', 'R023']

def load_weather_data(resort_id):
    path = f'raw/weather/data_{resort_id}.json'
    with open(path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    weather_df = pd.DataFrame(data['weather_data']['daily'])
    weather_df['resort_id'] = data['resort_id']
    return weather_df

def prepare_resorts_weather():
    weather_df = []
    resorts_data = load_resort_locations()
    for resort_id, _, _ in resorts_data:
        resort_weather = load_weather_data(resort_id)
        weather_df.append(resort_weather)
    weather_df = pd.concat(weather_df, ignore_index=True)
    weather_df['time'] = pd.to_datetime(weather_df['time'])
    weather_df_season = weather_df[weather_df['time'].dt.month.isin([11,12,1,2,3,4])].copy()
    weather_df_season['season'] = np.where(weather_df_season['time'].dt.month.isin([11, 12]),
                                        weather_df_season['time'].dt.year,
                                        weather_df_season['time'].dt.year - 1)
    weather_df_season['is_snow_day'] = weather_df_season['snowfall_sum'] >= 0.1
    weather_df_season['is_freezing_day'] = weather_df_season['temperature_2m_mean'] < 0
    resort_season_weather_grouped = weather_df_season.groupby(['resort_id', 'season']).agg(
        snowfall_cm_per_season = ('snowfall_sum', 'sum'),
        snow_days_per_season = ('is_snow_day', 'sum'),
        freezing_days_per_season = ('is_freezing_day', 'sum')
    )
    resort_season_avg_weather = resort_season_weather_grouped.groupby(['resort_id']).agg(
        avg_snowfall_cm_per_season = ('snowfall_cm_per_season', 'mean'),
        avg_snow_days_per_season = ('snow_days_per_season', 'mean'),
        avg_freezing_days_per_season = ('freezing_days_per_season', 'mean')
    ).reset_index()
    return resort_season_avg_weather

def prepare_resorts_prices():
    with open('raw/prices_monthly.json', 'r', encoding='utf-8') as f:
        resorts_prices = json.load(f)
    prices_df = pd.DataFrame(resorts_prices[1:], columns=resorts_prices[0])
    prices_df_prepared = prices_df.melt(
        id_vars=['resort_id', 'month'],
        value_vars=['adult_price_min_rub', 'adult_price_max_rub'],
        value_name='all_prices'
    )
    resorts_avg_prices_df = prices_df_prepared.groupby('resort_id').agg(
        adult_skipass_avg_rub=('all_prices', 'mean'),
        price_months_count=('month', 'nunique')
    ).reset_index()
    return resorts_avg_prices_df

def prepare_regions_demand_data():
    tourist_nights_df = pd.read_csv('raw/rosstat_tourist_nights.csv', sep=';', encoding='utf-8-sig')
    tourist_nights_2025_df = tourist_nights_df[tourist_nights_df['Ряд'].str.endswith('январь-декабрь')][['Ряд', '2025']].copy()
    tourist_nights_2025_df['region'] = tourist_nights_2025_df['Ряд'].str.split(' — ').str[0]
    tourist_trips_df = pd.read_csv('raw/rosstat_tourist_trips.csv', sep=';', encoding='utf-8-sig')
    tourist_trips_2024_2025_df = tourist_trips_df[tourist_trips_df['Ряд'].str.endswith('январь-декабрь')][['Ряд', '2024', '2025']].copy()
    tourist_trips_2024_2025_df['region'] = tourist_trips_2024_2025_df['Ряд'].str.split(' — ').str[0]
    tourist_trips_2024_2025_df['trips_growth_2025'] = tourist_trips_2024_2025_df['2025'] / tourist_trips_2024_2025_df['2024'] - 1
    region_demand_df = tourist_nights_2025_df[['region', '2025']].merge(
        tourist_trips_2024_2025_df[['region', '2024', '2025', 'trips_growth_2025']],
        on='region',
        how='left',
        suffixes=('_nights', '_trips')
    )
    region_demand_df['avg_stay_nights_2025'] = region_demand_df['2025_nights'] / region_demand_df['2025_trips']
    region_demand_df = region_demand_df.rename(columns={
        '2025_nights': 'nights_2025',
        '2024': 'trips_2024',
        '2025_trips': 'trips_2025',
    })
    return region_demand_df

def prepare_resorts_reference():
    resorts_data = load_resorts_full_data()
    collected_resort_locations = pd.read_csv('raw/coordinate_checks.csv')
    resorts_data_check = resorts_data.merge(
        collected_resort_locations,
        on='resort_id',
        how='left'
    )
    resorts_data_check['distance_km'] = haversine_vector(
        resorts_data_check[['latitude', 'longitude']],
        resorts_data_check[['checked_latitude', 'checked_longitude']]
    )
    resorts_data_check['coordinate_check'] = pd.cut(
        resorts_data_check['distance_km'],
        bins=[0, 1, 3, np.inf],
        labels=['exact', 'approximate', 'mismatch'],
        include_lowest=True
    ).cat.add_categories('unchecked').fillna('unchecked')
    resorts_data_check['is_closed'] = resorts_data_check['resort_id'].isin(CLOSED_RESORTS)
    columns_list = ['resort_id', 'name_ru', 'region', 'latitude', 'longitude',
        'coordinate_quality', 'coordinate_source_title',
        'coordinate_source_url', 'wikidata_id', 'piste_segments_6km',
        'lift_lines_6km', 'lodging_objects_6km', 'food_objects_6km',
        'transport_objects_6km', 'osm_overlap_warning', 'attraction_objects_6km',
        'nearest_scheduled_airport','nearest_airport_iata', 'nearest_airport_distance_km',
        'nearest_airport_municipality', 'completeness_pct', 'quality_flags',
        'collected_at', 'checked_latitude', 'checked_longitude',
        'distance_km', 'coordinate_check', 'is_closed']
    resorts_reference = resorts_data_check[columns_list]
    return resorts_reference

resort_season_avg_weather = prepare_resorts_weather()
save_df_to_csv(resort_season_avg_weather, 'prepared', 'weather_features')
resorts_avg_prices_df = prepare_resorts_prices()
save_df_to_csv(resorts_avg_prices_df, 'prepared', 'resorts_avg_prices')
region_demand_df = prepare_regions_demand_data()
save_df_to_csv(region_demand_df, 'prepared', 'region_demand')

resorts_data = load_resorts_full_data()
region_data = pd.read_csv('prepared/region_demand.csv')
not_matched_regions = resorts_data[~resorts_data['region'].isin(region_data['region'])]['region'].unique()
resorts_reference = prepare_resorts_reference()
save_df_to_csv(resorts_reference, 'prepared', 'resorts_reference')
