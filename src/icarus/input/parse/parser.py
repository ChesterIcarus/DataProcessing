
import csv

from random import randint
from collections import defaultdict

from icarus.input.parse.database import PlansParserDatabase
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
        mazs = set(default.keys())

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

        # iterate over households in chunks
        for min_hh, max_hh in households:
            pr.print(f'Fetching trips for households {min_hh} to {max_hh}.', time=True)
            trips_dict = self.database.get_trips(min_hh, max_hh)

            agents = []
            routes = []
            activities = []

            # process each houshold individually
            pr.print(f'Processing trips into plans.', time=True)
            for household_id, trips in trips_dict.items():
                household_maz = list(trips.values())[0][0][keys['origin_maz']]
                household_apn = None
                remove = []
                
                count['total'] += len(trips)

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
                    count['bad'] += len(trips)
                    count['maz'] += len(trips)
                    continue


                # check that all trip activities have valid MAZs
                # and that trips are in valid activites and modes
                # and that vehicle trips have vehicles
                # if not, remove agent trips
                for agent, agent_trips in trips.items():
                    agent_mazs = set(trip[keys['dest_maz']] for trip in agent_trips)
                    agent_acts = set(trip[keys['dest_act']] for trip in agent_trips)
                    agent_modes = set(trip[keys['mode']] for trip in agent_trips)
                    agent_vehcs = all(trip[keys['vehicle_id']] != 0 for trip 
                        in agent_trips if trip[keys['mode']] in (1, 2, 3))
                    valid = True

                    if not agent_vehcs:
                        valid = False
                        count['vehicle'] += 1
                    if not agent_mazs.issubset(mazs):
                        valid = False
                        count['maz'] += 1
                    if not agent_acts.issubset(acts):
                        valid = False
                        count['act'] += 1
                    if not agent_modes.issubset(modes):
                        valid = False
                        count['mode'] += 1
                    if not valid:
                        count['bad'] += 1
                        remove.append(agent)

                for agent in remove:
                    del trips[agent]
                remove = []

                
                # check for trip passengers (non drivers)
                # if driver found, merge trip vehicle for passengers 
                # otherwise, remove agent trips
                if any(trip[keys['mode']] == 4  for agent_trips in trips.values()
                        for trip in agent_trips):
                    start = {trip[keys['depart_time']]: trip[keys['vehicle_id']]
                        for agent_trips in trips.values() for trip in agent_trips
                        if trip[keys['mode']] in (2, 3)}
                    for agent, agent_trips in trips.items():
                        for trip in agent_trips:
                            if trip[keys['mode']] == 4:
                                depart = trip[keys['depart_time']]
                                if depart in start:
                                    agent_idx = trip[keys['agent_idx']]
                                    copy = list(trip)
                                    copy[keys['vehicle_id']] = start[depart]
                                    trips[agent][agent_idx] = tuple(copy)
                                else:
                                    count['bad'] += 1
                                    count['driver'] += 1
                                    remove.append(agent)
                                    break
                
                for agent in remove:
                    del trips[agent]
                remove = []


                # iterate over remaining valid trips and add them 
                # to the lists to add to database
                for agent_trips in trips.values():
                    agent_id = agent_trips[0][keys['agent_id']]
                    household_idx = agent_trips[0][keys['household_idx']]
                    agents.append((
                        agent_id,
                        household_id,
                        household_idx,
                        2 * len(agent_trips) + 1))

                    for trip in agent_trips:
                        depart = trip[keys['depart_time']]
                        arrive = trip[keys['arrive_time']]
                        duration = trip[keys['act_duration']]
                        maz = trip[keys['dest_maz']]
                        act = trip[keys['dest_act']]
                        mode = trip[keys['mode']]
                        vehicle = trip[keys['vehicle_id']]
                        agent_idx = trip[keys['agent_idx']]

                        # apn assignment
                        # priority: commerce => residence => default
                        if act == 0 and maz == household_maz:
                            apn = household_apn
                        elif maz in commerces:
                            apn = commerces[maz][randint(0, len(commerces[maz]) - 1)]
                        elif maz in residences:
                            apn = residences[maz][randint(0, len(residences[maz]) - 1)]
                        elif maz in default:
                            apn = default[maz]

                        if agent_idx == 0:
                            activities.append((
                                activity_id,
                                agent_id,
                                agent_idx,
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
                            agent_idx,
                            mode,
                            vehicle,
                            depart,
                            arrive,
                            arrive - depart))
                        route_id += 1

                        activities.append((
                            activity_id,
                            agent_id,
                            agent_idx + 1,
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
        total = count['total']
        bad = count['bad']
        good = total - bad
        driver = count['driver']
        vehicle = count['vehicle']
        maz = count['maz']
        act = count['act']
        mode = count['mode']
        pr.print(f'Total plans analyzed: {total}')
        pr.print(f'Plans kept: {good} ({100 * good / total}%)')
        pr.print(f'Plans dropped: {bad} ({100 * bad / total}%)')
        pr.print(f'Plans without driver: {driver} ({100 * driver / total}%)')
        pr.print(f'Plans without vehicle: {vehicle} ({100 * vehicle / total}%)')
        pr.print(f'Plans using invalid MAZ: {maz} ({100 * maz / total}%)')
        pr.print(f'Plans using invalid activity: {act} ({100 * act / total}%)')
        pr.print(f'Plans using invalid mode: {mode} ({100 * mode / total}%)')


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

