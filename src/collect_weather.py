import json
import os
import requests
import time
from datetime import datetime

URL = 'https://archive-api.open-meteo.com/v1/archive'
MODELS = 'era5'
DAILY = ['temperature_2m_mean', 'snowfall_sum']
START_DATE = '2021-11-01'
END_DATE = '2026-04-30'

def get_meteo_data(resort_id, latitude, longitude):
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'start_date': START_DATE,
        'end_date': END_DATE,
        'daily': DAILY,
        'models': MODELS
    }
    for attempt in range(3):
        try:
            response = requests.get(URL, params=params, timeout=10)
            response.raise_for_status()
            resort_weather_data = {
                'resort_id': resort_id,
                'collected_at': datetime.now().isoformat(),
                'requested_params': params,
                'weather_data': response.json()
            }
            with open(f'raw/weather/data_{resort_id}.json', 'w', encoding='utf-8') as f:
                json.dump(resort_weather_data, f, ensure_ascii=False, indent=4)
            return True
        except requests.exceptions.RequestException as e:
            print(f'Внимание! Ошибка при получении данных для курорта {resort_id}: {e}, попытка {attempt + 1} из 3')
            time.sleep(30)
    return False

def load_resort_locations():
    with open('raw/resorts.json', 'r', encoding='utf-8') as f:
        resorts = json.load(f)
    resort_locations = []
    resort_id_index = resorts[0].index('resort_id')
    latitude_index = resorts[0].index('latitude')
    longitude_index = resorts[0].index('longitude')
    for resort in resorts[1:]:
        resort_id = resort[resort_id_index]
        latitude = resort[latitude_index]
        longitude = resort[longitude_index]
        resort_location = (resort_id, latitude, longitude)
        resort_locations.append(resort_location)
    return resort_locations

os.makedirs('raw/weather', exist_ok=True)
unprocessed_resorts = []
processed_resorts = 0
total_resorts = load_resort_locations()
for resort_id, latitude, longitude in total_resorts:
    success = get_meteo_data(resort_id, latitude, longitude)
    time.sleep(1)
    if success is False:
        unprocessed_resorts.append(resort_id)
    else:
        processed_resorts += 1
if unprocessed_resorts:
    print(f'Не обработано {len(unprocessed_resorts)} курортов: {unprocessed_resorts} из {len(total_resorts)}')
else:
    print(f'Обработаны все курорты ({processed_resorts} из {len(total_resorts)}), ошибок нет')



