=========================
MATSim Simulation Results
=========================

owner:      Benjamin Brownlee
contact:    benjamin.brownlee1@gmail.com
run:        run_20_28_10
created:    02-28-2020
updated:    02-28-2020


Overview
--------

This documentation is a quick summary of the input and output files used in the
simulation of Maricopa county. This documentation is not wholistic, but is intended
to describe the nature of the data enough such that someone could begin to analyze
it a bit. Please let me know if anything is incorrect, missing or unclear.


Files
-----

[ABM FILES]

ABM/agents.csv.gz

Here are the fields from the ABM dataset that I chose to parse as part of our analysis;
I would recommend having the ABM documentation at hand if you are going to use this data.

    agent_id            int     unique id number to identify each agent
    household_id        int     unique id number to identify each household
    household_idx       int     unique id number to identify each agent within household
    serial              float   unique serial id for each agent
    type                int     aggregate agent type (see ABM docs)
    detailed_type       int     detailed agetn type (see ABM docs)
    age                 int     age
    gender              int     gender (1=male, 0=female)
    industry            int     work industry type (see ABM docs)
    school_grade        int     school grade (see ABM docs)
    education           int     education level (see ABM docs)
    work_type           int     work type (1=in-home, 2=out-of-home)
    work_taz            int     work taz
    work_maz            int     work maz
    school_type         int     school type (1=in-home, 2=out-of-home)
    school_taz          int     school taz
    school_maz          int     school maz
    campus_taz          int     campus taz
    campus_maz          int     campus maz
    activity_pattern    int     activity pattern (1=mandatory day, 2=non-mandatory 
                                    travel day, 3=staying at home)


ABM/trips.csv.gz

I don't see this as useful at the moment. Maybe I'll add it at a later time.


[SIMULATION FILES]

simulation


[INPUT FILES]

input/agents.csv.gz

A cleaned list of all the agents of the sampled agents from the ABM; this
was used to generate the input for the simulation. The schema is as follows:

    agent_id (int):         unique id number to identify each agent
    household_id (int):     unique id number to identify each household
    household_idx (int):    unique id number to identify each agent within household
    uses_vehicle (int):     if 1, this agent uses a vehicle at some point, otherwise 0
    uses_walk (int):        if 1, this agent walks at some point, otherwise 0
    uses_bike (int):        if 1, this agent uses a bike at some point, otherwise 0
    uses_transit (int):     if 1, this agent uses transit at some point, otherwise 0
    uses_party (int):       if 1, this agent shares a a route at some point, otherwise 0
    size (int):             the number of activites and routes that this
                            agent has in their plan

This table was used just to generate the input for the simulation, so if you
are looking for more detailed demographic information of the agents, look towards
the original ABM agent table.


input/activities.csv.gz

A cleaned list of all the activities of the sampled agents from the ABM; this
was used to generate the input for the simulation. The schema is as follows:

    agent_id (int):     unique id number to identify each agent
    agent_idx (int):    sequence order of the activities occurrence
    maz (int):          maricopa region code for activity location
    apn (string):       parcel identification code for activity location
    type (int):         activity type code (see ABM documentation)
    start (int):        start time of activity in secs from 00:00:00
    end (int):          end time of activity in secs from 00:00:00
    duration (int):     duration of activity in secs; equal to end - start

Note only the apn is information not directly extracted from the ABM dataset.
The ABM provided a artificial population described at a MAZ resolution, and we
randomized parcel assignment of activities inside the described MAZs.


input/routes.csv.gz

A cleaned list of all the routes of the sampled agents from the ABM; this
was used to generate the input for the simulation. The schema is as follows:

    agent_id (int):     unique id number to identify each agent
    agent_idx (int):    sequence order of the routes occurrence
    mode (int):         route mode code (see ABM documentation)
    vehicle (string):   vehicle id of the trip taken; all routes except transit
                        should have a vehicle defined
    shared (int):       if 1, the route was party or shared route, meaning
                        multiple agents shared a personal vehicle; otherwise 0
    start (int):        start time of route in secs from 00:00:00
    end (int):          end time of route in secs from 00:00:00
    duration (int):     duration of route in secs; equal to end - start

Note that in the ABM model, every agnet has a plan is constructed from a series
of activities with routes connecting them. So, each agent will have exactly one
more activity than route.


[OUTPUT FILES]

output/activities.csv.gz

A list of all the activites of the sampled agents as parsed from the simulation
output events file. The schema is as follows:

    agent_id (int):     unique id number to identify each agent
    agent_idx (int):    sequence order of the activities occurrence
    start (int):        start time of activity in secs from 00:00:00
    end (int):          end time of activity in secs from 00:00:00
    duration (int):     duration of activity in secs; equal to end - start
    type (string):      activity type description (see ABM documentation)
    exposure (float):   the exposure the agent experience at this activity
                        in degrees celcius seconds


output/routes.csv.gz

    agent_id (int):     unique id number to identify each agent
    agent_idx (int):    sequence order of the routes occurrence
    start (int):        start time of route in secs from 00:00:00
    end (int):          end time of route in secs from 00:00:00
    duration (int):     duration of route in secs; equal to end - start


output/agents.csv.gz

Note that if the simulation was struggling to accurately represent the input data,
there is a chance that a simulated agent became so behind schedule they do not 
completed their plan, or that they became stuck and had to be aborted from the
simulation. This will lead to the input plan size being larger than the output.


[RESULT FILES]

result/

This is a collection of files that were generated to analyze the output simulation
data wholistically to get an understanding of its accuracy. This includes mostly
charts, graphs, and other visuals.


[MATSIM FILES]

matsim/

The original matsim input and output files. They are not very easy to work with,
but they are here if you need them for some reason. Documentation for these types
of files can be found on the MATSim website and Github.