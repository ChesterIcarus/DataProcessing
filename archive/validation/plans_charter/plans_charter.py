
import sys
import os
import json
import statistics
import gzip
import shutil

import numpy as np
import matplotlib.pyplot as plt

from getpass import getpass
from matplotlib import colors
from matplotlib.ticker import PercentFormatter
from argparse import ArgumentParser
from collections import defaultdict
from xml.etree.ElementTree import iterparse

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from validation.plans_charter.plans_charter_db import PlansCharterDatabaseHandle
from  icarus.util.print import Printer as pr

class PlansCharter:
    def __init__(self, database=None):
        self.database = PlansCharterDatabaseHandle(database)
        self.output = defaultdict(dict)
        self.input = {}
        self.agents = set()

    @staticmethod
    def parse_time(string):
        time = [int(t) for t in string.split(':')]
        return time[0]*3600 + time[1]*60 + time[0]

    @staticmethod
    def decompress_plans(gzplans, plans):
        with open(plans, 'wb') as outfile, gzip.open(gzplans, 'rb') as infile:
            shutil.copyfileobj(infile, outfile)

    @staticmethod
    def trim_data(data):
        mean = statistics.mean(data)
        stdev = statistics.stdev(data)
        low = mean - 3 * stdev
        high = mean + 3 * stdev
        return [d for d in data if d >= low and d <= high]

    def parse_output(self, filepath, it, bin_size=100000, silent=False):

        planspath = f'{filepath}/it.{it}/{it}.plans.xml'
        gzplanspath = f'{filepath}/it.{it}/{it}.plans.xml.gz'

        if not os.path.isfile(planspath):
            if os.path.isfile(gzplanspath):
                self.decompress_plans(gzplanspath, planspath)
            else:
                raise Exception

        parser = iterparse(planspath, events=('start', 'end'))
        parser = iter(parser)
        evt, root = next(parser)

        count = 0
        agent = 0
        selected = False
        self.agents = []

        for evt, elem in parser:
            count += 1
            if evt == 'start':
                if elem.tag == 'person':
                    agent = elem.get('id')
                elif elem.tag == 'plan':
                    selected = elem.get('selected') == 'yes'
                    if selected:
                        self.agents.append(agent)
                    trip = 0
                elif elem.tag == 'leg' and selected:
                    self.output[it][f'{agent}-{trip}'] = self.parse_time(elem.get('trav_time'))
                    trip += 1
            if count % 100000 == 0:
                root.clear()
        root.clear()

    def parse_input(self, agents):
        self.input = {f'{row[0]}-{row[1]}':row[2] for row in self.database.fetch_plans(tuple(agents))}

    def run(self, config):
        pass

    def chart_cdf(self, filepath, its):

        for it in its:
            if not len(self.output[it]):
                self.parse_output(filepath, it)
            if not len(self.output):
                self.parse_input(self.agents)

            data = self.trim_data(self.output[it].values())
            ct = len(data)
            low = min(data)
            high = max(data)
            dx = (high - low) / 100
            X = np.arange(low, high, dx)

            pmf = [len([d for d in data if d > x1 and d <= x2]) / ct 
                for x1, x2 in zip(X[:-1], X[1:])]
            cdf = [sum(pmf[:i]) for i in range(pmf)]

    def chart_dot(self):
        pass

    def chart_scatter(self, planspath, it, savepath):
        if not len(self.output[it]):
            self.parse_output(planspath, it)
        if not len(self.input):
            self.parse_input(self.agents)

        x = []
        y = []
        for key, val in self.output[it].items():
            err = (val- self.input[key]) / self.input[key] * 100
            if err < 4000 and self.input[key] < 20000:
                x.append(self.input[key])
                y.append(err)

        plt.scatter(x, y, s=[1]*len(x), alpha=0.02)
        plt.xlabel("travel time (secs)")
        plt.ylabel("travel time error (%)")
        plt.title("travel error vs duration")
        plt.savefig(savepath)
        



if __name__ == '__main__':
    cmdline = ArgumentParser(prog='AgentsParser',
        description='Parse ABM agents csv file into table in a SQL database.')
    cmdline.add_argument('--config', type=str,  dest='config',
        default=(os.path.dirname(os.path.abspath(__file__)) + '/config.json'),
        help=('Specify a config file location; default is "config.json" in '
            'the current working directory.'), nargs=1)
    args = cmdline.parse_args()

    try:
        with open(args.config, 'r') as configfile:
            config = json.load(configfile)['WORKSTATION']
        
        database = config['database']
        database['password'] = getpass(
            f'SQL password for {database["user"]}@localhost: ')

        charter = PlansCharter(database)

        charter.chart_scatter(config['planspath'], config['iteration'], config['savepath'])

    except FileNotFoundError as err:
        print(f'Config file {args.config} not found.')
        quit()
    except json.JSONDecodeError as err:
        print(f'Config file {args.config} is not valid JSON.')
        quit()
    # except KeyError as err:
    #     print(f'Config file {args.config} is not valid config file.')
    #     quit()
    except Exception as err:
        raise(err)