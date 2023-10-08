#! /bin/bash

# 文件路径
input="./sphere/"
output="./sphere_out/"
xslib="subxslib_sphere.dat"
# 燃耗过程
powers=(1.8e7)
timesteps=(1)
timesteps_unit='MWd/kg'
diff_burnable_mats=0
# 燃耗区域
burn_materials=(7)
burn_materials_index='id'
burn_cells=()
burn_cells_index='name'

python prerun.py --input $input --output $output --xslib $xslib \
    --powers ${powers[@]} --timesteps ${timesteps[@]} --timesteps_unit ${timesteps_unit} \
    --burn_materials ${burn_materials[@]} --burn_materials_index $burn_materials_index \
    --burn_cells ${burn_cells[@]} --burn_cells_index $burn_cells_index --diff_burnable_mats $diff_burnable_mats

python postrun.py --input $input --output $output --xslib $xslib \
    --powers ${powers[@]} --timesteps ${timesteps[@]} --timesteps_unit ${timesteps_unit} \
    --burn_materials ${burn_materials[@]} --burn_materials_index $burn_materials_index \
    --burn_cells ${burn_cells[@]} --burn_cells_index $burn_cells_index --diff_burnable_mats $diff_burnable_mats
