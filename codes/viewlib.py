import os
import shutil
import watts
import click
import json
import re


from pathlib import Path
from collections import namedtuple

sys_path = Path(__file__).parent.parent / 'files/manager.json'

class Database(dict):
    
    def __init__(self, name, template, path, parameters):
        super().__init__(name=name, template=template,
                         path=path, parameters=parameters)

    @property
    def name(self):
        return self['name']

    @property
    def template(self):
        return self['template']

    @property
    def path(self):
        return self['path']

    @property
    def parameters(self):
        return self['parameters']

    @classmethod
    def from_dict(cls, d):
        return cls(d['name'], d['template'], d['path'], d['parameters'])




def get_data(path):
    if not Path(path).exists():
        raise ValueError(f"Path {path} does not exist.")
    
    with open(path, 'r') as f:
        if f.read() == '':
            return []

    with open(path, 'r') as f:
        data = json.load(f)

    return data

def get_database_list(path):
    database_list = get_data(path)['database_list']
    database_list = [Database.from_dict(database) for database in database_list]
    return database_list

def set_database_list(database_list, path):
    data = get_data(path)
    data['database_list'] = [database for database in database_list]
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def get_current_db(path):
    current_db = get_data(path)['current_db']
    return current_db

def set_current_db(current_db, path):
    data = get_data(path)
    data['current_db'] = current_db
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

@click.group()
def cli():
    pass

@click.command(help='Initialize the xslib manager.')
def init():
    if not Path(sys_path).exists():
        Path(sys_path).touch()

    confirm = input("Are you sure to initialize the xslib manager? (y/n)")
    if confirm != 'y':
        return

    with open(sys_path, 'w') as f:
        json.dump({'database_list': [], 'current_db': None}, f)
    click.echo("The xslib manager has been initialized successfully.")

@click.command(help='List existing databases.')
@click.option('--name', '-n', type=str, help='The name of the database.', default=None)
def list(name):
    database_list = get_database_list(sys_path)
    if name is not None:
        matched_database_list = [database for database in database_list if re.search(name, database.name)]
    else:
        matched_database_list = database_list

    for database in matched_database_list:
        print("|================================================================================|")
        print(f"|Database: {database.name:<70s}|")
        print(f"|Template: {database.template:<70s}|")
        print(f"|Path    : {database.path:<70s}|")
        print("|--------------------------------------------------------------------------------|")
        for parameter in database.parameters:
            print(f"|{parameter['name']:<29s}|{parameter['type']:<50s}|")
    print("|================================================================================|")

@click.command(help='Create a new database.')
@click.option('--name', '-n', type=str, help='The name of the database.', required=True)
@click.option('--template', '-t', type=str, help='The file path of the database model template.', required=True)
@click.option('--path', '-p', type=str, help='The path of the database manager.', required=True)
def create(name, template, path):
    database_list = get_database_list(sys_path)
    if name in [database.name for database in database_list]:
        raise ValueError(f"Database {name} already exists. Please change the name.")
    
    template, path = Path(template), Path(path)
    if not template.exists():
        raise ValueError(f"Template file {template} does not exist. Please check the path.")
    if not path.exists():
        raise ValueError(f"Path {path} does not exist.  Please check the path.")

    shutil.copy(template, path / template.name)
    path = str(path.resolve())
    template = path + '/' + template.name
    with open(path + '/.libdir.json', 'r') as f:
        json.dump([], f)

    with open(template, 'r') as f:
        content = f.read()
    parameters = re.findall(r'\{\{\s*([A-z][A-z0-9\_]*\:[A-z]+)\s*\}\}', content)
    parameters = [p.split(':') for p in parameters]
    parameters = [{'name': p[0], 'type': p[1]} for p in parameters]

    database = Database(name, template, path, parameters)
    database_list.append(database)
    set_database_list(database_list, sys_path)

    click.echo(f"Database \"{database.name}\" has been created successfully.")

@click.command(help='Remove a database.')
@click.option('--name', '-n', type=str, help='The name of the database.', required=True)
@click.option('--remove_all_files', type=bool, help='If remove the files of the database.', default=False)
def remove(name, remove_all_files):
    confirm = input(f"Are you sure to remove the database containing \"{name}\"? (y/n)")
    if confirm != 'y':
        return

    database_list = get_database_list(sys_path)
    matched_database_list = [database for database in database_list if re.search(name, database.name)]
    unmatched_database_list = [database for database in database_list if not re.search(name, database.name)]

    for database in matched_database_list:
        if remove_all_files:
            os.remove(database.path)
        click.echo(f"Database {database.name} has been removed successfully.")
        
    set_database_list(unmatched_database_list, sys_path)

@click.command(help='Enter a database.')
@click.option('--name', '-n', type=str, help='The name of the database.', required=True)
def enter(name):
    database_list = get_database_list(sys_path)
    if name not in [database.name for database in database_list]:
        raise ValueError(f"Database {name} does not exist.")
    set_current_db(name, sys_path)
    click.echo(f"Database {name} has been entered successfully.")
    click.echo("All 'vlib db' commands will be redirected to the database.")

cli.add_command(init)
cli.add_command(list)
cli.add_command(create)
cli.add_command(remove)
cli.add_command(enter)


@click.group()
def db():
    pass
cli.add_command(db)

@click.command(help='View the template file')
def template():
    current_db = get_current_db(sys_path)
    if current_db is None:
        click.echo("Please enter a database first.")
        return
    database_list = get_database_list(sys_path)
    database = [database for database in database_list if database.name == current_db][0]
    os.system(f'vim {database.template}')
db.add_command(template)

# @click.command(help='View the parameter combinations')
# def parameter():
#     current_db = get_current_db(sys_path)
#     if current_db is None:
#         click.echo("Please enter a database first.")
#         return
#     database_list = get_database_list(sys_path)
#     database = [database for database in database_list if database.name == current_db][0]
#     for parameter in database.parameters:
#         print(f"{parameter['name']:<29s}{parameter['type']:<50s}")
# db.add_command(parameter)

def get_openmc_model_builder(parameters):
    watts.TemplateRenderer()
    pass

# @click.command()
# def run():
#     current_db = get_current_db(sys_path)
#     if current_db is None:
#         click.echo("Please enter a database first.")
#         return
#     database_list = get_database_list(sys_path)
#     database = [database for database in database_list if database.name == current_db][0]
    
#     plugin = watts.PluginOpenMC(model_builder=)
    

if __name__ == "__main__":
    cli()




