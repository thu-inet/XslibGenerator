from re import match
from pickle import load
from pathlib import Path
from numpy import array, zeros, insert

from constants import *

class Reaction():

    def __init__(self, rec_name):
        self.name = rec_name
        self.MT = MT_dict[rec_name]

class Nuclide():
    
    def __init__(self, nuc_name):
        self.name = nuc_name
        self.reactions = []
        self.info()
    
    def __repr__(self):
        return self.name

    def info(self):
        info = match(r'^([a-zA-Z]+)(\d+)_?(m[123])?$', self.name).groups()
        self.symbol = info[0]
        self.mass = int(info[1])
        self.state = 0 if info[2] is None else int(info[2][1])
        self.atomic = Atomic_dict[self.symbol]
        self.id = self.atomic * 10000 + self.mass * 10 + self.state
    
    def check_reaction(self, rec_name, initiate=True):
        if (reaction:=next((reaction for reaction in self.reactions if reaction.name == rec_name), None)) is None and initiate:
            self.reactions.append(Reaction(rec_name))
            reaction = self.reactions[-1]
        return reaction

    def __getitem__(self, rec_name):
        return self.check_reaction(rec_name)

    def set_reaction(self, rec_name):
        self.reactions.append(Reaction(rec_name))

    def sort_reactions(self):
        self.reactions.sort(key=lambda reaction: reaction.MT)

    @property
    def num_rec(self):
        return len(self.reactions)


class ISOMERICS():

    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as fileopen:
            self.isomerics = load(fileopen)

    def __call__(self, nuc_name, rec_name):
        isomeric = next((isomeric for isomeric in self.isomerics if (isomeric['MT'] == MT_dict[rec_name]) and (isomeric['name'] == nuc_name)), None)
        return isomeric['fracm'] if isomeric else 0

class XSLIB():
    
    def __init__(self, filepath='testlib.dat', read=True):
        self.nuclides = []
        self.filepath = filepath
        if Path(filepath).exists() and read:
            with open(self.filepath, 'r') as fileopen:   
                self.filelines = fileopen.readlines()
            self._read()

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
        while index < len(self.filelines) and self.filelines[index][:2] != '-1':
            if (data:=match(r'^(\d+)\s+([A-Za-z0-9_]+)\s+(\d+)\s*\n$', self.filelines[index])) is not None:
                nuclide = self.check_nuclide(data.group(2))
                subindex = 1
                while index+subindex < len(self.filelines) and (data:=match(r'^\s+([\d]+)', self.filelines[index+subindex])) is not None:
                    rec_name = next((name for name, MT in MT_dict.items() if MT == int(data.group(1))), None)
                    reaction = nuclide.check_reaction(rec_name)
                    data = [float(xs) for xs in self.filelines[index+subindex].split()]
                    if self.new:
                        reaction.xses = array(data[1:])
                    else:
                        reaction.xses = array(data[2:] * 2)
                    subindex += 1
            index += subindex

    def check_nuclide(self, nuc_name, initiate=True):
        if (nuclide:=next((nuclide for nuclide in self.nuclides if nuclide.name == nuc_name), None)) is None and initiate:
            self.nuclides.append(Nuclide(nuc_name))
            nuclide = self.nuclides[-1]
        return nuclide
    
    def __getitem__(self, nuc_name):
        return self.check_nuclide(nuc_name, initiate=False)
    
    def set_den(self, nuc_name, den):
        nuclide = self.check_nuclide(nuc_name)
        nuclide.den = den

    def set_rate(self, nuc_name, rec_name, rate):
        nuclide = self.check_nuclide(nuc_name)
        reaction = nuclide.check_reaction(rec_name)
        reaction.rate = rate

    def sort_nuclides(self):
        self.nuclides.sort(key=lambda nuclide: nuclide.id)

    def format_nuclide(self, nuclide):
        return f"{nuclide.id:<8d} {nuclide.name:<8s} {nuclide.num_rec:<8d}"

    def format_reaction(self, reaction):
        return f"{reaction.MT:<6d}" + "   ".join(["{0:<12.8E}".format(xs) for xs in reaction.xses])

    def format_mreaction(self, reaction):
        return f"{reaction.MT*10+1:<6d}" + "   ".join(["{0:<12.8E}".format(mxs) for mxs in reaction.mxses])
    
    def calculate_xs(self):
        for nuclide in self.nuclides:
            for reaction in nuclide.reactions:
                reaction.xses = reaction.rate / (nuclide.den+1E-40) / self.flux
                reaction.xses[nuclide.den==0] = 0
                if reaction.xses.max() > 0 and reaction.xses.min()/reaction.xses.max() < 1E-3:
                    print(f"Warning: XS ratio for {nuclide.name} {reaction.MT} is very large")
                    print(f"Max: {reaction.xses.max():<12.8E} Min: {reaction.xses.min():<12.8E}")

    def remove_reactions(self, threshold):
        for nuclide in self.nuclides:
            nuclide.reactions = [reaction for reaction in nuclide.reactions if reaction.xses.mean() > threshold]
        self.nuclides = [nuclide for nuclide in self.nuclides if len(nuclide.reactions) > 0]
        self.sort_nuclides()
    
    def remove_cooling(self):
        self.index_active = self.burnups[1:] != self.burnups[:-1]
        self.index_active = insert(self.index_active, -1, self.burnups[-2] != self.burnups[-1])
        self.burnups = self.burnups[self.index_active]
        self.flux = self.flux[self.index_active]
        for nuclide in self.nuclides:
            nuclide.den = nuclide.den[self.index_active]
            for reaction in nuclide.reactions:
                reaction.rate = reaction.rate[self.index_active]

    def export(self, filepath=None):
        if filepath is None:
            filepath = self.filepath
        fileopen = open(filepath, 'w')
        fileopen.write("*************************** NUIT one-group neutron cross-section data ***************************\n" )
        fileopen.write(f"Number of isotopes with neutron data: \n\t{len(self.nuclides)}\n")
        fileopen.write(f"Number of burnup steps:\n\t{len(list(self.burnups))}\n\n")

        fileopen.write("BU(MWd/kgHM)\n")
        fileopen.write("   ".join([f"{burnup:<12.8E}" for burnup in self.burnups]) + "\n\n")
        fileopen.write("NucId    NucName  MT\n")
        for nuclide in self.nuclides:
            nuclide.sort_reactions()
            fileopen.write(self.format_nuclide(nuclide) + "\n")
            for reaction in nuclide.reactions:
                fileopen.write("                  " + self.format_reaction(reaction) + "\n")
    
    # def export_to_xml(self):
    #     df = pd.DataFrame(columns=['NucId', 'NucName', 'MT', 'BU(MWd/kgHM)', 'XS(barns)'])
    #     for nuclide in self.nuclides:
    #         nuclide.sort_reactions()
    #         df = df.append(self.format_nuclide_df(nuclide), ignore_index=True)
    #         for reaction in nuclide.reactions: