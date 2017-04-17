#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 14 15:32:40 2017

@author: aero-10
"""
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from tkinter import Button, mainloop, X, Tk
from tkinter.filedialog import askopenfilename
from collections import Counter
import scipy.stats.stats as sci_stats

# Class version of the csv_reader function used for the
# combustion institute conference paper


class ProcessData:

    def findfile(self, button_text):
        def openFile():
            global Fname
            Fname = askopenfilename()
            print(Fname)
            root.destroy()
        root = Tk()
        root.attributes("-topmost", True)
        Button(root, text=button_text, command=openFile).pack(fill=X)
        mainloop()
        return Fname

    def __init__(self, file_name=None, trim_limits=(500, 3000),
                 bins=np.linspace(0, .5, 50)):
        try:
            # Read the data from the csv into a Pandas DataFrame
            self.file_name = str(file_name)
            self.data = pd.read_csv(self.file_name)
        except:
            self.file_name = self.findfile('csv file to plot')
            # Read the data from the csv into a Pandas DataFrame
            self.data = pd.read_csv(self.file_name)
        self.trim_limits = sorted(trim_limits)
        self.bins = bins
        self.correction = 0.95

    def stripcols(self, desired_columns=['Diluent', 'V1', 'R1']):
        self.keep_columns = []
        for i in desired_columns:
            [self.keep_columns.append(loc) for loc,
             idx in enumerate(self.data.columns) if i in idx]
        return self.data.take(self.keep_columns, axis=1)

    def columns(self):
        return self.data.columns

    def separate(self):
        sep_data = self.stripcols()
        base = sep_data[sep_data.columns[0::3]]
        base.replace(base[base.columns[0]])
        pd.options.mode.chained_assignment = None
        base[base.columns[0]] = 0
        CO2 = sep_data[sep_data.columns[1::3]]
        N2 = sep_data[sep_data.columns[2::3]]
        return base, CO2, N2

    def trimdata(self, trim_columns='V1'):
        base, CO2, N2 = self.separate()

        base = base[base['V1'] > self.trim_limits[0]]
        base = base[base['V1'] < self.trim_limits[1]]

        CO2 = CO2[CO2['V1.1'] > self.trim_limits[0]]
        CO2 = CO2[CO2['V1.1'] < self.trim_limits[1]]

        # add in the correction factor
#        N2['Diluent (N2)'] = N2['Diluent (N2)']*1/self.correction
        N2 = N2[N2['V1.2'] > self.trim_limits[0]]
        N2 = N2[N2['V1.2'] < self.trim_limits[1]]
        return base, CO2, N2

    def successful_tests(self):
        none, CO2, N2 = self.trimdata()
        none = len(none['V1'])
        CO2 = len(CO2['V1.1'])
        N2 = len(N2['V1.2'])
        print('No Diluent: ', none)
        print('CO2 Diluent: ', CO2)
        print('N2 Diluent: ', N2)
        return {'none': none, 'CO2': CO2, 'N2': N2}

    def plot(self):
        base, CO2, N2 = self.trimdata()
        fig = plt.figure('Velocity Data')
        fig.clf()
        p2, = plt.plot(CO2['Diluent (CO2)'], CO2['V1.1'], 'ob')
        p3, = plt.plot(N2['Diluent (N2)'], N2['V1.2'], 'xg')
        fig.legend(handles=[p2, p3], labels=[r'$CO_{2}$', r'$N_{2}$'],
                   numpoints=1)
        plt.show()

    def grouping(self, column='Diluent'):
        none, CO2, N2 = self.trimdata()
        for i in [none, CO2, N2]:
            group_col = [idx for loc, idx in enumerate(i.columns) if
                         column in idx][0]
            i['groups'] = pd.cut(i[group_col], bins=self.bins)
        return none, CO2, N2

    def means(self, columns=['Dilution', 'Velocity', 'Error']):
        mean_vals = []
        none, CO2, N2 = self.grouping()
        none_mean = [none['V1'].mean(), none['R1'].mean()]
        for i in [CO2, N2]:
            i.columns = ['{0} mean'.format(i.columns[0]), 'V mean',
                         'Error mean', 'groups']
            mean_vals.append(i.groupby(['groups']).mean())
        return none_mean, mean_vals[0], mean_vals[1]

    def std_devs(self):
        std_vals = []
        none, CO2, N2 = self.grouping()
        for i in [CO2, N2]:
            i.columns = ['{0} std'.format(i.columns[0]), 'V std', 'Error std',
                         'groups']
            std_vals.append(i.groupby(['groups']).std())
        return [none['V1'].std(), none['R1'].std()], std_vals[0], std_vals[1]

    def group_sizes(self):
        none, CO2, N2 = self.grouping()
        sizes = []
        for i in [CO2, N2]:
            sizes.append(Counter(i.groups))
        CO2 = pd.DataFrame.from_dict(sizes[0], orient='index')
        CO2.columns = ['count']
        N2 = pd.DataFrame.from_dict(sizes[1], orient='index')
        N2.columns = ['count']
        return CO2, N2

    def confidence_intervals(self, confidence=0.95):
        CO2_counts, N2_counts = self.group_sizes()

        CO2_data = pd.merge(self.means()[1], self.std_devs()[1],
                            right_index=True, left_index=True)
        CO2_data = pd.merge(CO2_data, CO2_counts, left_index=True,
                            right_index=True)
        CO2_ci = {}
        for idx, row in CO2_data.iterrows():
            CO2_ci[idx] = stats.norm.interval(confidence, loc=row['V mean'],
                                              scale=row['V std'] /
                                              np.sqrt(row['count']))
        CO2_ci = pd.DataFrame.from_dict(CO2_ci, orient='index')
        CO2_ci.columns = ['Lower Limit', 'Upper Limit']
        CO2_data = pd.merge(CO2_data, CO2_ci, left_index=True,
                            right_index=True)

        N2_data = pd.merge(self.means()[2], self.std_devs()[2],
                           right_index=True, left_index=True)
        N2_data = pd.merge(N2_data, N2_counts, left_index=True,
                           right_index=True)
        N2_ci = {}
        for idx, row in N2_data.iterrows():
            N2_ci[idx] = stats.norm.interval(confidence, loc=row['V mean'],
                                             scale=row['V std'] /
                                             np.sqrt(row['count']))
        N2_ci = pd.DataFrame.from_dict(N2_ci, orient='index')
        N2_ci.columns = ['Lower Limit', 'Upper Limit']
        N2_data = pd.merge(N2_data, N2_ci, left_index=True,
                           right_index=True)

        base, _, _ = self.grouping()
        base_ci = stats.norm.interval(confidence, loc=base['V1'].mean(),
                                      scale=base['V1'].std() /
                                      np.sqrt(len(base['V1'])))
        base_ci = (base_ci[0], base['V1'].mean(), base_ci[1])
        return base_ci, CO2_data, N2_data
    
    def linefit(self):
        CO2 = self.confidence_intervals()[1]
        N2 = self.confidence_intervals()[2]
        fit = []
        fit.append(None)
        fit.append(sci_stats.linregress(CO2[CO2.columns[0]].values[:-3],
                                        CO2[CO2.columns[1]].values[:-3]))
        fit.append(sci_stats.linregress(N2[N2.columns[0]].values,
                                        N2[N2.columns[1]].values))
        return fit

    def plot_error(self):
        base, CO2, N2 = self.confidence_intervals()
        fig = plt.figure('Velocity vs Dilution')
        fig.clf()
        plt.errorbar(x=CO2['Diluent (CO2) mean']*self.correction, y=CO2['V mean'],
                     yerr=CO2['V mean']-CO2['Lower Limit'], fmt='^k',
                     label='CO2', linestyle ='')
        plt.errorbar(x=N2['Diluent (N2) mean'], y=N2['V mean'],
                     yerr=N2['V mean']-N2['Lower Limit'], fmt='ok',
                     label='N2', markerfacecolor='none', linestyle='')
        plt.legend(['CO2', 'N2'])
#        plt.plot(N2['Diluent (N2) mean'],
#                     [base[0] for i in N2['Diluent (N2) mean']], '--k')
#        plt.plot(N2['Diluent (N2) mean'],
#                     [base[1] for i in N2['Diluent (N2) mean']], '--k')
        plt.xlabel(r'$Y_{N_{2}}$ equivalent', fontsize=14)
        plt.ylabel('Detonation Velocity (m/s)', fontsize=14)
        plt.show()
        plt.plot(N2['Diluent (N2) mean'],
                 self.linefit()[2].slope*N2['Diluent (N2) mean'] +
                 self.linefit()[2].intercept, linestyle='--', color='black',
                             marker=None)
        plt.plot(CO2['Diluent (CO2) mean']*self.correction,
                 self.linefit()[1].slope*CO2['Diluent (CO2) mean'] +
                 self.linefit()[1].intercept, linestyle='--', color='black')
#        plt.savefig('/run/user/1000/gvfs/dav:host=dav.box.com,ssl=true,' +
#                    'prefix=%2Fdav/Blunck Group/10th Annual Combustion ' +
#                    'Conference/Bean_detonation_dilution/velocity.png')

    def suppression_error(self):
        base, CO2, N2 = self.confidence_intervals()
        fig = plt.figure('Velocity Suppression')
        fig.clf()
        plt.errorbar(x=CO2['Diluent (CO2) mean'],
                     y=self.means()[0][0]-CO2['V mean'],
                     yerr=CO2['V mean']-CO2['Lower Limit'], fmt='^k',
                     label='CO2')
        plt.errorbar(x=N2['Diluent (N2) mean'],
                     y=self.means()[0][0]-N2['V mean'],
                     yerr=N2['V mean']-N2['Lower Limit'], fmt='ok',
                     label='N2', markerfacecolor='none')
#        plt.plot(N2['Diluent (N2) mean'],
#                     [base[0] for i in N2['Diluent (N2) mean']], '--k')
#        plt.plot(N2['Diluent (N2) mean'],
#                     [base[1] for i in N2['Diluent (N2) mean']], '--k')
        plt.xlabel(r'$Y_{N_{2}}$ equivalent', fontsize=14)
        plt.ylabel('Detonation Velocity (m/s)', fontsize=14)
        plt.legend()
        plt.show()
#        plt.savefig('/run/user/1000/gvfs/dav:host=dav.box.com,ssl=true,' +
#                    'prefix=%2Fdav/Blunck Group/10th Annual Combustion ' +
#                    'Conference/Bean_detonation_dilution/suppresion.png')

if __name__ == '__main__':
    Fname = '/home/aero-10/Documents/Mass-Flow-Calculator/Compiled test data.csv'
    data = ProcessData(file_name=Fname, trim_limits=(1200, 2100),
                       bins=np.linspace(0, .5, 50))
    a = data.linefit()
    data.plot_error()
#    data.suppression_error()
