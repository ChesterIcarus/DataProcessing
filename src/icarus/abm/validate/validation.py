
import csv
import math

import matplotlib.pyplot as plt

from matplotlib.ticker import PercentFormatter

from icarus.abm.validate.database import AbmValidationDatabase
from icarus.util.print import Printer as pr

class AbmValidation:
    def __init__(self, database):
        self.database = AbmValidationDatabase(database)

    def validate(self, charts):
        for chart, savepath in charts.items():
            if savepath != '':
                if chart == 'compare_activity_time':
                    self.compare_activity_time(savepath)
                elif chart == 'compare_network_load':
                    self.compare_network_load(savepath)
                elif chart == 'compare_travel_time':
                    self.compare_travel_time(savepath)

    def validate_(self, charts):
        for chart in charts:
            if chart['type'] == 'compare_travel_time':
                options = ('bin_count', 'bin_size')

    def compare_travel_time(self, savepath, bin_size=20, bin_count=0, 
            bin_start=None, bin_end=None, percent=True):

        fig, axs = plt.subplots(1, 2, tight_layout=True)

        bins, vals = self.database.get_hist('abm', 'trips', 'trav_time', 
            bin_count=bin_count, bin_size=bin_size)


        pr.print('Graphing histogram.', time=True)
        pos = tuple(range(len(bins)))
        tick = len(bins) // 4
        axs[0].bar(pos, vals, width=0.9, color='b')
        if percent:
            axs[0].yaxis.set_major_formatter(PercentFormatter(xmax=sum(vals)))
        axs[0].set_xticks(pos[0::tick])
        axs[0].set_xticklabels(bins[0::tick])
        axs[0].set_title('2015 ABM Data')
        axs[0].set_ylabel('frequency (%)')
        axs[0].set_xlabel('trip duration (secs)')

        bins, vals = self.database.get_hist('abm2018', 'trips', 
            'arrive_time - depart_time', bin_count=20, bin_size=5)
        pr.print('Graphing histogram.', time=True)
        pos = tuple(range(len(bins)))
        tick = len(bins) // 4
        axs[1].bar(pos, vals, width=0.9, color='r')
        if percent:
            axs[1].yaxis.set_major_formatter(PercentFormatter(xmax=sum(vals)))
        axs[1].set_xticks(pos[0::tick])
        axs[1].set_xticklabels(bins[0::tick])
        axs[1].set_title('2018 ABM Data')
        axs[1].set_xlabel('trip duration (secs)')
        
        pr.print('Saving histogram.', time=True)
        fig.savefig(savepath)
        

    def compare_activity_time(self, savepath):
        fig, axs = plt.subplots(1, 2, tight_layout=True)

        bins, vals = self.database.get_bins('abm', 'trips', 'act_time', bin_size=-2)
        pos = tuple(range(len(bins)))
        tick = len(bins) // 5
        axs[0].bar(pos, vals, width=0.9, color='b')
        axs[0].yaxis.set_major_formatter(PercentFormatter(xmax=sum(vals)))
        axs[0].set_xticks(pos[0::tick])
        axs[0].set_xticklabels(bins[0::tick])
        axs[0].set_title('2015 ABM Data')
        axs[0].set_ylabel('frequency (%)')
        axs[0].set_xlabel('activity duration (secs)')

        bins, vals = self.database.get_bins('abm2018', 'trips', 'act_duration', bin_size=-4)
        pos = tuple(range(len(bins)))
        tick = len(bins) // 3
        axs[1].bar(pos, vals, width=0.9, color='r')
        axs[1].yaxis.set_major_formatter(PercentFormatter(xmax=sum(vals)))
        axs[1].set_xticks(pos[0::tick])
        axs[1].set_xticklabels(bins[0::tick])
        axs[1].set_title('2018 ABM Data')
        axs[1].set_xlabel('activity duration (secs)')
        
        fig.savefig(savepath)
        plt.clf()

    def compare_network_load(self, savepath):
        bins, vals = self.database.get_bins_comp('abm', 'trips', 
            'start_time', 'end_time', bin_size=-2)
        vals = [sum(vals[:i]) for i in range(len(vals))]
        plt.plot(bins, vals, alpha=0.75, color='b', label='2015 ABM')

        bins, vals = self.database.get_bins_comp('abm2018', 'trips', 
            'depart_time', 'arrive_time', bin_size=-2)
        vals = [sum(vals[:i]) for i in range(len(vals))]
        plt.plot(bins, vals, alpha=0.75, color='r', label='2018 ABM')

        plt.xlabel('time of day (sec)')
        plt.ylabel('agents traveling')
        plt.title('agent travel activity')
        plt.legend()
        plt.tight_layout()
        plt.savefig(savepath)
        plt.clf()

        

