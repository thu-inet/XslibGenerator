import os
import codes

# os.environ['chain_file'] = '/home/dodo/nuclear_data/openmc/chain/chain_casl_pwr_0.11.xml'
# os.environ['cross_sections'] = '/home/dodo/nuclear_data/openmc/endfb8/cross_sections.xml'
os.environ['cross_sections'] = '/home/dodo/nuclear_data/openmc/endfb71/cross_sections.xml'

card = {
    'input_path': 'input',
    'output_path': 'output',
    'xslib_path': 'xslib.dat',
    'burn_materials': ["kernel"],
    'burn_materials_index': 'name',
    'burn_cells': [],
    'burn_cells_index': 'id',
    'powers': [10 for i in range(1)],
    'power_densities': [10 for i in range(1)],
    'timesteps': [1 for i in range(1)],
    'timesteps_unit': 'MWd/kg',
    'diff_burnable_mats': 0
}

args = codes.get_args(card)
codes.retrieve_openmc_results(args)
codes.retrieve_openmc_results(args)