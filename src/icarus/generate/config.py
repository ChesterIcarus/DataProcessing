
import os
import logging as log

from argparse import ArgumentParser, SUPPRESS

from icarus.util.file import format_xml
from icarus.util.config import ConfigUtil


def ready():
    return True


def complete(folder):
    complete = False
    filepath = os.path.abspath(os.path.join(folder, 'input/config.xml'))
    if os.path.exists(filepath):
        log.warn(f'Config file {filepath} already exists.')
        complete = True
    return complete


def generate(folder, config):
    outfile = open(os.path.join(folder, 'input/config.xml'), 'w')

    header = '''
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">
        <config>
    '''

    outfile.write(header.strip())

    module_network(outfile)
    module_vehicles(outfile)
    module_plans(outfile)
    module_transit(outfile, config)
    module_transit_router(outfile)
    module_controler(outfile, config)
    module_global(outfile, config)
    module_jdeqsim(outfile)
    module_strategy(outfile)
    module_planscalcroute(outfile, config)
    module_plancalcscore(outfile, config)
    module_qsim(outfile, config)
    module_vspexperimental(outfile)

    outfile.write('</config>')
    outfile.close()

    format_xml('input/config.xml')
    

def module_network(outfile):
    outfile.write('<module name="network">')
    outfile.write('<param name="inputNetworkFile" value="network.xml.gz" />')
    outfile.write('</module>')


def module_vehicles(outfile):
    outfile.write('<module name="vehicles">')
    outfile.write('<param name="vehiclesFile" value="vehicles.xml.gz" />')
    outfile.write('</module>')


def module_plans(outfile):
    outfile.write('<module name="plans">')
    outfile.write('<param name="inputPlansFile" value="plans.xml.gz" />')
    outfile.write('</module>')


def module_transit(outfile, config):
    transit = 'true' if config['simulation']['transit'] else 'false' 
    outfile.write('<module name="transit">')
    outfile.write(f'''
        <param name="useTransit" value="{transit}" />
        <param name="transitModes" value="pt" />
        <param name="transitScheduleFile" value="transitSchedule.xml.gz" />
        <param name="vehiclesFile" value="transitVehicles.xml.gz" />
    ''')
    outfile.write('</module>')


def module_transit_router(outfile):
    outfile.write('<module name="transitRouter">')
    outfile.write('''
        <param name="additionalTransferTime" value="0.0" />
        <param name="directWalkFactor" value="1.0" />
        <param name="extensionRadius" value="200.0" />
        <param name="maxBeelineWalkConnectionDistance" value="100.0" />
        <param name="searchRadius" value="1000.0" />
    ''')
    outfile.write('</module>')


def module_controler(outfile, config):
    iterations = config['simulation']['iterations'] - 1
    outfile.write('<module name="controler">')
    outfile.write(f'''<param name="outputDirectory" value="output/" />
        <param name="firstIteration" value="0" />
        <param name="lastIteration" value="{iterations}" />
        <param name="writeEventsInterval" value="5" />
        <param name="writePlansInterval" value="1" />
    ''')
    outfile.write('</module>')


def module_global(outfile, config):
    threads = config['resources']['cores']
    outfile.write('<module name="global">')
    outfile.write(f'''
        <param name="coordinateSystem" value="EPSG:2223" />
        <param name="insistingOnDeprecatedConfigVersion" value="true" />
        <param name="numberOfThreads" value="{threads}" />
        <param name="randomSeed" value="4711" />
    ''')
    outfile.write('</module>')


def module_jdeqsim(outfile):
    outfile.write('<module name="JDEQSim">')
    outfile.write('''
        <param name="carSize" value="7.5" />
        <param name="endTime" value="undefined" />
        <param name="flowCapacityFactor" value="1.0" />
        <param name="gapTravelSpeed" value="15.0" />
        <param name="minimumInFlowCapacity" value="1800.0" />
        <param name="squeezeTime" value="1800.0" />
        <param name="storageCapacityFactor" value="1.0" />
    ''')
    outfile.write('</module>')


def module_strategy(outfile):
    outfile.write('<module name="strategy">')
    outfile.write('''
        <param name="ExternalExeConfigTemplate" value="null" />
        <param name="ExternalExeTimeOut" value="3600" />
        <param name="ExternalExeTmpFileRootDir" value="null" />
        <param name="fractionOfIterationsToDisableInnovation" value="Infinity" />
        <param name="maxAgentPlanMemorySize" value="5" />
        <param name="planSelectorForRemoval" value="WorstPlanSelector" />
        <parameterset type="strategysettings" >
            <param name="disableAfterIteration" value="-1" />
            <param name="executionPath" value="null" />
            <param name="strategyName" value="BestScore" />
            <param name="subpopulation" value="null" />
            <param name="weight" value="0.9" />
        </parameterset>
        <parameterset type="strategysettings" >
            <param name="disableAfterIteration" value="-1" />
            <param name="executionPath" value="null" />
            <param name="strategyName" value="ReRoute" />
            <param name="subpopulation" value="null" />
            <param name="weight" value="0.1" />
        </parameterset>
    ''')
    
    outfile.write('</module>')


def module_planscalcroute(outfile, config):
    modes = config['simulation']['modes']
    networked = ','.join(modes['networked'] + modes['routed'])
    outfile.write('<module name="planscalcroute">')
    outfile.write('<param name="clearDefaultTeleportedModeParams" value="true"/>')
    outfile.write(f'<param name="networkModes" value="{networked}" />')

    teleport = '''
        <parameterset type="teleportedModeParameters" >
            <param name="beelineDistanceFactor" value="%s" />
            <param name="mode" value="%s" />
            <param name="teleportedModeSpeed" value="%s" />
        </parameterset>
    '''

    for mode in modes['teleported']:
        outfile.write(teleport % (1.3, mode, 1.4))

    for mode in modes['virtualized']:
        outfile.write(teleport % (0.0, mode, 1.0))

    outfile.write('</module>')


def module_plancalcscore(outfile, config):
    outfile.write('<module name="planCalcScore">')
    outfile.write('''
        <param name="BrainExpBeta" value="1.0" />
        <param name="PathSizeLogitBeta" value="1.0" />
        <param name="fractionOfIterationsToStartScoreMSA" value="null" />
        <param name="learningRate" value="1.0" />
        <param name="usingOldScoringBelowZeroUtilityDuration" value="false" />
        <param name="writeExperiencedPlans" value="false" />
    ''')
    outfile.write('''
        <parameterset type="scoringParameters" >
            <param name="earlyDeparture" value="-0.0" />
            <param name="lateArrival" value="-18.0" />
            <param name="marginalUtilityOfMoney" value="1.0" />
            <param name="performing" value="6.0" />
            <param name="subpopulation" value="null" />
            <param name="utilityOfLineSwitch" value="-1.0" />
            <param name="waiting" value="-0.0" />
            <param name="waitingPt" value="-6.0" />
    ''')

    activity_pattern = '''
        <parameterset type="activityParams">
            <param name="activityType" value="%s" />
            <param name="scoringThisActivityAtAll" value="%s" />
            <param name="typicalDuration" value="%s" />
        </parameterset>
    '''

    modes = config['simulation']['modes']
    modes = set(modes['networked'] + modes['routed'] + modes['transit'] + 
        modes['teleported'] + modes['virtualized'])
    acts = set(f'{mode} interaction' for mode in modes)
    acts.add('other interaction')
    acts.add('fackeactivity')
    
    for act in acts:
        outfile.write(activity_pattern % (act, 'false', '00:00:01'))

    outfile.write(activity_pattern % ('default', 'true', '00:00:01'))

    acts = config['population']['activity_types']
    acts = set(acts)

    for act in acts:
        outfile.write(activity_pattern % (act, 'true', '12:00:00'))

    mode_pattern = '''
        <parameterset type="modeParams" >
            <param name="mode" value="%s" />
        </parameterset>
    '''

    modes.add('default')
    modes.add('fakemode')
    modes.add('netwalk')
    modes.add('pt')
    
    for mode in modes:
        outfile.write(mode_pattern % mode)

    outfile.write('</parameterset></module>')


def module_qsim(outfile, config):
    threads = config['resources']['cores']
    outfile.write('<module name="qsim">')
    outfile.write(f'''
        <param name="endTime" value="31:00:00" />
        <param name="flowCapacityFactor" value="1.0" />
        <param name="insertingWaitingVehiclesBeforeDrivingVehicles" value="false" />
        <param name="isRestrictingSeepage" value="true" />
        <param name="isSeepModeStorageFree" value="false" />
        <param name="linkDynamics" value="FIFO" />
        <param name="linkWidth" value="30.0" />
        <param name="nodeOffset" value="0.0" />
        <param name="mainMode" value="car,Bus,Tram" />
        <param name="removeStuckVehicles" value="false" />
        <param name="seepMode" value="bike" />
        <param name="simEndtimeInterpretation" value="null" />
        <param name="simStarttimeInterpretation" value="maxOfStarttimeAndEarliestActivityEnd" />
        <param name="snapshotStyle" value="equiDist" />
        <param name="snapshotperiod" value="00:00:00" />
        <param name="startTime" value="04:00:00" />
        <param name="storageCapacityFactor" value="1.0" />
        <param name="stuckTime" value="10.0" />
        <param name="timeStepSize" value="00:00:01" />
        <param name="trafficDynamics" value="queue" />
        <param name="useLanes" value="false" />
        <param name="usingFastCapacityUpdate" value="true" />
        <param name="usingThreadpool" value="true" />
        <param name="numberOfThreads" value="{threads}" />
        <param name="vehiclesSource" value="modeVehicleTypesFromVehiclesData" />
        <param name="vehicleBehavior" value="teleport" />
    ''')
    outfile.write('</module>')


def module_vspexperimental(outfile):
    outfile.write('<module name="vspExperimental">')
    outfile.write('''
        <param name="isAbleToOverwritePtInteractionParams" value="false" />
        <param name="isGeneratingBoardingDeniedEvent" value="false" />
        <param name="isUsingOpportunityCostOfTimeForLocationChoice" value="true" />
        <param name="logitScaleParamForPlansRemoval" value="1.0" />
        <param name="vspDefaultsCheckingLevel" value="ignore" />
        <param name="writingOutputEvents" value="true" />''')
    outfile.write('</module>')


def main():
    parser = ArgumentParser()
    parser.add_argument('--folder', type=str, dest='folder', default='.')
    parser.add_argument('--log', type=str, dest='log', default=None)
    parser.add_argument('--level', type=str, dest='level', default='info',
        choices=('notset', 'debug', 'info', 'warning', 'error', 'critical'))
    args = parser.parse_args()

    handlers = []
    handlers.append(log.StreamHandler())
    if args.log is not None:
        handlers.append(log.FileHandler(args.log, 'w'))
    log.basicConfig(
        format='%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s',
        level=getattr(log, args.level.upper()),
        handlers=handlers)

    path = lambda x: os.path.abspath(os.path.join(args.folder, x))
    home = path('')
    config = ConfigUtil.load_config(path('config.json'))

    log.info('Running config generation tool.')
    log.info(f'Loading run data from {home}.')

    if not ready():
        log.error('Dependent data not parsed or generated; see warnings for details.')
        exit(1)
    elif complete(args.folder):
        log.warning('Config already generated. Would you like to replace it? [Y/n]')
        if input().lower() not in ('y', 'yes', 'yeet'):
            log.info('User chose to keep existing config; exiting generation tool.')
            exit()

    try:
        log.info('Starting config generation.')
        generate(args.folder, config)
    except:
        log.exception('Critical error while generating config; '
            'terminating process and exiting.')
        exit(1)


if __name__ == '__main__':
    main()
