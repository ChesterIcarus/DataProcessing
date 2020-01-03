
import dropbox
import readline
import shlex
import sys
import os

from datetime import datetime
from argparse import ArgumentParser
from collections import defaultdict

from icarus.util.print import PrintUtil as pr

class DropboxUtil:
    team = {}
    local_dir = '/'
    drop_dir = '/'
        
    @classmethod
    def connect(self, key):
        self.dbx = dropbox.Dropbox(key, timeout=30)

    @classmethod
    def shell(self, key=None):
        self.local_dir = os.getcwd()
        if key is not None:
            self.connect(key)
        if self.dbx is not None:
            while self.exec_command(self.read_command()):
                pass
        else:
            pr.print('not connected to dropbox API; shell request terminated')

    @classmethod
    def upload(self, local_path, dest_path):
        local_file = open(local_path, 'rb')
        file_size = os.path.getsize(local_path)

        CHUNK_SIZE = 4 * 1024 * 1024

        if file_size <= CHUNK_SIZE:
            self.dbx.files_upload(local_file.read(), dest_path)
        else:
            pr.print('building session')
            session = self.dbx.files_upload_session_start(local_file.read(CHUNK_SIZE))
            pr.print('creating cursor')
            cursor = dropbox.files.UploadSessionCursor(session_id=session.session_id, offset=local_file.tell())
            pr.print('building commit')
            commit = dropbox.files.CommitInfo(path=dest_path)
            pr.print('iterating')
            while local_file.tell() < file_size:
                if file_size - local_file.tell() <= CHUNK_SIZE:
                    self.dbx.files_upload_session_finish(local_file.read(CHUNK_SIZE), cursor, commit)
                else:
                    self.dbx.files_upload_session_append(local_file.read(CHUNK_SIZE), cursor.session_id, cursor.offset)
                    cursor.offset = local_file.tell()

    @classmethod
    def download(self, local_path, dest_path):
        self.dbx.files_download_to_file(local_path, dest_path)

    @classmethod
    def format_ls(self, data):
        output = []
        for entry in data:
            output.append((
                (self.decode_user(entry.sharing_info.modified_by)
                    if hasattr(entry.sharing_info, 'modified_by') else 'folder'),
                *(self.decode_size(entry.size) 
                    if hasattr(entry, 'size') else ('4096', '')),
                (self.decode_time(entry.server_modified)
                    if hasattr(entry, 'server_modified') else '-'),
                entry.name))
        align = ['l', 'r', 'l', 'r', 'l']
        pad = [2, 0, 2, 2, 2]
        return pr.table(output, align=align, pad=pad)

    @classmethod
    def format_lls(self, target):
        table = []
        with os.scandir(target) as dir_entries:
            for entry in dir_entries:
                stats = entry.stat()
                table.append((
                    stats.st_uid,
                    *self.decode_size(stats.st_size),
                    self.decode_time(datetime.fromtimestamp(stats.st_mtime)),
                    entry.name))
        align = ['l', 'r', 'l', 'r', 'l']
        pad = [2, 0, 2, 2, 2]
        return pr.table(table, align=align, pad=pad)

    @classmethod
    def decode_dir(self, dir1, dir2):
        str1 = dir1.split('/')
        str2 = dir2.split('/')
        if str2[0] == '':
            return '/'.join(str2)
        while len(str2) and str2[0] == '..':
            str2.pop(0)
            str1.pop(-1)
        while len(str2) and str2[0] == '.':
            str2.pop(0)
        while len(str1) > 1 and str1[-1] == '':
            str1.pop(-1)
        return '/'.join(str1 + str2)

    @classmethod
    def decode_user(self, user):
        if not hasattr(self.team, user):
            self.team[user] = self.dbx.users_get_account(user).name.given_name
        return self.team[user]

    @classmethod
    def decode_time(self, time):
        months = ('', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul',
            'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
        return (str(time.day).zfill(2) + ' ' + months[time.month] + ' ' +
            str(time.hour).zfill(2) + ':' + str(time.minute).zfill(2))

    @classmethod
    def decode_size(self, value):
        if value >= 10000000000:
            value /= 1000000000
            unit = 'GB'
        elif value >= 10000000:
            value /= 1000000
            unit = 'MB'
        elif value >= 10000:
            value /= 1000
            unit = 'KB'
        else:
            unit = ''
        return str(int(value)), unit        

    @classmethod
    def parse_command(self, string):
        args = string.split(' ')
        args = [arg for arg in args if arg != '']
        cmd = args[0] if len(args) else ''
        return cmd, args[1:]

    @classmethod
    def read_command(self):
        return input('dropbox> ')

    @classmethod
    def exec_command(self, cmd):
        args = shlex.split(cmd)
        cmd = args.pop(0)
        if cmd == 'exit':
            pr.print('goodbye')
            return False
        elif cmd == 'help':
            pr.print(pr.table((
                ('cd', 'changes dropbox directory to specified directory'),
                ('dir', 'displays working directories'),
                ('exit', 'exits the dropbox API shell'),
                ('help', 'lists all valid commands and their usage'),
                ('get', 'downloads file from dropbox to local filesystem'),
                ('lcd', 'changes local directory to specified directory'),                
                ('lls', 'lists all the files and folders in working local directory'),
                ('ls', 'lists all the files and folders in working dropbox directory'),
                ('put', 'uploads file from local filesystem to dropbox'))))
        elif cmd == 'ls':
            if len(args) < 2:
                try:
                    target = (self.drop_dir if len(args) == 0
                        else self.decode_dir(self.drop_dir, args[0]))
                    pr.print(target)
                    files = self.dbx.files_list_folder(target if target != '/' 
                        else '').entries
                    pr.print(self.format_ls(files))
                except Exception:
                    pr.print('invalid target directory')
            else:
                pr.print(f'command "ls" expected zero or one arguments but got {len(args)}')
        elif cmd == 'lls':
            if len(args) < 2:
                target = (self.local_dir if len(args) == 0
                    else self.decode_dir(self.local_dir, args[0]))
                if os.path.isdir(target):
                    pr.print(target)
                    pr.print(self.format_lls(target))
                else:
                    pr.print('invalid target directory')
            else:
                pr.print(f'command "lls" expected zero or one arguments but got {len(args)}')
        elif cmd == 'cd':
            if len(args) == 1:
                try:
                    target = self.decode_dir(self.drop_dir, args[0])
                    if target != '/':
                        self.dbx.files_get_metadata(target)
                    self.drop_dir = target
                except Exception:
                    pr.print('invalid target directory')
            else:
                pr.print(f'command "cd" expected exactly one argument but got {len(args)}')
        elif cmd == 'lcd':
            if len(args) == 1:
                target = self.decode_dir(self.local_dir, args[0])
                if os.path.isdir(target):
                    self.local_dir = target
                else:
                    pr.print('invalid target directory')
            else:
                pr.print(f'command "lcd" expected exactly one argument but got {len(args)}')
        elif cmd == 'dir':
            pr.print(f'drop:  {self.drop_dir}')
            pr.print(f'local: {self.local_dir}')
        elif cmd == 'put':
            if len(args) == 2:
                if os.path.isfile(args[0]):
                    try:
                        local = self.decode_dir(self.local_dir, args[0])
                        drop = self.decode_dir(self.drop_dir, args[1])
                        pr.print('uploading file to dropbox')
                        self.upload(local, drop)
                    except Exception as err:
                        pr.print('invalid dropbox file path')
                        raise(err)
                else:
                    pr.print('invalid local file path')
            else:
                pr.print(f'command "put" expected exactly two arguments but got {len(args)}')
        elif cmd == 'get':
            if len(args) == 2:
                if os.path.isdir('/'.join(args[0].split('/')[:-1])):
                    try:
                        local = self.decode_dir(self.local_dir, args[0])
                        drop = self.decode_dir(self.drop_dir, args[1])
                        pr.print('downloading file from dropbox')
                        self.download(local, drop)
                    except Exception:
                        pr.print('invalid dropbox file path')
                else:
                    pr.print('invalid local directory')
            else:
                pr.print(f'command "get" expected exactly two arguments but got {len(args)}')
        else:
            pr.print('invalid command; type "help" for list of valid commands')
        return True

if __name__ == '__main__':
    argparser = ArgumentParser(prog='DropboxShell',
        description='Creates a bash interface for using a Dropbox API.')
    argparser.add_argument('--key', type=str, dest='key', default=None, required=True,
        help=('Specify a Dropbox API key to connect to an account.'))
    args = argparser.parse_args()

    DropboxUtil.connect(args.key)
    DropboxUtil.shell()
