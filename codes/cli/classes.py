import os
import shutil
import json
import re

from pathlib import Path
from contextlib import contextmanager


sys_path = Path(__file__).parent.parent.parent / 'files/manager.json'


class Manager:

    with open(sys_path, 'r') as f:
        data = json.load(f)

    # ========================================================================
    # if data['current_db'] is not None:
    #     click.echo(f"Databae \"{data['current_db']}\" has been entered successfully.")
    #     click.echo("All 'vlib db' commands will be redirected to this database.")
    # ========================================================================
    
    @classmethod
    def read(cls, key):
        return cls.data[key]

    @classmethod
    def write(cls, key, value):
        cls.data[key] = value
        with open(sys_path, 'w') as f:
            json.dump(cls.data, f, indent=2)

    @classmethod
    def get_database_list(cls):
        database_list = cls.read('database_list')
        database_list = [Database.from_dict(database) for database in database_list]
        return database_list

    @classmethod
    def set_database_list(cls, database_list):
        if not all([isinstance(database, Database) for database in database_list]):
            raise ValueError("All elements in the database list must be of type Database.")
        cls.write('database_list', [database for database in database_list])    

    @classmethod
    def get_current_db(cls):
        current_db = cls.read('current_db')
        if current_db is None:
            return None
        if current_db not in [database.name for database in cls.get_database_list()]:
            raise ValueError(f"Database {current_db} does not exist.")
        return current_db

    @classmethod
    def set_current_db(cls, current_db):
        if current_db is not None and current_db not in [database.name for database in cls.get_database_list()]:
            raise ValueError(f"Database {current_db} does not exist.")
        cls.write('current_db', current_db)

    @classmethod
    def get_current_database(cls):
        current_db = cls.get_current_db()
        database_list = cls.get_database_list()
        matched_database = [database for database in database_list if database.name == current_db]
        if matched_database == []:
            return None, None
        return current_db, matched_database[0]


class Database(dict):
    
    def __init__(self, name, template, path):
        super().__init__(name=name, template=template,
                         path=path)

    @property
    def name(self):
        return self['name']

    @property
    def template(self):
        return self['template']

    @property
    def path(self):
        return self['path']

    def get_parameters(self):
        with open(self.template, 'r') as f:
            content = f.read()
        parameters = re.findall(r'\{\{\s*([A-z]+\_[A-z][A-z0-9\_]*)\s*\}\}', content)
        parameters = [{'name': p[p.index('_')+1:], 'type': p[:p.index('_')]} for p in parameters]
        return parameters

    @classmethod
    def from_dict(cls, d):
        return cls(d['name'], d['template'], d['path'])

class DatabaseManager:
    
    current_db, database = Manager().get_current_database()
    if current_db is not None:
        libdir = Path(database.path) / '.libdir.json'
        if libdir.exists():
            with open(libdir, 'r') as f:
                data = json.load(f)

    @classmethod
    def read(cls, key):
        return cls.data[key]

    @classmethod
    def write(cls, key, value):
        cls.data[key] = value
        with open(sys_path, 'w') as f:
            json.dump(cls.data, f, indent=2)

    @classmethod
    def get_xslib_list(cls):
        return cls.data

    @classmethod
    def add_xslib(cls, task, path, name_value_pairs):
        xslib_info = {'task': task, 'path': path}
        xslib_info.update(name_value_pairs)
        cls.data.append(xslib_info)
        with open(cls.libdir, 'w') as f:
            json.dump(cls.data, f, indent=2)
    
    @classmethod
    def remove_xslib(cls, task):
        cls.data = [xslib for xslib in cls.data if xslib['task'] != task]
        with open(cls.libdir, 'w') as f:
            json.dump(cls.data, f, indent=2)
            
@contextmanager
def run_in_folder(folder):
    cwd = os.getcwd()
    try:
        os.chdir(folder)
        yield
    finally:
        os.chdir(cwd)