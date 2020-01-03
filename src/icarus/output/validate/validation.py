
from icarus.output.validation.database import ValidationDatabase
from icarus.util.print import PrintUtil as pr

class OutputValidation:
    def __init__(self, database, encoding, config):
        self.database = ValidationDatabase(params=database, config=config)
        self.encoding = encoding

    def validate(self, fields, stats, silent=False):
        options = ('rmse', 'rmspe', 'me', 'mpe', 'correlation', 'coeff',
            'bias', 'variance', 'covariance')
        results = []
        results.append([' '] + [opt for opt in options if opt in stats])
        pr.print(f'Beginning MATSim output validation.', time=True)
        for tbl, col in fields:
            pr.print(f'Analyzing field "{col}" from table "{tbl}".', time=True)
            result = [f'{tbl} {col}']
            for opt in options:
                if opt in stats:
                    result.append(getattr(self.database, opt)(tbl, col))
            results.append(result)
        pr.print(f'MATSim output validation complete.', time=True)
        pr.print(pr.table(results, hrule=0, border=True))