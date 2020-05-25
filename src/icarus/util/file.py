
import gzip
import os
import sys
import tempfile
import subprocess


def multiopen(filepath, mode='rt', **kwargs):
    if os.path.splitext(filepath)[1] == '.gz':
        data = gzip.open(filepath, mode=mode, **kwargs)
    else:
        data = open(filepath, mode=mode, **kwargs)
    return data


def touch(filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w'):
        pass


def exists(filepath):
    return os.path.exists(filepath)


def readable(filepath):
    return os.access(filepath, os.R_OK)


def writable(filepath):
    write = False
    if exists(filepath):
        if os.path.isfile(filepath):
            write = os.access(filepath, os.W_OK)
    else:
        pdir = os.path.dirname(filepath)
        if not pdir: 
            pdir = '.'
        write = os.access(pdir, os.W_OK)
    return write


def format_xml(source, target=None):
    if target is None:
        targetfile = tempfile.NamedTemporaryFile(suffix='xml', delete=False)
        target = targetfile.name
        targetfile.close()
        subprocess.run(f'xmllint --format {source} > {target}',
            shell=True, check=True)
        subprocess.run(('mv', target, source), shell=False, check=True)
    else:
        subprocess.run(f'xmllint --format {source} > {target}', 
            shell=True, check=True)


def resource(self, package, resource, error=False):
    res = None
    try:
        module = os.path.dirname(sys.modules[package].__file__)
        res = os.path.join(module, resource)
    except Exception:
        if error:
            raise FileNotFoundError
    return res
