
import csv
import logging as log

from random import randint
from enum import IntEnum

from icarus.input.parse.database import PlansParserDatabase
from icarus.util.config import ConfigUtil


def chunk(start, stop, chunk):
    bins = zip(range(start, stop, chunk), 
        range(start+chunk, stop+chunk, chunk))
    for low, high in bins:
        yield low, high


class defaultdict(dict):
    def __init__(self, function):
        self.function = function

    def __getitem__(self, item):
        if item in self:
            return super().__getitem__(item)
        else:
            value = self.function(item)
            self[item] = value
            return value


class Act(IntEnum):
    HOME = 0
    WORKPLACE = 1
    UNIVERSITY = 2
    SCHOOL = 3
    ESCORT = 4
    SCHOOL_ESCPORT = 41
    PURE_ESCROT = 411
    RIDSESHARE_ESCORT = 412
    OTHER_ESCORT = 42
    SHOPPING = 5
    OTHER_MAINTENANCE = 6
    EATING_OUT = 7
    BREAKFAST = 71
    LUNCH = 72
    DINNER = 73
    VISITING = 8
    OTHER_DISCRETIONARY = 9
    SPECIAL_EVENT = 10
    WORK = 11
    WORK_BUSINESS = 12
    WORK_LUNCH = 13
    WORK_OTHER = 14
    WORK_RELATED = 15
    ASU = 16

    @classmethod
    def escort(self, act):
        return act in (
            self.ESCORT,
            self.SCHOOL_ESCPORT,
            self.PURE_ESCROT,
            self.RIDSESHARE_ESCORT,
            self.OTHER_ESCORT   )


class Mode(IntEnum):
    SOV = 1
    HOV2 = 2
    HOV3 = 3
    PASSENGER = 4
    CONV_TRANS_WALK = 5
    CONV_TRANS_KNR = 6
    CONV_TRANS_PNR = 7
    PREM_TRANS_WALK = 8
    PREM_TRANS_KNR = 9
    PREM_TRANS_PNR = 10
    WALK = 11
    BIKE = 12
    TAXI = 13
    SCHOOL_BUS = 14

    @classmethod
    def transit(self, mode):
        return mode in (
            self.CONV_TRANS_WALK,
            self.CONV_TRANS_KNR,
            self.CONV_TRANS_PNR,
            self.PREM_TRANS_WALK,
            self.PREM_TRANS_KNR,
            self.PREM_TRANS_PNR )
    
    @classmethod
    def vehicle(self, mode):
        return mode in (
            self.SOV,
            self.HOV2,
            self.HOV3,
            self.PASSENGER,
            self.TAXI,
            self.SCHOOL_BUS )


class Population:
    def __init__(self):
        self.households = defaultdict(lambda x: Household(x))

    def get_agent(self, trip):
        household = Agent.get(trip, 'household_id')
        agent = Agent.get(trip, 'agent_id')
        return self.households[household].agents[agent]


class Household:
    def __init__(self, household):
        self.id = household
        self.parties = defaultdict(lambda x: Party(x))
        self.agents = defaultdict(lambda x: Agent(x, self))

    def filter_agents(self, valid, debug=False):
        remove = set()
        for agent in self.agents.values():
            if agent not in remove:
                if not valid(agent):
                    remove = remove.union(agent.dependents(debug=debug))
        if debug:
            input(tuple(agent.id for agent in remove))
        for agent in remove:
            agent.leave_parties()
            del self.agents[agent.id]
        remove = set()
        for party in self.parties.values():
            if len(party.agents) < 2:
                remove.add(party)
        for party in remove:
            del self.parties[party.id]


class Party:
    def __init__(self, party):
        self.id = party
        self.agents = set()
        self.driver = None
        self.vehicle = None

    def set_driver(self, driver, vehicle):
        self.driver = driver
        self.vehicle = vehicle


class Agent:
    cols = ('trip_id', 'household_id', 'household_idx', 'agent_id', 'agent_idx',
        'party_id', 'party_idx', 'party_role',  'origin_taz', 'origin_maz', 
        'dest_taz',  'dest_maz', 'origin_act', 'dest_act', 'mode', 'vehicle_id', 
        'depart_time', 'arrive_time', 'act_duration')
    keys = {key: val for val, key in enumerate(cols)}

    def __init__(self, agent, household):
        self.id = agent
        self.household = household
        self.trips = []
        self.modes = set()
        self.acts = set()
        self.mazs = set()
        self.parties = set()

    @classmethod
    def get(self, trip, prop):
        return trip[self.keys[prop]]

    def dependents(self, agents=None, debug=False):
        if agents is None:
            agents = set()
        agents.add(self)
        for party in self.parties:
            if party.driver == self:
                for agent in party.agents:
                    if agent not in agents:
                        agents = agent.dependents(agents, debug=debug)
        return agents

    def leave_parties(self):
        for party in self.parties:
            party.agents.remove(self)
            if party.driver == self:
                party.driver = None
                party.vehicle = None
        self.parties = set()

    def parse_trip(self, trip):
        mode = self.get(trip, 'mode')
        party_id = int(self.get(trip, 'party_id'))
        vehicle_id = int(self.get(trip, 'vehicle_id'))
        act = self.get(trip, 'dest_act')
        maz = self.get(trip, 'dest_maz')

        self.modes.add(mode)
        self.acts.add(act)
        self.mazs.add(maz)

        self.trips.append(trip)

        if Mode.vehicle(mode):
            if party_id != 0:
                party = self.household.parties[party_id]
                party.agents.add(self)
                self.parties.add(party)
                if vehicle_id not in (0, None):
                    party.set_driver(self, vehicle_id)


class PlansParser:
    def __init__(self, database):
        self.database = PlansParserDatabase(params=database)

    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath)
        # specs = ConfigUtil.load_specs(specspath)
        # config = ConfigUtil.verify_config(specs, config)

        return config


    def run(self, config):
        seed = config['run']['seed']
        abm_db = config['run']['abm_db']
        simulation_start = config['run']['simulation_start']
        # simulation_end = config['run']['simulation_end']

        valid_modes = set(config['filter']['modes'])
        valid_acts = set(config['filter']['acts'])

        log.info('Preallocating files and tables.')
        self.create_tables(*self.database.tables.keys())

        log.info('Fetching maricopa county parcel data.')
        residences = self.database.get_parcels('residences', seed=seed)
        commerces = self.database.get_parcels('commerces', seed=seed)
        default = self.database.get_parcels('mazparcels', seed=seed)

        offset = defaultdict(lambda x: 0)
        mazs = tuple(default.keys())

        target = self.database.get_max(config['run']['abm_db'], 
            'trips','household_id')
        ranges = chunk(0, target + 1, config['run']['bin'])

        valid = (lambda agent:
            agent.modes.issubset(valid_modes) and 
            agent.acts.issubset(valid_acts) and
            agent.mazs.issubset(mazs) and 
            all(party.driver is not None for party in agent.parties ))

        count = 0
        n = 1

        for low, high in ranges:
            log.debug(f'Fetching trips for households {low} to {high}.')
            trips = self.database.get_trips(abm_db, low, high)

            population = Population()
            activities = []
            routes = []
            agents = []
            households = []

            # iterate over trips
            log.debug('Parsing trips into agent-party data.')
            for trip in trips:
                agent = population.get_agent(trip)
                agent.parse_trip(trip)

            # iterate over households
            log.debug('Building plans from agent-party data.')
            for household in population.households.values():
                household.filter_agents(valid)
                if len(household.agents) == 0:
                    continue

                # home apn assignment
                trip = next(iter(household.agents.values())).trips[0]
                home_maz = Agent.get(trip, 'origin_maz')
                if home_maz in residences:
                    home_apn = residences[home_maz][offset[home_maz]]
                    offset[home_maz] = (offset[home_maz] + 1) % \
                        len(residences[home_maz])
                elif home_maz in commerces:
                    home_apn = commerces[home_maz][randint(0, 
                        len(commerces[home_maz]) - 1)]
                elif home_maz in default:
                    home_apn = default[home_maz]
                else:
                    log.error(f'Household {household.id} has an invalid '
                        'maz not ahndled in filtering.')
                    raise ValueError

                # iterate over household agents
                for agent in household.agents.values():
                    uses_vehicle = False
                    uses_walk = False
                    uses_bike = False
                    uses_transit = False
                    uses_party = False

                    # iterate over agent trips
                    for idx, trip in enumerate(agent.trips):
                        act = Agent.get(trip, 'dest_act')
                        maz = Agent.get(trip, 'dest_maz')
                        mode = Agent.get(trip, 'mode')
                        arrive = Agent.get(trip, 'arrive_time')
                        depart = Agent.get(trip, 'depart_time')
                        duration = Agent.get(trip, 'act_duration')

                        # vehicle assignment
                        if Mode.vehicle(mode):
                            uses_vehicle = True
                            party = Agent.get(trip, 'party_id')
                            vehicle = household.parties[party].vehicle
                            if vehicle is None:
                                vehicle_id = Agent.get(trip, 'vehicle_id')
                                vehicle = f'car-{vehicle_id}'
                                party = False
                            else:
                                vehicle = f'car-{vehicle}'
                                uses_party = True
                                party = True
                        elif Mode.transit(mode):
                            uses_transit = True
                            vehicle = None
                        elif mode == Mode.WALK:
                            uses_walk = True
                            vehicle = f'walk-{agent.id}'
                        elif mode == Mode.BIKE:
                            uses_bike = True
                            vehicle = f'bike-{agent.id}'

                        # apn assingment
                        if act == Act.HOME:
                            apn = home_apn
                        elif maz in commerces:
                            apn = commerces[maz][randint(0, 
                                len(commerces[maz]) - 1)]
                        elif maz in residences:
                            apn = residences[maz][randint(0, 
                                len(residences[maz]) - 1)]
                        elif maz in default:
                            apn = default[maz]
                        else:
                            raise ValueError

                        if idx == 0:
                            activities.append((
                                agent.id,
                                idx,
                                home_maz,
                                home_apn,
                                int(Act.HOME),
                                simulation_start,
                                depart,
                                depart - simulation_start))

                        routes.append((
                            agent.id,
                            idx,
                            mode,
                            vehicle,
                            int(party),
                            depart,
                            arrive,
                            arrive - depart ))

                        activities.append((
                            agent.id,
                            idx + 1,
                            maz,
                            apn,
                            act,
                            arrive,
                            arrive + duration,
                            duration    ))

                        count += 1
                        if count == n:
                            log.info(f'Parsing trip {count}.')
                            n <<= 1

                    agents.append((
                        agent.id,
                        household.id,
                        Agent.get(trip, 'household_idx'),
                        int(uses_vehicle),
                        int(uses_walk),
                        int(uses_bike),
                        int(uses_transit),
                        int(uses_party),
                        2*len(agent.trips) + 1 ))

                households.append((
                    household.id,
                    len(household.agents),
                    len(household.parties)  ))
            
            log.debug(f'Writing parsed and cleaned plans to database.')
            self.database.write_households(households)
            self.database.write_agents(agents)
            self.database.write_activities(activities)
            self.database.write_routes(routes)


    def create_idxs(self, config):
        if config['run']['create_idxs']:
            log.info(f'Creating all indexes in database {self.database.db}.')
            for tbl in self.database.tables:
                self.database.create_all_idxs(tbl)


    def create_tables(self, *tables, force=False):
        if not force:
            exists = self.database.table_exists(*tables)
            if len(exists):
                exists = '", "'.join(exists)
                log.warn(f'Table{"s" if len(exists) > 1 else ""} "{exists}" '
                    f'already exist in database "{self.database.db}".')
                if input('Drop and continue? [Y/n] ').lower() not in ('y', 'yes'):
                    log.error('User chose to terminate process.')
                    raise RuntimeError
        for table in tables:
            self.database.create_table(table)
