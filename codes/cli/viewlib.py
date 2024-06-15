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

    data = json.dumps({'database_list': [], 'current_db': None})
    with open(sys_path, 'w') as f:
        f.write(data)
    click.echo("The xslib manager has been initialized successfully.")
cli.add_command(init)

@click.command(help='Create a new database.')
@click.argument('name', type=str)
@click.option('--template', '-t', type=str, help='The file path of the database model template.', required=True)
@click.option('--script', '-s', type=str, help='The file path of the genlib script.', required=True)
@click.option('--path', '-p', type=str, help='The path of the database.', required=True)
def create(name, template, script, path):
    database_list = Manager.get_database_list()
    if name in [database.name for database in database_list]:
        raise ValueError(f"Database {name} already exists. Please change the name.")

    template, script, path = Path(template), Path(script), Path(path)
    if not template.exists():
        raise ValueError(f"Template file {template} does not exist. Please check the path.")
    if not script.exists():
        raise ValueError(f"Script file {script} does not exist. Please check the path.")
    if not path.exists():
        path.mkdir()

    new_template = path / '.template.py'
    new_script = path / ('.script'+script.suffix)
    if template != new_template:
        shutil.copy(template, new_template)
    if script != new_script:
        shutil.copy(script, new_script)

    path = str(path.resolve())
    new_template = str(new_template.resolve())
    new_script = str(new_script.resolve())
    
    data = json.dumps([])
    with open(path + '/.libdir.json', 'w') as f:
        f.write(data)

    database = Database(name, new_template, new_script, path)
    database_list.append(database)
    Manager.set_database_list(database_list)

    click.echo(f"Database \"{database.name}\" has been created successfully.")
cli.add_command(create)

@click.command(help='Remove a database.')
@click.argument('name', type=str)
@click.option('--remove_all_files', type=bool, help='If remove the files of the database.', default=False)
def remove(name, remove_all_files):

    confirm = input(f"Are you sure to remove the database containing \"{name}\"? (y/n)")
    if confirm != 'y':
        return

    database_list = Manager.get_database_list()
    matched_database_list = [database for database in database_list if re.fullmatch(name, database.name)]
    unmatched_database_list = [database for database in database_list if not re.fullmatch(name, database.name)]

    for database in matched_database_list:
        if remove_all_files and Path(database.path).exists():
            shutil.rmtree(database.path)
        click.echo(f"Database {database.name} has been removed successfully.")

    Manager.set_database_list(unmatched_database_list)
cli.add_command(remove)

@click.command(help='List existing databases.')
@click.argument('name', type=str, default='')
def list(name):
    database_list = Manager.get_database_list()
    if name == '':
        matched_database_list = database_list
    else:
        matched_database_list = [database for database in database_list if re.fullmatch(name, database.name)]

    for database in matched_database_list:
        print("|================================================================================|")
        print(f"|Database: {database.name:<70s}|")
        print(f"|Path    : {database.path:<70s}|")
        print(f"|Template: {database.template:<70s}|")
        print(f"|Script  : {database.script:<70s}|")
        print("|--------------------------------------------------------------------------------|")
        for parameter in database.get_template_parameters():
            print(f"|{parameter['name']:<29s}|{parameter['type']:<50s}|")
    print("|================================================================================|")
cli.add_command(list)

@click.command(help='Enter a database.')
@click.argument('name', type=str)
def enter(name):
    Manager.set_current_db(name)
    if name is not None:
        click.echo(f"Database {name} has been entered successfully.")
        click.echo("All 'vlib db' commands will be redirected to the database.")
cli.add_command(enter)


@click.group(help='Commands for configuring databases.')
def db():
    # if Manager.get_current_database()[0] is None:
    #     raise ValueError("No database has been entered.")
    pass
cli.add_command(db)

@click.command(help='View the template file')
def template():
    _, database = Manager.get_current_database()
    os.system(f'vi {database.template}')
db.add_command(template)

@click.command(help='View the script file')
def script():
    _, database = Manager.get_current_database()
    os.system(f'vi {database.script}')
db.add_command(script)

@click.command(help='Rebuild the database.')
def rebuild():

    confirm = input("Are you sure to rebuild the database? (y/n)")
    if confirm != 'y':
        return

    _, database = Manager.get_current_database()
    with open(database.template, 'r') as f:
        template_lines = f.readlines()
    template_parameters = database.get_template_parameters()
    
    with open(database.script, 'r') as f:
        script_lines = f.readlines()
    script_parameters = database.get_script_parameters()

    # find all lines that contain parameters
    template_parameter_lines = []
    for parameter in template_parameters:
        for i, line in enumerate(template_lines):
            if f"{parameter['type']}_{parameter['name']}" in line:
                if parameter['type'] == 'int':
                    template = re.sub("{{\s*" + f"{parameter['type']}_{parameter['name']}" + "\s*}}", r"(-?\d+)", line)
                elif parameter['type'] == 'float':
                    template = re.sub("{{\s*" + f"{parameter['type']}_{parameter['name']}" + "\s*}}", r"([0-9\.\-]+)", line)
                else:
                    template = re.sub("{{\s*" + f"{parameter['type']}_{parameter['name']}" + "\s*}}", r"(\S+)", line)
                template_parameter_lines.append((i, parameter, template))
    # print(template_parameter_lines)

    # find all lines that contain parameters
    script_parameter_lines = []
    for parameter in script_parameters:
        for i, line in enumerate(script_lines):
            if re.fullmatch(f"{parameter['type']}_{parameter['name']}", line):
                if parameter['type'] == 'int':
                    template = re.sub("{{\s*" + f"{parameter['type']}_{parameter['name']}" + "\s*}}", "(-?\d+)", line)
                elif parameter['type'] == 'float':
                    template = re.sub("{{\s*" + f"{parameter['type']}_{parameter['name']}" + "\s*}}", "(-?[0-9\.]+)", line)
                else:
                    template = re.sub("{{\s*" + f"{parameter['type']}_{parameter['name']}" + "\s*}}", "(\S+)", line)
                script_parameter_lines.append((i, parameter, template))

    DatabaseManager().remove_all_xslib()
    subfolders = [subfolder for subfolder in Path(database.path).glob('*') if subfolder.is_dir()]
    for folder in subfolders:

        with open(folder / '.template.py', 'r') as f:
            rendered_template_lines = f.readlines()
        template_render_parameters = {}
        for i, parameter, template in template_parameter_lines:
            result = re.fullmatch(template, rendered_template_lines[i])
            if result is not None:
                if parameter['type'] == 'int':
                    value = int(result.group(1))
                elif parameter['type'] == 'float':
                    value = float(result.group(1))
                else:
                    pass
                template_render_parameters[parameter['type'] + '_' + parameter['name']] = value
                
        with open(folder / Path(database.script).name, 'r') as f:
            rendered_script_lines = f.readlines()
        script_render_parameters = {}
        for i, parameter, template in script_parameter_lines:
            result = re.fullmatch(template, rendered_script_lines[i])
            if result is not None:
                if parameter['type'] == 'int':
                    value = int(result.group(1))
                elif parameter['type'] == 'float':
                    value = float(result.group(1))
                else:
                    pass
                script_render_parameters[parameter['type'] + '_' + parameter['name']] = value
        DatabaseManager.add_xslib(folder.name, str(folder), template_render_parameters, {})
db.add_command(rebuild)


@click.command(help="Create a task")
@click.argument('name', type=str)
def create(name):
    click.echo("Creating a task is not implemented.")
    click.echo("Try using the command 'vlib db run' instead.")
    click.echo("And 'vlib db itp' will be implemented soon.")
db.add_command(create)

@click.command(help='Remove a task.')
@click.argument('task', type=str)
@click.option('--remove_all_files', type=bool, help='If remove the files of the task.', default=False)
def remove(task, remove_all_files):
    _, database = Manager.get_current_database()
    xslib_list = DatabaseManager().get_xslib_list()
    matched_xslib_list = [xslib for xslib in xslib_list if re.fullmatch(task, xslib['task'])]

    for xslib in matched_xslib_list:
        if remove_all_files:
            os.remove(xslib['path'])
        DatabaseManager.remove_xslib(xslib['task'])
        click.echo(f"Task {xslib['task']} has been removed successfully.")
db.add_command(remove)

@click.command()
@click.argument('task', type=str)
@click.option('--parameter', '-p', type=str, help='The name of the parameter.', required=True)
def config(task, parameter):
    _, database = Manager.get_current_database()
    if '=' not in parameter or parameter.count('=') > 1:
        raise ValueError(f"Parameter should be in the format of 'name=value'.")
    name, value = parameter.split('=')
    value = value.strip("\"").strip("\'")
    matched_xslib = [xslib for xslib in DatabaseManager.get_xslib_list() if re.fullmatch(task, xslib['task'])]
    for xslib in matched_xslib:
        DatabaseManager().set_xslib(xslib['task'], name, value)
db.add_command(config)


@click.command(help='List the parameters of the database.')
@click.argument('task', type=str, default='')
def list(task):
    _, database = Manager.get_current_database()
    xslib_list = DatabaseManager().get_xslib_list()
    if task == '':
        matched_xslib_list = xslib_list
    else:
        matched_xslib_list = [xslib for xslib in xslib_list if re.fullmatch(task, xslib['task'])]
    print("|================================================================================|")
    print(f"|Database: {database.name:<70s}|")
    print(f"|Path    : {database.path:<70s}|")
    print(f"|Template: {database.template:<70s}|")
    print(f"|Script  : {database.script:<70s}|")
    for xslib in matched_xslib_list:
        print("|================================================================================|")
        print(f"|Task    : {xslib['task']:<70s}|")
        print(f"|Path    : {xslib['path']:<70s}|")
        print("|--------------------------------------------------------------------------------|")
        for name, value in xslib.items():
            if name not in ['task', 'path']:
                print(f"|{name:<29s}|{str(value):<50s}|")
    print("|================================================================================|")
db.add_command(list)

@click.command(help='Run a task.')
@click.argument('task', type=str)
@click.option('--inputs_template', '-it', type=str, help='The input parameters of the template.', required=False, multiple=True)
@click.option('--inputs_script', '-is', type=str, help='The input parameters of the script.', required=False, multiple=True)
def run(task, inputs_template, inputs_script):

    _, database = Manager.get_current_database()

    if task in [xslib['task'] for xslib in DatabaseManager().get_xslib_list()]:
        raise ValueError(f"Task {task} already exists. Please change the name.")

    if len(inputs_template) != len(database.get_template_parameters()):
        raise ValueError(f"The number of inputs_template does not match the number of parameters in the database.")

    template_render_parameters = {}
    for inp, parameter in zip(inputs_template, database.get_template_parameters()):
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
        template_render_parameters[parameter['type'] + '_' + parameter['name']] = value

    if len(inputs_script) != len(database.get_script_parameters()):
        raise ValueError(f"The number of inputs_script does not match the number of parameters in the database.")

    script_render_parameters = {}
    for inp, parameter in zip(inputs_script, database.get_script_parameters()):
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
        script_render_parameters[parameter['type'] + '_' + parameter['name']] = value

    jinja_template = jinja2.Template(Path(database.template).read_text())
    rendered_template = jinja_template.render(template_render_parameters)

    jinja_script = jinja2.Template(Path(database.script).read_text())
    rendered_script = jinja_script.render(script_render_parameters)

    folderpath = Path(database.path) / task
    if not folderpath.exists():
        folderpath.mkdir()

    with open(folderpath / Path(database.template).name, 'w') as f:
        f.write(rendered_template)
    with open(folderpath / Path(database.script).name, 'w') as f:
        f.write(rendered_script)

    with run_in_folder(folderpath):
        os.system(f'python {folderpath / Path(database.template).name}')
        if '.sh' in database.script:
            os.system(f'bash {folderpath / Path(database.script).name}')
        else:
            os.system(f'python {folderpath / Path(database.script).name}')

    click.echo(f"Task {task} has been created successfully.")

    DatabaseManager.add_xslib(task, str(folderpath), template_render_parameters, script_render_parameters)
db.add_command(run)

@click.command(help='Interpolate the xslib.')
@click.argument('task', type=str)
@click.option('--inputs_template', '-it', type=str, help='The input parameters of the template.', required=False, multiple=True)
@click.option('--inputs_script', '-is', type=str, help='The input parameters of the script.', required=False, multiple=True)
def itpl(task, inputs_template, inputs_script):
    
    _, database = Manager.get_current_database()

    if task in [xslib['task'] for xslib in DatabaseManager().get_xslib_list()]:
        raise ValueError(f"Task {task} already exists. Please change the name.")

    if len(inputs_template) != len(database.get_template_parameters()):
        raise ValueError(f"The number of inputs_template does not match the number of parameters in the database.")

    template_interpolate_parameters = {}
    for inp, parameter in zip(inputs_template, database.get_template_parameters()):
        if '=' in inp:
            if inp[:inp.index('=')] != parameter['name']:
                raise ValueError(f"Parameter {type + '_' + inp[:inp.index('=')]} does not match the parameter {parameter['name']}.")
            value = inp[inp.index('=')+1:]
        else:
            value = inp
        if parameter['type'] == 'int':
            value = int(value)
        elif parameter['type'] == 'float':
            value = float(value)
        else:
            pass
        template_interpolate_parameters[parameter['type'] + '_' + parameter['name']] = value

    if len(inputs_script) != len(database.get_script_parameters()):
        raise ValueError(f"The number of inputs_script does not match the number of parameters in the database.")

    script_interpolate_parameters = {}
    for inp, parameter in zip(inputs_script, database.get_script_parameters()):
        if '=' in inp:
            if inp[:inp.index('=')] != parameter['name']:
                raise ValueError(f"Parameter {type + '_' + inp[:inp.index('=')]} does not match the parameter {parameter['name']}.")
            value = inp[inp.index('=')+1:]
        else:
            value = inp

        if parameter['type'] == 'int':
            value = int(value)
        elif parameter['type'] == 'float':
            value = float(value)
        else:
            pass
        script_interpolate_parameters[parameter['type'] + '_' + parameter['name']] = value

    xslib_list = DatabaseManager().get_xslib_list()
    for xslib in xslib_list:
        weights_template = [(xslib[key]/val-1)**2 for key, val in template_interpolate_parameters.items()]
        weights_script = [(xslib[key]/val-1)**2 for key, val in script_interpolate_parameters.items()]
        print(xslib['task'], sum(weights_template), sum(weights_script))
        # weights = [sum()**2  ]) for xslib in xslib_list]
    # print(weights)
    pass
db.add_command(itpl)

if __name__ == "__main__":
    cli()
