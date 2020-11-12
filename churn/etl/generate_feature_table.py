from pathlib import Path
from datetime import datetime
import time
import argparse

import pandas as pd

from churn.etl import psql_tools


def generate(version, transaction_manager=None):
    """Script to generate a table with all the interesting features needed for training a model. The time series
    features are here aggregated for each user, thus we loose the granular time information. The pre-processing
    is based on the following Kaggle kernel: https://www.kaggle.com/garylee29181/fork-of-churn.

    Args:
        version: the version of the dataset, one of {1, 2}
        transaction_manager: an optional transaction manager to handle the connection to psql. If not set, it will
            default to my local database
    """
    start_time = time.time()
    version_suffix = '' if version == 1 else '_v2'
    if transaction_manager is None:
        transaction_manager = psql_tools.TransactionManager()

    print('Processing labels...')
    labels_query = f"""
    SELECT * FROM train{version_suffix}
    """
    labels = transaction_manager.pd_read_psql(labels_query)

    print('Processing user logs, this can take a while...')
    user_logs_query = f"""
    SELECT 
        msno, 
        sum(total_secs) / (sum(num_25) + sum(num_50) + sum(num_75) + sum(num_985) + sum(num_100)) as secs_per_song, 
        count(date) AS days_active 
    FROM user_logs{version_suffix}
    GROUP BY msno
    """
    user_logs = transaction_manager.pd_read_psql(user_logs_query)

    print('Processing user transactions...')
    transactions_query = f"""
    SELECT 
        msno, 
        avg(payment_method_id) as payment_method_id, 
        avg(payment_plan_days) as payment_plan_days, 
        avg(plan_list_price) as plan_list_price, 
        avg(actual_amount_paid) as actual_amount_paid, 
        avg(is_auto_renew) as is_auto_renew
    FROM transactions{version_suffix}
    GROUP BY msno
    """
    transactions = transaction_manager.pd_read_psql(transactions_query)

    print('Processing members...')
    members_query = 'SELECT msno, gender, registered_via, registration_init_time FROM members_v3'
    current = datetime.strptime('20170228', "%Y%m%d").date()
    members = (
        transaction_manager.pd_read_psql(members_query)
        .assign(
            gender=lambda df: df['gender'].map({'male': 1, 'female': 2}),
            num_days=lambda df: df['registration_init_time'].apply(
                lambda x: (
                    (current - datetime.strptime(str(int(x)), "%Y%m%d").date()).days
                    if pd.notnull(x)
                    else "NAN")))
        .drop(columns='registration_init_time'))

    print('Merging all tables...')
    all_features = (
        labels
        .merge(user_logs, on='msno', how='left')
        .merge(transactions, on='msno', how='left')
        .merge(members, on='msno', how='left')
        .fillna(-1)
    )

    print('Exporting output to disk and database...')
    features_cache_path = Path(f'~/data/kkbox-churn/proc_all_features_{version}.csv').expanduser()
    all_features.to_csv(features_cache_path, index=False)

    transaction_manager.import_csv_to_table(features_cache_path)
    print(f'--- {time.time() - start_time} seconds ---')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a feature table for v1 or v2 of the datasets.')
    parser.add_argument('--dataset-version', type=int, help='version of the dataset, one of {1, 2}')

    args = parser.parse_args()
    generate(args.dataset_version)
