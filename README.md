# XslibGenerator

XslibGenerator基于OpenMC输运-燃耗耦合计算产生用于点堆源项程序NUIT的单群中子反应截面数据库。程序分为基础依赖和流程控制部分，基础依赖（constants.py和classes.py)存储了计算中需要用到的常量、数据等，以及定义了计算中使用的类（反应、核素和截面库），流程控制部分(prerun.py, postrun.py和interpolate.py）负责接受参数进行计算，包含模型处理、数据提取和插值三个模块，使用OpenMC模型做计算并制备截面库仅需要使用模型处理和数据提取模块，插值仅在用户需要从已有截面库中插值新截面库时需要使用。

## 依赖
标准库： pathlib， shutil, argparse, xml, time, logging
其他：pandas, numpy, openmc

## 使用


### 产生截面库

模型处理和数据提取同时使用，采用相同的输入参数，如下：

| 参数                  | 类型            | 含义                                                         | 默认值              |
| --------------------- | --------------- | ------------------------------------------------------------ | ------------------- |
| input                 | string          | OpenMC模型（xml文件）存放路径                                | -                   |
| output                | string          | OpenMC输出存放路径                                           | input +  '_out'     |
| xslib                 | string          | 单群截面库存放路径                                           | input + '_xslib.dat |
| powers                | list[float]     | 所有燃耗步的功率，单位W，和power_densities需要二选一         | -                   |
| power_densities       | list[float]     | 所有燃耗步的功率密度，单位MW/tU，和powers需要二选一          | -                   |
| timesteps             | list[float]     | 所有燃耗步的单步时间/燃耗设置                                | -                   |
| timesteps_unit        | Literal[string] | 燃耗步时间单位，可选值: 'a'=年, 'd'=天，'h'=时, 'm'=分，'s'=秒, 'MWd/kg'=燃耗 | 'd'                 |
| burn_materials        | list[string]    | 截面库统计反应率和通量的材料，和burn_cells需要二选一         | -                   |
| burnup_material_index | Literal[string] | 指定材料的方式，可选值： 'name'=命名, 'id'=编号              | 'name'              |
| burn_cells            | list[string]    | 截面库统计反应率和通量的栅元，和burn_materials需要二选一     | -                   |
| burn_cell_index       | Literal[string] | 指定材料的方式，可选值： 'name'=命名, 'id'=编号              | 'name'              |
| diff_burnable_mats    | bool            | 是否将重复结构划分为多个燃耗区                               | 0                   |

上述模块目前基于argparse通过命令行调用，因此可以从命令终端、shell脚本或者python脚本（调用os或subprocess等shell接口）来调用。以下为示例的shell文件：

```shell
#! /bin/bash

# 文件路径
input="./pin/"
output="./pin_out/"
xslib="subxslib_pin.dat"

# 燃耗过程
powers=(1.8e7)
timesteps=(1)
timesteps_unit='MWd/kg'
diff_burnable_mats=1
# 燃耗区域
burn_materials=('moxpellet', 'h2o')
burn_materials_index='name'
burn_cells=()
burn_cells_index='name'

python prerun.py \
    --input $input --output $output --xslib $xslib \
    --power_densities ${power_densities[@]} --timesteps ${timesteps[@]} --timesteps_unit ${timesteps_unit} \
    --burn_materials ${burn_materials[@]} --burn_materials_index $burn_materials_index \
    --burn_cells ${burn_cells[@]} --burn_cells_index $burn_cells_index --diff_burnable_mats $diff_burnable_mats

python postrun.py --input $input --output $output --xslib $xslib \
    --input $input --output $output --xslib $xslib \
    --powers ${powers[@]} --timesteps ${timesteps[@]} --timesteps_unit ${timesteps_unit} \
    --burn_materials ${burn_materials[@]} --burn_materials_index $burn_materials_index \
    --burn_cells ${burn_cells[@]} --burn_cells_index $burn_cells_index --diff_burnable_mats $diff_burnable_mats
```

此处给出一些shell语法的介绍和提示：1.首行需指明运行脚本的shell路径；2.参数赋值时等号两边不能有空格；3.列表使用()包裹浮点数或者字符串等任意类型元素；4.循环的写法如下；5.引用变量需要写为${var}，引用列表变量中所有参数写为${var[@]}，切片写法${var:start_index:number}

```shell
powers=[]
for i in {0..10}  # shell循环会包括最后一为
do
	 powers[i]=1
done
echo ${powers[@]}
```

此外也可以通过python调用os或者subprocess等shell接口来调用，但需要注意powers等列表提供给shell时需要转化为可识别的字符串如下：

```python
powers = [1, 2, 3]
powers = ' '.join([f'{i:.1f}' for i in powers])
print(powers)  # output：1.0 2.0 3.0
```

目前的调用形式还比较麻烦，同时也不方便调试，后期计划修改为库的形式。

### 插值截面库

