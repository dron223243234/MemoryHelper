from os import scandir, path, remove
from datetime import datetime
from hashlib import sha256


class ErrorFile(Exception):  # todo сделать отдельный файл для ошибок
    pass


def folder_size(folder_path):
    size = 0
    with scandir(folder_path) as files:
        for file in files:
            try:
                if file.is_file():
                    with open(file.path, 'rb'):
                        pass
                    size += file.stat().st_size
                elif file.is_dir():
                    size += folder_size(file.path)

            except OSError:
                continue

    return size

def scan(folder_path):
    res = list()
    repeats = dict()
    sizes = dict()
    if not path.isdir(folder_path):
        raise ErrorFile('Указан неправильный путь до папки')
    try:
        with scandir(folder_path) as files:
            for file in files:
                try:
                    if file.is_file():
                        with open(file.path, 'rb'):
                            pass
                        inf = file.stat()
                        m = inf.st_size
                        date = datetime.fromtimestamp(inf.st_mtime).strftime('%d.%m.%Y %H:%M:%S')
                        res.append((file.path, m, date))
                        if m not in sizes:
                            sizes[m] = list()
                        sizes[m].append((file.path, len(res) - 1))

                    elif file.is_dir():
                        m = folder_size(file.path)
                        date = datetime.fromtimestamp(file.stat().st_mtime).strftime('%d.%m.%Y %H:%M:%S')
                        res.append((file.path, m, date))

                except (OSError, ValueError, OverflowError):
                    res.append((file.path, -1, '-1'))

    except OSError as e:
        raise ErrorFile(f'Не удалось прочитать содержимое папки: {e}') from None
    if not res:
        raise ErrorFile('В указанной папке нет файлов')

    for files in sizes.values():
        if len(files) < 2:
            continue

        for file_path in files:
            try:
                file_hash = sha256()
                with open(file_path[0], 'rb') as f:
                    while chunk := f.read(1024 * 1024):
                        file_hash.update(chunk)

                file_hash = file_hash.hexdigest()

            except OSError:
                res[file_path[1]] = (file_path[0], -1, '-1')
                continue
            if file_hash not in repeats:
                repeats[file_hash] = list()
            repeats[file_hash].append(file_path)

    sum_size = sum(file[1] for file in res if file[1] >= 0)
    repeats = [files for files in repeats.values() if len(files) > 1]
    res.sort(key=lambda x: x[1], reverse=True)
    positions = {}
    i = 0
    for file in res:
        positions[file[0]] = i
        i += 1
    for group in repeats:
        i = 0
        for file in group:
            group[i] = (file[0], positions[file[0]])
            i += 1
    try:
        folder_date = datetime.fromtimestamp(path.getmtime(folder_path)).strftime('%d.%m.%Y %H:%M:%S')
    except (OSError, ValueError, OverflowError):
        folder_date = '-1'

    return res, repeats, (path.normpath(folder_path), sum_size, folder_date)

def file_selection(down, up, files):
    ln = len(files)
    if down > up:
        raise ErrorFile('Нижняя граница больше верхней')

    flag1 = down < files[-1][1]
    flag2 = up > files[0][1]
    left, right = 0, ln
    down_num = ln
    up_num = 0

    while not flag1 or not flag2:
        if left < right:
            mid = left + (right - left) // 2

            if not flag1:
                if files[mid][1] < down:
                    right = mid
                else:
                    left = mid + 1
            else:
                if files[mid][1] > up:
                    left = mid + 1
                else:
                    right = mid
        else:
            if not flag1:
                down_num = left
                flag1 = True
                left, right = 0, ln
            else:
                up_num = left
                flag2 = True

    return up_num, down_num


def parse_file_numbers(nums, files):
    if not nums.strip():
        raise ErrorFile('Введите номера файлов для удаления')
    selected = set()
    for part in nums.split(','):
        part = part.strip()
        try:
            bounds = list(map(int, part.split('-')))
        except ValueError:
            raise ErrorFile(f'Неправильный номер или диапазон: {part}')
        if len(bounds) not in (1, 2):
            raise ErrorFile(f'Неправильный диапазон: {part}')
        start, end = bounds[0], bounds[-1]
        if start > end:
            raise ErrorFile(f'Начало диапазона больше конца: {part}')
        if start < 1 or end > len(files):
            raise ErrorFile(f'Номера должны быть от 1 до {len(files)}')
        selected.update(range(start - 1, end))
    indices = sorted(selected)
    for i in indices:
        if not path.isfile(files[i][0]):
            raise ErrorFile(f'Это не файл или файл недоступен: {files[i][0]}')
    return indices


def delete_files(nums, files):
    indices = parse_file_numbers(nums, files)
    deleted_files = list()
    errors = list()
    for i in indices:
        file_path = files[i][0]
        try:
            remove(file_path)
            deleted_files.append(file_path)
        except OSError as e:
            errors.append(f'{file_path}: {e}')

    return deleted_files, errors


def delete_repeats(repeats):
    files = []
    for group in repeats:
        for file in group[1:]:
            files.append((file[0],))
    if not files:
        return [], []
    nums = ','.join(str(i + 1) for i in range(len(files)))
    return delete_files(nums, files)


if __name__ == '__main__':
    res, repeats, main = scan(r'C:\Users\MAXIM')
    print(res)
    print(repeats)
    print(main)
    l, r = file_selection(1000, 97959, res)
    print(res[l: r])
