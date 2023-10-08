#! /bin/bash

# 文件路径
input="./pin/"
output="./pin_out/"
xslib="subxslib_pin.dat"
# 燃耗过程
powers=(1.8e7)
burnups=(1)
diff_burnable_mats=1
# 燃耗区域
burn_materials=('moxpellet', 'h2o')
burn_materials_index='name'
burn_cells=()
burn_cells_index='name'

python prerun.py --input $input --output $output --xslib $xslib \
    --powers ${powers[@]} --burnups ${burnups[@]} \
    --burn_materials ${burn_materials[@]} --burn_materials_index $burn_materials_index \
    --burn_cells ${burn_cells[@]} --burn_cells_index $burn_cells_index --diff_burnable_mats $diff_burnable_mats

python postrun.py --input $input --output $output --xslib $xslib \
    --powers ${powers[@]} --burnups ${burnups[@]} \
    --burn_materials ${burn_materials[@]} --burn_materials_index $burn_materials_index \
    --burn_cells ${burn_cells[@]} --burn_cells_index $burn_cells_index --diff_burnable_mats $diff_burnable_mats
