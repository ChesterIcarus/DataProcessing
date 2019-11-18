
import csv

from random import randint
from collections import defaultdict

from icarus.input.parser.database import PlansParserDatabase
from icarus.util.print import Printer as pr

class PlansParser:
    def __init__(self, database, encoding):
        self.database = PlansParserDatabase(params=database)
        self.encoding = encoding

    def parse(self, modes=[], acts=[], bin_size=250000, resume=False, 
            silent=False, seed=None):
        pr.print('Beginning parsing ABM data into MATSim input plans.', time=True)
        pr.print('Loading process metadata and fetching reference data.', time=True)

        target_household = self.database.get_max(self.database.abm_db, 
            'trips', 'household_id') + 1
        groups = list(range(0, target_household, bin_size)) + [target_household]
        households = zip(groups[:-1], groups[1:])

        residences = self.database.get_parcels('residences', seed=seed)
        commerces = self.database.get_parcels('commerces', seed=seed)
        default = self.database.get_parcels('mazparcels', seed=seed)

        res = defaultdict(int)

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

        count = defaultdict(int)

        for min_hh, max_hh in households:
            pr.print(f'Fetching trips for households {min_hh} to {max_hh}.', time=True)
            trips = self.database.get_trips(min_hh, max_hh)

            agid = 0
            agidx = 0
            hhid = 0
            hhidx = 0
            hhmaz = 0
            hhapn = ''

            valid = True

            agent_routes = []
            agent_acts = []

            agents = []
            routes = []
            activities = []

            pr.print(f'Processing trips into plans.', time=True)
            for trip in trips:

                agidx = trip[keys['agent_idx']]
                hhidx = trip[keys['household_idx']]

                if agidx == 0:
                    count['total'] += 1
                    if not valid:
                        count['bad plan'] += 1
                        valid = True
                        activity_id -= len(agent_acts)
                        route_id -= len(agent_routes)
                    elif len(agent_acts):
                        agents.append((
                            agid,
                            hhid,
                            None,
                            len(agent_routes) + len(agent_acts)))
                        routes.extend(agent_routes)
                        activities.extend(agent_acts)

                    agent_routes = []
                    agent_acts = []
                    agid = trip[keys['agent_id']]

                if hhidx == 1:
                    hhid = trip[keys['household_id']]
                    hhmaz = trip[keys['origin_maz']]
                    if hhmaz in residences:
                        hhapn = residences[hhmaz][res[hhmaz]]
                        res[hhmaz] = (res[hhmaz] + 1) % len(residences[hhmaz])
                    elif hhmaz in commerces:
                        hhapn = commerces[hhmaz][randint(0, len(commerces[hhmaz]) - 1)]
                    elif hhmaz in default:
                        hhapn = default[hhmaz]
                    else:
                        hhapn = ''

                if not valid:
                    continue

                maz = trip[keys['dest_maz']]
                act = trip[keys['dest_act']]
                mode = trip[keys['mode']]

                if act not in acts and len(acts):
                    count['bad act'] += 1
                    valid = False
                if mode not in modes and len(modes):
                    count['bad mode'] += 1
                    valid = False
                
                if hhapn == '':
                    count['bad apn'] += 1
                    valid = False
                elif act == 0 and maz == hhmaz:
                    apn = hhapn
                elif maz in commerces:
                    apn = commerces[maz][randint(0, len(commerces[maz]) - 1)]
                elif maz in residences:
                    apn = residences[maz][randint(0, len(residences[maz]) - 1)]
                elif maz in default:
                    apn = default[maz]
                else:
                    count['bad apn'] += 1
                    valid = False

                if not valid:
                    continue

                depart = trip[keys['depart_time']]
                arrive = trip[keys['arrive_time']]
                duration = trip[keys['act_duration']]
                vehicle = trip[keys['vehicle_id']]

                # if mode == 4 and vehicle_id

                if agidx == 0:
                    agent_acts.append((
                        activity_id,
                        agid,
                        agidx,
                        hhmaz,
                        hhapn,
                        0,
                        0,
                        depart,
                        arrive))
                    activity_id += 1
                
                agent_routes.append((
                    route_id,
                    agid,
                    agidx,
                    mode,
                    vehicle,
                    depart,
                    arrive,
                    arrive - depart))
                route_id += 1

                agent_acts.append((
                    activity_id,
                    agid,
                    agidx + 1,
                    maz,
                    apn,
                    act,
                    arrive,
                    arrive + duration,
                    duration))
                activity_id += 1

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
        pr.print(f'bad: {count["bad plan"]/count["total"]*100}')
        pr.print(f'bad act: {count["bad act"]/count["total"]*100}')
        pr.print(f'bad mode: {count["bad mode"]/count["total"]*100}')
        pr.print(f'bad apn: {count["bad apn"]/count["total"]*100}')

    def index(self, silent=False):
        if not silent:
            pr.print(f'Creating all indexes in database "{self.database.db}".',
                time=True)
        for tbl in self.database.tables:
            self.database.create_all_idxs(tbl)
        if not silent:
            pr.print(f'Index creating complete.', time=True)

    def verify(self, silent=False):
        pr.print(f'Beginning contradiction analysis.', time=True)
        
        pr.print(f'Contradiction analysis complete.', time=True)

