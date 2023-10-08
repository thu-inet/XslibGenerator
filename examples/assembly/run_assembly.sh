#! /bin/bash

# 文件路径
input="./assembly/"
output="./assembly_out/"
xslib="subxslib_assembly.dat"
# 燃耗过程
powers=(1.8e7)
timesteps=(1)
timesteps_unit='MWd/kg'
diff_burnable_mats=1
# 燃耗区域
burn_materials=()
burn_materials_index='name'
burn_cells=(101)
burn_cells_index='id'

python prerun.py --input $input --output $output --xslib $xslib \
    --powers ${powers[@]} --timesteps ${timesteps[@]} --timesteps_unit ${timesteps_unit} \
    --burn_materials ${burn_materials[@]} --burn_materials_index $burn_materials_index \
    --burn_cells ${burn_cells[@]} --burn_cells_index $burn_cells_index --diff_burnable_mats $diff_burnable_mats

python postrun.py --input $input --output $output --xslib $xslib \
    --powers ${powers[@]} --timesteps ${timesteps[@]} --timesteps_unit ${timesteps_unit} \
    --burn_materials ${burn_materials[@]} --burn_materials_index $burn_materials_index \
    --burn_cells ${burn_cells[@]} --burn_cells_index $burn_cells_index --diff_burnable_mats $diff_burnable_mats
