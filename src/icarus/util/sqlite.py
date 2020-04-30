
import sqlite3


class SqliteUtil:
    def __init__(self, database):
        self.name = database
        self.connection = None
        self.cursor = None
        self.open()


    def open(self):
        if self.connection is not None:
            self.close()
        self.connection = sqlite3.connect(self.name)
        self.cursor = self.connection.cursor()


    def close(self):
        self.connection.close()
        self.connection = None
        self.cursor = None


    def count_rows(self, table):
        self.cursor.execute(f'SELECT COUNT(*) from {table};')
        return self.cursor.fetchall()[0][0]

    
    def fetch_tables(self):
        self.cursor.execute('SELECT name FROM sqlite_master WHERE type="table";')
        tables = self.cursor.fetchall()
        return [table[0] for table in tables] 


    def table_exists(self, *tables):
        exist = self.fetch_tables()
        return tuple(set(exist).intersection(tables))


    def drop_table(self, *tables):
        for table in tables:
            self.cursor.execute(f'DROP TABLE IF EXISTS {table};')

    
    def insert_values(self, table, values, num_cols):
        self.cursor.executemany(
            f'INSERT INTO {table} VALUES({", ".join("?" * num_cols)});', values)
