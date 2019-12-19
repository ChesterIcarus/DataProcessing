
import json
import re
import os
import subprocess
import tempfile

from icarus.util.error import ConfigError
from icarus.util.print import Printer as pr


class ConfigUtil:
    '''static class used to verify config to specs for runner

    also includes some useful tools for handling config parameters
    '''

    types = {'str': str, 'int': int, 'bool': bool, 'dict': dict,
        'list': list, 'float': float, 'null': None}

    @classmethod
    def format_xml(self, src, target=None, delete=False):
        if not self.file_readable(src):
            raise FileNotFoundError()
        if target is None:
            if not self.file_writable(src):
                raise FileNotFoundError()
            temp = self.file_temporary(suffix='xml', delete=False)
            subprocess.run(f'xmllint --format ')


    @classmethod
    def file_temporary(self, suffix=None, delete=True):
        'create new temporary file'
        return tempfile.NamedTemporaryFile(suffix=suffix, delete=delete)
        

    @classmethod
    def file_readable(self, filepath):
        'check that file can be read'
        return os.access(filepath, os.R_OK)


    @classmethod
    def file_exists(self, filepath):
        'check that file exists'
        return os.path.exists(filepath)
    

    @classmethod
    def file_writable(self, filepath):
        'check that file is writable'
        if self.file_exists(filepath):
            if os.path.isfile(filepath):
                return os.access(filepath, os.W_OK)
            else:
                return False 
        
        pdir = os.path.dirname(filepath)
        if not pdir: 
            pdir = '.'
        return os.access(pdir, os.W_OK)


    @classmethod
    def load_config(self, filepath):
        'load a config file; catches file and JSON errors'
        try:
            with open(filepath) as handle:
                return json.load(handle)
        except FileNotFoundError as err:
            pr.print(f'Config file "{filepath}" does not exist; '
                'terminating model run.', time=True)
            raise err
        except json.JSONDecodeError as err:
            pr.print(f'Config file "{filepath}" is not valid json; '
                'terminating model run.', time=True)
            raise err
        

    @classmethod
    def load_specs(self, filepath):
        'load a config file; catches file and JSON errors'
        try:
            with open(filepath) as handle:
                return json.load(handle)
        except FileNotFoundError as err:
            pr.print(f'Specs file "{filepath}" does not exist; '
                'terminating model run.', time=True)
            raise err
        except json.JSONDecodeError as err:
            pr.print(f'Specs file "{filepath}" is not valid json; '
                'terminating model run.', time=True)
            raise err


    @classmethod
    def verify_config(self, specs, config, name=''):
        '''recursively validates a specifications dict to a configuration dict

        Parameters
        ----------
        specs: dict
            The dict representing a JSON specifications file.

        config: dict
            The dict representing a JSON configurations file; will be checked
            against the specifications file.

        Returns
        -------
        config: dict
            A new dict representing the JSON configuration file with any missing
            default values added onto it.
        '''

        for attr in config.keys():
            if attr not in specs.keys():
                if type(attr) is int:
                    path = f'{name}[{attr}]' if name != '' else attr
                else:
                    path = f'{name}.{attr}' if name != '' else attr
                pr.print(f'Warning: config parameter "{path}" is not '
                    'in model specifications.', time=True)

        for attr, spec in specs.items():
            param = config[attr] if attr in config else None
            if type(attr) is int:
                path = f'{name}[{attr}]' if name != '' else attr
            else:
                path = f'{name}.{attr}' if name != '' else attr

            if type(spec) is not dict:
                config[attr] = spec
            elif 'type' in spec:
                if param is None:
                    if 'required' not in spec or not spec['required']:
                        config[attr] = spec['default'] if 'default' in spec else None
                        continue
                    else:
                        raise ConfigError(f'Parameter "{attr}" is required.')

                if spec['type'] == 'dict':
                    if type(param) == dict:
                        if 'min' in spec and spec['min'] > len(param):
                            raise ValueError(f'Parameter "{path}" expected to have at '
                                f'least {spec["min"]} elements but only found '
                                f'{len(param)}.')
                        if 'max' in spec and spec['max'] < len(param):
                            raise ValueError(f'Parameter "{path}" expected to have at '
                                f'most {spec["max"]} elements but found '
                                f'{len(param)}.')
                        if 'options' in spec and not all(k in spec['options'] 
                                for k in param.keys()):
                            valid = '","'.join(spec['options'])
                            invalid = '","'.join(k for k in param.keys() if 
                                k not in spec['options'])
                            raise ValueError(f'Parameter "{path}" expected to only '
                                f'"{valid}" for keys but found "{invalid}".')
                        if 'struct' in spec:
                            spec = {k: spec['struct'] for k in param.keys()}
                            config[attr] = self.verify_config(spec, param, name=path)
                    else:
                        raise TypeError(f'Parameter "{path}" expected to be of type '
                            f'"dict" but found "{type(param).__name__}".')
                elif spec['type'] == 'list':
                    if type(param) == list:
                        if 'min' in spec and spec['min'] > len(param):
                            raise ValueError(f'Parameter "{path}" expected to have at '
                                f'least {spec["min"]} elements but only found '
                                f'{len(param)}.')
                        if 'max' in spec and spec['max'] < len(param):
                            raise ValueError(f'Parameter "{path}" expected to have at '
                                f'most {spec["max"]} elements but found '
                                f'{len(param)}.')
                        if 'struct' in spec:
                            spec = {k: spec['struct'] for k in range(len(param))}
                            config[attr] = self.verify_config(spec,
                                dict(enumerate(param)), name=path).values()
                    else:
                        raise TypeError(f'Parameter "{path}" expected to be of type '
                            f'"list" but found "{type(param).__name__}".')
                else:
                    self.verify_param(path, spec, param)
            else:
                config[attr] = self.verify_config(spec, param, name=path)
        
        return config

    
    @classmethod
    def verify_param(self, name, spec, param):
        types = [self.types[t] for t in spec['type'].split(',')]

        if type(param) not in types:
            types = '", "'.join(spec['type'].split(','))
            raise TypeError(f'Parameter "{name}" expected to be of type "'
                f'{types}" but found "{type(param).__name__}".')

        if 'options' in spec and len(spec['options']) and param not in spec['options']:
            options = ', '.join([f'"{str(opt)}"' for opt in spec['options']])
            raise ValueError(f'Parameter "{name}" expected to be {options} '
                f'but found "{param}".')

        if 'exceptions' in spec and param in spec['exceptions']:
            raise ValueError(f'Parameter "{name}" cannot be "{param}".')

        if 'min' in spec and param < spec['min']:
            raise ValueError(f'Parameter "{name}" expected to be greater than '
                f'{spec["min"]} but found {name}.')

        if 'max' in spec and param > spec['max']:
            raise ValueError(f'Parameter "{name}" expected to be less than '
                f'{spec["max"]} but found {param}.')

        if 'regex' in spec and not re.search(spec['regex'], param):
            raise ValueError (f'Parameter "{name}" expected to match pattern '
                f'{spec["regex"]} but found "{param}".')

        # TODO complete error handling
        if 'file' in spec:
            if spec['file'] == 'exists' and not self.file_exists(param):
                raise ValueError()
            elif spec['file'] == 'readable' and not self.file_readable(param):
                raise ValueError()
            elif spec['file'] == 'writable' and not self.file_writable(param):
                raise ValueError()
