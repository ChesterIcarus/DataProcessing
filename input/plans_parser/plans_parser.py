
import csv
import json
import os
import sys
from getpass import getpass
from random import randint
from collections import defaultdict

if __name__ == '__main__':
    sys.path.insert(1, os.path.join(sys.path[0], '../..'))

from input.plans_parser.plans_parser_db import PlansParserDatabaseHandle
from util.print_util import Printer as pr

class PlansParser:
    def __init__(self, database, encoding):
        self.database = PlansParserDatabaseHandle(database)
        self.encoding = encoding

    def parse_plans(self, bin_size=100000):
        pr.print('Beginning parsing ABM data into MATsim input plans.', time=True)
        pr.print('Fetching process metadata.', time=True)

        max_trip = self.database.count_trips()
        max_hhid = self.database.count_households()
        residences = self.database.fetch_res_parcels()
        rotate = defaultdict(int)
        commerces = self.database.fetch_com_parcels()
        hhids = range(bin_size, max_hhid, bin_size)
        last_hhid = 0

        pr.print(f'Iterating over {max_trip} trips and parsing plans.', time=True)
        pr.print('Input Plans Parsing Progress', persist=True, replace=True,
            frmt='bold', progress=0)

        activity_id = 0
        route_id = 0

        for hhid in hhids:
            pr.print(f'Fetching trips for households {last_hhid} to {hhid}'
                ' and parsing input plans.', time=True)
            trips = self.database.fetch_trips(last_hhid, hhid)
            activities = []
            routes = []
            plans = []
            sharing = False
            prev_trip = [-1]*10 + [0]*2
            count = 0

            for trip in trips:
                # trip is by a new agent and not first trip in iter
                if trip[3] != prev_trip[3] and prev_trip[0] >= 0:
                    activities.append((
                        activity_id,
                        prev_trip[3],
                        prev_trip[4],
                        home_apn,
                        prev_trip[7],
                        prev_trip[10],
                        86400))
                    activity_id += 1
                    count += 1
                    plans.append((
                        prev_trip[3],
                        prev_trip[1],
                        prev_trip[2],
                        count))
                    count = 0
                    sharing = False

                # trip is in new houshold
                if trip[1] != prev_trip[1]:
                    maz = trip[8]
                    if maz in residences:
                        home_apn = residences[maz][rotate[maz]]
                        rotate[maz] += 1
                        if rotate[maz] == len(residences[maz]):
                            rotate[maz] = 0
                    else:
                        home_apn = None
                    apn = home_apn
                    apns = {0: apn}
                # trip is already processed (shared)
                elif trip[2] in apns:
                    apn = apns[trip[2]]
                    sharing = True
                # trip isn't shared but previous trip was
                elif sharing:
                    if prev_trip[2] + 1 in apns:
                        apn = 0 if trip[6] == 0 else apns[prev_trip[2] + 1]
                    else:
                        apn = None
                    sharing = False
                # trip from home
                elif trip[6] == 0:
                    apn = home_apn
                    apns[trip[2]] =  apn
                # all other trips
                else:
                    if trip[8] in commerces:
                        maz = commerces[trip[8]]
                        apn = maz[randint(0, len(maz) - 1)]
                    elif trip[8] in residences:
                        maz = residences[trip[8]]
                        apn = maz[randint(0, len(maz) - 1)]
                    else:
                        apn = None
                    apns[trip[2]] = apn

                activities.append((
                    activity_id,
                    trip[3],
                    trip[4],
                    apn,
                    trip[7],
                    0 if trip[4] == 0 else prev_trip[11],
                    trip[10]))
                routes.append((
                    route_id,
                    trip[3],
                    trip[4],
                    trip[5],
                    trip[11] - trip[10]))
                activity_id += 1
                route_id += 1
                count += 2

                prev_trip = trip

            activities.append((
                activity_id,
                prev_trip[3],
                prev_trip[4],
                home_apn,
                prev_trip[7],
                prev_trip[10],
                86400))
            activity_id += 1
            count += 1
            plans.append((
                prev_trip[3],
                prev_trip[1],
                prev_trip[2],
                count))
            count = 0

            pr.print(f'Pushing plans for households {last_hhid} to {hhid} to'
                ' database.', time=True)

            self.database.write_activities(activities)
            self.database.write_routes(routes)
            self.database.write_plans(plans)       

            pr.print('Input Plans Parsing Progress', persist=True, replace=True,
                frmt='bold', progress=hhid/max_hhid)

            last_hhid = hhid

if __name__ == '__main__':
    if len(sys.argv) > 2:
        configpath = sys.argv[1]
    else:
        configpath = os.path.dirname(os.path.abspath(__file__)) + '/config.json'
    try:
        with open(configpath) as handle:
            params = json.load(handle)['WORKSTATION']
        database = params['database']
        encoding = params['encoding']
        database['password'] = getpass(
            f'Password for {database["user"]}@localhost: ')

        parser = PlansParser(database, encoding)

        if not params['resume']:
            for table in database['tables'].keys():
                parser.database.create_table(table)

        parser.parse_plans()


    except FileNotFoundError as err:
        print(f'Config file {configpath} not found.')
        quit()
    except json.JSONDecodeError as err:
        print(f'Config file {configpath} is not valid JSON.')
        quit()
    # except KeyError as err:
    #     print(f'Config file {configpath} is not valid config file.')
    #     quit()
    except Exception as err:
        raise(err)