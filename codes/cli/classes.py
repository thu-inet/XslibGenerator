import os
import shutil
import json
import re

from typing import List
from pathlib import Path
from contextlib import contextmanager


sys_path = Path(__file__).parent.parent.parent / 'files/manager.json'


class Manager:

    with open(sys_path, 'r') as f:
        data = f.read()

    if data == '':
        with open(sys_path, 'w') as f:
            f.write(json.dumps({'database_list': [], 'current_db': None}, indent=2))

    with open(sys_path, 'r') as f:
        data = json.load(f)

    @classmethod
    def read(cls, key):
        return cls.data[key]

    @classmethod
    def write(cls, key, value):
        cls.data[key] = value
        data = json.dumps(cls.data, indent=2)
        with open(sys_path, 'w') as f:
            f.write(data)

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
    
    def __init__(self, name, template, script, path):
        super().__init__(name=name, template=template,
                         script=script, path=path)

    @property
    def name(self):
        return self['name']

    @property
    def template(self):
        return self['template']

    @property
    def script(self):
        return self['script']

    @property
    def path(self):
        return self['path']

    def get_template_parameters(self):
        with open(self.template, 'r') as f:
            content = f.read()
        parameters = re.findall(r'\{\{\s*([A-z]+\_[A-z][A-z0-9\_]*)\s*\}\}', content)
        parameters = [{'name': p[p.index('_')+1:], 'type': p[:p.index('_')]} for p in parameters]
        return parameters

    def get_script_parameters(self):
        with open(self.script, 'r') as f:
            content = f.read()
        parameters = re.findall(r'\{\{\s*([A-z]+\_[A-z][A-z0-9\_]*)\s*\}\}', content)
        parameters = [{'name': p[p.index('_')+1:], 'type': p[:p.index('_')]} for p in parameters]
        return parameters

    @classmethod
    def from_dict(cls, d):
        return cls(d['name'], d['template'], d['script'], d['path'])

class DatabaseManager:
    
    # In the developing phrase, the code always corrupts here when something is changed
    # so we make it a try-except block to make the code can start normally
    # and database can be re-configured.
    try:
        current_db, database = Manager().get_current_database()
        if current_db is not None:
            libdir = Path(database.path) / '.libdir.json'
            # print(current_db, database, libdir)
            if libdir.exists():
                with open(libdir, 'r') as f:
                    data = json.load(f)
    except:
        print("Initialization of Database Manager failed.")
        pass

    @classmethod
    def read(cls, key):
        return cls.data[key]

    @classmethod
    def write(cls, key, value):
        cls.data[key] = value
        data = json.dumps(cls.data, indent=2)
        with open(cls.libdir, 'w') as f:
            f.write(data)

    @classmethod
    def get_xslib_list(cls) -> List[dict]:
        return cls.data.copy()

    @classmethod
    def add_xslib(cls, task, path, template_render_parameters, script_render_parameters):
        xslib_info = {'task': task, 'path': path}
        xslib_info.update(template_render_parameters)
        xslib_info.update(script_render_parameters)
        cls.data.append(xslib_info)
        data = json.dumps(cls.data, indent=2)
        with open(cls.libdir, 'w') as f:
            f.write(data)

    @classmethod
    def remove_xslib(cls, task):
        if task not in [xslib['task'] for xslib in cls.data]:
            raise ValueError(f"Task {task} does not exist.")
        cls.data = [xslib for xslib in cls.data if xslib['task'] != task]
        data = json.dumps(cls.data, indent=2)
        with open(cls.libdir, 'w') as f:
            f.write(data)

    @classmethod
    def remove_all_xslib(cls):
        cls.data = []
        data = json.dumps(cls.data, indent=2)
        with open(cls.libdir, 'w') as f:
            f.write(data)

    @classmethod
    def set_xslib(cls, task, name, value):

        if task not in [xslib['task'] for xslib in cls.data]:
            raise ValueError(f"Task {task} does not exist.")

        xslib = [xslib for xslib in cls.data if xslib['task'] == task][0]
        if name not in xslib.keys():
            raise ValueError(f"Name {name} does not exist.")
        
        if name == 'task':
            if value in [xslib['task'] for xslib in cls.data]:
                raise ValueError(f"Task {value} already exists.")
            xslib[name] = value
            shutil.move(xslib['path'], Path(cls.database.path).parent / f"{value}")
            xslib['path'] = str(Path(cls.database.path).parent / f"{value}")
        elif name == 'path':
            raise ValueError("Path should be changed according to the task.")
        else:
            if isinstance(xslib[name], float):
                value = float(value)
            elif isinstance(xslib[name], int):
                value = int(value)
            else:
                pass

        xslib[name] = value
        data = json.dumps(cls.data, indent=2)
        with open(cls.libdir, 'w') as f:
            f.write(data)

@contextmanager
def run_in_folder(folder):
    cwd = os.getcwd()
    try:
        os.chdir(folder)
        yield
    finally:
        os.chdir(cwd)