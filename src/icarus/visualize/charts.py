
import os
import logging as log
import seaborn as sns
import pandas as pd

from icarus.util.sqlite import SqliteUtil


class Charts:
    def __init__(self, database: SqliteUtil, folder: str):
        self.database = database
        self.folder = folder


    def get_activity_differentials(self, parameter, bounds, sample, types):
        conds = []
        if types is not None:
            if len(types) > 1:
                conds.append(f'output_activities.type IN {tuple(types)}')
            else:
                conds.append(f'output_activities.type = {types[0]}')
        if bounds is not None:
            conds.append(f'activities.{parameter} >= {bounds[0]}')
            conds.append(f'output_activities.{parameter} >= {bounds[1]}')
            conds.append(f'activities.{parameter} <= {bounds[2]}')
            conds.append(f'output_activities.{parameter} <= {bounds[3]}')

        condition = 'WHERE ' + ' AND '.join(conds) if len(conds) else ''
        limit = f'LIMIT {sample}' if sample is not None else ''

        query = f'''
            SELECT 
                activities.{parameter},
                output_activities.{parameter}
            FROM activities
            INNER JOIN output_activities
            USING(agent_id, agent_idx)
            {condition}
            ORDER BY RANDOM()
            {limit}; '''

        self.database.cursor.execute(query)

        return self.database.cursor.fetchall() 

    
    def get_leg_differentials(self, parameter, bounds, sample, modes):
        conds = []
        if modes is not None:
            if len(modes) > 1:
                conds.append(f'output_legs.mode IN {tuple(modes)}')
            else:
                conds.append(f'output_legs.mode = "{modes[0]}"')
        if bounds is not None:
            conds.append(f'legs.{parameter} >= {bounds[0]}')
            conds.append(f'output_legs.{parameter} >= {bounds[1]}')
            conds.append(f'legs.{parameter} <= {bounds[2]}')
            conds.append(f'output_legs.{parameter} <= {bounds[3]}')

        condition = 'WHERE ' + ' AND '.join(conds) if len(conds) else ''
        limit = f'LIMIT {sample}' if sample is not None else ''

        query = f'''
            SELECT 
                legs.{parameter},
                output_legs.{parameter}
            FROM legs
            INNER JOIN output_legs
            USING(agent_id, agent_idx)
            {condition}
            ORDER BY RANDOM()
            {limit};    '''        
        
        self.database.cursor.execute(query)

        return self.database.cursor.fetchall() 


    def plot_activity_dist(self, parameter, bounds, sample, types, axes, title):
        values = self.get_activity_differentials(parameter, bounds, sample, types)
        data = pd.DataFrame(list(values), columns=axes)
        high = max(*data[axes[0]], *data[axes[1]])
        low = min(*data[axes[0]], *data[axes[1]])
        plot = sns.jointplot(
            x=data[axes[0]], 
            y=data[axes[1]], kind='hex').fig
        plot.axes[2].plot([low, low], [high, high], linewidth=1.5)
        plot.subplots_adjust(top=0.95)
        plot.suptitle(title)

        return plot


    def plot_leg_dist(self, parameter, bounds, sample, modes, axes, title):
        values = self.get_leg_differentials(parameter, bounds, sample, modes)
        data = pd.DataFrame(list(values), columns=axes)
        high = max(*data[axes[0]], *data[axes[1]])
        low = min(*data[axes[0]], *data[axes[1]])
        plot = sns.jointplot(
            x=data[axes[0]], 
            y=data[axes[1]], kind='hex').fig
        plot.axes[2].plot([low, low], [high, high], linewidth=1.5)
        plot.subplots_adjust(top=0.95)
        plot.suptitle(title)

        return plot

    
    def plot_activity_diff(self, parameter, bounds, sample, types, axes, title):
        values = self.get_activity_differentials(parameter, None, sample, types)
        values = map(lambda x: x[1] - x[0], values)
        if bounds is not None:
            condition = lambda x: x >= bounds[0] and x <= bounds[1]
            values = filter(condition, values)
        data = pd.Series(values)
        plt_axes = sns.distplot(data)
        plt_axes.set_title(title)
        plt_axes.set_xlabel(axes[0])
        plt_axes.set_ylabel(axes[1])
        plot = plt_axes.get_figure()

        return plot

    
    def plot_leg_diff(self, parameter, bounds, sample, modes, axes, title):
        values = self.get_leg_differentials(parameter, None, sample, modes)
        values = map(lambda x: x[1] - x[0], values)
        if bounds is not None:
            condition = lambda x: x >= bounds[0] and x <= bounds[1]
            values = filter(condition, values)
        data = pd.Series(values)
        plt_axes = sns.distplot(data)
        plt_axes.set_title(title)
        plt_axes.set_xlabel(axes[0])
        plt_axes.set_ylabel(axes[1])
        plot = plt_axes.get_figure()

        return plot 

    
    def plot_chart(self, name, chart, error):
        try:
            plot = None
            path = lambda x: os.path.join(self.folder, x)

            if chart['type'] == 'activity_distribution':
                plot = self.plot_activity_dist(chart['parameter'], chart['bounds'],
                    chart['sample'], chart['types'], chart['axes'], chart['title'])
            elif chart['type'] == 'leg_distribution':
                plot = self.plot_leg_dist(chart['parameter'], chart['bounds'],
                    chart['sample'], chart['modes'], chart['axes'], chart['title'])
            elif chart['type'] == 'activity_differential':
                plot = self.plot_activity_diff(chart['parameter'], chart['bounds'],
                    chart['sample'], chart['types'], chart['axes'], chart['title'])
            elif chart['type'] == 'leg_differential':
                plot = self.plot_leg_diff(chart['parameter'], chart['bounds'],
                    chart['sample'], chart['modes'], chart['axes'], chart['title'])
            else:
                raise ValueError('Unexpected chart type.')

            plot.savefig(path(f'result/{name}.png'), bbox_inches='tight')
            plot.clf()

        except:
            if error:
                log.exception(f'Failed to build chart "{name}"'
                    '; terminating visualization.')
                exit()
            else:
                log.exception(f'Failed to build chart "{name}"'
                    '; continuing with visualization.')


    def chart(self, charts, error):
        for name, chart in charts.items():
            log.info(f'Creating chart "{name}".')
            self.plot_chart(name, chart, error)

