import sqlite3
from pathlib import Path


def save_result(file_path, res, repeats, main):
    groups = {}
    for number, group in enumerate(repeats, 1):
        for file in group:
            groups[file[1]] = number
    connection = sqlite3.connect(file_path)
    try:
        with connection:
            connection.execute('''
                CREATE TABLE IF NOT EXISTS scan_info (
                    id INTEGER PRIMARY KEY,
                    folder_path TEXT,
                    total_size INTEGER,
                    modified TEXT
                )
            ''')
            connection.execute('''
                CREATE TABLE IF NOT EXISTS scan_files (
                    position INTEGER PRIMARY KEY,
                    file_path TEXT,
                    size INTEGER,
                    modified TEXT,
                    group_num INTEGER
                )
            ''')
            connection.execute('DELETE FROM scan_files')
            connection.execute('DELETE FROM scan_info')
            folder_data = {
                'id': 1,
                'folder_path': main[0],
                'total_size': sum(file[1] for file in res if file[1] >= 0),
                'modified': main[2]
            }
            connection.execute('''
                INSERT INTO scan_info (
                    id,
                    folder_path,
                    total_size,
                    modified
                )
                VALUES (
                    :id,
                    :folder_path,
                    :total_size,
                    :modified
                )
            ''', folder_data)
            rows = []
            for i, file in enumerate(res):
                file_data = {
                    'position': i,
                    'file_path': file[0],
                    'size': file[1],
                    'modified': file[2],
                    'group_num': groups.get(i, 0)
                }
                rows.append(file_data)
            connection.executemany('''
                INSERT INTO scan_files (
                    position,
                    file_path,
                    size,
                    modified,
                    group_num
                )
                VALUES (
                    :position,
                    :file_path,
                    :size,
                    :modified,
                    :group_num
                )
            ''', rows)

    finally:
        connection.close()


def load_result(file_path):
    uri = Path(file_path).resolve().as_uri() + '?mode=ro'
    connection = sqlite3.connect(uri, uri=True)
    try:
        main = connection.execute('''
            SELECT folder_path, total_size, modified
            FROM scan_info
            WHERE id = :id
        ''', {'id': 1}).fetchone()
        rows = connection.execute('''
            SELECT position, file_path, size, modified, group_num
            FROM scan_files
            ORDER BY position
        ''').fetchall()

    finally:
        connection.close()
    if main is None or not rows:
        raise ValueError('В базе нет сохранённого результата')

    res = []
    groups = {}
    for position, file_path, size, modified, group_num in rows:
        res.append((file_path, size, modified))
        if group_num:
            if group_num not in groups:
                groups[group_num] = []
            groups[group_num].append((file_path, position))

    repeats = [groups[number] for number in sorted(groups)]
    return res, repeats, main
