from re import match
from pickle import load
from pathlib import Path
from numpy import array, zeros, insert

from .constants import *


class Reaction():
    """
    Class representing a nuclear reaction.
    """
    def __init__(self, rec_name, rate=None, xs=None):
        """
        Initialize the reaction.

        :param rec_name: str, name of the reaction, like '(n,gamma)', '(n,2n)', '(n,f)'etc.
        :param rate: array, optional, reaction rate of the reaction.
        :param xs: array, optional, cross section of the reaction.
        """
        self.name = rec_name
        self.MT = MT_dict[rec_name]
        self.rate = rate if rate is not None else []
        self.xs = xs if xs is not None else []


class Nuclide():
    """
    Class representing a nuclide.
    """
    def __init__(self, nuc_name, den=None):
        """
        Initialize the nuclide.
        
        :param nuc_name: str, name of the nuclide, like 'U235', 'Pu239', 'Xe135' etc.
        :param den: float, optional, density of the nuclide.
        """
        self.name = nuc_name
        self.reactions = []
        self.den = den
        
        if (results := match(r'^([a-zA-Z]+)(\d+)_?(m[123])?$', self.name)) is None:
            raise ValueError(f"Invalid nuclide name: {self.name}")
        else:
            info = results.groups()
            self.symbol = info[0]
            self.mass = int(info[1])
            self.state = 0 if info[2] is None else int(info[2][1])
            self.atomic = Atomic_dict[self.symbol]
            self.id = self.atomic * 10000 + self.mass * 10 + self.state

    def check_reaction(self, rec_name, initiate=True):
        """
        Find the reaction in the reactions list using the reaction name.
        If the reaction exists in the list, return the reaction directly.
        Otherwise, and when 'initiate' is True, create a new reaction and return it.
        When there is no such reaction and 'initiate' is False, raise an error instead.
        
        :param rec_name: str, name of the reaction, like '(n,gamma)', '(n,2n)', '(n,f)'etc.
        :param initiate: bool, whether to create a new reaction if the reaction does not exist.
        """
        if (reaction:=next((reaction for reaction in self.reactions if reaction.name == rec_name), None)) is None:
            if initiate:
                self.reactions.append(Reaction(rec_name))
                reaction = self.reactions[-1]
            else:
                raise ValueError(f"Reaction {rec_name} not found")
        return reaction

    # def __getitem__(self, rec_name):
    #     if isinstance(rec_name, int):
    #         rec_name = [name for name, MT in MT_dict.items() if MT == rec_name][0]
    #     return self.check_reaction(rec_name, initiate=False)

    def sort_reactions(self):
        """
        Sort the reactions list by the reaction MT number.
        """
        self.reactions.sort(key=lambda reaction: reaction.MT)


class ISOMERICS():
    """
    Class representing the database of isomeric ratios.
    The isomeric ratios are taken from http://serpent.vtt.fi/mediawiki/index.php/Default_isomeric_branching_ratios
    They are stored in a pickle file and use this class as the interface.
    """
    def __init__(self, path):
        """
        Initialize the isomerics object.
        
        :param path: str, path to the pickle file containing the isomeric ratios.
        """
        self.path = path
        with open(path, 'rb') as fileopen:
            self.isomerics = load(fileopen)

    def __call__(self, nuc_name, rec_name):
        """
        Search the isomeric ratio for a nuclide and a reaction.
        
        :param nuc_name: str, name of the nuclide, like 'U235', 'Pu239', 'Xe135' etc.
        :param rec_name: str, name of the reaction, like '(n,gamma)', '(n,2n)', '(n,f)'etc.
        """
        isomeric = next((isomeric for isomeric in self.isomerics if (isomeric['MT'] == MT_dict[rec_name]) and (isomeric['name'] == nuc_name)), None)
        return isomeric['fracm'] if isomeric else 0


class XSLIB():
    """
    Class representing the cross section library in a hierarchical structure.
    It stores the nuclides in a list, and nuclides store their own reactions in other smaller lists.
    
    This class is compatible with libraries of both old and new formats when reading existing files.
    But it only exports into the new format.
    """
    def __init__(self, filepath='testlib.dat', burnups=None, nuclides=None, read=True):
        """
        Initialize the cross section library.
        If the file already exists and 'read' is True, read the file.
        
        :param filepath: str, path to the cross section library file.
        :param burnups: list, optional, burnup steps of the cross section library.
        :param nuclides: list, optional, nuclides in the cross section library.
        :param read: bool, whether to read the file if the file exists.
        """
        self.filepath = filepath
        self.burnups = burnups if burnups is not None else []
        self.nuclides = nuclides if nuclides is not None else []

        if Path(filepath).exists() and read:
            with open(self.filepath, 'r') as fileopen:
                self.filelines = fileopen.readlines()

            # read burnup table
            index = 0
            while index < len(self.filelines):
                # count index until the burnup table
                if 'BU(MWd/kgHM)' not in self.filelines[index]:
                    index += 1
                else:
                    new_format = True
                    self.burnups = array([float(bu) for bu in self.filelines[index+1].split()])
                    break
            if self.burnups == []:
                new_format = False
                self.burnups = array([0, 100])
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
                        if new_format:
                            reaction.xses = array(data[1:])
                        else:
                            reaction.xses = array(data[2:] * 2)
                        subindex += 1
                index += subindex

    def check_nuclide(self, nuc_name, initiate=True) -> Nuclide:
        """
        Find the nuclide in the nuclides list using the nuclide name.
        If the nuclide exists in the list, return the nuclide directly.
        Otherwise, and when 'initiate' is True, create a new nuclide and return it.
        When there is no such nuclide and 'initiate' is False, raise an error instead.
        
        :param nuc_name: str, name of the nuclide, like 'U235', 'Pu239', 'Xe135' etc.
        :param initiate: bool, whether to create a new nuclide if the nuclide does not exist.
        """
        if (nuclide:=next((nuclide for nuclide in self.nuclides if nuclide.name == nuc_name), None)) is None:
            if initiate:
                self.nuclides.append(Nuclide(nuc_name))
                nuclide = self.nuclides[-1]
            else:
                raise ValueError(f"Nuclide {nuc_name} not found")
        return nuclide

    # def __getitem__(self, nuc_name):
    #     return self.check_nuclide(nuc_name, initiate=False)

    def set_nuc_den(self, nuc_name, den):
        """
        Shortcut to set the density of a nuclide.
        
        :param nuc_name: str, name of the nuclide, like 'U235', 'Pu239', 'Xe135' etc.
        :param den: float, density of the nuclide.
        """
        nuclide = self.check_nuclide(nuc_name)
        nuclide.den = den

    def set_nuc_rec_rate(self, nuc_name, rec_name, rate):
        """
        Shortcut to set the reaction rate of a reaction of a nuclide.
        
        :param nuc_name: str, name of the nuclide, like 'U235', 'Pu239', 'Xe135' etc.
        :param rec_name: str, name of the reaction, like '(n,gamma)', '(n,2n)', '(n,f)'etc.
        :param rate: array, reaction rate of the reaction.
        """
        nuclide = self.check_nuclide(nuc_name)
        reaction = nuclide.check_reaction(rec_name)
        reaction.rate = rate

    def sort_nuclides(self):
        """
        Sort the nuclide list by the nuclide ID.
        """
        self.nuclides.sort(key=lambda nuclide: nuclide.id)

    def format_nuclide(self, nuclide):
        return f"{nuclide.id:<8d} {nuclide.name:<8s} {len(nuclide.reactions):<8d}"

    def format_reaction(self, reaction):
        return f"{reaction.MT:<6d}" + "   ".join(["{0:<12.8E}".format(xs) for xs in reaction.xses])

    def format_mreaction(self, reaction):
        return f"{reaction.MT*10+1:<6d}" + "   ".join(["{0:<12.8E}".format(mxs) for mxs in reaction.mxses])
    
    def calculate_xs(self):
        """
        Calculate the cross sections of the reactions.
        """
        for nuclide in self.nuclides:
            for reaction in nuclide.reactions:
                reaction.xses = reaction.rate / (nuclide.den+1E-40) / self.flux
                reaction.xses[nuclide.den==0] = 0
                
                # if the fluctuataion is too large, print a warning
                # if reaction.xses.max() > 0 and reaction.xses.min()/reaction.xses.max() < 1E-3:
                #     print(f"Warning: XS ratio for {nuclide.name} {reaction.MT} seems to be unstable")
                #     print(f"\tMax: {reaction.xses.max():<8.2E} Min: {reaction.xses.min():<8.2E}")

    def remove_reactions(self, threshold):
        """
        Remove the reactions with cross sections below the threshold.
        
        :param threshold: float, threshold of the cross section.
        """
        for nuclide in self.nuclides:
            nuclide.reactions = [reaction for reaction in nuclide.reactions if reaction.xses.mean() > threshold]
        self.nuclides = [nuclide for nuclide in self.nuclides if len(nuclide.reactions) > 0]
        self.sort_nuclides()
    
    def remove_cooling(self):
        """
        Remove the reaction rate of the cooling phrases in the nuclide.reaction.rate.
        """
        self.index_active = self.burnups[1:] != self.burnups[:-1]
        self.index_active = insert(self.index_active, -1, self.burnups[-2] != self.burnups[-1])
        self.burnups = self.burnups[self.index_active]
        self.flux = self.flux[self.index_active]
        for nuclide in self.nuclides:
            nuclide.den = nuclide.den[self.index_active]
            for reaction in nuclide.reactions:
                reaction.rate = reaction.rate[self.index_active]

    def export(self, filepath=None):
        """
        Export to a cross section library file.
        
        :param filepath: str, optional, path to the cross section library file.
        """
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
