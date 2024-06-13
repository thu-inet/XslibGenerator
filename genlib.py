from codes import *


if __name__ == "__main__":

    args = get_args()
    modify_openmc_input(args)
    retrieve_openmc_results(args)
    