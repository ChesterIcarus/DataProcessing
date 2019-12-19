
import os

class Configurator:
    def __init__(self, config):
        self.config = self.validate_config(config)

    @staticmethod
    def validate_config(config):
        # TODO Config input validation

        return config
        

    def build_config(self):
        configfile = open(self.config['input']['config_file'], 'w')

        configfile.write('''<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">
            <config> ''')
        
        self.module_network(configfile)
        self.module_vehicles(configfile)
        self.module_plans(configfile)
        self.module_transit(configfile)
        self.module_transit_router(configfile)
        self.module_controler(configfile)
        self.module_global(configfile)
        self.module_jdeqsim(configfile)
        self.module_strategy(configfile)
        self.module_plancalcscore(configfile)
        self.module_planscalcroute(configfile)
        self.module_qsim(configfile)
        self.module_vspexperimental(configfile)

        configfile.write('</config>')
        configfile.close()
        

    def module_vehicles(self, configfile):
        configfile.write('<module name="vehicles">')

        configfile.write('<param name="vehiclesFile" value="%s" />' %
            self.config['input']['vehicles_file'])

        configfile.write('</module>')


    def module_global(self, configfile):
        configfile.write('<module name="global">')
        
        configfile.write('''
            <param name="coordinateSystem" value="EPSG:2223" />
            <param name="insistingOnDeprecatedConfigVersion" value="true" />
            <param name="numberOfThreads" value="%s" />
            <param name="randomSeed" value="4711" /> ''' %
            self.config['simulation']['threads'])
        
        configfile.write('</module>')


    def module_jdeqsim(self, configfile):
        configfile.write('<module name="JDEQSim">')

        configfile.write('''
            <param name="carSize" value="7.5" />
            <param name="endTime" value="undefined" />
            <param name="flowCapacityFactor" value="1.0" />
            <param name="gapTravelSpeed" value="15.0" />
            <param name="minimumInFlowCapacity" value="1800.0" />
            <param name="squeezeTime" value="1800.0" />
            <param name="storageCapacityFactor" value="1.0" /> ''')

        configfile.write('</module>')


    def module_controler(self, configfile):
        configfile.write('<module name="controler">')

        configfile.write('<param name="outputDirectory" value="%s" />' %
            self.config['output']['output_dir'])
        configfile.write('<param name="firstIteration" value="0" />')
        configfile.write('<param name="lastIteration" value="%s" />' %
            (self.config['output']['iterations'] - 1))
        configfile.write('<param name="writeEventsInterval" value="%s" />' %
            self.config['output']['save_events_it'])
        configfile.write('<param name="writePlansInterval" value="%s" />' %
            self.config['output']['save_plans_it'])

        configfile.write('</module>')


    def module_network(self, configfile):
        configfile.write('<module name="network">')

        configfile.write('<param name="inputNetworkFile" value="%s" />' %
            self.config['input']['network_file'])

        configfile.write('</module>')


    def module_plans(self, configfile):
        configfile.write('<module name="plans">')

        configfile.write('<param name="inputPlansFile" value="%s" />' %
            self.config['input']['plans_file'])

        configfile.write('</module>')


    def module_qsim(self, configfile):
        configfile.write('<module name="qsim">')

        configfile.write('''
            <param name="endTime" value="31:00:00" />
            <param name="flowCapacityFactor" value="1.0" />
            <param name="insertingWaitingVehiclesBeforeDrivingVehicles" value="true" />
            <param name="isRestrictingSeepage" value="true" />
            <param name="isSeepModeStorageFree" value="false" />
            <param name="linkDynamics" value="PassingQ" />
            <param name="linkWidth" value="30.0" />
            <param name="nodeOffset" value="0.0" />
            <param name="numberOfThreads" value="20" />
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
            <param name="useLanes" value="true" />
            <param name="usingFastCapacityUpdate" value="true" />
            <param name="usingThreadpool" value="true" /> ''')

        if self.config['simulation']['init'] == True:
            configfile.write('''
                <param name="usePersonIdForMissingVehicleId" value="true" />
                <param name="vehiclesSource" value="modeVehicleTypesFromVehiclesData" />
                <param name="vehicleBehavior" value="teleport" /> ''')
        else:
            configfile.write('''
                <param name="usePersonIdForMissingVehicleId" value="false" />
                <param name="vehiclesSource" value="fromVehiclesData" />
                <param name="vehicleBehavior" value="wait" /> ''')

        configfile.write('</module>')

    
    def module_strategy(self, configfile):
        configfile.write('<module name="strategy">')

        configfile.write('''
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
            </parameterset> ''')
        
        configfile.write('</module>')


    def module_transit(self, configfile):
        configfile.write('<module name="transit">')

        configfile.write('<param name="useTransit" value="true" />')
        configfile.write('<param name="transitModes" value="pt" />')
        configfile.write('<param name="transitScheduleFile" value="%s" />' %
            self.config['input']['transit_schedule_file'])
        configfile.write('<param name="vehiclesFile" value="%s" />' %
            self.config['input']['transit_vehicles_file'])

        configfile.write('</module>')

    
    def module_transit_router(self, configfile):
        configfile.write('<module name="transitRouter">')

        configfile.write('''
            <param name="additionalTransferTime" value="0.0" />
            <param name="directWalkFactor" value="1.0" />
            <param name="extensionRadius" value="200.0" />
            <param name="maxBeelineWalkConnectionDistance" value="100.0" />
            <param name="searchRadius" value="1000.0" /> ''')

        configfile.write('</module>')


    def module_planscalcroute(self, configfile):
        configfile.write('<module name="planscalcroute">')

        configfile.write('<param name="networkModes" value="%s" />' %
            ', '.join(self.config['modes']['network']))

        teleport = '''
            <parameterset type="teleportedModeParameters" >
                <param name="beelineDistanceFactor" value="1.3" />
                <param name="mode" value="%s" />
                <param name="teleportedModeFreespeedFactor" value="null" />
                <param name="teleportedModeSpeed" value="%s" />
            </parameterset> '''

        modes = [('fakemode', 10)] + self.config['modes']['teleported']

        for mode in modes:
            configfile.write(teleport % tuple(mode))

        configfile.write('</module>')


    def module_plancalcscore(self, configfile):
        configfile.write('<module name="planCalcScore">')

        configfile.write('''
		    <param name="BrainExpBeta" value="2.0" />
		    <param name="PathSizeLogitBeta" value="1.0" />
		    <param name="fractionOfIterationsToStartScoreMSA" value="null" />
		    <param name="learningRate" value="1.0" />
		    <param name="usingOldScoringBelowZeroUtilityDuration" value="false" />
		    <param name="writeExperiencedPlans" value="false" /> ''')

        configfile.write('''
            <parameterset type="scoringParameters" >
                <param name="earlyDeparture" value="-0.0" />
                <param name="lateArrival" value="-18.0" />
                <param name="marginalUtilityOfMoney" value="1.0" />
                <param name="performing" value="6.0" />
                <param name="subpopulation" value="null" />
                <param name="utilityOfLineSwitch" value="-1.0" />
                <param name="waiting" value="-0.0" />
                <param name="waitingPt" value="-6.0" /> ''')

        activity_pattern = '''
            <parameterset type="activityParams">
                <param name="activityType" value="%s" />
                <param name="closingTime" value="undefined" />
                <param name="earliestEndTime" value="undefined" />
                <param name="latestStartTime" value="undefined" />
                <param name="minimalDuration" value="undefined" />
                <param name="openingTime" value="undefined" />
                <param name="priority" value="1.0" />
                <param name="scoringThisActivityAtAll" value="%s" />
                <param name="typicalDuration" value="12:00:00" />
                <param name="typicalDurationScoreComputation" value="relative" />
            </parameterset> '''

        acts = ['default', 'other interaction', 'pt interaction']
        acts.extend([f'{mode} interaction' for mode in self.config['modes']['network']])
        
        for act in acts:
            configfile.write(activity_pattern % (act, 'false'))

        acts = self.config['activities']
        for act in acts:
            configfile.write(activity_pattern % (act, 'true'))

        mode_pattern = '''
            <parameterset type="modeParams" >
				<param name="constant" value="0.0" />
				<param name="dailyMonetaryConstant" value="0.0" />
				<param name="dailyUtilityConstant" value="0.0" />
				<param name="marginalUtilityOfDistance_util_m" value="0.0" />
				<param name="marginalUtilityOfTraveling_util_hr" value="-6.0" />
				<param name="mode" value="%s" />
				<param name="monetaryDistanceRate" value="0.0" />
			</parameterset> '''

        modes = self.config['modes']['network']

        for mode in modes:
            configfile.write(mode_pattern % mode)

        configfile.write('''
            <parameterset type="modeParams">
                <param name="mode" value="pt"/>
            </parameterset> ''')

        configfile.write('</parameterset></module>')


    def module_vspexperimental(self, configfile):
        configfile.write('<module name="vspExperimental">')

        configfile.write('''
            <param name="isAbleToOverwritePtInteractionParams" value="false" />
            <param name="isGeneratingBoardingDeniedEvent" value="false" />
            <param name="isUsingOpportunityCostOfTimeForLocationChoice" value="true" />
            <param name="logitScaleParamForPlansRemoval" value="1.0" />
            <param name="vspDefaultsCheckingLevel" value="ignore" />
            <param name="writingOutputEvents" value="true" />
        ''')

        configfile.write('</module>')