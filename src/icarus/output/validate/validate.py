
import logging as log

from icarus.util.config import ConfigUtil

class OutputValidation:
    def __init__(self, database):
        self.database = None
        

    @classmethod
    def validate_config(self, configpath, specspath):
        config = ConfigUtil.load_config(configpath)
        specs = ConfigUtil.load_specs(specspath)
        config = ConfigUtil.verify_config(specs, config)

        return config


    def run(self, config):
        charts = config['charts']

        if charts['']


    