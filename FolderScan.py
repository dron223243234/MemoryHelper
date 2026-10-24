from os import scandir, path
from datetime import datetime
from hashlib import sha256


class ErrorFile(Exception):
    pass


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
                    (file.name, round(m / 1024, 1), datetime.fromtimestamp(inf.st_mtime).strftime('%d.%m.%Y %H:%M:%S')))

                if m not in sizes:
                    sizes[m] = list()
                sizes[m].append(file.path)

    if not res:
        raise ErrorFile('В указанной папке нет файлов')

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
    res.append((path.basename(path.normpath(folder_path)), round(sum_size / 1024, 1)))

    return res, repeats


if __name__ == '__main__':
    res, repeats = scan(r'C:\Users\MAXIM\Desktop\assets')
    print(res)
    print(repeats)
