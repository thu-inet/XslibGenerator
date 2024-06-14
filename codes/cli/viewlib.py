import os
import shutil
import watts
import click
import json
import jinja2
import re


from pathlib import Path
from collections import namedtuple

from classes import Database
from classes import sys_path
from classes import Manager, DatabaseManager
from classes import run_in_folder

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
cli.add_command(init)

@click.command(help='List existing databases.')
@click.option('--name', '-n', type=str, help='The name of the database.', default=None)
def list(name):
    database_list = Manager.get_database_list()
    if name is not None:
        matched_database_list = [database for database in database_list if re.match(name, database.name)]
    else:
        matched_database_list = database_list

    for database in matched_database_list:
        print("|================================================================================|")
        print(f"|Database: {database.name:<70s}|")
        print(f"|Template: {database.template:<70s}|")
        print(f"|Path    : {database.path:<70s}|")
        print("|--------------------------------------------------------------------------------|")
        for parameter in database.get_parameters():
            print(f"|{parameter['name']:<29s}|{parameter['type']:<50s}|")
    print("|================================================================================|")
cli.add_command(list)

@click.command(help='Create a new database.')
@click.option('--name', '-n', type=str, help='The name of the database.', required=True)
@click.option('--template', '-t', type=str, help='The file path of the database model template.', required=True)
@click.option('--path', '-p', type=str, help='The path of the database manager.', required=True)
def create(name, template, path):
    database_list = Manager.get_database_list()
    if name in [database.name for database in database_list]:
        raise ValueError(f"Database {name} already exists. Please change the name.")

    template, path = Path(template), Path(path)
    if not template.exists():
        raise ValueError(f"Template file {template} does not exist. Please check the path.")
    if not path.exists():
        raise ValueError(f"Path {path} does not exist.  Please check the path.")

    if template != path / template.name:
        shutil.copy(template, path / template.name)
    path = str(path.resolve())
    template = path + '/' + template.name
    with open(path + '/.libdir.json', 'w') as f:
        json.dump([], f)

    database = Database(name, template, path)
    database_list.append(database)
    Manager.set_database_list(database_list)

    click.echo(f"Database \"{database.name}\" has been created successfully.")
cli.add_command(create)

@click.command(help='Remove a database.')
@click.option('--name', '-n', type=str, help='The name of the database.', required=True)
@click.option('--remove_all_files', type=bool, help='If remove the files of the database.', default=False)
def remove(name, remove_all_files):
    confirm = input(f"Are you sure to remove the database containing \"{name}\"? (y/n)")
    if confirm != 'y':
        return

    database_list = Manager.get_database_list()
    matched_database_list = [database for database in database_list if re.match(name, database.name)]
    unmatched_database_list = [database for database in database_list if not re.match(name, database.name)]

    for database in matched_database_list:
        if remove_all_files and Path(database.path).exists():
            shutil.rmtree(database.path)
        click.echo(f"Database {database.name} has been removed successfully.")

    Manager.set_database_list(unmatched_database_list)
cli.add_command(remove)

@click.command(help='Enter a database.')
@click.option('--name', '-n', type=str, help='The name of the database.', default=None)
def enter(name):
    database_list = Manager.get_database_list()
    Manager.set_current_db(name)
    if name is not None:
        click.echo(f"Database {name} has been entered successfully.")
        click.echo("All 'vlib db' commands will be redirected to the database.")
cli.add_command(enter)


@click.group(help='Commands for configuring databases.')
def db():
    pass
cli.add_command(db)

@click.command(help='View the template file')
def template():
    _, database = Manager.get_current_database()
    os.system(f'vi {database.template}')
db.add_command(template)


@click.command(help='List the parameters of the database.')
@click.option('--name', '-n', type=str, help='The name of the database.', default=None)
def list(name):
    _, database = Manager.get_current_database()
    xslib_list = DatabaseManager().get_xslib_list()
    print("|================================================================================|")
    print(f"|Database: {database.name:<70s}|")
    print(f"|Template: {database.template:<70s}|")
    print(f"|Path    : {database.path:<70s}|")
    for xslib in xslib_list:
        print("|================================================================================|")
        print(f"|Task    : {xslib['task']:<70s}|")
        print(f"|Path    : {xslib['path']:<70s}|")
        print("|--------------------------------------------------------------------------------|")
        for name, value in xslib.items():
            if name not in ['task', 'path']:
                print(f"|{name:<29s}|{str(value):<50s}|")
    print("|================================================================================|")
db.add_command(list)


@click.command(help='Remove a task.')
@click.option('--task', '-t', type=str, help='The name of the task.', required=True)
@click.option('--remove_all_files', type=bool, help='If remove the files of the task.', default=False)
def remove(task, remove_all_files):
    _, database = Manager.get_current_database()
    xslib_list = DatabaseManager().get_xslib_list()
    matched_xslib_list = [xslib for xslib in xslib_list if re.match(task, xslib['task'])]
    unmatched_xslib_list = [xslib for xslib in xslib_list if not re.match(task, xslib['task'])]

    for xslib in matched_xslib_list:
        if remove_all_files:
            os.remove(xslib['path'])
        DatabaseManager.remove_xslib(xslib['task'])
        click.echo(f"Task {xslib['task']} has been removed successfully.")
db.add_command(remove)

@click.command()
@click.option('--task', '-t', type=str, help='The name of the task.', required=True)
@click.option('--inputs', '-i', type=str, help='The input parameters of the task.', required=True, multiple=True)
def run(task, inputs):

    _, database = Manager.get_current_database()

    if task in [xslib['task'] for xslib in DatabaseManager().get_xslib_list()]:
        raise ValueError(f"Task {task} already exists. Please change the name.")

    name_value_pairs = {}
    for inp, parameter in zip(inputs, database.get_parameters()):
        if '=' in inp:
            if inp[:inp.index('=')] != parameter['name']:
                raise ValueError(f"Parameter {type + '_' + inp[:inp.index('=')]} does not match the parameter {parameter['name']}.")
            value = inp[inp.index('=')+1:]
        else:
            value = inp
        if parameter['type'] == 'int':
            value = int(value)
        if parameter['type'] == 'float':
            value = float(value)
        name_value_pairs[parameter['type'] + '_' + parameter['name']] = value

    jtemplate = jinja2.Template(Path(database.template).read_text())
    jrendered = jtemplate.render(name_value_pairs)

    folderpath = Path(database.path) / task
    if not folderpath.exists():
        folderpath.mkdir()
    with open(folderpath / Path(database.template).name, 'w') as f:
        f.write(jrendered)

    with run_in_folder(folderpath):
        os.system(f'python {folderpath / Path(database.template).name}')

    click.echo(f"Task {task} has been created successfully.")

    DatabaseManager.add_xslib(task, str(folderpath), name_value_pairs)
db.add_command(run)


if __name__ == "__main__":
    cli()
