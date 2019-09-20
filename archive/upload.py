import dropbox
import os

dbx = dropbox.Dropbox('H6qngz3zvcAAAAAAAAAAHO1J9mj1NfHBTJr0P1gY5uNDog3qP5M-twkKy0h2ekx2')

local_path = '/home/Shared/matsim/run2/input/config.xml'
dest_path = '/Icarus/Data/Benjamin Data Transfer/run2/input/config.xml'

local_file = open(local_path, 'rb')
file_size = os.path.getsize(local_path)

CHUNK_SIZE = 4 * 1024 * 1024

if file_size <= CHUNK_SIZE:
    dbx.files_upload(local_file.read(), dest_path)
else:
    session = dbx.files_upload_session_start(local_file.read(CHUNK_SIZE))
    cursor = dropbox.files.UploadSessionCursor(session_id=session.session_id, offset=local_file.tell())
    commit = dropbox.files.CommitInfo(path=dest_path)
    while local_file.tell() < file_size:
        if file_size - local_file.tell() <= CHUNK_SIZE:
            dbx.files_upload_session_finish(local_file.read(CHUNK_SIZE), cursor, commit)
        else:
            dbx.files_upload_session_append(local_file.read(CHUNK_SIZE), cursor.session_id, cursor.offset)
            cursor.offset = local_file.tell()