
import os
import tempfile
import subprocess

from icarus.util.print import Printer

class FilesysUtil:
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
        'check that file can be written to'
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
    def delete_file(self, filepath):
        'delete a file'
        os.remove(filepath)


    @classmethod
    def create_tempfile(self, suffix=None, delete=True):
        'create a temporary file'
        return tempfile.NamedTemporaryFile(suffix=suffix, delete=delete)


    @staticmethod
    def format_xml(self, source, target=None):
        'format an xml file'
        if target is None:
            targetfile = self.create_tempfile(suffix='xml', delete=False)
            target = targetfile.name
            targetfile.close()
            subprocess.run(f'xmllint --format {source} > {target}', shell=True)
            subprocess.run(('mv', target, source), shell=False)
            self.delete_file(target)
        else:
            subprocess.run(f'xmllint --format {source} > {target}', shell=True)
