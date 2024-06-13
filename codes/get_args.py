from pathlib import Path
from argparse import ArgumentParser

def get_args(input_args=None):
    """
    Read the arguments in dictionary and return them as a namespace.
    The args are provided to modify_openmc_input and retrieve_openmc_results.
    When 'args' is None, the command line arguments are read.
    
    :param args: dictionary of arguments
    
    :return: namespace of arguments
    """

    # 命令行输入参数定义
    parser = ArgumentParser()
    # 输入输出和截面库路径
    parser.add_argument("--input_path", type=str, default='.')
    parser.add_argument("--output_path", type=str, default=None)
    parser.add_argument("--xslib_path", type=str, default=None)
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
    
    parser.add_argument("--batch", type=int, default=None)
    parser.add_argument("--inactive", type=int, default=None)
    parser.add_argument("--particles", type=int, default=None)

    if input_args:
        args = parser.parse_args([])
        for key, value in input_args.items():
            setattr(args, key, value)
    else:
        args = parser.parse_args()
    
    args.input_path = Path(args.input_path)
    args.output_path = Path(args.output_path) if args.output_path is not None else args.input_path.stem / 'output'
    args.xslib_path = Path(args.xslib_path) if args.xslib_path is not None else args.output_path / '_xslib.dat'

    return args