
import dropbox
import sys

class DropboxShell:
    team = {}
    local_dir = '~/'
    drop_dir = ''

    @staticmethod
    def connect(key):
        DropboxShell.dbx = dropbox.Dropbox(key)

    @staticmethod
    def format_ls(data):
        shell = DropboxShell
        output = []
        for entry in data:
            output.append([
                shell.decode_user(entry.sharing_info.modified_by),
                shell.decode_size(entry.size if hasattr(entry, 'size') else 4096),
                shell.decode_time(entry.server_modified),
            ])
        return '\n'.join('  '.join(v for v in f) for f in output)

    @staticmethod
    def decode_dir(dir1, dir2):
        str1 = dir1.split('/')
        str2 = dir2.split('/')
        if str2[0] == '':
            return '/'.join(str2)
        while str2[0] == '..':
            str2.pop(0)
            str1.pop(-1)
        while len(str1) > 1 and str1[-1] == '':
            str1.pop(-1)
        return '/'.join(str1 + str2)

    @staticmethod
    def decode_user(user):
        shell = DropboxShell
        if not hasattr(shell.team, user):
            shell.team[user] = shell.dbx.users_get_account(user).name.given_name
        return shell.team[user]

    @staticmethod
    def decode_time(time):
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'
            'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        return (str(time.day).rjust(2) + ' ' + months[time.month] +
            str(time.hour).rjust(3) + ':' + str(time.minute).zfill(2))

    @staticmethod
    def decode_size(value):
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
        return str(int(value)) + unit

    @staticmethod
    def read_command():
        shell = DropboxShell
        cmd = input('dropbox> ')
        comp = cmd.split(' ')
        if comp[0] == 'exit':
            print('goodbye')
            return
        elif comp[0] == 'help':
            print(
                'exit\texits the dropbox API shell\n'
                'help\tlists all valid commands and their usage\n'
                'ls\tlists all the files and folders in directory\n'
                'cd\tchanges directory to specified directory\n'
                'dir\tlist the current working directory')   
        elif comp[0] == 'ls':
            try:
                target = shell.drop_dir if len(comp) == 0 \
                    else shell.decode_dir(shell.drop_dir, comp[1])
                files = shell.dbx.files_list_folder(target).entries
                print(shell.format_ls(files))
            except Exception:
                print('invalid target directory')
        elif comp[0] == 'cd':
            try:
                target = shell.drop_dir + '/' + comp[1]
                shell.dbx.files_get_metadata(target)
                shell.drop_dir = target
            except Exception:
                print('invalid target directory')
        elif comp[0] == 'dir':
            print(f'drop: {DropboxShell.drop_dir}')
            print(f'local: {DropboxShell.local_dir}')
        elif comp[0] == 'put':
            pass
        elif comp[0] == 'get':
            pass
        else:
            print('invalid command; type "help" for list of valid commands')
        shell.read_command()

if __name__ == '__main__':
    DropboxShell.connect(sys.argv[1])
    DropboxShell.read_command()