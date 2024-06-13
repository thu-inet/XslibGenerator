#-*-coding: UTF-8 -*-

import os
import shutil

from pathlib import Path
from xml.dom.minidom import parse
from time import time
from logging import info, basicConfig, INFO
from argparse import Namespace

import openmc
from openmc.deplete import Chain
from openmc.deplete import CoupledOperator, PredictorIntegrator
from openmc.deplete.coupled_operator import _get_nuclides_with_data

from .get_args import get_args

def modify_openmc_input(args: Namespace):

    time_start = time()
    basicConfig(level=INFO, format="%(asctime)s %(message)s")

    # 读取xml文件为openmc类实例
    info("XslibGenerator: 读取xml文件为openmc类实例...")
    materials_obj = openmc.Materials.from_xml(args.input_path / 'materials.xml')
    tallies_obj = openmc.Tallies.from_xml(args.input_path / 'tallies.xml')
    settings_obj = openmc.Settings.from_xml(args.input_path / 'settings.xml')
    geometry_obj = openmc.Geometry.from_xml(args.input_path / 'geometry.xml', materials=materials_obj)

    # 读取xml文件为xml树实例
    info("XslibGenerator: 读取xml文件为xml树实例...")
    materials_xml = parse(str(args.input_path / 'materials.xml'))
    geometry_xml = parse(str(args.input_path / 'geometry.xml'))
    tallies_xml = parse(str(args.input_path / 'tallies.xml'))
    geometry_xml = parse(str(args.input_path / 'geometry.xml'))

    # 将xml文件转储为tmp文件
    info("XslibGenerator: 将xml文件转储为tmp文件...")
    shutil.copy(str(args.input_path / 'materials.xml'), str(args.input_path / 'materials_original.xml'))
    shutil.copy(str(args.input_path / 'geometry.xml'), str(args.input_path / 'geometry_original.xml'))
    shutil.copy(str(args.input_path / 'tallies.xml'), str(args.input_path / 'tallies_original.xml'))
    shutil.copy(str(args.input_path / 'settings.xml'), str(args.input_path / 'settings_original.xml'))
    
    # 读取主要xml元素
    info("XslibGenerator: 读取主要xml元素...")
    materials = materials_xml.getElementsByTagName('material')
    cells = geometry_xml.getElementsByTagName('cell')
    lattices = geometry_xml.getElementsByTagName('lattice')
    filters = tallies_xml.getElementsByTagName('filter')
    tallies = tallies_xml.getElementsByTagName('tally')

    # 读取燃耗链文件
    info("XslibGenerator: 读取燃耗链文件...")
    chain_file_path = None
    if 'chain_file' in openmc.config.keys() and Path(openmc.config['chain_file']).exists():
        chain_file_path = Path(openmc.config['chain_file'])
    if os.getenv('OPENMC_CHAIN_FILE') is not None and Path(os.getenv('OPENMC_CHAIN_FILE')).exists():
        chain_file_path = Path(os.getenv('OPENMC_CHAIN_FILE'))
    if chain_file_path is None:
        raise ValueError(f"Chain file does not exist. Please set the chain file settings first")
    chain = Chain().from_xml(openmc.config['chain_file'])
    
    # 读取截面索引文件
    info("XslibGenerator: 读取截面索引文件...")
    cross_section_path = None
    if 'cross_sections' in openmc.config.keys() and Path(openmc.config['cross_sections']).exists():
        cross_section_path = Path(openmc.config['cross_sections'])
    if os.getenv('OPENMC_CROSS_SECTIONS') is not None and Path(os.getenv('OPENMC_CROSS_SECTIONS')).exists():
        cross_section_path = Path(os.getenv('OPENMC_CROSS_SECTIONS'))
    if cross_section_path is None:
        raise ValueError(f"Cross section file does not exist. Please set the cross section file settings first")

    # 读取核素和反应道
    info("XslibGenerator: 读取核素和反应道...")
    recs_name = chain.reactions
    nucs_name = chain.nuclides
    nucs_name = [nuc.name for nuc in nucs_name if nuc.name in _get_nuclides_with_data(cross_section_path)]

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
    existing_tally_id = [int(tally.getAttribute('id')) for tally in tallies]
    while tally_reaction_id in existing_tally_id:
        tally_reaction_id += 1
    tally_reaction = openmc.Tally(tally_reaction_id, name="_tally_reaction_xslib")
    tally_reaction.nuclides = nucs_name
    tally_reaction.scores = recs_name

    # 添加通量计数器
    info("XslibGenerator: 添加通量计数器...")
    tally_flux_id = 20000
    while tally_flux_id in existing_tally_id or tally_flux_id == tally_reaction_id:
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
        if cell.getAttribute('fill') == '':  # 体积为纯材料，没有填充其他
            burn_cells_materials_id.extend(cell.getAttribute('material').split())
        else:  # 栅元内使用了其他几何填充
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

    # 设置输运规模
    info("XslibGenerator: 设置输运规模...")
    settings_obj.particles = args.particles if args.particles is not None else settings_obj.particles
    settings_obj.inactive = args.inactive if args.inactive is not None else settings_obj.inactive
    settings_obj.batches = args.batch if args.batch is not None else settings_obj.batches

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
                                    timestep_units=args.timesteps_unit,
                                    solver='cram48')
    integrator.integrate()

    # 转储输出文件
    info("XslibGenerator: 转储输出文件...")
    if str(args.output_path) != str(Path().cwd()):
        if not args.output_path.exists():
            args.output_path.mkdir()
        files = [file for file in Path().cwd().glob('*') if file.is_file()]
        files = [file for file in files if file.stat().st_ctime > time_start and (file.suffix in ['.h5', '.out', '.log', '.xml'])]
        for file in files:
            shutil.copy(str(file), str(args.output_path))
            if '_original' not in file.name:
                os.remove(file)
    shutil.copy(str(args.input_path / 'materials_original.xml'), str(args.input_path / 'materials.xml'))
    shutil.copy(str(args.input_path / 'geometry_original.xml'), str(args.input_path / 'geometry.xml'))
    shutil.copy(str(args.input_path / 'tallies_original.xml'), str(args.input_path / 'tallies.xml'))
    shutil.copy(str(args.input_path / 'settings_original.xml'), str(args.input_path / 'settings.xml'))
    os.remove(str(args.input_path / 'materials_original.xml'))
    os.remove(str(args.input_path / 'geometry_original.xml'))
    os.remove(str(args.input_path / 'tallies_original.xml'))
    os.remove(str(args.input_path / 'settings_original.xml'))
    

    info("XslibGenerator: 运行结束")
    info("XslibGenerator: 运行时间: {:.2f}s".format(time() - time_start))

if __name__ == "__main__":

    args = get_args()
    modify_openmc_input(args)
    
