

import sys
import os
import json
import statistics
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.ticker import PercentFormatter
from argparse import ArgumentParser
from collections import defaultdict
from xml.etree.ElementTree import iterparse

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

# from validation.plans_validator.plans_validator_db import PlansValidatorDatabaseHandle
from  icarus.util.print import Printer as pr

class PlansValidator:
    def __init__(self, database=None):
        # self.database = PlansValidatorDatabaseHandle(database)
        pass

    @staticmethod
    def parse_time(string):
        time = [int(t) for t in string.split(':')]
        return time[0]*3600 + time[1]*60 + time[0]

    def validate_plans(self, planspath, savepath, iters=[], silent=False):
        pr.print(f'Beginning plans validation from {planspath}.', time=True)
        fig, axs = plt.subplots(len(iters), 2, tight_layout=True)
        bins = 25

        for idx, it in zip(range(len(iters)), iters):
            pr.print(f'Reading plans from iter {it}.', time=True)
            parser = iterparse(planspath + f'it.{it}/{it}.plans.xml', events=('start', 'end'))
            parser = iter(parser)
            evt, root = next(parser)

            scores = []
            trips = []
            selected = False
            count = 0

            for evt, elem in parser:
                count += 1
                if evt == 'start':
                    if elem.tag == 'plan':
                        if elem.get('selected') == 'yes':
                            selected = True
                            scores.append(float(elem.get('score')))
                        else:
                            selected = False
                    elif elem.tag == 'leg':
                        if selected:
                            trips.append(self.parse_time(elem.get('trav_time')))
                if count % 100000 == 0:
                    root.clear()
            root.clear()

            pr.print('Trimming data.', time=True)
            mean = statistics.mean(scores)
            stdev = statistics.stdev(scores)
            low = mean - stdev * 3
            high = mean + stdev * 3
            scores = [score for score in scores if score >= low and score <= high]

            mean = statistics.mean(trips)
            stdev = statistics.stdev(trips)
            low = mean - stdev * 3
            high = mean + stdev * 3
            trips = [trip for trip in trips if trip >= low and trip <= high]

            pr.print('Graphing scores and trip durations.', time=True)
            axs[idx, 0].hist(scores, bins=bins)
            axs[idx, 0].yaxis.set_major_formatter(PercentFormatter(xmax=len(scores)))
            axs[idx, 1].hist(trips, bins=bins)
            axs[idx, 1].yaxis.set_major_formatter(PercentFormatter(xmax=len(trips)))

        fig.savefig(savepath)



if __name__ == '__main__':
    cmdline = ArgumentParser(prog='AgentsParser',
        description='Validtion of simulation output through charting iteration progress.')
    cmdline.add_argument('--config', type=str,  dest='config',
        default=(os.path.dirname(os.path.abspath(__file__)) + '/config.json'),
        help=('Specify a config file location; default is "config.json" in '
            'the current working directory.'), nargs=1)
    args = cmdline.parse_args()

    try:
        with open(args.config, 'r') as configfile:
            config = json.load(configfile)['WORKSTATION']
        validator = PlansValidator()
        validator.validate_plans(config['planspath'], config['savepath'], config['iters'])

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