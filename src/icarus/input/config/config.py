
import os



class Config:
    def __init__(self, config):
        self.config = self.validate_config(config)

    @staticmethod
    def validate_config(config):
        pass
        

    def build_config(self):

        configfile = open(self.config['input']['config_file'], 'w')

        configfile.write('''
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">
            <config> ''')
        
        self.module_planclaclscore(configfile)

        configfile.write('</config>')
        configfile.close()

    def module_planclaclscore(self, configfile):

        configfile.write('<module name="planCalcScore" >')

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
                <param name="scoringThisActivityAtAll" value="false" />
                <param name="typicalDuration" value="12:00:00" />
                <param name="typicalDurationScoreComputation" value="relative" />
            </parameterset> '''

        acts = ['default', 'other interaction', 'pt interaction']
        acts.extend([f'{mode} interaction' for mode in self.config['modes']])
        acts.append(self.config['activities'])
        
        for act in acts:
            configfile.write(activity_pattern % act)

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

        modes = self.config['modes']

        for mode in modes:
            configfile.write(mode_pattern % mode)

        configfile.write('</parameterset></module>')

