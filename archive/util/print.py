
import math
import os
import re
import time

from datetime import datetime
from getpass import getpass

class PrintUtil:
    persist_str = ''
    persist_rows = 0
    logfile = None
    silent = False
    FRMTS = {
        'bold': 1,
        'faint': 2,
        'italic': 3,
        'underline': 4,
        'strikethrough': 9
    }

    @classmethod
    def silence(self):
        self.silent = True

    @classmethod
    def unsilence(self):
        self.silence = False

    @classmethod
    def log(self, filename):
        self.logfile = open(filename, 'w')

    @classmethod
    def render_width(self, string):
        # https://en.wikipedia.org/wiki/ANSI_escape_code
        return len(re.sub('\\x1b\[[0-9]*m', '', string))

    @classmethod
    def render_rows(self, string):
        rows, cols = os.popen('stty size', 'r').read().split()
        rows = int(rows)
        cols = int(cols)
        return sum(self.render_width(line) // cols + 1 for line 
            in string.split('\n'))

    @classmethod
    def table(self, tbl, align='l', pad=1, border=False, wrap=False, hrule=None):
        if align in ('r', 'l'):
            aligns = [align] * len(tbl[0])
        elif type(align) in (list, tuple) and all([a in ('r', 'l') for a in align]):
            aligns = align 
        else:
            return ''
        if type(pad) is int:
            pads = [pad] * len(tbl[0])
        elif type(pad) in (list, tuple) and all([type(p) is int for p in pad]):
            pads = pad
        else:
            return ''
        tbl = [[str(cell) for cell in row] for row in tbl]
        widths = [max([self.render_width(cell) for cell in col]) 
            for col in list(map(list, zip(*tbl)))]
        if border:
            if hrule is None:
                hrules = [0]*(len(tbl))
            elif (type(hrule) in (list, tuple) 
                    and all([type(h) is int for h in hrules])):
                hrules = [1 if i in hrule else 0 for i in range(len(tbl)-1)] + [0]
            top = '+' + '+'.join('-'*(w+p*2) for w, p in zip(widths, pads)) + '+'
            return (top + '\n' +
                '\n'.join('|' + '|'.join([' '*p + cell.ljust(w) + ' '*p 
                if a == 'l' else ' '*p + cell.rjust(w) + ' '*p
                for cell, w, a, p in zip(row, widths, aligns, pads)]) + 
                (f'|\n{top}' if hrule else '|')
                for row, hrule in zip(tbl, hrules)) + '\n' + top)
        else:
            return '\n'.join(''.join(cell.ljust(w) + ' '*p
                if a == 'l' else cell.rjust(w) + ' '*p
                for cell, w, a, p in zip(row, widths, aligns, pads)) 
                for row in tbl)
    
    @classmethod
    def time(self, string):
        date = datetime.now()
        return ('[' + date.strftime('%H:%M:%S:') + 
            str(date.microsecond // 1000).zfill(3) +
            '] ' + string)

    @classmethod
    def format(self, string, *frmts):
        # https://en.wikipedia.org/wiki/ANSI_escape_code
        codes = tuple(self.FRMTS[frmt] for frmt in frmts if frmt in self.FRMTS)
        return ('\x1b[%sm'*len(codes) % codes) + string + '\x1b[0m'        
    
    @classmethod
    def progress(self, string, prog):
        prog = min(1, max(0, prog))
        perc = 100 * prog
        return ( string + ' [' + 
                '=' * int(perc // 5) + 
                '_' * int(20 - perc // 5) + 
                '] ' + str(round(perc, 1)) + '%')

    @classmethod
    def clear(self, rows=None):
        if rows is None:
            rows, cols = os.popen('stty size', 'r').read().split()
            rows = int(rows)
            cols = int(cols)
        print('\n'*(rows-1) + '\033[F'*rows, end='\r')

    @classmethod
    def delete(self, rows):
        pass

    @classmethod
    def push(self):
        persist = self.persist_str
        self.print('', persist=True, replace=True)
        self.print(persist)

    @classmethod
    def printer(self, *args, **kwargs):
        def custom_print(string, *margs, **mkwarg):
            self.print(string, *args, *margs, **kwargs, **mkwarg)
        return custom_print

    @classmethod
    def getpass(self, *args, **kwargs):
        return self.print(*args, **kwargs, prompt=True, password=True)

    @classmethod
    def input(self, *args, **kwargs):
        return self.print(*args, **kwargs, prompt=True)

    @classmethod
    def print(self, string='', persist=False, replace=False, time=False, 
            progress=None, frmt=None, inquiry=False, force=False, prompt=False,
            password=False):
        if self.silent and not force:
            return
        string = str(string)
        rows, cols = os.popen('stty size', 'r').read().split()
        rows = int(rows)
        cols = int(cols)
        print(('\033[F'+' '*cols)*self.persist_rows, end='\r')
        if time:
            string = self.time(string)
        if progress is not None:
            string = self.progress(string, progress)
        if self.logfile is not None and not persist:
            self.logfile.write(string + '\n')
            self.logfile.flush()
        if frmt is not None:
            if type(frmt) is list:
                string = self.format(string, *frmt)
            elif type(frmt) is str:
                string = self.format(string, frmt)
        if persist:
            if not replace and self.persist_rows:
                self.persist_str += '\n' + string
            else:
                self.persist_str = string
            self.persist_rows = self.render_rows(self.persist_str)
        elif prompt:
            if password:
                return getpass(string)
            else:
                return input(string)
        elif inquiry:
            response = input(string).lower()
            return response == 'y' or response == 'yes'
        else:
            print(string)
        if self.persist_rows:
            print(self.persist_str)
