
import csv

from random import randint
from collections import defaultdict

from icarus.input.parse.database import PlansParserDatabase
from icarus.util.print import PrintUtil as pr

class PlansParser:
    def __init__(self, database, encoding):
        self.database = PlansParserDatabase(params=database)
        self.encoding = encoding


    @classmethod
    def remove_parties(self, parties, remove, driver=None):
        if driver is None:
            for party in parties.values():
                if party[1] is None or party[1] in remove:
                    for agent in party[2]:
                        if agent not in remove:
                            remove.add(agent)
                            self.remove_parties(parties, remove, driver=agent)
        else:
            for party in filter(lambda p: p[1] == driver, parties.values()):
                for agent in party[2]:
                    if agent not in remove:
                        remove.add(agent)
                        self.remove_parties(parties, remove, driver=agent)


    @classmethod
    def report(self, count):
        total = count['total']
        bad = count['bad']
        good = total - bad
        vehicle = count['vehicle']
        party = count['party']
        maz = count['maz']
        act = count['act']
        mode = count['mode']

        table = [
            ['total plans analyzed', total, ''],
            ['plans kept', good, '%.4f%%' % (100 * good / total)],
            ['plans dropped', bad, '%.4f%%' % (100 * bad / total)],
            ['plans in invalid party', party, '%.4f%%' % (100 * party / total)],
            ['plans without vehicle', vehicle, '%.4f%%' % (100 * vehicle / total)],
            ['plans using invalid MAZ', maz, '%.4f%%' % (100 * maz / total)],
            ['plans using invalid activity', act, '%.4f%%' % (100 * act / total)],
            ['plans using invalid mode', mode, '%.4f%%' % (100 * mode / total)]
        ]
        
        pr.print(pr.table(table, pad=3))


    def parse(self, modes=[], acts=[], bin_size=250000, resume=False, 
            silent=False, seed=None):
        pr.print('Beginning parsing ABM data into MATSim input plans.', time=True)

        pr.print('Calculating parsing task size.', time=True)
        target_household = self.database.get_max(self.database.abm_db, 
            'trips', 'household_id') + 1
        groups = list(range(0, target_household, bin_size)) + [target_household]
        households = zip(groups[:-1], groups[1:])

        pr.print('Fetching Maricopa parcel data.', time=True)
        residences = self.database.get_parcels('residences', seed=seed)
        commerces = self.database.get_parcels('commerces', seed=seed)
        default = self.database.get_parcels('mazparcels', seed=seed)
        mazs = set(default.keys())

        res = defaultdict(int)

        cols = ('trip_id', 'household_id', 'household_idx', 'agent_id', 'agent_idx',
            'party_id', 'party_idx', 'party_role',  'origin_taz', 'origin_maz', 
            'dest_taz',  'dest_maz', 'origin_act', 'dest_act', 'mode', 'vehicle_id', 
            'depart_time', 'arrive_time', 'act_duration')
        keys = {key: val for key, val in zip(cols, range(len(cols)))}

        pr.print('Starting input plans parsing.', time=True)
        pr.print('Input Plans Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=0)

        activity_id = 0
        route_id = 0

        count = defaultdict(int)

        # iterate over household chunks in population

        for min_hh, max_hh in households:
            pr.print(f'Fetching trips for households {min_hh} '
                f'to {max_hh}.', time=True)
            all_trips = self.database.get_trips(min_hh, max_hh)

            agents = []
            routes = []
            activities = []

            # iterate over households in household chunk

            pr.print(f'Processing trips into plans.', time=True)
            for household_id, household_trips in all_trips.items():
                household_maz = \
                    list(household_trips.values())[0][0][keys['origin_maz']]
                household_apn = None
                household_parties = defaultdict(lambda: [None, None, set()])
                remove = set()
                
                count['total'] += len(household_trips)

                # validate that household has valid MAZ
                # if so, assign household an APN
                # otherwise, remove household

                if household_maz in residences:
                    household_apn = residences[household_maz][res[household_maz]]
                    res[household_maz] = ((res[household_maz] + 1) 
                        % len(residences[household_maz]))
                elif household_maz in commerces:
                    household_apn = commerces[household_maz][randint(0, 
                        len(commerces[household_maz]) - 1)]
                elif household_maz in default:
                    household_apn = default[household_maz]
                else:
                    count['bad'] += len(household_trips)
                    count['maz'] += len(household_trips)
                    continue

                # check that all trip activities have valid MAZs,
                # that trips are in valid activites and modes,
                # and that all agents in a party align properly
                # if not, remove agent trips involved

                # iterate over agents in household

                for agent_hhidx, agent_trips in household_trips.items():
                    agent_mazs = set()
                    agent_acts = set()
                    agent_modes = set()
                    agent_hasvehc = True

                    # iterate over trips for agent
                    
                    for trip in agent_trips:
                        agent_id = trip[keys['agent_id']]
                        party_id = trip[keys['party_id']]
                        vehicle_id = int(trip[keys['vehicle_id']])
                        mode = trip[keys['mode']]

                        agent_mazs.add(trip[keys['dest_maz']])
                        agent_acts.add(trip[keys['dest_act']])
                        agent_modes.add(mode)
                        
                        if mode in (1,2,3,4,13,14):
                            if party_id != 0:
                                party = household_parties[party_id]
                                party[2].add(agent_hhidx)
                                if vehicle_id != 0 and vehicle_id is not None:
                                    party[0] = vehicle_id
                                    party[1] = agent_hhidx
                            elif vehicle_id == 0 or vehicle_id is None:
                                agent_hasvehc = False

                    valid = True
                    if not agent_mazs.issubset(mazs):
                        valid = False
                        count['maz'] += 1
                    if not agent_acts.issubset(acts):
                        valid = False
                        count['act'] += 1
                    if not agent_modes.issubset(modes):
                        valid = False
                        count['mode'] += 1
                    if not agent_hasvehc:
                        valid = False
                        count['vehicle'] += 1
                    if not valid:
                        remove.add(agent_hhidx)

                remove_size = len(remove)
                self.remove_parties(household_parties, remove)
                count['party'] += len(remove) - remove_size

                for agent_hhidx in remove:
                    count['bad'] += 1
                    del household_trips[agent_hhidx]


                # iterate over remaining valid trips in
                # to the lists to add to database

                # iterate over agents in household

                for agent_trips in household_trips.values():
                    agent_id = agent_trips[0][keys['agent_id']]
                    household_idx = agent_trips[0][keys['household_idx']]
                    agents.append((
                        agent_id,
                        household_id,
                        household_idx,
                        2 * len(agent_trips) + 1))

                    # iterate over trips for each agent

                    for trip in agent_trips:
                        depart = trip[keys['depart_time']]
                        arrive = trip[keys['arrive_time']]
                        duration = trip[keys['act_duration']]
                        maz = trip[keys['dest_maz']]
                        act = trip[keys['dest_act']]
                        mode = trip[keys['mode']]
                        vehicle_id = int(trip[keys['vehicle_id']])
                        agent_hhidx = trip[keys['agent_idx']]
                        party_id = trip[keys['party_id']]

                        # vehicle assignment

                        if mode in (1,2,3,4,13,14):
                            if party_id == 0:
                                vehicle_id = f'car-{vehicle_id}'
                            else:
                                vehicle_id = f'car-{household_parties[party_id][0]}'
                        elif mode in (5,6,7,8,9,10):
                            vehicle_id = None
                        elif mode in (11,):
                            vehicle_id = f'walk-{agent_id}'
                        elif mode in (12,):
                            vehicle_id = f'bike-{agent_id}'

                        # apn assignment
                        # priority: commerce => residence => default

                        if act == 0 and maz == household_maz:
                            apn = household_apn
                        elif maz in commerces:
                            apn = commerces[maz][randint(0, 
                                len(commerces[maz]) - 1)]
                        elif maz in residences:
                            apn = residences[maz][randint(0, 
                                len(residences[maz]) - 1)]
                        elif maz in default:
                            apn = default[maz]

                        if agent_hhidx == 0:
                            activities.append((
                                activity_id,
                                agent_id,
                                agent_hhidx,
                                household_maz,
                                household_apn,
                                0,
                                0,
                                depart,
                                arrive))
                            activity_id += 1

                        routes.append((
                            route_id,
                            agent_id,
                            agent_hhidx,
                            mode,
                            vehicle_id,
                            depart,
                            arrive,
                            arrive - depart))
                        route_id += 1

                        activities.append((
                            activity_id,
                            agent_id,
                            agent_hhidx + 1,
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
        self.report(count)


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
