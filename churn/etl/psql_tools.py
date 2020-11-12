from pathlib import Path
import io

import pandas as pd
import psycopg2
from sqlalchemy import create_engine


class TransactionManager:
    def __init__(
            self,
            database='kkbox_churn',
            user='mariosk',
            password='pass',
            host='localhost',
            port=5432):
        """Wrapper around psycopg2 and sqlalchemy which provides simple functions to handle psql transactions.
        NOTE: This class allows pretty unsafe transactions (e.g. pass a query as string) which could lead to sql
        injection. Use with caution!

        Args:
            database: database name
            user: user name
            password: user password
            host: the hostname of the database server
            port: the database server port
        """
        self.conn_dict = dict(
            database=database,
            user=user,
            password=password,
            host=host,
            port=port)

        self.conn_string = f'postgresql://{user}:{password}@{host}:{port}/{database}'

    def pd_read_psql(self, query):
        """Query data from the database to a pandas dataframe.

        Args:
            query: a sql query

        Returns:
            A dataframe containing the output table of the query.
        """
        if query.endswith(';'):
            query = query[:-1]
        copy_sql = f'COPY ({query}) TO STDOUT WITH CSV HEADER;'
        with psycopg2.connect(**self.conn_dict) as conn:
            try:
                with conn.cursor() as cursor:
                    with io.StringIO() as cache:
                        cursor.copy_expert(copy_sql, cache)
                        cache.seek(0)
                        return pd.read_csv(cache)
            except Exception as e:
                print(e)
                conn.rollback()

    def import_csv_to_table(self, path, table_name=None, drop_old_table=False):
        """Import a csv file to a table in the database.

        Args:
            path: the filepath of the csv to be imported
            table_name: optional name for the table. If not set, it defaults to the name of the file.
            drop_old_table: if set to true, it will drop any existing table with the given name before importing
        """
        path = Path(path)
        if table_name is None:
            table_name = path.stem
        with psycopg2.connect(**self.conn_dict) as conn:
            engine = create_engine(self.conn_string)
            self._create_table_from_csv(path, conn, engine, table_name, drop_old_table)
            self._stream_from_file_to_psql(path, conn, table_name)

    @staticmethod
    def _execute_command(cursor, command, conn):
        try:
            cursor.execute(command)
            conn.commit()
        except Exception as e:
            print(e)
            conn.rollback()

    @staticmethod
    def _create_table_from_csv(path, conn, engine, table_name, drop_old_table=False):
        single_line_table = next(pd.read_csv(path, chunksize=1000))

        if drop_old_table:
            with conn.cursor() as cursor:
                TransactionManager._execute_command(cursor, f'DROP TABLE IF EXISTS {table_name}', conn)

        single_line_table.to_sql(table_name, engine, index=False, if_exists='fail')
        with conn.cursor() as cursor:
            TransactionManager._execute_command(cursor, f'DELETE FROM {table_name};', conn)

    @staticmethod
    def _stream_from_file_to_psql(path, conn, table_name):
        with open(path, 'r') as f:
            next(f)  # skip the header
            with conn.cursor() as cursor:
                try:
                    cursor.copy_from(f, table_name, sep=",")
                    conn.commit()
                except Exception as e:
                    print(f'Failed to ingest {path.stem}: {e}')
