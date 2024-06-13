import numpy as np
import pathlib

from re import match

# dict of nuclear reaction: channel -> MT number
MT_dict = {'(n,2n)': 16,
           '(n,3n)': 17,
           '(n,4n)': 37,
           '(n,a)': 107,
           '(n,gamma)': 102,
           '(n,gamma)M': 1021,
           '(n,p)': 103,
           'fission': 18}

# dict of periodic table: symbol -> atomic number
Atomic_list = ['H', 'He',
               'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
               'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
               'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr',
               'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In','Sn', 'Sb', 'Te', 'I', 'Xe',
               'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn',
               'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og']
Atomic_dict = {item: ind+1 for ind, item in enumerate(Atomic_list)}

actinides = ['Th231', 'Th234', 'Pa232', 'Pa233', 'Pa234m1',
             'Np236', 'Np237', 'Np238',
             'U234', 'U235', 'U236', 'U237', 'U238',
             'Pu238', 'Pu239', 'Pu240', 'Pu241', 'Pu242',
             'Am241', 'Am242m1', 'Am242',
             'Cm242', 'Cm245']
fission_products = ['Kr85m1', 'Kr85', 'Kr87', 'Kr88',
                    'Rb86',
                    'Sr89', 'Sr90', 'Sr91', 'Sr92',
                    'Y90', 'Y91',
                    'Zr95', 'Nb95', 'Mo99', 'Tc99m1',
                    'Rh103m1', 'Ru105', 'Ru106', 'Rh106', 'Pd109', 'Ag110m1',
                    'Te131', 'Te132', 'Te134',
                    'I130', 'I131', 'I132', 'I133', 'I134', 'I135',
                    'Xe133m1', 'Xe133', 'Xe135', 'Xe138',
                    'Cs134', 'Cs136', 'Cs137', 'Cs138',
                    'Ba140', 'La140', 'Ce141', 'Ce143', 'Pr143', 'Ce144', 'Pr144']
nuclides_list = actinides + fission_products

# atomic data
h1_atomic_mass = 1.007825032
b0_atomic_mass = 10.811
b10_atomic_mass = 10.012937
b11_atomic_mass = 11.0093054
o16_atomic_mass = 15.99491462
o17_atomic_mass = 16.9991317
o18_atomic_mass = 17.9991604
o0_atomic_mass = 15.9994
al27_atomic_mass = 26.9815386
al28_atomic_mass = 27.98191021
al29_atomic_mass = 28.9804565
si0_atomic_mass = 28.085
gd0_atomic_mass = 157.25
u238_atomic_mass = 238.0507882
u235_atomic_mass = 235.0439299
gd2o3_atomic_mass = 2 * gd0_atomic_mass + 3 * o16_atomic_mass
h2o_atomic_mass = o16_atomic_mass + 2 * h1_atomic_mass


def atomic_mass_boron(impurity_ebc, atomic_mass_main):
    mass_impurity = atomic_mass_main * impurity_ebc / (1 - impurity_ebc) / b0_atomic_mass
    return mass_impurity

# def wo2ao(wo, Mx, M0):
#     return M0 / ( Mx * (1/wo-1) + M0)

# def ao2wo(ao, Mx, M0):
#     return ao*Mx / (ao*Mx + (1-ao)*M0)

def ao2wo(aos, Ms):
    ms = np.array(aos) * np.array(Ms)
    return ms / ms.sum()

def wo2ao(wos, Ms):
    ns = np.array(wos) / np.array(Ms)
    return ns / ns.sum()

def enrichment2abundance(enrichment):
    return enrichment / u235_atomic_mass / (enrichment / u235_atomic_mass + (1-enrichment) / u238_atomic_mass)


def abundance2u0atomicweight(abundance):
    return abundance * u235_atomic_mass + (1-abundance) * u238_atomic_mass


# functions for data processing
def interpolate(t, x, y):
    x, y = np.array(x), np.array(y)
    ind = np.where(x <= t)[0][-1] if t<x[-1] else -2 if t > x[0] else 0
    return (y[ind+1]-y[ind])/(x[ind+1]-x[ind]) * (t-x[ind]) + y[ind]


def integrate(t1, t2, x, y, npoint=100):
    inds = np.linspace(t1, t2, npoint)
    powers = [interpolate(ind, x, y) for ind in inds]
    return sum(powers) / npoint


def horizonal_print(label, data, scale=1):
    if isinstance(data[0], str):
        print(f"{label:<10s}|", "|".join([f"{di:>10s}" for di in data]))
    else:
        if scale == 1:
            print(f"{label:<10s}|", "|".join([f"{di:>10.3e}" for di in data]))
        else:
            print(f"{label:<10s}|", "|".join([f"{di:>10.6f}" for di in data]))

# class of OpenMC output tally file
class Tallyfile():

    def __init__(self, filepath):
        with open(filepath) as fileopen:
            self.filelines = fileopen.readlines()

    def read_tally(self, tally_id, keywork):
        index = 0
        while f'TALLY {tally_id}' not in self.filelines[index]:
            index += 1
        results, errors = [], []
        index += 1
        while (index < len(self.filelines)) and ('TALLY' not in self.filelines[index]):
            if keywork not in self.filelines[index]:
                index += 1
            else:
                results.append(float(self.filelines[index].split()[1]))
                errors.append(float(self.filelines[index].split()[3]))
                index += 1
        return np.array(results), np.array(errors)

    def read_flux_3D_distribution(self, tally_id):
        return self.read_tally(tally_id, 'Flux')

    def read_flux_spectrum(self, tally_id):
        return self.read_tally(tally_id, 'Flux')


# function to read OpenMC log
def read_log_time(filepath):
    with open(filepath, 'r') as fileopen:
        filelines = fileopen.readlines()
    index = 0
    t_total = 0
    t_init, t_simu, v_active = [], [], []
    while index < len(filelines):
        if ' Total time for initialization ' in (filelines[index]):
            t_init.append(float(filelines[index].split()[-2]))
        if ' Total time in simulation ' in (filelines[index]):
            t_simu.append(float(filelines[index].split()[-2]))
        if ' Calculation Rate (active) ' in (filelines[index]):
            v_active.append(float(filelines[index].split()[-2]))
        if 'Elapsed time for depletion:' in (filelines[index]):
            t_total = float(filelines[index].split()[-1])
        index += 1
    return np.array(t_init), np.array(t_simu), np.array(v_active), t_total


def read_final_keffs(filepath):

    with open(filepath, 'r') as fileopen:
        filelines = fileopen.readlines()
    index = 0
    keffs_2d = []
    while index < len(filelines):
        while "K EIGENVALUE SIMULATION" not in filelines[index]:
            index += 1
        index += 4
        keffs = []
        while "Creating state point" not in (line:=filelines[index]):
            splits = line.split()
            keff = float(splits[1])
            keff_err = float(splits[2])
            keffs.append([keff, keff_err])
            index += 1
        keffs_2d.append(keffs)
    return np.array(keffs_2d)

class XslibReader():

    def __init__(self, filepath):
        self.filepath = filepath
        with open(filepath, 'r') as fileopen:   
            self.filelines = fileopen.readlines()
        self.xslib = self._read()
    
    def __call__(self, nuclide, reaction):
        try:
            return self.xses[self.inds.index([nuclide, reaction])]
        except:
            return None
    
    def _read(self):
        # read burnup table
        index = 0
        while index < len(self.filelines):
            # count index until the burnup table
            if 'BU(MWd/kgHM)' not in self.filelines[index]:
                index += 1
            else:
                self.new = True
                self.burnups = [float(bu) for bu in self.filelines[index+1].split()]
                break
        if index == len(self.filelines):
            self.new = False
            self.burnups = [0, 100]
            index = 0

        # count index until the xs table
        while 'NucId' not in self.filelines[index]:
            index += 1
        index += 1

        # read xs table
        self.inds = []
        self.xses = []
        while index < len(self.filelines) and self.filelines[index][:2] != '-1':
            if (data:=match(r'^(\d+)\s+([A-Za-z0-9_]+)\s+(\d+)\s*\n$', self.filelines[index])) is not None:
                nuc_name = data.group(2)
                subindex = 1
                while index+subindex < len(self.filelines) and (data:=match(r'^\s+([\d]+)', self.filelines[index+subindex])) is not None:
                    rec_name = next((name for name, MT in MT_dict.items() if MT == int(data.group(1))), None)
                    self.inds.append([nuc_name, rec_name])
                    data = [float(xs) for xs in self.filelines[index+subindex].split()]
                    if self.new:
                        self.xses.append(data[1:])
                    else:
                        self.xses.append(data[2:]*2)
                    subindex += 1
                index += subindex
            else:
                index += 1
        self.burnups = np.array(self.burnups)
        self.xses = np.array(self.xses)
    
    def export(self, filepath=None):
        if not filepath:
            filepath = self.filepath
        with open(filepath, 'w') as f:
            f.write(f'{len(self.inds)}\n')


def count_files(folderpath, filetype='*.h5'):
    files = pathlib.Path(folderpath).glob(filetype)
    files_names = [file.name for file in files]
    return files_names

def nuc_name(name):
    name = name.replace('_m', '')
    return name