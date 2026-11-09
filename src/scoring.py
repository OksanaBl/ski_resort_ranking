import numpy as np
import pandas as pd

from utils import save_df_to_csv

def calc_min_max_score(df, column):
    score = 100 * (df[column] - df[column].min()) / (df[column].max() - df[column].min())
    return score

def calc_log_min_max_score(df, column):
    score = 100 * (np.log1p(df[column]) - np.log1p(df[column].min())) / (np.log1p(df[column].max()) - np.log1p(df[column].min()))
    return score

def calc_inverse_log_min_max_score(df, column):
    score = 100 - calc_log_min_max_score(df, column)
    return score

def calc_growth_score(df, column):
    score =  np.clip(50 + 200 * df[column], 0, 100)
    return score

def calc_stay_score(df, column):
    score =  np.clip((df[column] - 1) / 6 * 100, 0, 100)
    return score

scoring_config = pd.DataFrame({
    "parameter": ['Поездки по региону', 'Рост поездок', 'Средняя длительность', 'Трассы OSM',
                'Подъёмники OSM', 'Размещение OSM', 'Питание и места интереса', 'Снежные дни',
                'Морозные дни', 'Сезонный снегопад', 'Расстояние до аэропорта',
                'Локальный транспорт OSM', 'Средняя цена ски пасса'],
    "column": ['trips_2025', 'trips_growth_2025', 'avg_stay_nights_2025', 'piste_segments_6km',
               'lift_lines_6km', 'lodging_objects_6km', 'food_attraction_objects_6km',
               'avg_snow_days_per_season', 'avg_freezing_days_per_season', 'avg_snowfall_cm_per_season',
               'nearest_airport_distance_km', 'transport_objects_6km', 'adult_skipass_avg_rub'],
    "func": [calc_log_min_max_score, calc_growth_score, calc_stay_score, calc_log_min_max_score,
             calc_log_min_max_score, calc_log_min_max_score, calc_log_min_max_score,
             calc_min_max_score, calc_min_max_score, calc_log_min_max_score,
             calc_inverse_log_min_max_score, calc_log_min_max_score, calc_inverse_log_min_max_score],
    "param_group": ['Региональный спрос', 'Региональный спрос', 'Региональный спрос',
                    'Инфраструктура', 'Инфраструктура', 'Инфраструктура', 'Инфраструктура',
                    'Зимние условия', 'Зимние условия', 'Зимние условия',
                    'Доступность', 'Доступность', 'Цена'],
    "basic_scenario": [25, 10, 5, 10, 7, 5, 3, 8, 6, 6, 8, 2, 5]
})
scoring_config['climate_scenario'] = np.where(scoring_config['parameter'].isin(['Снежные дни', 'Морозные дни', 'Сезонный снегопад']), scoring_config['basic_scenario'] * 2, scoring_config['basic_scenario'] * 0.75)
scoring_config['access_scenario'] = np.where(scoring_config['parameter'].isin(['Расстояние до аэропорта', 'Локальный транспорт OSM']), scoring_config['basic_scenario'] * 3, scoring_config['basic_scenario'] * (70 / 90))

scoring_config['demand_group_scenario'] = np.where(scoring_config['param_group'].isin(['Региональный спрос']), scoring_config['basic_scenario'] * 1.2, scoring_config['basic_scenario'] * (52 / 60))
scoring_config['infrastructure_group_scenario'] = np.where(scoring_config['param_group'].isin(['Инфраструктура']), scoring_config['basic_scenario'] * 1.2, scoring_config['basic_scenario'] * (70 / 75))
scoring_config['weather_group_scenario']  = np.where(scoring_config['param_group'].isin(['Зимние условия']), scoring_config['basic_scenario'] * 1.2, scoring_config['basic_scenario'] * (76 / 80))
scoring_config['accessibility_group_scenario'] = np.where(scoring_config['param_group'].isin(['Доступность']), scoring_config['basic_scenario'] * 1.2, scoring_config['basic_scenario'] * (88 / 90))
scoring_config['price_group_scenario'] = np.where(scoring_config['param_group'].isin(['Цена']), scoring_config['basic_scenario'] * 1.2, scoring_config['basic_scenario'] * (94 / 95))

def validate_sum_weights(scoring_config):
    for column in [col for col in scoring_config.columns if col.endswith('_scenario')]:
        total_weight = scoring_config[column].sum()
        if abs(total_weight - 100) >= 0.001:
            raise ValueError(f"Сумма весов для сценария '{column}' должна быть равна 100, но она равна {total_weight}.")

def validate_score_columns(df, column, mask):
    if round(df[column].min(), 6) < 0 or round(df[column].max(), 6) > 100 or df[column].isna().any(): # защита от ошибок округления, чтобы не было false positive
        raise ValueError(f"Значения в столбце '{column}' должны быть в диапазоне от 0 до 100 и не содержать NaN.")
    if mask.sum() > 0:
        print(f'Для колонки {column} есть пропуски в данных, количество пропусков: {mask.sum() }. Они заменены на 50 при расчете скоринга.')

def calculate_all_scores(df, scoring_config):
    for _, row in scoring_config.iterrows():
        column_name = row['column']
        function = row['func']
        df[f'{column_name}_score'] = function(df, column_name)
        mask = df[f'{column_name}_score'].isna()
        missed_data = df.loc[mask, 'quality_flags'].fillna('')
        df.loc[mask, 'quality_flags'] = missed_data.where(missed_data == '', missed_data +'; ') + f'нет данных {column_name}'
        df[f'{column_name}_score'] =  df[f'{column_name}_score'].fillna(50) # Заполняем NaN значением 50, чтобы не было влияния на итоговый скоринг
        validate_score_columns(df, f'{column_name}_score', mask)
    return df

def calculate_final_scores(df, df_contribution, df_resort_scores, scoring_config, scenario_type):
    if scoring_config[scenario_type].isna().any():
        raise ValueError(f"Обнаружен пропуск в весе параметра для сценария '{scenario_type}'. Пожалуйста, проверьте данные.")
    for _, row in scoring_config.iterrows():
        column_name = row['column']
        param_weight = row[scenario_type]
        df_contribution[f'{column_name}_contribution_{scenario_type}'] = df[f'{column_name}_score'] * param_weight / 100
    df_contribution[f'popularity_score_{scenario_type}'] = df_contribution[[col for col in df_contribution.columns if col.endswith(f'_contribution_{scenario_type}')]].sum(axis=1)

    df_resort_scores =  df_resort_scores.merge(
        df_contribution[['resort_id', f'popularity_score_{scenario_type}']],
        on='resort_id',
        how='left'
    )
    df_resort_scores[f'rank_{scenario_type}'] =  df_resort_scores[f'popularity_score_{scenario_type}'].rank(method='min', ascending=False).astype(int)
    return df_contribution, df_resort_scores

def get_param_group_contribution(contribution_scores, scoring_config, scenario_type):
    param_contributions = contribution_scores[['resort_id']].copy()
    for param_group in scoring_config['param_group'].unique():
        column_list = (scoring_config[scoring_config['param_group'] == param_group]['column'] + f'_contribution_{scenario_type}').tolist()
        param_contributions[param_group] = contribution_scores[column_list].sum(axis=1)
    return param_contributions

df = pd.read_csv('mart/resort_features.csv')
# проверка корректности распределения весов по сценариям. Сумма весов по каждому сценарию должна быть равна 100
validate_sum_weights(scoring_config)
save_df_to_csv(scoring_config[['parameter', 'column', 'param_group'] +[col for col in scoring_config.columns if col.endswith('_scenario')]], 'mart', 'scoring_config')
calculate_all_scores(df, scoring_config)
df_contribution = df[['resort_id']].copy()
df_resort_scores = df[['resort_id', 'name_ru', 'region', 'quality_flags', 'confidence_score', 'is_closed']].copy()
for scenario in [col for col in scoring_config.columns if col.endswith('_scenario')]:
    df_contribution, df_resort_scores = calculate_final_scores(df, df_contribution, df_resort_scores, scoring_config, scenario)
sorted_df_resort_scores = df_resort_scores.sort_values(by='rank_basic_scenario', ascending=True).reset_index(drop=True)
sorted_df_resort_scores['basic_climat_scenario_diff'] = sorted_df_resort_scores['rank_basic_scenario'] - sorted_df_resort_scores['rank_climate_scenario']
sorted_df_resort_scores['basic_access_scenario_diff'] = sorted_df_resort_scores['rank_basic_scenario'] - sorted_df_resort_scores['rank_access_scenario']
save_df_to_csv(df_contribution, 'mart', 'contribution_scores')
save_df_to_csv(sorted_df_resort_scores, 'mart', 'resort_scores')
param_group_contribution = get_param_group_contribution(df_contribution, scoring_config, 'basic_scenario')
rating_columns = ['resort_id'] + [col for col in sorted_df_resort_scores.columns
                                  if col.startswith(('popularity_score_', 'rank_')) or col.endswith('_diff')]
resort_rating_full = (df
    .merge(param_group_contribution, on='resort_id', how='left')
    .merge(sorted_df_resort_scores[rating_columns], on='resort_id', how='left')
    .sort_values('rank_basic_scenario')
    .reset_index(drop=True))
resort_rating_full['resort_status'] = np.where(resort_rating_full['is_closed'], 'закрыт', 'работает')
save_df_to_csv(resort_rating_full, 'mart', 'resort_rating_full')
print(df_contribution.info())
print(sorted_df_resort_scores.info())
print(sorted_df_resort_scores)
print(resort_rating_full.info())



