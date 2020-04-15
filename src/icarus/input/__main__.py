
import os
import logging as log
from argparse import ArgumentParser
from icarus.input.generate import Generation
from icarus.input.validate import Validation
from icarus.input.parse import Parsing
from icarus.input.sample import Sampling
from icarus.util.sqlite import SqliteUtil
from icarus.util.config import ConfigUtil
from icarus.util.file import exists

def run(database, config, action, replace, folder):
    path = lambda x: os.path.join(folder, x)
    if action == 'parse':
        parsing = Parsing(database)
        if parsing.complete() and not replace:
            log.info('Input population already parsed; skipping parsing.')
        else:
            parsing.parse(
                config['population']['trips_file'],
                config['population']['households_file'],
                config['population']['persons_file'])
    elif action == 'generate':
        generation = Generation(database)
        if generation.complete() and not replace:
            log.info('Input population already generated; skipping generation.')
        else:
            generation.generate(
                config['population']['modes'],
                config['population']['activity_types'],
                config['population']['seed'])
    elif action == 'sample':
        sampling = Sampling(database)
        planspath = path('input/plans.xml.gz')
        vehiclespath = path('input/vehicles.xml.gz')
        if (exists(planspath) or exists(vehiclespath)) and not replace:
            log.info('Input population already sampled; skipping sampling.')
        else:
            # hardcoded parameters
            sampling.sample(
                planspath,
                vehiclespath,
                sample_perc=0.01,
                sample_size=10000,
                transit=None,
                party=None,
                virtual=['pt', 'car'])
    elif action == 'validate':
        validation = Validation(database)
        validation.validate()


parser = ArgumentParser()
parser.add_argument('--folder', type=str, dest='folder', default='.')
parser.add_argument('--log', type=str, dest='log', default=None)
parser.add_argument('--level', type=str, dest='level', default='info',
    choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'))
parser.add_argument('action', type=str)
parser.add_argument('--replace', dest='replace', action='store_true', default=False)
args = parser.parse_args()

handlers = []
handlers.append(log.StreamHandler())
if args.log is not None:
    handlers.append(log.FileHandler(args.log, 'w'))
log.basicConfig(
    format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
    level=getattr(log, args.level.upper()),
    handlers=handlers)

path = lambda x: os.path.join(args.folder, x)
config = ConfigUtil.load_config(path('config.json'))
database = SqliteUtil(path('database.db'))

run(database, config, args.action, args.replace, args.folder)
