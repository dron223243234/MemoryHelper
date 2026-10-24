from os import scandir, path
from datetime import datetime
from hashlib import sha256 # сделать сравнение файлов


class ErrorFile(Exception):
    pass


def scan(folder_path):
    res = list()

    if not path.isdir(folder_path):
        raise ErrorFile('Указан неправильный путь до папки')

    sum_size = 0
    for file in scandir(folder_path):
        if file.is_file():
            inf = file.stat()
            m = inf.st_size
            sum_size += m
            res.append((file.name, round(m / 1024, 1),
                        datetime.fromtimestamp(inf.st_mtime).strftime('%d.%m.%Y %H:%M:%S')))

    res.append((folder_path.split('\\')[-1], round(sum_size / 1024, 1)))
    if res:
        return res
    raise ErrorFile('В указанной папке нет файлов')


if __name__ == '__main__':
    print(scan(r'C:\Users\MAXIM\Desktop\assets'))
