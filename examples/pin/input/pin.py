
import numpy as np

import openmc
import openmc.stats
import openmc.deplete
import openmc.mgxs
import openmc.data
import openmc.model
import openmc.source

pellet_diameter = 0.819
pellet_height = 10
pellet_density = 10.4
pellet_temperature = 293
pellet_abundance = 0.01822  # 富集度1.8%换算

clad_inner_diameter = 8.36 * 0.1
clad_outer_diameter = 9.50 * 0.1
clad_comps = ['Cr50', 'Fe56', 'O16', 'Sn118', 'Zr90']
clad_compos_den = [0.0066, 0.0132, 0.00792, 0.0924, 6.501]
clad_density = sum(clad_compos_den)
clad_compos_wo = [x / clad_density for x in clad_compos_den]
clad_temperature = 293

helium_density = 0.0050178
helium_temperature = 293

water_temperature = 293
water_diameter = 14.2 * 0.1
water_density = openmc.data.water_density(water_temperature)
water_boron_concentration = 0.0005

# material definition
pellet = openmc.Material(1, "pellet")
pellet.add_nuclide('U235', pellet_abundance, 'ao')
pellet.add_nuclide('U238', 1 - pellet_abundance, 'ao')
pellet.add_nuclide('O16', 2.0)
pellet.set_density('g/cm3', pellet_density)
pellet.temperature = pellet_temperature
pellet.volume = np.pi * pellet_diameter**2 / 4 * pellet_height

clad = openmc.Material(2, "clad")
for compo, wo in zip(clad_comps, clad_compos_wo):
    clad.add_nuclide(compo, wo, 'wo')
clad.set_density('g/cm3', clad_density)
clad.temperature = clad_temperature

water = openmc.Material(3, "h2o")
water.add_nuclide('H1', 2.0)
water.add_nuclide('O16', 1.0)
water.add_element('B', water_boron_concentration, 'ao')
water.set_density('g/cm3', water_density)
water.add_s_alpha_beta('c_H_in_H2O')
water.temperature = water_temperature
water.depletable = True
water.volume = np.pi * water_diameter**2 / 4 * pellet_height \
                    - np.pi * clad_outer_diameter**2 / 4 * pellet_height

helium = openmc.Material(4, "helium")
helium.add_nuclide('He4', 1.0)
helium.set_density('g/cm3', helium_density)
helium.temperature = helium_temperature

# material export
mats = openmc.Materials([pellet, clad, water, helium])
mats.export_to_xml()

# geometry definition
surf_pellet = openmc.ZCylinder(r=pellet_diameter/2)
surf_clad_inner = openmc.ZCylinder(r=clad_inner_diameter/2)
surf_clad_outer = openmc.ZCylinder(r=clad_outer_diameter/2)

cell_pellet = openmc.Cell(1, "fuel", fill=pellet, region=-surf_pellet)
cell_air = openmc.Cell(2, "air gap", fill=helium, region=+surf_pellet & -surf_clad_inner)
cell_clad = openmc.Cell(3, "clad", fill=clad, region=+surf_clad_inner & -surf_clad_outer)
cell_water = openmc.Cell(4, "water", fill=water, region=+surf_clad_outer)

univ_pin = openmc.Universe(cells=[cell_pellet, cell_air, cell_clad, cell_water])

# root universe
surf_side = openmc.ZCylinder(r=water_diameter/2, boundary_type='white')
surf_above = openmc.ZPlane(z0=pellet_height, boundary_type='white')
surf_below = openmc.ZPlane(z0=0, boundary_type='white')
cell_pin = openmc.Cell(5, "universe", fill=univ_pin, region=-surf_above & +surf_below & -surf_side)
univ_root = openmc.Universe(cells=[cell_pin])

# geometry export
geom = openmc.Geometry(univ_root)
geom.export_to_xml()

# settings definition
settings = openmc.Settings()
settings.batches = 1000
settings.inactive = 50
settings.particles = 10000
initial_source = openmc.stats.CylindricalIndependent(r=openmc.stats.Uniform(a=0, b=pellet_diameter/2),
                                                    phi=openmc.stats.Uniform(a=0, b=2*openmc.pi),
                                                    z=openmc.stats.Uniform(a=0, b=10))
settings.source = openmc.source.Source(space=initial_source)
settings.temperature['default'] = 293
settings.temperature['method'] = 'interpolation'
settings.export_to_xml()

energyfilter = openmc.EnergyFilter(openmc.mgxs.GROUP_STRUCTURES['SHEM-361'])
materialfilter = openmc.MaterialFilter([pellet])

tally2 = openmc.Tally(2)
tally2.filters = [energyfilter, materialfilter]
tally2.scores = ['flux']

tally3 = openmc.Tally(3)
tally3.filters = [materialfilter]
tally3.scores = ['heating-local']

tallies = openmc.Tallies([tally2, tally3])
tallies.export_to_xml()

model = openmc.model.Model(geom, mats, settings)
model.export_to_xml()





