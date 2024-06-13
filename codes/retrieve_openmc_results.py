#-*-coding: UTF-8 -*-
from pathlib import Path
from pandas import merge
from functools import reduce

from xml.dom.minidom import parse
from numpy import array
from time import time
from logging import info, basicConfig, INFO
from re import match

basicConfig(level=INFO, format="%(asctime)s %(message)s")

from openmc import StatePoint
from openmc.deplete import Results
from argparse import Namespace

from .classes import XSLIB, ISOMERICS
from .constants import fissile_HM, time_conversion, Na
from .get_args import get_args


def retrieve_openmc_results(args: Namespace):
    
    time_start = time()
    basicConfig(level=INFO, format="%(asctime)s %(message)s")

    # 读取输入文件
    info("读取输入文件...")
    materials_xml = parse(str(args.output_path / 'materials.xml'))
    geometry_xml = parse(str(args.output_path / 'geometry.xml'))
    materials = materials_xml.getElementsByTagName('material')
    cells = geometry_xml.getElementsByTagName('cell')
    lattices = geometry_xml.getElementsByTagName('lattice')

    # 读取输出文件
    info("读取输出文件...")
    result = Results(args.output_path / 'depletion_results.h5')
    statepoints = []
    for file in sorted(args.output_path.glob('openmc_simulation_n*.h5'), key=lambda x: int(x.name[19:-3])):
        # info(f"读取输出文件{file.stem}...")
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
    xslib = XSLIB(args.xslib_path, read=False)
    isomerics = ISOMERICS(Path(__file__).parent.parent / 'files' / 'isomeric_ratios.pkl')

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
        match_result = match(r'^([a-zA-Z]+)(\d+)_?(m[123])?$', nuc_name)
        if match_result is None:
            raise ValueError(f"Invalid nuclide name: {nuc_name}")
        else:
            nuc_M = int(match_result.group(2))
        mass_HM += sum([result.get_atoms(burn_material_id, nuc=nuc_name, nuc_units='atoms')[1][0] for burn_material_id in burn_materials_id]) / Na * nuc_M

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
            xslib.burnups = [sum(times[:i+1]*powers[:i+1])/1000/mass_HM for i in range(len(args.timesteps))]
    xslib.burnups.insert(0, 0)
    xslib.burnups = array(xslib.burnups)

    # 读取核素密度
    info("读取核素密度...")
    # 仍然依赖depletion results 
    nucs_name = df_reaction['nuclide'].unique()
    for nuc_name in nucs_name:
        atom_dens = [result.get_atoms(burn_material_id, nuc=nuc_name, nuc_units='atoms')[1] for burn_material_id in burn_materials_id]
        # print(nuc_name, atom_dens, burn_materials_id)
        atom_dens = array(atom_dens).sum(axis=0) / burn_materials_volume / 1E24
        if any(array(atom_dens) < 0):
            info(f"Warning:[{nuc_name}] negative atom_dens")
            atom_dens[atom_dens < 0] = 0
        nuc_name = nuc_name.replace('_', '')
        xslib.set_nuc_den(nuc_name, atom_dens)

    # 读取反应率
    info("读取反应率...")
    for i, serie in df_reaction.iterrows():
        rate = serie[tags_data].to_numpy()
        m_ratio = isomerics(serie['nuclide'], serie['score'])
        xslib.set_nuc_rec_rate(serie['nuclide'].replace('_', ''), serie['score'], rate * (1 - m_ratio))
        if m_ratio > 0:
            xslib.set_nuc_rec_rate(serie['nuclide'].replace('_', ''), serie['score'] + 'M', rate * m_ratio)

    # 生成截面并导入截面库
    info("生成截面并导入截面库...")
    xslib.remove_cooling()
    xslib.calculate_xs()
    xslib.remove_reactions(1E-7)
    xslib.export()
    
    info("XslibGenerator: 运行结束")
    info("XslibGenerator: 运行时间: {:.2f}s".format(time() - time_start))


if __name__  == "__main__":

    args = get_args()
    retrieve_openmc_results(args)
    