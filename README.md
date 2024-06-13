# XslibGenerator

基于OpenMC输运-燃耗耦合计算产生用于**点堆源项程序NUIT**的单群截面数据库。

程序分为基础依赖和流程控制部分，基础依赖（constants.py和classes.py)存储了计算中需要用到的常量、数据等，以及定义了计算中使用的类（反应、核素和截面库），流程控制部分(modify_openmc_model.py, retrieve_openmc_resutls.py和xslib_interpolator.py）负责接受参数进行计算，包含模型处理、数据提取和插值三个模块。

使用OpenMC模型制备单群截面库仅需要使用模型处理和数据提取模块，仅当用户需要从已有截面库中插值产生新截面库时需要使用。目前插值模块正计划进一步修改并增加功能。


## 依赖
标准库： pathlib, shutil, argparse, xml, time, logging
其他：pandas, numpy, **openmc**

本程序使用的openmc为0.13.2版本，更高版本也应该可以适用。

## 使用

模型处理和数据提取同时使用，采用相同的输入参数，如下：

| 参数                  | 类型            | 含义                                                         | 默认值              |
| --------------------- | --------------- | ------------------------------------------------------------ | ------------------- |
| input_path            | string          | OpenMC模型（xml文件）存放路径                                 | -                   |
| output_path           | string          | OpenMC输出文件的存放路径                                 | input +  '_out'     |
| xslib_path            | string          | 单群截面库存放路径                                           | input + '_xslib.dat |
| powers                | list[float]     | 所有燃耗步的功率，单位W，和power_densities需要二选一         | -                   |
| power_densities       | list[float]     | 所有燃耗步的功率密度，单位MW/tU，和powers需要二选一          | -                   |
| timesteps             | list[float]     | 所有燃耗步的单步时间/燃耗增加值设置                           | -                   |
| timesteps_unit        | Literal[string] | 燃耗步时间单位，可选值: 'a'=年, 'd'=天，'h'=时, 'm'=分，'s'=秒, 'MWd/kg'=燃耗 | 'd'  |
| burn_materials        | list[string]    | 截面库统计反应率和通量的材料，和burn_cells需要二选一         | -                   |
| burnup_material_index | Literal[string] | 指定材料的方式，可选值： 'name'=命名, 'id'=编号              | 'name'              |
| burn_cells            | list[string]    | 截面库统计反应率和通量的栅元，和burn_materials需要二选一     | -                   |
| burn_cell_index       | Literal[string] | 指定材料的方式，可选值： 'name'=命名, 'id'=编号              | 'name'              |
| diff_burnable_mats    | bool            | 是否将重复结构划分为多个燃耗区                               | 0                   |
| batch                 | int             | OpenMC每次输运的代数，不设置则默认原模型的参数                  | None                |
| inactive              | int             | OpenMC每次输运的非活跃代数，不设置则默认原模型的参数            | None                |
| particles             | int             | OpenMC每次输运的每代中子数，不设置则默认原模型的参数             | None                |


上述模块目前基于argparse打包参数，并定义了```get_args```函数，用于读取字典中的参数。
因此，有两种调用方式：
 - 通过Python导入库，将参数打包为字典后传给```get_args```，再依次调用```modify_openmc_model```和```retrieve_openmc_results```函数；
 - 通过命令行或者shell脚本，运行NuitXsLibGenerator文件夹下的```genlib.py```脚本，并传入参数，脚本会调用上述两个函数。

后一种方法比较简单，但想实现灵活的批量处理需要学习一些shell语法，而且不能只运行openmc或者只从已运行结果中提取数据，且代码报错时更不好调试。因此更推荐从Python中导入后运行的方式。 

以下为示例的shell文件：

```shell
#! /bin/bash

# 设置参数
# 这里的很多参数都是可选的，如果不想输出这些参数怎么做：
# 如果参数类型是列表，比方说burn_cells，那就留成空列表；
# 如果参数类型是数字或者字符串，比方说batch，可以设置
# 文件路径
input_path="."
output_path="./output/"
xslib_path="xslib.dat"

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

# 模拟参数
batch=10
inactive=5
particles=1000

# 设置OpenMC的环境变量
# 这里是因为openmc需要指定数据库位置，一般要么在Python文件中指定，要么在环境变量中设置
# 程序会在openmc.config和环境变量中搜索这两个文件位置，搜索到就不会报错
# 因此如果没有设置的话，可以在这里临时声明
export OPENMC_CROSS_SECTIONS=/home/dodo/nuclear_data/openmc/endfb8/cross_sections.xml
export OPENMC_CHAIN_FILE=/home/dodo/nuclear_data/openmc/chain/chain_endfb71_pwr_0.12.xml

# 指定NuitXsLibGenerator的路径并运行genlib.py
# 主要是需要指定到genlib文件的位置，可以用genlib_path指定
genlib_path="./NuitXsLibGenerator"
python $genlib_path/genlib.py --input_path $input_path --output_path $output_path --xslib_path $xslib_path \
    --powers ${powers[@]} --timesteps ${timesteps[@]} --timesteps_unit ${timesteps_unit} \
    --burn_materials ${burn_materials[@]} --burn_materials_index $burn_materials_index \
    --batch $batch --inactive $inactive --particles $particles \
    --burn_cells ${burn_cells[@]} --burn_cells_index $burn_cells_index --diff_burnable_mats $diff_burnable_mats
```
```
import sys
import openmc

sys.path.append('/home/dodo/RSAG/zhangweij/openmc/NuitXsLibGenerator')
from codes import *

openmc.config['chain_file'] = '/home/dodo/nuclear_data/openmc/chain/chain_casl_pwr_0.11.xml'
# openmc.config['cross_sections'] = '/home/dodo/nuclear_data/openmc/endfb8/cross_sections.xml'
openmc.config['cross_sections'] = '/home/dodo/nuclear_data/openmc/endfb71/cross_sections.xml'

card = {
    'input_path': '.',
    'xslib_path': 'xslib.dat',
    'burn_materials': ["kernel"],
    'burn_materials_index': 'name',
    'burn_cells': [],
    'burn_cells_index': 'id',
    'power_densities': [10 for i in range(1)],
    'timesteps': [1 for i in range(1)],
    'timesteps_unit': 'MWd/kg',
    'diff_burnable_mats': 0
}

args = get_args(card)
modify_openmc_input(args)
retrieve_openmc_results(args)
```

此处给出一些shell语法的介绍和提示：
1. 首行需指明运行脚本的shell路径；
2. 参数赋值时等号两边不能有空格；
3. 列表使用()包裹浮点数或者字符串等任意类型元素；
4. 循环的写法如下；
5. 引用变量需要写为\${var}，引用列表变量中所有参数写为${var[@]}；
6. 引用列表变量并切片的写法${var:start_index:number}

```shell
powers=[]
for i in {0..10}  # shell循环会包括最后一位
do
	 powers[i]=1
done
echo ${powers[@]}
```
