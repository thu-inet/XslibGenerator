import pathlib
import numpy as np

import openmc
import openmc.data
import openmc.stats
import openmc.deplete
import openmc.mgxs
import openmc.source
import openmc.mesh

import utils
import examples.assembly.input.E18BP0GD0 as E18BP0GD0

'''
data reference:
[1] 大亚湾堆芯图
[2] 付彬由Zr4合金组分比例计算
[2] https://www.matweb.com/search/datasheet.aspx?matguid=e36a9590eb5945de94d89a35097b7faa&ckck=1
[4] NIST: Nitrogen 13.423 kg/m3, Oxygen:15.392 kg/m3 T=768.5 K, P=3.10 MPa
[4] https://webbook.nist.gov/cgi/fluid.cgi?T=768.5&PLow=3.10&PHigh=3.10&PInc=&Digits=5&ID=C7782447&Action=Load&Type=IsoTherm&TUnit=K&PUnit=MPa&DUnit=kg%2Fm3&HUnit=kJ%2Fmol&WUnit=m%2Fs&VisUnit=uPa*s&STUnit=N%2Fm&RefState=DEF
[5] https://webbook.nist.gov/cgi/fluid.cgi?T=768.5&PLow=3.10&PHigh=3.10&PInc=&Digits=5&ID=C7440597&Action=Load&Type=IsoTherm&TUnit=K&PUnit=MPa&DUnit=kg%2Fm3&HUnit=kJ%2Fmol&WUnit=m%2Fs&VisUnit=uPa*s&STUnit=N%2Fm&RefState=DEF
[6] https://www.thomasnet.com/articles/metals-metal-products/all-about-304-SS304-properties-strength-and-uses/#:~:text=Below%20is%20a%20chemical%20breakdown%20of%20304%20SS304%3A,%3C%3D0.045%25%20phosphorus%207%20%3C%3D0.03%25%20sulfur%208%20%3C%3D1%25%20silicon
[7] https://www.engineeringtoolbox.com/water-density-specific-weight-d_595.html
[8] BEAVRS benchmark specification
[9] 大亚湾核电站 18 个月换料燃料组件机械设计验证
[10] 岭澳核电厂3、4号机组最终安全分析报告第4章——反应堆
'''

assembly = E18BP0GD0.assembly_name
pellet_number = 0
poisoned_pellet_number = 0
borosilicate_number = 0
for i in range(17):
    for j in range(17):
        if assembly[i][j] == 'fuel_pin':
            pellet_number += 1
        elif assembly[i][j] == 'gd_fuelpin':
            poisoned_pellet_number += 1
        elif assembly[i][j] == 'borosilicate':
            borosilicate_number += 1
        else:
            pass

openmc.config['cross_sections'] = '/home/dodo/nuclear_data/openmc/endfb8/cross_sections.xml'
openmc.config['chain_file'] = '/home/dodo/nuclear_data/openmc/chain/chain_casl_pwr_0.12.xml'

# geometry parameters
# ===================================================
pellet_diameter = 0.8192  # cm [10]P54
pellet_height = 365.76    # cm [10]P63 [1]P14 [10]中值386.71或386.93为整个燃料棒长度，芯块部分长度为385.76

clad_inner_diameter = 0.836  # cm [10]P12
clad_outer_diameter = 0.950  # cm [10]P12

guide_tube_inner_diameter = 1.009  # cm [10]P51 取缓冲段半径
guide_tube_outer_diameter = 1.245  # cm [10]P51

instrument_tube_inner_diameter = 1.145  # cm [10]P51
instrument_tube_outer_diameter = 1.245  # cm [10]P51

lattice_pitch = 1.26  # cm [10]P12
lattice_dimension = (17, 17)  # [10]P11
lattice_length = lattice_pitch * lattice_dimension[0]  # cm [10]
assembly_pitch = 21.504  # cm [1]P14 [10]有组件尺寸21.4cm，21.504应为包括水隙的组件距离

borosilicate_air_radius = 0.21400           # cm [8]
borosilicate_inner_SS304_radius = 0.23051   # cm [8]
borosilicate_inner_helium_radius = 0.24130  # cm [8]
borosilicate_borosilicate_radius = 0.42672  # cm [8]
borosilicate_outer_helium_radius = 0.43688  # cm [8]
borosilicate_outer_SS304_radius = 0.48387   # cm [8]
borosilicate_water_radius = 0.56134         # cm [8]
borosilicate_m5alloy_radius = 0.60198       # cm [8]

# pellet material
# ===================================================
pellet_temperature = 924  # K [1]
pellet_density = 10.41  # g/cm3 [1]
pellet_enrichement = 0.018  # % [1]
pellet_abundance = utils.enrichment2abundance(pellet_enrichement)  # %
pellet_u0_atomic_mass = utils.abundance2u0atomicweight(pellet_abundance)  # g/mol
pellet_uo2_atomic_mass = pellet_u0_atomic_mass + 2 * openmc.data.atomic_weight('O')
pellet_volume = np.pi * pellet_diameter**2 / 4 * pellet_height * pellet_number  # cm3

pellet = openmc.Material(name="pellet")
pellet.add_nuclide('U235', pellet_abundance, 'ao')
pellet.add_nuclide('U238', 1 - pellet_abundance, 'ao')
pellet.add_nuclide('O16', 2.0, 'ao')
pellet.set_density('g/cm3', pellet_density)
pellet.temperature = pellet_temperature
pellet.volume = pellet_volume

# z4alloy material
# ===================================================
z4alloy_density = 6.55  # g/cm3 [8]
z4alloy_temperature = 613  # K [1]
z4alloy_compos = ['Cr50', 'Cr52', 'Cr53', 'Cr54',
                    'Fe54', 'Fe56', 'Fe57', 'Fe58',
                    'O16', 'O17', 'O18',
                    'Sn112', 'Sn114', 'Sn115', 'Sn116',
                    'Sn117', 'Sn118', 'Sn119',
                    'Sn120', 'Sn122', 'Sn124',
                    'Zr90', 'Zr91', 'Zr92', 'Zr94', 'Zr96']
z4alloy_compos_ao = [3.2962E-6, 6.3564E-5, 7.2076E-6, 1.7941E-6,
                        8.6698E-6, 1.3610E-4, 3.1431E-6, 4.1829E-7,
                        3.0744E-04, 1.1680E-7, 6.1648e-07,
                        4.6735E-6, 3.1799E-6, 1.6381E-6, 7.0055E-5,
                        3.7003E-5, 1.1669E-4, 4.1387E-05,
                        1.5697E-4, 2.2308E-5, 2.7897E-5,
                        2.1828E-2, 4.7601E-3, 7.2759E-3, 7.3734E-3, 1.1879E-3]

z4alloy = openmc.Material(name="z4alloy")
z4alloy.set_density('g/cm3', z4alloy_density)
z4alloy.temperature = z4alloy_temperature
for compo, ao in zip(z4alloy_compos, z4alloy_compos_ao):
    z4alloy.add_nuclide(compo, ao, 'ao')

# m5alloy material
# ===================================================
m5alloy_density = 6.65  # g/cm3 [8] 
m5alloy_temperature = 613  # K [1] 
m5alloy_compos = ['Zr', 'Nb', 'O']
m5alloy_compos_wo = [0.97875, 0.01, 0.00125]  # [10] 含1%铌，氧约为0.125%
m5alloy_compos_ao = utils.wo2ao(m5alloy_compos_wo, [openmc.data.atomic_weight('Zr'), openmc.data.atomic_weight('Nb'), openmc.data.atomic_weight('O')])
m5alloy = openmc.Material(name="m5alloy")
m5alloy.set_density('g/cm3', m5alloy_density)
m5alloy.temperature = m5alloy_temperature
for compo, ao in zip(m5alloy_compos, m5alloy_compos_ao):
    m5alloy.add_element(compo, ao, 'ao')

# SS304 material
# ===================================================
SS304_density = 8.03  # g/cm3 [8]
SS304_compos = ['Cr50', 'Cr52', 'Cr53', 'Cr54',
                'Fe54', 'Fe56', 'Fe57', 'Fe58',
                'Mn55',
                'Ni58', 'Ni60', 'Ni61', 'Ni62', 'Ni64',
                'Si28', 'Si29', 'Si30']
SS304_compos_ao = [7.6778e-04, 1.4806e-02, 1.6789e-03, 4.1791e-04,
                    3.4620e-03, 5.4345e-02, 1.2551e-03, 1.6703e-04,
                    1.7604e-03,
                    5.6089e-03, 2.1605e-03, 9.3917e-05, 2.9945e-04, 7.6261e-05,
                    9.5281e-04, 4.8381e-05, 3.1893e-05]

SS304 = openmc.Material(name="SS304")
SS304.set_density('g/cm3', SS304_density)
for compo, ao in zip(SS304_compos, SS304_compos_ao):
    SS304.add_nuclide(compo, ao, 'ao')

# helium material
# ===================================================
helium_temperature = 768.5  # K [1]
helium_density = 0.0019324  # g/cm3 [5] 768.5K,3.10MPa

helium = openmc.Material(name="helium")
helium.add_nuclide('He4', 1.0, 'ao')
helium.set_density('g/cm3', helium_density)
helium.temperature = helium_temperature

# water material
# ===================================================
water_temperature = 583.7  # K
water_ebc = 600 * 1E-6  # ppm
water_density = openmc.data.water_density(water_temperature, pressure=15.51)  # [1]
water_boron_ao, water_water_ao = utils.wo2ao([water_ebc, 1-water_ebc], [openmc.data.atomic_weight('B'), openmc.data.atomic_weight('O')+openmc.data.atomic_weight('H')*2])

water = openmc.Material(name="h2o")
water.add_nuclide('H1', water_water_ao * 2, 'ao')
water.add_nuclide('O16', water_water_ao * 1, 'ao')
water.add_element('B', water_boron_ao, 'ao')
water.set_density('g/cm3', water_density)
water.add_s_alpha_beta('c_H_in_H2O')
water.temperature = water_temperature

# Gd2O3 material
# ===================================================
poisoned_pellet_gd2o3_wo = 8.0 * 0.01  # % [1]
poisoned_pellet_gd2o3_density = 8.33  # g/cm3 [10]P116
poisoned_pellet_uo2_density = 10.41   # g/cm3 [1]
poisoned_pellet_volume = np.pi * pellet_diameter**2 / 4 * pellet_height * poisoned_pellet_number  # cm3
poisoned_pellet_density = poisoned_pellet_uo2_density * poisoned_pellet_gd2o3_density / (poisoned_pellet_gd2o3_density * (1 - poisoned_pellet_gd2o3_wo) + poisoned_pellet_uo2_density * poisoned_pellet_gd2o3_wo)

poisoned_pellet_enrichment = 2.5 * 0.01  # % [1]
poisoned_pellet_abundance = utils.enrichment2abundance(poisoned_pellet_enrichment)  # %
poisoned_pellet_u0_atomic_mass = utils.abundance2u0atomicweight(poisoned_pellet_abundance)
poisoned_pellet_uo2_atomic_mass = poisoned_pellet_u0_atomic_mass + 2 * openmc.data.atomic_weight('O')
poisoned_pellet_gd2o3_atomic_mass = 2 * openmc.data.atomic_weight('Gd') + 3 * openmc.data.atomic_weight('O')
poisoned_pellet_gd2o3_ao, poisoned_pellet_uo2_ao = utils.wo2ao([poisoned_pellet_gd2o3_wo, 1-poisoned_pellet_gd2o3_wo], [poisoned_pellet_gd2o3_atomic_mass, poisoned_pellet_uo2_atomic_mass])
poisoned_pellet_gd0_ao = poisoned_pellet_gd2o3_ao * 2
poisoned_pellet_u235_ao = poisoned_pellet_uo2_ao * 1 * poisoned_pellet_abundance
poisoned_pellet_u238_ao = poisoned_pellet_uo2_ao * 1 * (1-poisoned_pellet_abundance)
poisoned_pellet_o0_ao = poisoned_pellet_gd2o3_ao * 3 + poisoned_pellet_uo2_ao * 2

gd_pellet = openmc.Material(name="poisoned_pellet")
gd_pellet.set_density('g/cm3', poisoned_pellet_density)
gd_pellet.add_nuclide('U235', poisoned_pellet_u235_ao, 'ao')
gd_pellet.add_nuclide('U238', poisoned_pellet_u238_ao, 'ao')
gd_pellet.add_nuclide('O16', poisoned_pellet_o0_ao, 'ao')
gd_pellet.add_element('Gd', poisoned_pellet_gd0_ao, 'ao')
gd_pellet.volume = poisoned_pellet_volume
gd_pellet.temperature = pellet_temperature

# # borosilicate material
# ===================================================
borosilicate_density = 2.26  # g/cm3 [8]
borosilicate_boron_wo = 0.74 * 0.01  # % [1]
borosilicate_volume = np.pi * (borosilicate_borosilicate_radius**2 - borosilicate_inner_helium_radius**2) / 4 * pellet_height * borosilicate_number  # cm3
borosilicate_compos = ['Al27',
                        'O16', 'O17', 'O18',
                        'Si28', 'Si29', 'Si30']
borosilicate_compos_ao = [1.7352E-3,
                            4.6514e-02, 1.7671e-05, 9.3268e-05,
                            1.6926e-02, 8.5944e-04, 5.6654e-04]
borosilicate_compos_wo = utils.ao2wo(borosilicate_compos_ao, [openmc.data.atomic_mass('Al27'), 
                                                            openmc.data.atomic_mass('O16'), openmc.data.atomic_mass('O17'), openmc.data.atomic_mass('O18'),
                                                            openmc.data.atomic_mass('Si28'), openmc.data.atomic_mass('Si29'), openmc.data.atomic_mass('Si30')])
borosilicate_compos.extend(['B10', 'B11'])
borosilicate_compos_wo = list(borosilicate_compos_wo)
borosilicate_compos_wo.extend([borosilicate_boron_wo*0.199, borosilicate_boron_wo*0.801])
borosilicate_compos_ao = utils.wo2ao(borosilicate_compos_wo, [openmc.data.atomic_mass('Al27'), 
                                                            openmc.data.atomic_mass('O16'), openmc.data.atomic_mass('O17'), openmc.data.atomic_mass('O18'),
                                                            openmc.data.atomic_mass('Si28'), openmc.data.atomic_mass('Si29'), openmc.data.atomic_mass('Si30'),
                                                            openmc.data.atomic_mass('B10'), openmc.data.atomic_mass('B11')])

borosilicate = openmc.Material(name="borosilicate")
borosilicate.set_density('g/cm3', borosilicate_density)
for compo, ao in zip(borosilicate_compos, borosilicate_compos_ao):
    borosilicate.add_nuclide(compo, ao, 'ao')
borosilicate.temperature = 900.1 
borosilicate.volume = borosilicate_volume
borosilicate.depletable = True

# all materials
# ===================================================
mats = openmc.Materials([pellet, helium, z4alloy, m5alloy, water, SS304, borosilicate, gd_pellet])
mats.export_to_xml()
print("================================================")
print(f"{'material':<20s}{'nuclide':<20s}{'density':<10s}")
for mat in mats:
    print("================================================")
    print(f"{mat.name:<40s}{mat.density:.3E}")
    for nuclide in mat.nuclides:
        print(f"{mat.name:<20s}{nuclide.name:<20s}{mat.get_mass_density(nuclide.name):<.3E}")

# fuelpin universe
# ===================================================
surf_fuelpin_pellet = openmc.ZCylinder(r=pellet_diameter/2)
surf_fuelpin_m5alloy_inner = openmc.ZCylinder(r=clad_inner_diameter/2)
surf_fuelpin_m5alloy_outer = openmc.ZCylinder(r=clad_outer_diameter/2)

cell_fuelpin_pellet = openmc.Cell(101, "fuelpin_pellet", fill=pellet, region=-surf_fuelpin_pellet)
cell_fuelpin_air = openmc.Cell(102, "fuelpin_air", fill=helium, region=+surf_fuelpin_pellet & -surf_fuelpin_m5alloy_inner)
cell_fuelpin_clad = openmc.Cell(103, "fuelpin_clad", fill=m5alloy, region=+surf_fuelpin_m5alloy_inner & -surf_fuelpin_m5alloy_outer)
cell_fuelpin_water = openmc.Cell(104, "fuelpin_water", fill=water, region=+surf_fuelpin_m5alloy_outer)
univ_fuelpin = openmc.Universe(cells=[cell_fuelpin_pellet, cell_fuelpin_air, cell_fuelpin_clad, cell_fuelpin_water])

# Gd fuelpin universe
# ===================================================
surf_Gd_fuelpin_pellet = openmc.ZCylinder(r=pellet_diameter/2)
surf_Gd_fuelpin_m5alloy_inner = openmc.ZCylinder(r=clad_inner_diameter/2)
surf_Gd_fuelpin_m5alloy_outer = openmc.ZCylinder(r=clad_outer_diameter/2)

cell_Gd_fuelpin_pellet = openmc.Cell(105, "Gd_fuelpin_pellet", fill=gd_pellet, region=-surf_Gd_fuelpin_pellet)
cell_Gd_fuelpin_air = openmc.Cell(106, "Gd_fuelpin_air", fill=helium, region=+surf_Gd_fuelpin_pellet & -surf_Gd_fuelpin_m5alloy_inner)
cell_Gd_fuelpin_clad = openmc.Cell(107, "Gd_fuelpin_clad", fill=m5alloy, region=+surf_Gd_fuelpin_m5alloy_inner & -surf_Gd_fuelpin_m5alloy_outer)
cell_Gd_fuelpin_water = openmc.Cell(108, "Gd_fuelpin_water", fill=water, region=+surf_Gd_fuelpin_m5alloy_outer)
univ_gd_fuelpin = openmc.Universe(cells=[cell_Gd_fuelpin_pellet, cell_Gd_fuelpin_air, cell_Gd_fuelpin_clad, cell_Gd_fuelpin_water])

# guide tube universe
# ===================================================
surf_guide_tube_inner = openmc.ZCylinder(r=guide_tube_inner_diameter/2)
surf_guide_tube_outer = openmc.ZCylinder(r=guide_tube_outer_diameter/2)

cell_guide_tube_inner_water = openmc.Cell(201, "guide_tube_inner_water", fill=water, region=-surf_guide_tube_inner)
cell_guide_tube_shell = openmc.Cell(202, "guide_tube_shell", fill=m5alloy, region=+surf_guide_tube_inner & -surf_guide_tube_outer)
cell_guide_tube_water = openmc.Cell(203, "guide_tube_water", fill=water, region=+surf_guide_tube_outer)
univ_guide_tube = openmc.Universe(cells=[cell_guide_tube_inner_water, cell_guide_tube_shell, cell_guide_tube_water])

# borosilicate guide tube universe
# ===================================================
surf_borosilicate_air = openmc.ZCylinder(r=borosilicate_air_radius)
surf_borosilicate_inner_SS304 = openmc.ZCylinder(r=borosilicate_inner_SS304_radius)
surf_borosilicate_inner_helium = openmc.ZCylinder(r=borosilicate_inner_helium_radius)
surf_borosilicate_borosilicate = openmc.ZCylinder(r=borosilicate_borosilicate_radius)
surf_borosilicate_outer_helium = openmc.ZCylinder(r=borosilicate_outer_helium_radius)
surf_borosilicate_outer_SS304 = openmc.ZCylinder(r=borosilicate_outer_SS304_radius)
surf_borosilicate_water = openmc.ZCylinder(r=borosilicate_water_radius)
surf_borosilicate_z4alloy = openmc.ZCylinder(r=borosilicate_m5alloy_radius)
cell_borosilicate_air = openmc.Cell(211, "borosilicate_air", fill=helium, region=-surf_borosilicate_air)
cell_borosilicate_inner_SS304 = openmc.Cell(212, "borosilicate_inner_SS304", fill=SS304, region=+surf_borosilicate_air & -surf_borosilicate_inner_SS304)
cell_borosilicate_inner_helium = openmc.Cell(213, "borosilicate_inner_helium", fill=helium, region=+surf_borosilicate_inner_SS304 & -surf_borosilicate_inner_helium)
cell_borosilicate_borosilicate = openmc.Cell(214, "borosilicate_borosilicate", fill=borosilicate, region=+surf_borosilicate_inner_helium & -surf_borosilicate_borosilicate)
cell_borosilicate_outer_helium = openmc.Cell(215, "borosilicate_outer_helium", fill=helium, region=+surf_borosilicate_borosilicate & -surf_borosilicate_outer_helium)
cell_borosilicate_outer_SS304 = openmc.Cell(216, "borosilicate_outer_SS304", fill=SS304, region=+surf_borosilicate_outer_helium & -surf_borosilicate_outer_SS304)
cell_borosilicate_water = openmc.Cell(217, "borosilicate_water", fill=water, region=+surf_borosilicate_outer_SS304 & -surf_borosilicate_water)
cell_borosilicate_z4alloy = openmc.Cell(218, "borosilicate_z4alloy", fill=z4alloy, region=+surf_borosilicate_water & -surf_borosilicate_z4alloy)
cell_borosilicate_outer_water = openmc.Cell(219, "borosilicate_outer_water", fill=water, region=+surf_borosilicate_z4alloy)
univ_borosilicate = openmc.Universe(cells=[cell_borosilicate_air, cell_borosilicate_inner_SS304, cell_borosilicate_inner_helium, cell_borosilicate_borosilicate, 
                                        cell_borosilicate_outer_helium, cell_borosilicate_outer_SS304, cell_borosilicate_water, cell_borosilicate_z4alloy, cell_borosilicate_outer_water])

# instrument tube universe
# ===================================================
surf_instrument_tube_shell_inner = openmc.ZCylinder(r=instrument_tube_inner_diameter/2)
surf_instrument_tube_shell_outer = openmc.ZCylinder(r=instrument_tube_outer_diameter/2)
cell_instrument_tube_inner_water = openmc.Cell(301, "instrument_tube_inner_water", fill=water, region=-surf_instrument_tube_shell_inner)
cell_instrument_tube_inner_shell = openmc.Cell(302, "instrument_tube_inner_shell", fill=m5alloy, region=+surf_instrument_tube_shell_inner & -surf_instrument_tube_shell_outer)
cell_instrument_tube_outer_water = openmc.Cell(303, "instrument_tube_outer_water", fill=water, region=+surf_instrument_tube_shell_outer)
univ_instrument_tube = openmc.Universe(cells=[cell_instrument_tube_inner_water, cell_instrument_tube_inner_shell, cell_instrument_tube_outer_water])

# lattice defintion and root universe
# ===================================================
universes = {'fuel_pin': univ_fuelpin,
            'gd_fuelpin': univ_gd_fuelpin,
            'guide_tube': univ_guide_tube,
            'borosilicate': univ_borosilicate,
            'instrument_tube': univ_instrument_tube}

lattice = openmc.RectLattice()
lattice.lower_left = [-lattice_length/2, -lattice_length/2]
lattice.pitch = [lattice_pitch, lattice_pitch]
lattice.universes = [[universes[assembly[i][j]] for j in range(lattice_dimension[0])] for i in range(lattice_dimension[1])]

surf_lattice_above = openmc.ZPlane(z0=pellet_height, boundary_type='reflective')
surf_lattice_below = openmc.ZPlane(z0=0, boundary_type='reflective')
surf_lattice_east = openmc.XPlane(x0=lattice_length/2)
surf_lattice_west = openmc.XPlane(x0=-lattice_length/2)
surf_lattice_north = openmc.YPlane(y0=lattice_length/2)
surf_lattice_south = openmc.YPlane(y0=-lattice_length/2)

surf_assembly_east = openmc.XPlane(x0=assembly_pitch/2, boundary_type='reflective')
surf_assembly_west = openmc.XPlane(x0=-assembly_pitch/2, boundary_type='reflective')
surf_assembly_north = openmc.YPlane(y0=assembly_pitch/2, boundary_type='reflective')
surf_assembly_south = openmc.YPlane(y0=-assembly_pitch/2, boundary_type='reflective')

lattice_space = -surf_lattice_east & +surf_lattice_west & -surf_lattice_north & +surf_lattice_south & -surf_lattice_above & +surf_lattice_below
total_space = -surf_assembly_east & +surf_assembly_west & -surf_assembly_north & +surf_assembly_south & -surf_lattice_above & +surf_lattice_below

cell_lattice = openmc.Cell(fill=lattice, region=lattice_space)
cell_water_gap = openmc.Cell(fill=water, region=total_space & ~lattice_space)

univ_root = openmc.Universe(cells=[cell_lattice, cell_water_gap])
geometry = openmc.Geometry(univ_root)
geometry.export_to_xml()


tallies = openmc.Tallies([])
tallies.export_to_xml()

# settings
# ===================================================
settings = openmc.Settings()
settings.batches = 100
settings.inactive = 20
settings.particles = 20000
initial_source = openmc.stats.CylindricalIndependent(r=openmc.stats.PowerLaw(a=0, b=assembly_pitch/2),
                                                        phi=openmc.stats.Uniform(a=0, b=2*openmc.pi),
                                                        z=openmc.stats.Uniform(a=0, b=pellet_height))
settings.source = openmc.source.Source(space=initial_source)
settings.temperature['default'] = 600
settings.temperature['method'] = 'interpolation'
settings.export_to_xml()

# openmc.run()