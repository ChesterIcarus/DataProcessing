
import logging as log
import seaborn as sns
import pandas as pd

from pprint import pprint

from icarus.output.validate.database import ValidationDatabaseUtil
from icarus.util.config import ConfigUtil

class OutputValidation:
    def __init__(self, database):
        self.database = ValidationDatabaseUtil(database)
        

    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath)
        # specs = ConfigUtil.load_specs(specspath)
        # config = ConfigUtil.verify_config(specs, config)

        return config


    def run(self, config):
        charts = config['charts']
        error = config['run']['continue']
        save = config['run']['result_dir']

        self.database.input_db = config['run']['input_db']
        self.database.output_db = config['run']['output_db']

        for name, chart in charts.items():
            if chart['run']:
                log.info(f'Building chart "{name}".')
                try:
                    plot = self.chart(chart)
                except KeyboardInterrupt as err:
                    raise err
                except EOFError as err:
                    raise err
                except Exception as err:
                    if error:
                        log.exception('Chart building failed, continuing to remaining charts.')
                        continue
                    else:
                        log.error('Chart building failed, terminating module run.')
                        raise err

                log.info(f'Saving chart to {save}/{chart["file"]}.')
                plot.savefig(f'{save}/{chart["file"]}')
                plot.clf()
            else:
                log.info(f'Skipping chart "{name}".')


    def chart(self, chart):
        plot = None

        if chart['type'] == 'activity_distributions':
            values = self.database.agent_act_diffs(chart['parameter'], 
                bounds=chart['bounds'], sample=chart['sample'], acts=chart['types'])
            data = pd.DataFrame(list(values), columns=chart['axes'])
            high = max(max(data[chart['axes'][0]]), max(data[chart['axes'][1]]))
            low = min(min(data[chart['axes'][0]]), min(data[chart['axes'][1]]))
            plot = sns.jointplot(x=data[chart['axes'][0]], 
                y=data[chart['axes'][1]], kind='hex').fig
            plot.axes[2].plot([low, low], [high, high], linewidth=1.5)
            plot.subplots_adjust(top=0.95)
            plot.suptitle(chart['title']) 

        elif chart['type'] == 'route_distributions':
            values = self.database.agent_route_diffs(chart['parameter'], 
                bounds=chart['bounds'], sample=chart['sample'], modes=chart['modes'])
            data = pd.DataFrame(list(values), columns=chart['axes'])
            high = max(max(data[chart['axes'][0]]), max(data[chart['axes'][1]]))
            low = min(min(data[chart['axes'][0]]), min(data[chart['axes'][1]]))
            plot = sns.jointplot(x=data[chart['axes'][0]], 
                y=data[chart['axes'][1]], kind='hex').fig
            plot.axes[2].plot([low, low], [high, high], linewidth=1.5)
            plot.subplots_adjust(top=0.95)
            plot.suptitle(chart['title']) 

        elif chart['type'] == 'route_differentials':
            values = self.database.agent_act_diffs(chart['parameter'], 
                sample=chart['sample'], acts=chart['types'])
            values = map(lambda x: x[1] - x[0], values)
            if chart['bounds'] is not None:
                values = filter(lambda x: (x >= chart['bounds'][0] 
                    and x <= chart['bounds'][1]), values)
            data = pd.Series(values)
            axes = sns.distplot(data)
            axes.set_title(chart['title'])
            axes.set_xlabel(chart['axes'][0])
            axes.set_ylabel(chart['axes'][1])
            plot = axes.get_figure()

        elif chart['type'] == 'activity_differentials':
            pass

        else:
            log.error(f'Chart type "{chart["type"]}" is not a valid option.')
            raise ValueError

        return plot

