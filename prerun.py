from pathlib import Path
from shutil import copy
from argparse import ArgumentParser
from xml.dom.minidom import parse
from time import time
from logging import info, basicConfig, INFO

import openmc
from openmc.deplete import Chain
from openmc.deplete import CoupledOperator, PredictorIntegrator
from openmc.deplete.coupled_operator import _get_nuclides_with_data

time_start = time()
basicConfig(level=INFO, format="%(asctime)s %(message)s")

# 程序应尽量仅依赖输运模块，尤其输运所使用的xml文件，增加泛用性
# 因此所需变量应尽量从xml中读取，python文件应生成xml后再读取数据

# 命令行输入参数定义
parser = ArgumentParser()
# 输入输出和截面库路径
parser.add_argument("--input", type=str, default='.')
parser.add_argument("--output", type=str, default=None)
parser.add_argument("--xslib", type=str, default=None)
# 截面库所对应区域材料
parser.add_argument("--burn_materials", type=str, default=[], nargs='*')
parser.add_argument("--burn_materials_index", type=str, default='name')
parser.add_argument("--burn_cells", type=str, default=[], nargs='*')
parser.add_argument("--burn_cells_index", type=str, default='name')
# 截面库所需燃耗信息
parser.add_argument("--powers", type=float, default=None, nargs='*')
parser.add_argument("--power_densities", type=float, default=None, nargs='*')
parser.add_argument("--timesteps", type=float, default=None, nargs='*')
parser.add_argument("--timesteps_unit", type=str, default='d')
parser.add_argument("--diff_burnable_mats", type=int, default=0)
args = parser.parse_args()

# if __name__ == '__main__':
#     class Args():
#         name = f'T{0*100+300}E1.80BP0GD0_test'
#         input = '/home/super/users/zhangwj/openmc/NuitXsLibGenerator2.0/' + name
#         output = input + '_out/'
#         xslib = input + '_xslib.txt'

#         powers = [1.8E7 for i in range(10)]
#         burnups = [1 for i in range(10)]
#         burn_materials = []
#         burn_materials_index = 'name'
#         burn_cells = ['101']
#         burn_cells_index = 'id'
#         diff_burnable_mats = 1
#     args = Args()


# 读取输入参数
input_path = Path(args.input)
if Path(args.output) is None:
    output_path = input_path / '_out/'
else:
    output_path = Path(args.output)
if Path(args.xslib) is None:
    xslib_path = output_path / '_xslib.txt'
else:
    xslib_path = Path(args.xslib)

# 读取xml文件为openmc类实例
info("XslibGenerator: 读取xml文件为openmc类实例...")
materials_obj = openmc.Materials.from_xml(input_path / 'materials.xml')
tallies_obj = openmc.Tallies.from_xml(input_path / 'tallies.xml')
settings_obj = openmc.Settings.from_xml(input_path / 'settings.xml')
geometry_obj = openmc.Geometry.from_xml(input_path / 'geometry.xml', materials=materials_obj)

# 读取xml文件为xml树实例
info("XslibGenerator: 读取xml文件为xml树实例...")
materials_xml = parse(str(input_path / 'materials.xml'))
geometry_xml = parse(str(input_path / 'geometry.xml'))
tallies_xml = parse(str(input_path / 'tallies.xml'))
geometry_xml = parse(str(input_path / 'geometry.xml'))

# 读取主要xml元素
info("XslibGenerator: 读取主要xml元素...")
materials = materials_xml.getElementsByTagName('material')
cells = geometry_xml.getElementsByTagName('cell')
lattices = geometry_xml.getElementsByTagName('lattice')
filters = tallies_xml.getElementsByTagName('filter')
tallies = tallies_xml.getElementsByTagName('tally')

# 读取核素和反应道
info("XslibGenerator: 读取核素和反应道...")
chain = Chain().from_xml(openmc.config.get('chain_file'))
recs_name = chain.reactions
nucs_name = chain.nuclides
nucs_name = [nuc.name for nuc in nucs_name if nuc.name in _get_nuclides_with_data(openmc.config.get('cross_sections'))]

# 处理燃耗材料和区域
info("XslibGenerator: 处理燃耗材料和区域...")
burn_materials_id = [material.getAttribute('id') for material in materials if material.getAttribute(args.burn_materials_index) in args.burn_materials]
burn_cells_id = [cell.getAttribute('id') for cell in cells if cell.getAttribute(args.burn_cells_index) in args.burn_cells]

# 添加材料筛选器
info("XslibGenerator: 添加材料筛选器...")
filter_mat_id = 10000
while filter_mat_id in [filter.getAttribute('id') for filter in filters]:
    filter_mat_id += 1
filter_mat = openmc.MaterialFilter([int(id) for id in burn_materials_id], filter_mat_id)

# 添加栅元筛选器
info("XslibGenerator: 添加栅元筛选器...")
filter_cell_id = 20000
while filter_cell_id in [filter.getAttribute('id') for filter in filters] or filter_cell_id == filter_mat_id:
    filter_cell_id += 1
filter_cell = openmc.CellFilter([int(id) for id in burn_cells_id], filter_cell_id)

# 添加反应计数器
info("XslibGenerator: 添加反应计数器...")
tally_reaction_id = 10000
while tally_reaction_id in [tally.getAttribute('id') for tally in tallies]:
    tally_reaction_id += 1
tally_reaction = openmc.Tally(tally_reaction_id, name="_tally_reaction_xslib")
tally_reaction.nuclides = nucs_name
tally_reaction.scores = recs_name

# 添加通量计数器
info("XslibGenerator: 添加通量计数器...")
tally_flux_id = 20000
while tally_flux_id in [tally.getAttribute('id') for tally in tallies] or tally_flux_id == tally_reaction_id:
    tally_flux_id += 1
tally_flux = openmc.Tally(tally_flux_id, name="_tally_flux_xslib")
tally_flux.scores = ['flux']

# 组合计数器和筛选器
info("XslibGenerator: 组合计数器和筛选器...")
if len(args.burn_materials) != 0:
    tally_reaction.filters.append(filter_mat)
    tally_flux.filters.append(filter_mat)
if len(args.burn_cells) != 0:
    tally_reaction.filters.append(filter_cell)
    tally_flux.filters.append(filter_cell)
tallies_obj.extend([tally_reaction, tally_flux])

# 解析栅元筛选器的材料
info("XslibGenerator: 解析栅元筛选器的材料...")
burn_cells_materials_id = []
for cell_id in burn_cells_id:
    cell = [cell for cell in cells if cell.getAttribute('id') == cell_id][0]
    if cell.getAttribute('fill') == '':
        burn_cells_materials_id.extend(cell.getAttribute('material').split())
    else:
        subcells_id = [subcell.getAttribute('id') for subcell in cells if subcell.getAttribute('universe') == cell.getAttribute('fill')]
        cell_lattice = [lattice for lattice in lattices if lattice.getAttribute('id') == cell.getAttribute('fill')][0]
        cell_lattice_universes = cell_lattice.getElementsByTagName('universes')[0].firstChild.data.split()
        cell_lattice_universes = list(set(cell_lattice_universes))
        subcells_id_lattice = [subcell.getAttribute('id') for subcell in cells if subcell.getAttribute('universe') in cell_lattice_universes]
        burn_cells_id.extend(subcells_id)
        burn_cells_id.extend(subcells_id_lattice)
burn_materials_id.extend(burn_cells_materials_id)
burn_materials_id = list(set(burn_materials_id))

# 添加燃耗区核素
info("XslibGenerator: 添加燃耗区核素...")
burn_materials_obj = [material for material in materials_obj if str(material.id) in burn_materials_id]
for material in burn_materials_obj:
    material.depletable = True
    material.get_nuclides()
    percent_type = material._nuclides[0].percent_type if len(material._nuclides) != 0 else 'ao'
    material_nucs_name = [nuc.name for nuc in material.nuclides]
    for nuc_name in nucs_name:
        if nuc_name not in material_nucs_name:
            material.add_nuclide(nuc_name, 1E-35, percent_type=percent_type)

# 输出模型xml文件
info("XslibGenerator: 输出模型xml文件...")
materials_obj = openmc.Materials(geometry_obj.get_all_materials().values())
materials_obj.export_to_xml()
geometry_obj.export_to_xml()
tallies_obj.export_to_xml()
settings_obj.export_to_xml()
model = openmc.Model(geometry=geometry_obj,
                     materials=materials_obj,
                     settings = settings_obj, 
                     tallies = tallies_obj)

# 设置燃耗求解器
info("XslibGenerator: 设置燃耗求解器...")
operator = CoupledOperator(model, 
                            normalization_mode='energy-deposition',
                            diff_burnable_mats=args.diff_burnable_mats)
integrator = PredictorIntegrator(operator=operator,
                                power=args.powers, 
                                power_density=args.power_densities,
                                timesteps=args.timesteps,
                                timestep_units=args.timestep_units,
                                solver='cram48')
integrator.integrate()

# 转储输出文件
info("XslibGenerator: 转储输出文件...")
if str(output_path) != str(Path().cwd()):
    if not output_path.exists():
        output_path.mkdir()
    files = [file for file in Path().cwd().glob('*') if file.is_file() and file.stat().st_ctime > time_start and (file.suffix in ['.h5', '.out', '.log', '.xml'])]
    for file in files:
        copy(str(file), str(output_path))