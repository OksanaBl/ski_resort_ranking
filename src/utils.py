import json
import os
import pandas as pd

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

def load_resorts_full_data():
    with open('raw/resorts.json', 'r', encoding='utf-8') as f:
        resorts = json.load(f)
    mentor_resorts_data_df = pd.DataFrame(resorts[1:], columns=resorts[0])
    return mentor_resorts_data_df

def save_df_to_csv(df, folder, file_name):
    os.makedirs(folder, exist_ok=True)
    df.to_csv(f'{folder}/{file_name}.csv', index=False, encoding='utf-8-sig')
    print(f'Данные {file_name} для {len(df)} строк сохранены.')