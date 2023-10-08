from pathlib import Path
from re import match, findall
from numpy import array
from pandas import DataFrame, merge, concat
from functools import reduce
from logging import info, basicConfig, INFO

basicConfig(level=INFO, format="%(asctime)s %(message)s")

from classes import XSLIB
from argparse import ArgumentParser

class XSLIBconverter(XSLIB):

    def export_pd_frame(self):
        self.df = DataFrame(columns=['nuc_name', 'rec_name', 'rec_rates'])
        for nuclide in self.nuclides:
            for reaction in nuclide.reactions:
                data = DataFrame({'nuc_name': [nuclide.name], 'rec_name': [reaction.name], 'rec_rates': [reaction.xses]})
                self.df = concat([self.df, data])
        return self.df

    @classmethod
    def from_pd_frame(cls, pd_frame, filename, rates_tag):
        xslib = cls(filename, read=False)
        for i, serie in pd_frame.iterrows():
            nuclide = xslib.check_nuclide(serie['nuc_name'])
            reaction = nuclide.check_reaction(serie['rec_name'])
            reaction.xses = serie[rates_tag]
        return xslib

class XSLIBinterpolater():

    def __init__(self, folderpath, format=r"^T([\.\d]+)E([\.\d]+)BP([\.\d]+)GD([\.\d]+)_xslib.dat$"):
        self.folderpath = Path(folderpath)
        self.format = format
        self._parsefolder()

    def _parsefolder(self):
        self.files = []
        self.params = []
        for file in self.folderpath.glob('*'):
            if (data:=match(self.format, file.name)) is not None:
                param = [float(item) for item in data.groups()]
                self.params.append(param)
                self.files.append({'file': file, 'param': param})
        self.params = array(self.params)

    def __call__(self, param, modes=None):
        if modes is None:
            modes = ['linear'] * len(self.params)
        files = self._get_files(param)
        df_xses, df_params, burnups = self._convert_df(files)
        
        info("Start to interpolate...")
        for i in range(len(param)-1, -1, -1):
            params_copy = df_params.copy()
            for param_1 in df_params:
                if param_1 in params_copy and param_1[i] != param[i]:
                    param_2 = [tag_res for tag_res in df_params if (tag_res[:i] == param_1[:i]) and (tag_res[i] != param_1[i])][0]
                    param_interp = param_1[:i] + param[i:]
                    info(f"{modes[i].capitalize()} Interpolate {self._param_to_tag(param_interp)}\n\t\t\tUsing {self._param_to_tag(param_1)}\n\t\t\tUsing {self._param_to_tag(param_2)}...")
                    df_xses_1 = df_xses[self._param_to_tag(param_1)]
                    df_xses_2 = df_xses[self._param_to_tag(param_2)]
                    if modes[i] == 'linear':
                        weight_1 = abs((param[i]-param_1[i])/(param_1[i]-param_2[i]))
                        weight_2 = abs((param[i]-param_2[i])/(param_1[i]-param_2[i]))
                    elif modes[i] == 'nearest':
                        weight_1 = 1 if abs(param[i]-param_1[i]) < abs(param[i]-param_2[i]) else 0
                        weight_2 = 1 - weight_1
                    elif modes[i] == 'average':
                        weight_1, weight_2 = 1/2, 1/2
                    elif modes[i] == 'doppler':
                        weight_1, weight_2 = self._doppler_coefficients(array([param_1[i], param_2[i]]), param[i])
                    else:
                        raise ValueError(f"Mode {modes[i]} is not supported.")
                    df_xses_interp = df_xses_1 * weight_1 + df_xses_2 * weight_2
                    df_xses[self._param_to_tag(param_interp)] = df_xses_interp
                    params_copy.remove(param_1)
                    params_copy.remove(param_2)
                    params_copy.append(param_interp)
            df_params = params_copy
        # df_xses.to_excel(self._param_to_tag(param) + '.xlsx')
        info(f"Export {self._param_to_tag(param)}...")
        xslib = XSLIBconverter.from_pd_frame(df_xses, self.folderpath / ('interp_'+self._param_to_tag(param)), rates_tag=self._param_to_tag(param))
        xslib.burnups = burnups
        xslib.remove_reactions(0)
        xslib.export()

    def _doppler_coefficients(self, temps, temp):
        coefs = []
        for j, temp_j in enumerate(temps):
            coef = (temp * temp_j) ** 0.5 / (temp + temp_j) * 2
            for i, temp_i in enumerate(temps):
                if i != j:
                    coef *= (temp_j + temp_i) / (temp_j - temp_i) * (temp - temp_i) / (temp + temp_i)
            coefs.append(coef)
        return coefs

    def _param_to_tag(self, param):
        tag = self.format
        tag = tag[1:] if tag[0] == '^' else tag
        tag = tag[:-1] if tag[-1] == '$' else tag
        params_reg = findall(r"(\([\[\]\\\.A-Za-z0-9\+]+\))", self.format)
        for param_i, param_reg in zip(param, params_reg):
            tag = tag.replace(param_reg, f"{param_i:<.2f}", 1)
        return tag

    def _convert_df(self, files):
        df_params = []
        dfs_xses = []
        for file in files:
            info(f"Read file {file['file'].name}...")
            xslib = XSLIBconverter(file['file'])
            df_xses = xslib.export_pd_frame()
            df_xses = df_xses.rename(columns={'rec_rates': self._param_to_tag(file['param'])})
            dfs_xses.append(df_xses)
            df_params.append(file['param'])
        merge_xses = lambda t1, t2: merge(t1, t2, on=['nuc_name', 'rec_name'])
        df_xses = reduce(merge_xses, dfs_xses)
        return df_xses, df_params, xslib.burnups

    def _get_files(self, param):
        params_interp = []
        for i, param_i in enumerate(param):
            params_i = array(self.params[:, i])
            param_i_left = max(params_i[params_i <= param_i])
            param_i_right = min(params_i[params_i >= param_i])
            params_interp.append((param_i_left, param_i_right))
        files = [file for file in self.files \
                 if all([param_i in params_i for param_i, params_i in zip(file['param'], params_interp)])]
        return files


parser = ArgumentParser()
parser.add_argument('--path', type=str, default=None)
parser.add_argument('--params', type=float, nargs='*')
parser.add_argument('--modes', type=str, nargs='*')
args = parser.parse_args()

# intep = XSLIBinterpolater(args.path)
# intep(args.params, modes=args.modes)

intep = XSLIBinterpolater(folderpath='/home/super/users/zhangwj/nuit/NUITLIB/PWR900K')
intep([750, 2.72, 0, 0], modes=['linear','doppler', 'linear', 'linear'])