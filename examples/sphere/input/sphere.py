import numpy as np

import openmc
import openmc.model
import openmc.data
import openmc.deplete
import openmc.stats
from openmc.mgxs import GROUP_STRUCTURES



# macro data setting
num_trisos = 8333
enrichment = 17 * 0.01
abundance = 0.085  # 注意富集度和丰度的区别
temperature = 900
radius_kernel = 250 * 1E-4
radius_buffer = 345 * 1E-4 # THICKNESS = 95
radius_iPyC = 385 * 1E-4 # THICKNESS = 40
radius_SiC = 420 * 1E-4 # THICKNESS = 35
radius_oPyC = 460 * 1E-4 # THICKNESS = 40

mass_U0 = 7
density_UO2 = 10.4
density_buffer = 1.05
density_PyC = 1.90
density_SiC = 3.18
density_graphite = 1.74

radius_fuel_region = 2.5
radius_fuel = 3
radius_helium = 3.55689

U235_atomic_mass = 235
U238_atomic_mass = 238
C0_atomic_mass = 12.0107
Si0_atomic_mass = 28.0855
O16_atomic_mass = 15.9994
B0_atomic_mass = 10.811

U0_atomic_mass = U235_atomic_mass * abundance + U238_atomic_mass * (1 - abundance)
UO2_atomic_mass = U0_atomic_mass + O16_atomic_mass * 2
SiC_atomic_mass = C0_atomic_mass + Si0_atomic_mass


ebc_kernel = 0.5 * 1E-6
ebc_graphite = 0.795 * 1E-6
ebc_coatings = 0.795 * 1E-6
def atomic_mass_boron(impurity_ebc, atomic_mass_main):
    B0_atomic_mass = 10.811
    mass_impurity = atomic_mass_main * impurity_ebc / (1 - impurity_ebc) / B0_atomic_mass
    return mass_impurity
b0_impurity_kernel = atomic_mass_boron(ebc_kernel, UO2_atomic_mass)
b0_impurity_coatings = atomic_mass_boron(ebc_coatings, C0_atomic_mass)
b0_impurity_graphite = atomic_mass_boron(ebc_graphite, C0_atomic_mass)

# data path config
num_lattice = 24
batches = 120
inactive = 40
particles = 10000

openmc.config['cross_sections'] = '/home/dodo/nuclear_data/openmc/endfb71/cross_sections.xml'


# kernel material
kernel = openmc.Material(name='kernel')
kernel.set_density('g/cm3', density_UO2)
kernel.add_nuclide('U235', abundance, percent_type='ao')
kernel.add_nuclide('U238', 1 - abundance, percent_type='ao')
kernel.add_nuclide('Pu239', 1E-10, percent_type='ao')
kernel.add_nuclide('O16', 2, percent_type='ao')
kernel.add_element('B', b0_impurity_kernel, percent_type='ao')
kernel.volume = num_trisos * np.pi * 4/3 * radius_kernel**3

# buffer material
buffer = openmc.Material(name='buffer')
buffer.set_density('g/cm3', density_buffer)
buffer.add_element('C', 1, percent_type='ao')
buffer.add_s_alpha_beta('c_Graphite')
buffer.add_element('B', b0_impurity_coatings, percent_type='ao')

# IPyC material
IPyC = openmc.Material(name='IPyC')
IPyC.set_density('g/cm3', density_PyC)
IPyC.add_element('C', 1, percent_type='ao')
IPyC.add_element('B', b0_impurity_coatings, percent_type='ao')
IPyC.add_s_alpha_beta('c_Graphite')

# SiC material
SiC = openmc.Material(name='SiC')
SiC.set_density('g/cm3', density_SiC)
SiC.add_element('C', 1, percent_type='ao')
SiC.add_element('Si', 1, percent_type='ao')
SiC.add_element('B', b0_impurity_coatings, percent_type='ao')

# OpyC material
OPyC = openmc.Material(name='OPyC')
OPyC.set_density('g/cm3', density_PyC)
OPyC.add_element('C', 1, percent_type='ao')
OPyC.add_element('B', b0_impurity_coatings, percent_type='ao')
OPyC.add_s_alpha_beta('c_Graphite')

# graphite material
graphite = openmc.Material(name='graphite')
graphite.set_density('g/cm3', density_graphite)
graphite.add_element('C', 1, percent_type='ao')
graphite.add_element('B', b0_impurity_graphite, percent_type='ao')
graphite.add_s_alpha_beta('c_Graphite')


# add graphite material
add_graphite = openmc.Material(name='add_graphite')
add_graphite.set_density('g/cm3', density_graphite)
add_graphite.add_element('C', 1, percent_type='ao')
add_graphite.add_s_alpha_beta('c_Graphite')

# pack all materials
mats = openmc.Materials([kernel, buffer, IPyC, SiC, OPyC, graphite, add_graphite])
mats.export_to_xml()

# surfaces and cells
surfs_triso = [openmc.Sphere(r=r) for r in [radius_kernel, radius_buffer, radius_iPyC, radius_SiC, radius_oPyC]]
cells_triso = [openmc.Cell(fill=kernel, region=-surfs_triso[0]),
               openmc.Cell(fill=buffer, region=+surfs_triso[0] & -surfs_triso[1]),
               openmc.Cell(fill=IPyC, region=+surfs_triso[1] & -surfs_triso[2]),
               openmc.Cell(fill=SiC, region=+surfs_triso[2] & -surfs_triso[3]),
               openmc.Cell(fill=OPyC, region=+surfs_triso[3] & -surfs_triso[4])]
univ_triso = openmc.Universe(name='univ_triso', cells=cells_triso)

surf_fuel = openmc.Sphere(r=radius_fuel_region)
surf_fuelfree = openmc.Sphere(r=radius_fuel)
surf_boundary = openmc.Sphere(r=radius_helium, boundary_type='white')
cell_fuel = openmc.Cell(fill=graphite, region=-surf_fuel)
cell_fuelfree = openmc.Cell(fill=graphite, region=+surf_fuel & - surf_fuelfree)
cell_boundary = openmc.Cell(fill=add_graphite, region=+surf_fuelfree & -surf_boundary)

# pack triso universe into random lattices
cntrs_triso = openmc.model.pack_spheres(radius=radius_oPyC, 
                                        region=cell_fuel.region, 
                                        num_spheres=num_trisos)
trisos = [openmc.model.TRISO(outer_radius=radius_oPyC, fill=univ_triso, center=cntr) for cntr in cntrs_triso]
latts_triso = openmc.model.create_triso_lattice(trisos=trisos, 
                                                lower_left=cell_fuel.bounding_box[0], 
                                                shape=[num_lattice]*3,
                                                pitch=(cell_fuel.bounding_box[1]-cell_fuel.bounding_box[0])/num_lattice,
                                                background=graphite)
cell_fuel.fill = latts_triso

# build the integral geometry
geometry = openmc.Geometry(openmc.Universe(cells=[cell_fuel, cell_fuelfree, cell_boundary]))
geometry.export_to_xml()

# tally filters
cellfilter = openmc.MaterialFilter(kernel)
energyfilter = openmc.EnergyFilter(GROUP_STRUCTURES['SHEM-361'])

# tally to measure flux
tally = openmc.Tally(tally_id=1)
tally.scores = ['flux']
tally.filters = [cellfilter, energyfilter]
tally.estimator = 'tracklength'

# tally to measure absorption and fission rate
tally2 = openmc.Tally(tally_id=2)
tally2.nuclides = ['U235', 'U238', 'Pu239']
tally2.scores = ['fission', 'absorption']
tally2.filters = [cellfilter]
tally2.estimator = 'tracklength'

# tally to measure overall flux
tally3 = openmc.Tally(tally_id=3)
tally3.scores = ['flux']
tally3.filters = [cellfilter]
tally3.estimator = 'tracklength'

tallies = openmc.Tallies(tallies=[tally2, tally3, tally])
tallies.export_to_xml()

# settings config
settings = openmc.Settings()
settings.run_mode = 'eigenvalue'
settings.batches = batches
settings.inactive = inactive
settings.particles = particles
settings.generations_per_batch = 1
settings.photon_transport = False
settings.source = openmc.Source(space=openmc.stats.spherical_uniform(r_outer=2.5), 
                                angle=openmc.stats.Isotropic())
settings.temperature['default'] = temperature
settings.temperature['method'] = 'interpolation'
settings.export_to_xml() 

# openmc.run()