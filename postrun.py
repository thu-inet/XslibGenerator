from pathlib import Path
from pandas import merge
from functools import reduce
from argparse import ArgumentParser
from xml.dom.minidom import parse
from numpy import array
from logging import info, basicConfig, INFO

basicConfig(level=INFO, format="%(asctime)s %(message)s")

from openmc import StatePoint
from openmc.deplete import Results

from classes import XSLIB, ISOMERICS
from constants import fissile_HM, time_conversion, nuclide_mass, Na

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
args = parser.parse_args()

if __name__ == '__main__':
    # class Args():

        input = '/home/super/users/zhangwj/openmc/NuitXsLibGenerator2.0/benchmarks/T750E2.72BP0GD0'
        output = '/home/super/users/zhangwj/openmc/NuitXsLibGenerator2.0/benchmarks/T750E2.72BP0GD0_out//'
        xslib = '/home/super/users/zhangwj/openmc/NuitXsLibGenerator2.0/benchmarks/T750E2.72BP0GD0_xslib.dat'

        # power_densities = (6.749, 6.749, 6.749, 6.749, 6.749, 6.749, 6.749, 6.749, 0, \
        #         10.482, 10.482, 10.482, 10.482, 10.482, 10.482, 10.482, 10.482, 10.482, 0, \
        #         12.123, 12.123, 12.123, 12.123, 12.123, 12.123, 12.123, 12.123, 12.123, 12.123)
        # powers = None
        # timesteps = (28.25, 28.25, 28.25, 28.25, 28.25, 28.25, 28.25, 28.25, 86.0, \
        #         29.22222222222222, 29.22222222222222, 29.22222222222222, 29.22222222222222, 29.22222222222222, 29.22222222222222, 29.22222222222222, 29.22222222222222, 29.22222222222222, 51.0, \
        #         29.2, 29.2, 29.2, 29.2, 29.2, 29.2, 29.2, 29.2, 29.2, 29.2)
        # timestep_units = 'd'

    #     burn_materials = ["1"]
    #     burn_materials_index = 'id'
    #     burn_cells = []
    #     burn_cells_index = 'id'
    #     diff_burnable_mats = 1
    # args = Args()

# 读取输入参数
info("读取输入参数...")
input_path = Path(args.input)
if Path(args.output) is None:
    output_path = input_path / '_out/'
else:
    output_path = Path(args.output)
if Path(args.xslib) is None:
    xslib_path = output_path / '_xslib.txt'
else:
    xslib_path = Path(args.xslib)

# 读取输入文件
info("读取输入文件...")
materials_xml = parse(str(output_path / 'materials.xml'))
geometry_xml = parse(str(output_path / 'geometry.xml'))
materials = materials_xml.getElementsByTagName('material')
cells = geometry_xml.getElementsByTagName('cell')
lattices = geometry_xml.getElementsByTagName('lattice')

# 读取输出文件
info("读取输出文件...")
result = Results(output_path / 'depletion_results.h5')
statepoints = []
for file in sorted(output_path.glob('openmc_simulation_n*.h5'), key=lambda x: int(x.name[19:-3])):
    info(f"读取输出文件{file.stem}...")
    statepoints.append(StatePoint(file))

# 整理计数器数据为数据表对象列表
info("整理计数器数据为数据表对象列表...")
dfs_tally_flux = []
dfs_tally_reaction = []
for i, file in enumerate(statepoints):
    df_tally_flux = file.get_tally(name='_tally_flux_xslib').get_pandas_dataframe()
    if 'mean' not in df_tally_flux.columns:
        df_tally_flux.insert(len(df_tally_flux.columns), 'mean', 1E-10)
    df_tally_flux = df_tally_flux.rename(columns={'mean': 'mean_' + str(i)})
    df_tally_flux.drop('std. dev.', axis=1, inplace=True)
    dfs_tally_flux.append(df_tally_flux)

    df_tally_reaction = file.get_tally(name='_tally_reaction_xslib').get_pandas_dataframe()
    if 'mean' not in df_tally_reaction.columns:
        df_tally_reaction.insert(len(df_tally_reaction.columns), 'mean', 0)
    df_tally_reaction = df_tally_reaction.rename(columns={'mean': 'mean_' + str(i)})
    df_tally_reaction.drop('std. dev.', axis=1, inplace=True)
    dfs_tally_reaction.append(df_tally_reaction)

# 合并列表得到通量和反应率数据表
info("合并列表得到通量和反应率数据表...")
tags_tally_flux = df_tally_flux.columns.tolist()[:-1]
tags_tally_reaction = df_tally_reaction.columns.tolist()[:-1]
tags_data = [f'mean_{i}' for i in range(len(dfs_tally_flux))]
merge_flux = lambda t1, t2: merge(t1, t2, on=tags_tally_flux)
merge_reaction = lambda t1, t2: merge(t1, t2, on=tags_tally_reaction)
df_flux = reduce(merge_flux, dfs_tally_flux)
df_reaction = reduce(merge_reaction, dfs_tally_reaction)

# 初始化截面库
info("初始化截面库...")
xslib = XSLIB(xslib_path, read=False)
isomerics = ISOMERICS('isomeric_ratios.pkl')

# 读取体积
info("读取体积...")
# 读取燃耗材料和燃耗区域的填充材料
burn_materials_id = [material.getAttribute('id') for material in materials if material.getAttribute(args.burn_materials_index) in args.burn_materials]
burn_cells_id = [cell.getAttribute('id') for cell in cells if cell.getAttribute(args.burn_cells_index) in args.burn_cells]
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
burn_materials_volume = sum([float(material.getAttribute('volume')) for material in materials if material.getAttribute('id') in burn_materials_id])

# 读取重金属质量
info("读取重金属质量...")
mass_HM = 0
for nuc_name in fissile_HM:
    nuc_M = nuclide_mass(nuc_name)
    mass_HM += sum([result.get_atoms(burn_material_id, nuc=nuc_name, nuc_units='atoms')[1][0] for burn_material_id in burn_materials_id]) / Na * nuc_M
xslib.mass_HM = mass_HM

# 读取通量和燃耗
info("读取通量和燃耗...")
xslib.flux = df_flux[tags_data].to_numpy().sum(axis=0)
if args.timesteps_unit == 'MWd/kg':
    xslib.burnups = [sum(args.timesteps[:i+1]) for i in range(len(args.timesteps))]
else:
    times = array([time_conversion(timestep, args.timesteps_unit, 'd') for timestep in args.timesteps])
    if args.power_densities is not None:
        power_densities = array(args.power_densities)
        xslib.burnups = [sum(times[:i+1]*power_densities[:i+1])/1000 for i in range(len(args.timesteps))]
    else:
        powers = array(args.powers)
        xslib.burnups = [sum(times[:i+1]*powers[:i+1])/1000/xslib.mass_HM for i in range(len(args.timesteps))]
xslib.burnups.insert(0, 0)
xslib.burnups = array(xslib.burnups)

# 读取核素密度
info("读取核素密度...")
# 仍然依赖depletion results 
nucs_name = df_reaction['nuclide'].unique()
for nuc_name in nucs_name:
    atom_dens = [result.get_atoms(burn_material_id, nuc=nuc_name, nuc_units='atoms')[1] for burn_material_id in burn_materials_id]
    atom_dens = array(atom_dens).sum(axis=0) / burn_materials_volume / 1E24
    if any(atom_dens < 0):
        info(f"Warning:[{nuc_name}] negative atom_dens")
        atom_dens[atom_dens < 0] = 0
    nuc_name = nuc_name.replace('_', '')
    xslib.set_den(nuc_name, atom_dens)

# 读取反应率
info("读取反应率...")
for i, serie in df_reaction.iterrows():
    rate = serie[tags_data].to_numpy()
    m_ratio = isomerics(serie['nuclide'], serie['score'])
    xslib.set_rate(serie['nuclide'].replace('_', ''), serie['score'], rate * (1 - m_ratio))
    if m_ratio > 0:
        xslib.set_rate(serie['nuclide'].replace('_', ''), serie['score'] + 'M', rate * m_ratio)

# 生成截面并导入截面库
info("生成截面并导入截面库...")
xslib.remove_cooling()
xslib.calculate_xs()
xslib.remove_reactions(0)
xslib.export()
