from pathlib import Path

from tqdm import tqdm

from churn.etl import psql_tools


def import_tables(files_dir=Path('/home/mariosk/data/kkbox-churn'), create_msno_index=True):
    """Import all the csv files in a given directory to the database.

    Args:
        files_dir: the directory containing the csv files to upload to the database
        create_msno_index: if true, adds an index on msno on each table. Implies that each file contains an msno column.
    Returns:

    """
    files_dir = Path(files_dir)
    files_to_ingest = list(files_dir.glob('**/*.csv'))
    transaction_manager = psql_tools.TransactionManager()

    for path in tqdm(files_to_ingest):
        transaction_manager.import_csv_to_table(path)

        if create_msno_index:
            transaction_manager.create_index_on_msno(path)
