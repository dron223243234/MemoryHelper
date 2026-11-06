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
        k = 0
        for file in files:
            if file.is_file():
                inf = file.stat()
                m = inf.st_size
                sum_size += m
                res.append(
                    (file.path, m, datetime.fromtimestamp(inf.st_mtime).strftime('%d.%m.%Y %H:%M:%S')))
                if m not in sizes:
                    sizes[m] = list()
                sizes[m].append((file.path, k))
            elif file.is_dir():
                m = folder_size(file.path)
                sum_size += m
                res.append((file.path, m,
                            datetime.fromtimestamp(file.stat().st_mtime).strftime('%d.%m.%Y %H:%M:%S')))
            k += 1

    if not res:
        raise ErrorFile('В указанной папке нет файлов')

    for files in sizes.values():
        if len(files) < 2:
            continue

        for file_path in files:
            file_hash = sha256()
            with open(file_path[0], 'rb') as f:
                while chunk := f.read(1024 * 1024):
                    file_hash.update(chunk)
            file_hash = file_hash.hexdigest()
            if file_hash not in repeats:
                repeats[file_hash] = list()
            repeats[file_hash].append(file_path)

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

    return res, repeats, ((path.normpath(folder_path), sum_size,
                           datetime.fromtimestamp(path.getmtime(folder_path)).strftime('%d.%m.%Y %H:%M:%S')))


def file_selection(down, up, files):
    ln = len(files)
    flag1, flag2 = False, False
    if down < files[-1][1]:
        flag1 = True
    if up > files[0][1]:
        flag2 = True
    if down > up:
        raise ErrorFile('Нижняя граница больше верхней')
    l, r = 0, ln
    down_num = ln
    if not flag1:
        while l < r:
            mid = l + (r - l) // 2
            if files[mid][1] < down:
                r = mid
            else:
                l = mid + 1
        down_num = l
        l, r = 0, ln
    up_num = 0
    if not flag2:
        while l < r:
            mid = l + (r - l) // 2
            if files[mid][1] > up:
                l = mid + 1
            else:
                r = mid
        up_num = l
    return up_num, down_num


def parse_file_numbers(nums, files):
    nums = nums.strip()
    if not nums:
        raise ErrorFile('Введите номера файлов для удаления')
    selected = set()
    for part in nums.split(','):
        part = part.strip()
        if not part:
            raise ErrorFile('После запятой должен быть номер или диапазон')
        if '-' in part:
            bounds = part.split('-')
            if len(bounds) != 2:
                raise ErrorFile(f'Неправильный диапазон: {part}')
            try:
                start, end = map(int, bounds)
            except ValueError:
                raise ErrorFile(f'Неправильный диапазон: {part}')
            if start > end:
                raise ErrorFile(f'Начало диапазона больше конца: {part}')
        else:
            try:
                start = end = int(part)
            except ValueError:
                raise ErrorFile(f'Неправильный номер: {part}')
        if start < 1 or end > len(files):
            raise ErrorFile(f'Номера должны быть от 1 до {len(files)}')
        selected.update(range(start - 1, end))

    indices = sorted(selected)
    for i in indices:
        if not path.isfile(files[i][0]):
            raise ErrorFile(f'Это не файл или файл недоступен:{files[i][0]}')
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
