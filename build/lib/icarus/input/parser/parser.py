
import csv
import json
import os
import sys

from pprint import pprint
from argparse import ArgumentParser
from getpass import getpass
from random import randint
from collections import defaultdict

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from input.parser.database import PlansParserDatabase
from  icarus.util.print import Printer as pr

class PlansParser:
    def __init__(self, database, encoding):
        self.database = PlansParserDatabase(database)
        self.encoding = encoding

    def parse(self, modes, acts, bin_size=250000, resume=False, 
            silent=False, seed=None):
        pr.print('Beginning parsing ABM data into MATsim input plans.', time=True)
        pr.print('Loading process metadata and fetching reference data.', time=True)

        target_household = self.database.get_max(self.database.abm_db, 
            'trips', 'household_id') + 1
        groups = list(range(0, target_household, bin_size)) + [target_household]
        households = zip(groups[:-1], groups[1:])

        residences = self.database.get_parcels('network', 'residences')
        commerces = self.database.get_parcels('network', 'commerces')
        residx = defaultdict(int)

        cols = ('trip_id', 'household_id', 'household_idx', 'agent_id',
            'agent_idx', 'origin_taz', 'origin_maz', 'dest_taz', 'dest_maz',
            'origin_act', 'dest_act', 'mode', 'vehicle_id', 'depart_time',
            'arrive_time', 'act_duration')
        keys = {key: val for key, val in zip(cols, range(len(cols)))}

        pr.print('Starting input plans parsing.', time=True)
        pr.print('Input Plans Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=0)

        activity_id = 0
        route_id = 0
        agent_id = 0
        household_id = 0
        count = defaultdict(int)

        for min_hh, max_hh in households:
            pr.print(f'Fetching trips for households {min_hh} to {max_hh}.', time=True)
            trips = self.database.get_trips(min_hh, max_hh)

            hhid = 0
            hhidx = 0
            hhmaz = 0
            hhapn = ''
            agid = 0
            agidx = 0
            used = False
            valid = True

            agent_routes = []
            agent_acts = []

            agents = []
            routes = []
            activities = []

            pr.print(f'Processing trips into plans.', time=True)
            for trip in trips + ((0,)*len(cols),):
                if (agid != trip[keys['agent_id']] or
                        hhid != trip[keys['household_id']]):
                    hhidx += 1
                    agidx = 0
                    count['total'] += 1
                    if not valid:
                        valid = True
                        count['bad'] += 1
                        activity_id -= len(agent_acts)
                        route_id -= len(agent_routes)
                    elif len(agent_acts):
                        used = True
                        agents.append((
                            agent_id,
                            household_id,
                            hhidx,
                            len(agent_routes) + len(agent_acts)))
                        agent_id += 1
                        routes.extend(agent_routes)
                        activities.extend(agent_acts)
                    agent_routes = []
                    agent_acts = []
                    agid = trip[keys['agent_id']]

                if hhid != trip[keys['household_id']]:
                    if used:
                        household_id += 1
                    hhidx = 0
                    hhid = trip[keys['household_id']]
                    hhmaz = trip[keys['origin_maz']]
                    used = False
                    if hhmaz in residences:
                        hhapn = residences[hhmaz][residx[hhmaz]]
                        residx[hhmaz] = (residx[hhmaz] + 1) % len(residences[hhmaz])
                    elif hhmaz in commerces:
                        hhapn = commerces[hhmaz][randint(0, len(commerces[hhmaz]))-1]

                if not valid:
                    continue

                maz = trip[keys['dest_maz']]
                if trip[keys['dest_act']] not in acts:
                    count['bad act'] += 1
                    valid = False
                    continue
                elif trip[keys['mode']] not in modes:
                    count['bad mode'] += 1
                    valid = False
                    continue
                elif not trip[keys['dest_act']] and maz == hhmaz:
                    apn = hhapn
                elif maz in commerces:
                    apn = commerces[maz][randint(0, len(commerces[maz]))-1]
                elif maz in residences:
                    apn = residences[maz][randint(0, len(residences[maz]))-1]
                else:
                    count['bad apn'] += 1
                    valid = False
                    continue

                if not agidx:
                    agent_acts.append((
                        activity_id,
                        agent_id,
                        agidx,
                        hhmaz,
                        hhapn,
                        0,
                        0,
                        trip[keys['depart_time']],
                        trip[keys['depart_time']]))
                    activity_id += 1
                
                agent_routes.append((
                    route_id,
                    agent_id,
                    agidx,
                    trip[keys['mode']],
                    trip[keys['depart_time']],
                    trip[keys['arrive_time']],
                    trip[keys['arrive_time']] - trip[keys['depart_time']]))
                route_id += 1

                agent_acts.append((
                    activity_id,
                    agent_id,
                    agidx + 1,
                    maz,
                    apn,
                    trip[keys['dest_act']],
                    trip[keys['arrive_time']],
                    trip[keys['arrive_time']] + trip[keys['act_duration']],
                    trip[keys['act_duration']]))
                activity_id += 1

                agidx += 1

            pr.print(f'Pushing {len(agents)} plans to database.', time=True)

            self.database.write_activities(activities)
            self.database.write_routes(routes)
            self.database.write_agents(agents)

            activities = []
            routes = []
            agents = []

            pr.print('Input Plans Parsing Progress', persist=True, replace=True,
                frmt='bold', progress=max_hh/target_household)

        pr.print('Input Plans Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=1)
        pr.push()
        pr.print(f'Input plans parsing complete.', time=True)
        pr.print('Plans filtering report:', time =True)
        pr.print(f'total: {count["total"]}')
        pr.print(f'bad: {count["bad"]/count["total"]*100}')
        pr.print(f'bad act: {count["bad act"]/count["total"]*100}')
        pr.print(f'bad mode: {count["bad mode"]/count["total"]*100}')
        pr.print(f'bad apn: {count["bad apn"]/count["total"]*100}')

    def index(self, silent=False):
        if not silent:
            pr.print(f'Creating all indexes in database "{self.database.db}"".',
                time=True)
        for tbl in self.database.tables:
            parser.database.create_all_idxs(tbl)
        if not silent:
            pr.print(f'Index creating complete.', time=True)

    def verify(self, silent=False):
        pr.print(f'Beginning contradiction analysis.', time=True)
        
        pr.print(f'Contradiction analysis complete.', time=True)

if __name__ == '__main__':
    parser = ArgumentParser(prog='AgentsParser',
        description='Converts ABM trips to MATSIM plans, activities, and routes.')
    parser.add_argument('--config', type=str,  dest='config',
        default=(os.path.dirname(os.path.abspath(__file__)) + '/config.json'),
        help=('Specify a config file location; default is "config.json" in '
            'the current working directory.'))
    parser.add_argument('--log', type=str, dest='log',
        help='specify a log file location; by default the log will not be saved',
        default=None)
    args = parser.parse_args()

    try:
        if args.log is not None:
            pr.log(args.log)

        with open(args.config) as handle:
            config = json.load(handle)

        database = config['database']
        encoding = config['encoding']

        database['password'] = getpass(
            f'SQL password for {database["user"]}@localhost: ')

        parser = PlansParser(database, encoding)

        if not config['resume']:
            for table in database['tables'].keys():
                parser.database.create_table(table)

        options = ('silent', 'bin_size', 'resume')
        params = {key:config[key] for key in options if key in config}

        parser.parse(config['modes'], config['acts'], **params)

        if config['create_idxs']:
            parser.index()

        if config['verify']:
            parser.verify() 

    except FileNotFoundError as err:
        print(f'Config file {args.config} not found.')
        quit()
    except json.JSONDecodeError as err:
        print(f'Config file {args.config} is not valid JSON.')
        quit()
    except KeyError as err:
        print(f'Config file {args.config} is not valid config file.')
        quit()
    except Exception as err:
        raise(err)