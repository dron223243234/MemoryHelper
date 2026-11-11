"""Сканирование папок, поиск дубликатов, фильтрация и удаление файлов."""

from os import scandir, path, remove
from datetime import datetime
from hashlib import sha256


class ErrorFile(Exception):
    """Ошибка проверки входных данных или выполнения операций сканера."""
    pass


def folder_size(folder_path):
    """Рекурсивно подсчитать размер доступных файлов внутри папки.

    :param folder_path: путь к папке.
    :return: суммарный размер доступных файлов в байтах.
    :raises OSError: если не удалось открыть исходную папку для обхода.
    """
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
    """Просканировать содержимое папки и найти дубликаты непосредственных файлов.

    Размеры вложенных каталогов рассчитываются рекурсивно.
    Для недоступных элементов размер и дата отмечаются как -1 и строка «-1».
    Неизвестные размеры не учитываются в общей сумме.

    :param folder_path: путь к папке для сканирования.
    :return: кортеж (res, repeats, main), где res содержит тройки
        (путь, размер в байтах, дата), отсортированные по убыванию размера;
        repeats содержит группы пар (путь, индекс в res);
        main содержит путь папки, суммарный размер и дату изменения.
    :raises ErrorFile: если путь неверен, папка недоступна или список элементов пуст.
    """
    res = list()
    repeats = dict()
    sizes = dict()
    # sizes: размер -> [(путь, индекс в res)]. Хешируем только файлы с совпавшим
    # размером: файлы разного размера не могут быть дубликатами
    if not path.isdir(folder_path):
        raise ErrorFile('Указан неправильный путь до папки')
    try:
        with scandir(folder_path) as files:
            for file in files:
                try:
                    if file.is_file():
                        # Открываем файл только для проверки доступа. Это дорого на больших папках
                        # и сетевых дисках, зато недоступные файлы не попадают в сумму
                        with open(file.path, 'rb'):
                            pass
                        inf = file.stat()
                        m = inf.st_size
                        date = datetime.fromtimestamp(inf.st_mtime).strftime('%d.%m.%Y %H:%M:%S')
                        # -1 и '-1' означают «размер/дата неизвестны»
                        res.append((file.path, m, date))
                        if m not in sizes:
                            sizes[m] = list()
                        sizes[m].append((file.path, len(res) - 1))

                    elif file.is_dir():
                        m = folder_size(file.path)
                        date = datetime.fromtimestamp(file.stat().st_mtime).strftime('%d.%m.%Y %H:%M:%S')
                        res.append((file.path, m, date))
                # Ошибка во вложенной папке гасится, и она считается как 0 байт
                # Поэтому итоговый размер может быть занижен
                except (OSError, ValueError, OverflowError):
                    res.append((file.path, -1, '-1'))

    except OSError as e:
        raise ErrorFile(f'Не удалось прочитать содержимое папки: {e}') from None
    if not res:
        raise ErrorFile('В указанной папке нет файлов')
    # Индексы в sizes относятся к res ДО сортировки. Ниже res сортируется,
    # поэтому индексы в repeats пересчитываются через positions
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
                # Файл не прочитался при хешировании: помечаем как недоступный
                # и не включаем в группы дубликатов
                res[file_path[1]] = (file_path[0], -1, '-1')
                continue
            if file_hash not in repeats:
                repeats[file_hash] = list()
            repeats[file_hash].append(file_path)

    sum_size = sum(file[1] for file in res if file[1] >= 0)
    repeats = [files for files in repeats.values() if len(files) > 1]
    # Порядок по убыванию размера нужен функции file_selection (бинарный поиск)
    res.sort(key=lambda x: x[1], reverse=True)
    # После сортировки старые индексы недействительны. Находим новый индекс по пути
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
    """Найти границы среза элементов с размерами в заданном диапазоне.

    :param down: минимальный размер в байтах включительно.
    :param up: максимальный размер в байтах включительно.
    :param files: непустой список элементов, отсортированный по убыванию размера.
    :return: пара индексов начала и конца среза; конец не включается.
    :raises ErrorFile: если нижняя граница больше верхней.
    """
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
    """Проверить номера файлов и преобразовать их в индексы списка.

    Проверка всех выбранных путей выполняется без удаления файлов.

    :param nums: строка номеров и диапазонов через запятую, например «1, 3-5, 8».
        Нумерация начинается с единицы.
    :param files: список элементов, к которому относятся введённые номера.
    :return: отсортированный список уникальных индексов, начиная с нуля.
    :raises ErrorFile: если ввод пуст, номера неверны, выходят за границы
        списка или выбранный путь не является доступным файлом.
    """
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
    """Удалить выбранные файлы с диска после проверки всех номеров.

    Удаление выполняется без перемещения в корзину. Исходный список не изменяется.

    :param nums: строка номеров и диапазонов; нумерация начинается с единицы.
    :param files: список элементов для выбора файлов.
    :return: пара списков путей успешно удалённых файлов и сообщений об ошибках.
    :raises ErrorFile: если номера или выбранные пути не прошли проверку.
    """
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
    """Удалить дубликаты, оставив первый файл в каждой группе.

    :param repeats: группы дубликатов, содержащие пары (путь, индекс в результате).
    :return: пара списков путей успешно удалённых файлов и сообщений об ошибках.
    :raises ErrorFile: если один из выбранных путей не прошёл проверку.
    """
    files = []
    for group in repeats:
        for file in group[1:]:
            files.append((file[0],))
    if not files:
        return [], []
    nums = ','.join(str(i + 1) for i in range(len(files)))
    return delete_files(nums, files)
