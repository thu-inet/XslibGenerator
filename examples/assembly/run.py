import os
import codes

args = {
    'input_path': 'input',
    'powers': [1],
    'timesteps': [1],
    'burn_materials': ['pellet'],
    'burn_materials_index': 'name',
    'batch': 10,
    'inactive': 5,
    'particles': 1000,
}

os.environ['OPENMC_CHAIN_FILE'] = '/home/dodo/nuclear_data/openmc/chain/chain_casl_pwr_0.12.xml'

args = codes.get_args(args)
codes.modify_openmc_input(args)
codes.retrieve_openmc_results(args)