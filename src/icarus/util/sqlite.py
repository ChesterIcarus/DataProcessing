
import sqlite3
import re
import os


class SqliteUtil:
    def __init__(self, database, readonly=False, timeout=30):
        self.name = database
        self.timeout = timeout
        self.readonly = readonly
        self.connection = None
        self.cursor = None
        self.open(timeout)


    def open(self, timeout):
        if self.connection is not None:
            self.close()
        if self.readonly:
            path = os.path.abspath(self.name)
            uri = f'file:{path}?mode=ro'
            self.connection = sqlite3.connect(uri, uri=True, timeout=timeout)
        else: 
            self.connection = sqlite3.connect(self.name, timeout=timeout)
        self.cursor = self.connection.cursor()


    def close(self):
        self.connection.close()
        self.connection = None
        self.cursor = None


    def count_rows(self, table):
        self.cursor.execute(f'SELECT COUNT(*) from {table};')
        return self.cursor.fetchall()[0][0]

    
    # def fetch_rows(self, chunk=None):
    #     if chunk is None:
    #         for row in self.cursor.fetchall():
    #             yield row
    #     else:
    #         rows = self.cursor.fetchmany(chunk)
    #         while len(rows):
    #             for row in rows:
    #                 yield row
    #             rows = self.cursor.fetchmany(chunk)


    def fetch_rows(self, chunk=None, block=1000000):

        def chunks(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        rows = self.cursor.fetchmany(block)
        while len(rows):
            if chunk is None:
                for row in rows:
                    yield row
            else:
                for row in chunks(rows, chunk):
                    yield row
            rows = self.cursor.fetchmany(block)

    
    def fetch_tables(self):
        self.cursor.execute('SELECT name FROM sqlite_master WHERE type="table";')
        tables = self.cursor.fetchall()
        return [table[0] for table in tables]

    
    def drop_temporaries(self):
        tables = self.fetch_tables()
        drop = [table for table in tables if re.match(r'^temp_[0-9]+$', table)]
        self.drop_table(*drop)


    def table_exists(self, *tables):
        exist = self.fetch_tables()
        return tuple(set(exist).intersection(tables))


    def drop_table(self, *tables):
        for table in tables:
            self.cursor.execute(f'DROP TABLE IF EXISTS {table};')

    
    def insert_values(self, table, values, num_cols):
        self.cursor.executemany(
            f'INSERT INTO {table} VALUES({", ".join("?" * num_cols)});', values)
