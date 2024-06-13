import numpy as np

# 富集度
enrichment = 1.80 * 0.01

# 组件形状
lattice_dimension = (17, 17)

# 棒种类映射: {棒位名: (ID, [(i, j), ...])}
pin_map = {'instrument_tube': (1, [(0, 0)]), 
                'guide_tube': (2, [(3, 3), (6, 0), (5, 5), (3, 6), (3, 0)]), 
                'gd_fuelpin': (3, []),
                'borosilicate': (4, [])}
# 八分之一组件上的位置映射
def position_map(i, j):
    return [(i, j), (i, -j), (-i, j), (-i, -j), (j, i), (j, -i), (-j, i), (-j, -i)]


# 将棒位映射到全尺寸的组件上
assembly = [[0 for _ in range(lattice_dimension[1])] for _ in range(lattice_dimension[0])]
for name, (id, positions) in pin_map.items():
    for position in positions:
        for i, j in position_map(*position):
            di = int((lattice_dimension[0]-1)/2)
            dj = int((lattice_dimension[1]-1)/2)
            print(i+di, j+dj)
            assembly[i+di][j+dj] = id
print(np.array(assembly))
