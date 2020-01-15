
import json
import re
import os

import logging as log

from icarus.util.filesys import FilesysUtil


class ConfigUtil:
    '''static class used to verify config to specs for runner

    also includes some useful tools for handling config parameters
    '''
    types = {'str': str, 'int': int, 'bool': bool, 'dict': dict,
        'list': list, 'float': float, 'null': None}


    @classmethod
    def load_config(self, filepath):
        'load a config file; catches file and JSON errors'
        try:
            with open(filepath) as handle:
                return json.load(handle)
        except FileNotFoundError:
            log.exception(f'Config file "{filepath}" does not exist; '
                'terminating model run.')
            exit()
        except json.JSONDecodeError:
            log.exception(f'Config file "{filepath}" is not valid json; '
                'terminating model run.')
            exit()
        

    @classmethod
    def load_specs(self, filepath):
        'load a config file; catches file and JSON errors'
        try:
            with open(filepath) as handle:
                return json.load(handle)
        except FileNotFoundError:
            log.exception(f'Specs file "{filepath}" does not exist; '
                'terminating model run.')
            exit()
        except json.JSONDecodeError:
            log.exception(f'Specs file "{filepath}" is not valid json; '
                'terminating model run.')
            exit()


    @classmethod
    def verify_config(self, specs, config, name=''):
        '''recursively validates a a configuration dict againast a 
        specifications dict

        Parameters
        ----------
        specs: dict
            The dict representing a JSON specifications file.

        config: dict
            The dict representing a JSON configurations file; will be checked
            against the specifications file.

        name: str
            The name of the specification property; used in error handling. This
            is set recursively; the intial name is an empty string.

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
                log.warning(f'Config parameter "{path}" is not in model '
                    'specifications; it will not impact model run.')

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
                        log.error(f'Parameter "{attr}" is required.')
                        raise ValueError

                if spec['type'] == 'dict':
                    if type(param) == dict:
                        if 'min' in spec and spec['min'] > len(param):
                            log.error(f'Parameter "{path}" expected to have at least '
                                f'{spec["min"]} elements but only found {len(param)}.')
                            raise ValueError
                        if 'max' in spec and spec['max'] < len(param):
                            log.error(f'Parameter "{path}" expected to have at most '
                                f'{spec["max"]} elements but found {len(param)}.')
                            raise ValueError
                        if 'options' in spec and not all(k in spec['options'] 
                                for k in param.keys()):
                            valid = '","'.join(spec['options'])
                            invalid = '","'.join(k for k in param.keys() if 
                                k not in spec['options'])
                            log.error(f'Parameter "{path}" expected to only '
                                f'"{valid}" for keys but found "{invalid}".')
                            raise ValueError
                        if 'struct' in spec:
                            spec = {k: spec['struct'] for k in param.keys()}
                            config[attr] = self.verify_config(spec, param, name=path)
                    else:
                        log.error(f'Parameter "{path}" expected to be of type '
                            f'"dict" but found "{type(param).__name__}".')
                        raise TypeError
                elif spec['type'] == 'list':
                    if type(param) == list:
                        if 'min' in spec and spec['min'] > len(param):
                            log.error(f'Parameter "{path}" expected to have at least '
                                f'{spec["min"]} elements but only found {len(param)}.')
                            raise ValueError
                        if 'max' in spec and spec['max'] < len(param):
                            log.error(f'Parameter "{path}" expected to have at most '
                                f'{spec["max"]} elements but found {len(param)}.')
                            raise ValueError
                        if 'struct' in spec:
                            spec = {k: spec['struct'] for k in range(len(param))}
                            config[attr] = self.verify_config(spec,
                                dict(enumerate(param)), name=path).values()
                    else:
                        log.error(f'Parameter "{path}" expected to be of type '
                            f'"list" but found "{type(param).__name__}".')
                        raise TypeError
                else:
                    self.verify_param(path, spec, param)
            else:
                config[attr] = self.verify_config(spec, param, name=path)
        
        return config

    
    @classmethod
    def verify_param(self, name, spec, param):
        '''validates a single config parameter against a specification

        Parameters
        ----------
        name: str
            Name of the attribute being checked; used in error handling.

        spec: dict
            A dict containing the attributes of the parameter.

        param: int/float/str/bool
            The config parameter being validated.
        '''
        types = [self.types[t] for t in spec['type'].split(',')]

        if type(param) not in types:
            types = '", "'.join(spec['type'].split(','))
            log.error(f'Parameter "{name}" expected to be of type "'
                f'{types}" but found "{type(param).__name__}".')
            raise TypeError

        if ('options' in spec and len(spec['options']) 
                and param not in spec['options']):
            options = ', '.join([f'"{str(opt)}"' for opt in spec['options']])
            log.error(f'Parameter "{name}" expected to be {options} '
                f'but found "{param}".')
            raise ValueError

        if 'exceptions' in spec and param in spec['exceptions']:
            log.error(f'Parameter "{name}" cannot be "{param}".')
            raise ValueError

        if 'min' in spec and param < spec['min']:
            log.error(f'Parameter "{name}" expected to be greater than '
                f'{spec["min"]} but found {name}.')
            raise ValueError

        if 'max' in spec and param > spec['max']:
            log.error(f'Parameter "{name}" expected to be less than '
                f'{spec["max"]} but found {param}.')
            raise ValueError

        if 'regex' in spec and not re.search(spec['regex'], param):
            log.error(f'Parameter "{name}" expected to match pattern '
                f'{spec["regex"]} but found "{param}".')
            raise ValueError

        if 'file' in spec:
            if spec['file'] == 'exists' and not FilesysUtil.file_exists(param):
                log.error(f'Parameter "{name}" expected to be an existing file '
                    'but file could not be found.')
                raise ValueError
            elif spec['file'] == 'readable' and not FilesysUtil.file_readable(param):
                log.error(f'Parameter "{name}" expected to be an readable file '
                    'but file could not be read.')
                raise ValueError
            elif spec['file'] == 'writable' and not FilesysUtil.file_writable(param):
                log.error(f'Parameter "{name}" expected to be an writable file '
                    'but file could not be written to.')
                raise ValueError
