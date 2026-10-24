from os import scandir, path
from datetime import datetime


class ErrorFile(Exception):
    pass


def scan(folder_path):
    res = list()

    if not path.isdir(folder_path):
        raise ErrorFile('Указан неправильный путь до папки')

    for file in scandir(folder_path):
        if file.is_file():
            inf = file.stat()
            res.append((file.name, round(inf.st_size / 1024, 1),
                        datetime.fromtimestamp(inf.st_mtime).strftime('%d.%m.%Y %H:%M:%S')))

    if res:
        return res
    raise ErrorFile('В указанной папке нет файлов')


if __name__ == '__main__':
    print(scan(r'C:\Users\MAXIM\Desktop\assets'))
