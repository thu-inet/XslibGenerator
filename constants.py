from re import match

Na = 6.022140857e23

MT_dict = {'(n,2n)': 16,
           '(n,3n)': 17,
           '(n,4n)': 37,
           '(n,a)': 107,
           '(n,gamma)': 102,
           '(n,p)': 103,
           'fission': 18}
MT_dict_copy = MT_dict.copy()
for key, val in MT_dict.items():
    MT_dict_copy[key+'M'] = val * 10 + 1
MT_dict = MT_dict_copy

Atomic_list = ['H', 'He',
               'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne',
               'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar',
               'K', 'Ca', 'Sc', 'Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se', 'Br', 'Kr',
               'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh', 'Pd', 'Ag', 'Cd', 'In','Sn', 'Sb', 'Te', 'I', 'Xe',
               'Cs', 'Ba', 'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho', 'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt', 'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn',
               'Fr', 'Ra', 'Ac', 'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es', 'Fm', 'Md', 'No', 'Lr', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og']
Atomic_dict = {item: ind+1 for ind, item in enumerate(Atomic_list)}

fissile_HM = ["U235", "U238", "Pu239", "Th232"]

time_convert_units = {'s': 1/86400, 'min': 1/1440, 'h': 1/24, 'd': 1, 'a': 365}
def time_conversion(time, unit1, unit2):
    return time * time_convert_units[unit1] / time_convert_units[unit2]

def nuclide_mass(nuc_name):
    return int(match(r'^([a-zA-Z]+)(\d+)_?(m[123])?$', nuc_name).group(2))