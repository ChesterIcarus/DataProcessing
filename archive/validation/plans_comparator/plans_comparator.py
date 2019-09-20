
import sys
import os
import json
import statistics
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

from validation.plans_comparator.plans_comparator_db import PlansComparatorDatbaseHandle
from  icarus.util.print import Printer as pr

class PlansComparator:
    def __init__(self, database=None):
        self.database = PlansComparatorDatbaseHandle(database)
    
    @staticmethod
    def parse_time(string):
        time = [int(t) for t in string.split(':')]
        return time[0]*3600 + time[1]*60 + time[0]

    def compare_plans(self, plansfile, savefile, bins=25):
        pr.print(f'Beginning plans comparing from {plansfile}.', time=True)

        parser = iterparse(plansfile, events=('start', 'end'))
        parser = iter(parser)
        evt, root = next(parser)

        trips = {}
        count = 0
        selected = False
        agent = 0
        agents = set()

        pr.print(f'Reading travel times from output plans file.', time=True)
        for evt, elem in parser:
            count += 1
            if evt == 'start':
                if elem.tag == 'person':
                    agent = elem.get('id')
                elif elem.tag == 'plan':
                    selected = elem.get('selected') == 'yes'
                    agents.add(agent)
                    trip = 0
                elif elem.tag == 'leg' and selected:
                    trips[f'{agent}-{trip}'] = self.parse_time(elem.get('trav_time'))
                    trip += 1
            if count % 100000 == 0:
                root.clear()

        pr.print('Fetching travel times from input plans.', time=True)
        input_trips = self.database.get_trips(tuple(agents))

        pr.print('Preparing data for comparison.', time=True)

        error = [(val - input_trips[key]) / input_trips[key] for key, val in trips.items()]
        count= len(error)

        mean = statistics.mean(error)
        stdev = statistics.stdev(error)
        low = mean - stdev * 3
        high = mean + stdev * 3
        error = [err for err in error if err >= low and err <= high]

        trips = trips.values()
        mean = statistics.mean(trips)
        stdev = statistics.stdev(trips)
        low = mean - stdev * 3
        high = mean + stdev * 3
        trips = [trip for trip in trips if trip >= low and trip <= high]

        input_trips = input_trips.values()
        mean = statistics.mean(input_trips)
        stdev = statistics.stdev(input_trips)
        low = mean - stdev * 3
        high = mean + stdev * 3
        input_trips = [trip for trip in input_trips if trip >= low and trip <= high]

        pr.print('Graphing data.', time=True)

        fig, axs = plt.subplots(1, 2, tight_layout=True)
        axs[0].hist(error, bins)
        axs[0].yaxis.set_major_formatter(PercentFormatter(xmax=count))
        axs[1].hist(trips, bins)
        axs[1].hist(input_trips, bins)
        axs[1].yaxis.set_major_formatter(PercentFormatter(xmax=count))
        fig.savefig(savefile)

        pr.print('Plans comparison complete.', time=True)

        





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

        comparator = PlansComparator(config['database'])

        path = config["planspath"]
        it = config["iteration"]
        plansfile = f'{path}/it.{it}/{it}.plans.xml'

        comparator.compare_plans(plansfile, config['savepath'])

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