import dropbox
import os

dbx = dropbox.Dropbox('')

local_path = '/home/benjamin/Documents/HII-C/data/export/umls.tar.gz'
dest_path = '/HII-C/data/source/umls.tar.gz'

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