from os import scandir, path, remove
from datetime import datetime
from hashlib import sha256


class ErrorFile(Exception):
    pass


def folder_size(folder_path):
    size = 0
    with scandir(folder_path) as files:
        for file in files:
            if file.is_file():
                size += file.stat().st_size
            elif file.is_dir():
                size += folder_size(file.path)

    return size


def scan(folder_path):
    res = list()
    repeats = dict()
    sizes = dict()
    if not path.isdir(folder_path):
        raise ErrorFile('Указан неправильный путь до папки')
    sum_size = 0

    with scandir(folder_path) as files:
        for file in files:
            if file.is_file():
                inf = file.stat()
                m = inf.st_size
                sum_size += m
                res.append(
                    (file.path, m, datetime.fromtimestamp(inf.st_mtime).strftime('%d.%m.%Y %H:%M:%S'), 0))
                if m not in sizes:
                    sizes[m] = list()
                sizes[m].append(file.path)
            elif file.is_dir():
                m = folder_size(file.path)
                sum_size += m
                res.append((file.path, m,
                            datetime.fromtimestamp(file.stat().st_mtime).strftime('%d.%m.%Y %H:%M:%S'), 1))

    if not res:
        raise ErrorFile('Указанная папка пуста')

    for files in sizes.values():
        if len(files) < 2:
            continue

        for file_path in files:
            file_hash = sha256()
            with open(file_path, 'rb') as f:
                while chunk := f.read(1024 * 1024):
                    file_hash.update(chunk)
            file_hash = file_hash.hexdigest()
            if file_hash not in repeats:
                repeats[file_hash] = list()
            repeats[file_hash].append(file_path)

    repeats = [files for files in repeats.values() if len(files) > 1]

    return res, repeats, ((path.normpath(folder_path), sum_size,
                datetime.fromtimestamp(path.getmtime(folder_path)).strftime('%d.%m.%Y %H:%M:%S'), 1))


def delete_repeats(repeats):
    for i in repeats:
        for j in i[1:]:
            remove(j)


if __name__ == '__main__':
    res, repeats, main = scan(r'C:\Users\MAXIM\Desktop\assets')
    print(res)
    print(repeats)
    print(main)
