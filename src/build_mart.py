import numpy as np
import pandas as pd

from utils import (
    save_df_to_csv
)

REGION_NAME_MAP = {
    'Кемеровская область': 'Кемеровская область - Кузбасс',
    'Республика Северная Осетия — Алания': 'Республика Северная Осетия - Алания'
}

def create_resorts_mart():
    resort_reference_df = pd.read_csv('prepared/resorts_reference.csv')
    resorts_avg_prices_df = pd.read_csv('prepared/resorts_avg_prices.csv')
    weather_features_df = pd.read_csv('prepared/weather_features.csv')
    region_demand_df = pd.read_csv('prepared/region_demand.csv')
    resort_reference_df['region_rosstat'] = resort_reference_df['region'].replace(REGION_NAME_MAP)
    resorts_full_data = resort_reference_df.merge(
        resorts_avg_prices_df,
        how='left',
        on='resort_id'
    ).merge(
        weather_features_df,
        how='left',
        on='resort_id'
    ).merge(
        region_demand_df.rename(columns={'region':'region_rosstat'}),
        how='left',
        on='region_rosstat'
    )
    resorts_full_data['food_attraction_objects_6km'] = resorts_full_data['food_objects_6km'] + resorts_full_data['attraction_objects_6km']
    df_len = len(resorts_full_data)
    if df_len != len(resort_reference_df):
        raise ValueError(f"Витрина не будет создана. Количество строк в итоговой таблице не соответствует количеству курортов.")
    print(f'Всего строк {df_len} - соответствует количеству курортов.')

    unique_resorts = resorts_full_data['resort_id'].nunique()
    if unique_resorts != df_len:
        raise ValueError(f"Витрина не будет создана. Есть дубликаты курортов - {resorts_full_data[resorts_full_data['resort_id'].duplicated()]['resort_id'].tolist()}.")
    print(f'Количество уникальных курортов ({unique_resorts}), соответвует количеству строк в таблице ({df_len}). Все курорты уникальны.')

    null_trips_2025_count = resorts_full_data['trips_2025'].isna().sum()
    if null_trips_2025_count != 0:
        raise ValueError(f"Витрина не будет создана. В поездках за 2025 есть пропуски для курортов {resorts_full_data[resorts_full_data['trips_2025'].isna()]['resort_id'].tolist()}")
    print(f"Для всех курортов есть даные по поездкам в 2025 году.")
    resorts_full_data['confidence_score'] = 50 * resorts_full_data['completeness_pct'] + 25 * resorts_full_data['adult_skipass_avg_rub'].notna() + 25 * resorts_full_data['coordinate_quality'].str.contains('resort_or_complex_page')
    return resorts_full_data

resort_features = create_resorts_mart()
save_df_to_csv(resort_features, 'mart', 'resort_features')
print(resort_features.info())
print(f"Всего строк {len(resort_features)}")
print(f"Уникальных id курортов{resort_features['resort_id'].nunique()}")
print(f"В столбце `trips_2025` {resort_features['trips_2025'].isna().sum()} отсутствующих значений")

print(resort_features)
