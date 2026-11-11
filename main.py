"""Графический интерфейс FolderScan, поток сканирования и окно игры."""

from PyQt6.QtWidgets import QTableWidget, QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, \
    QTableWidgetItem, QMessageBox, QHeaderView, QLabel, QLineEdit, QFormLayout, QHBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRectF
from PyQt6.QtGui import QIcon, QPainter, QFont
from PyQt6.QtSvg import QSvgRenderer
import sys
import FolderScan
import os
import sqlite3
import ScanDatabase
from random import choice


class BackgroundWidget(QWidget):
    """Виджет с фоновым SVG-изображением по центру."""
    def __init__(self, image_path):
        """Создать виджет и загрузить SVG-изображение.

        :param image_path: путь к файлу SVG.
        """
        super().__init__()
        self.renderer = QSvgRenderer(image_path, self)

    def paintEvent(self, event):
        """Нарисовать изображение по центру виджета с размером не более 320 пикселей.

        :param event: событие перерисовки виджета.
        """
        super().paintEvent(event)
        size = min(320, self.width(), self.height())
        x = (self.width() - size) / 2
        y = (self.height() - size) / 2
        painter = QPainter(self)
        try:
            self.renderer.render(painter, QRectF(x, y, size, size))
        finally:
            painter.end()


class Game(QMainWindow):
    """Окно игры «Крестики-нолики» с ручным вводом и случайным ходом соперника."""
    def __init__(self):
        """Создать игровое окно и подключить кнопки."""
        super().__init__()
        self.start = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
        self.make_funny()
        self.button_clear.clicked.connect(self.clear_field)
        self.button_step.clicked.connect(self.enemy_step)

    def clear_field(self):
        """Очистить поле и разрешить редактирование всех клеток."""
        self.start = [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
        for row in range(3):
            for col in range(3):
                item = self.square.item(row, col)
                item.setText('')
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

    def enemy_step(self):
        """Поставить O в случайную свободную клетку или очистить заполненное поле."""
        while self.start:
            x, y = choice(self.start)
            self.start.remove((x, y))
            item = self.square.item(x, y)
            if item.text().strip():
                continue
            item.setText('O')
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            return
        QMessageBox.information(self, 'Крестики-Нолики', 'Нет свободных клеток')
        self.clear_field()

    def make_funny(self):
        """Создать игровое поле, кнопки и настроить окно игры."""
        self.cont1 = QWidget()
        self.layout1 = QVBoxLayout(self.cont1)
        self.setCentralWidget(self.cont1)
        self.square = QTableWidget(3, 3)
        self.layout1.addWidget(self.square)
        self.square.horizontalHeader().hide()
        self.square.verticalHeader().hide()
        self.square.setFont(QFont('Arial', 20))
        for row in range(3):
            self.square.setRowHeight(row, 100)
            self.square.setColumnWidth(row, 100)
            for col in range(3):
                item = QTableWidgetItem('')
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.square.setItem(row, col, item)
        self.button_clear = QPushButton('Очистить поле')
        self.button_step = QPushButton('Ход соперника')
        self.layout1.addWidget(self.button_clear)
        self.layout1.addWidget(self.button_step)
        self.resize(350, 420)
        self.setWindowTitle('Крестики-Нолики')


class MainWindow(QMainWindow):
    """Главное окно сканирования папок и управления результатами."""
    def __init__(self):
        """Создать интерфейс, начальное состояние и подключить обработчики событий."""
        super().__init__()
        self.res = None
        self.loaded_result = False
        self.current_path = None
        self.visible_files = list()
        self.scan_thread = None
        self.make_funny()
        self.save_button.clicked.connect(self.save_result)
        self.load_button.clicked.connect(self.load_result)
        self.game_button.clicked.connect(self.game.show)
        # lambda нужна: clicked передаёт аргумент checked (bool),
        # и он попал бы в folder_path.
        self.open_button.clicked.connect(lambda: self.choose_folder())
        self.file_selection.clicked.connect(self.show_slice)
        self.clear_filters.clicked.connect(self.filter_cleaning)
        self.delete_button.clicked.connect(self.remove_selected_files)
        self.delete_repeats_button.clicked.connect(self.remove_all_repeats)
        self.up_button.clicked.connect(self.go_up)
        self.table.cellDoubleClicked.connect(self.open_folder)

    def save_result(self):
        """Сохранить текущий результат в выбранную базу SQLite."""
        if not self.res:
            QMessageBox.information(self, 'Сохранение', 'Нет результата для сохранения')
            return
        dialog = QFileDialog(self, 'Сохранить результат')
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        dialog.setNameFilter('База SQLite (*.db)')
        dialog.setDefaultSuffix('db')
        dialog.selectFile('scan-result.db')
        if not dialog.exec():
            return
        file_path = dialog.selectedFiles()[0]
        try:
            ScanDatabase.save_result(file_path, self.res, self.repeats, self.main)
        except (sqlite3.Error, OSError, ValueError) as e:
            QMessageBox.critical(self, 'Ошибка сохранения', str(e))
            return
        QMessageBox.information(self, 'Сохранение', 'Результат сохранён в базу данных')

    def load_result(self):
        """Загрузить результат из выбранной базы SQLite и отключить удаление файлов."""
        file_path, _ = QFileDialog.getOpenFileName(self,
                                                   'Загрузить результат', '', 'База SQLite (*.db)')
        if not file_path:
            return
        try:
            res, repeats, main = ScanDatabase.load_result(file_path)
        except (sqlite3.Error, OSError, ValueError) as e:
            QMessageBox.critical(self, 'Ошибка загрузки', f'Не удалось загрузить результат: {e}')
            return
        self.show_result(res, repeats, main, from_file=True)
        self.up_button.setEnabled(os.path.dirname(self.current_path) != self.current_path)

    def choose_folder(self, folder_path=None):
        """Выбрать папку и запустить сканирование в отдельном потоке.

        :param folder_path: путь к папке; если None, открыть диалог выбора папки.
        """
        if self.scan_thread is not None and self.scan_thread.isRunning():
            return
        self.file_selection.setEnabled(False)
        self.clear_filters.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.delete_repeats_button.setEnabled(False)
        if folder_path is None:
            folder_path = QFileDialog.getExistingDirectory()
        path = folder_path
        if not path:
            if self.res:
                self.file_selection.setEnabled(True)
                self.clear_filters.setEnabled(True)
                self.delete_button.setEnabled(bool(self.res) and not self.loaded_result)
                self.delete_repeats_button.setEnabled(bool(self.repeats) and not self.loaded_result)
            return
        path = os.path.abspath(path)
        self.up_button.setEnabled(False)
        self.scan_thread = ScanThread(path)
        self.scan_thread.result_ready.connect(self.show_result)
        self.open_button.setEnabled(False)
        self.open_button.setText('Сканирование')
        self.scan_thread.finished.connect(lambda: self.open_button.setEnabled(True))
        self.scan_thread.finished.connect(lambda: self.up_button.setEnabled(
        self.current_path is not None and os.path.dirname(self.current_path) != self.current_path))
        self.scan_thread.error.connect(self.show_error)
        self.scan_thread.start()

    def show_result(self, res, repeat, main, from_file=False):
        """Показать результат сканирования или загрузки из базы.

        :param res: список элементов с путями, размерами в байтах и датами изменения.
        :param repeat: группы дубликатов с путями и индексами элементов в res.
        :param main: путь папки, суммарный размер и дата изменения.
        :param from_file: True, если результат загружен из базы и удаление нужно отключить.
        """
        self.loaded_result = from_file
        self.res, self.repeats, self.main = res, repeat, main
        self.current_path = os.path.abspath(self.main[0])
        self.current_path_label.setText(f'Текущая папка: {self.current_path}')
        self.min_size.clear()
        self.max_size.clear()
        # Строка таблицы i соответствует visible_files[i]. Номера для удаления и
        # двойной щелчок работают именно с этим списком, а не с res
        # Сортировку таблицы включать нельзя: порядок строк разойдётся со списком
        self.visible_files = self.res[:]
        self.delete_nums.clear()
        self.fill_table()
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle('Сканирование папки')
        message.setText('Результат загружен из базы' if from_file else 'Сканирование завершено')
        message.setWindowFlags(message.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.open_button.setText('Выбрать папку')
        self.file_selection.setEnabled(True)
        self.clear_filters.setEnabled(True)
        self.delete_button.setEnabled(bool(self.res) and not self.loaded_result)
        self.delete_repeats_button.setEnabled(bool(self.repeats) and not self.loaded_result)
        self.files_count.setText(f'''Количество файлов/папок: {len(self.res)}
Суммарный вес файлов: {round(sum(i[1] for i in self.res if i[1] >= 0) / 1024, 1)} КБ
''')
        message.exec()

    def show_error(self, e):
        """Показать ошибку и восстановить доступные действия для прежнего результата.

        :param e: текст сообщения об ошибке.
        """
        QMessageBox.critical(self, 'Ошибка', e)
        self.open_button.setText('Выбрать папку')
        if self.res:
            self.file_selection.setEnabled(True)
            self.clear_filters.setEnabled(True)
            self.delete_button.setEnabled(bool(self.res) and not self.loaded_result)
            self.delete_repeats_button.setEnabled(bool(self.repeats) and not self.loaded_result)

    def closeEvent(self, event):
        """Запретить закрытие окна во время сканирования.

        :param event: событие закрытия окна.
        """
        if self.scan_thread is not None and self.scan_thread.isRunning():
            event.ignore()
            QMessageBox.critical(self, 'Ошибка', 'Сканирование ещё выполняется. Дождитесь завершения.')

    def show_slice(self):
        """Отфильтровать элементы по размеру в КБ и обновить таблицу и статистику."""
        try:
            x1, x2 = self.min_size.text(), self.max_size.text()
            if not x1:
                x1 = 0
            if not x2:
                x2 = max(0, self.res[0][1]) / 1024
            if float(x1) < 0 or float(x2) < 0:
                raise FolderScan.ErrorFile('Размер файлов должен быть больше или равен 0')
            x1, x2 = float(x1) * 1024, float(x2) * 1024
            mn, mx = FolderScan.file_selection(x1, x2, self.res)
            self.visible_files = self.res[mn:mx]
            self.delete_nums.clear()
            k = 0
            self.table.setRowCount(mx - mn)
            for i in range(mn, mx):
                self.table.setItem(k, 0, QTableWidgetItem(str(os.path.basename(self.res[i][0]))))
                self.table.setItem(k, 1, QTableWidgetItem(
                    '-1' if self.res[i][1] < 0 else str(round(self.res[i][1] / 1024, 1))))
                self.table.setItem(k, 2, QTableWidgetItem(str(self.res[i][2])))
                self.table.setItem(k, 3, QTableWidgetItem('-'))
                k += 1
            self.files_count.setText(f'''Количество файлов/папок: {mx - mn}
Суммарный вес файлов: {round(sum(i[1] for i in self.res[mn: mx] if i[1] >= 0) / 1024, 1)} КБ
''')
            k = 0
            for i in self.repeats:
                k += 1
                for j in i:
                    if mn <= j[1] < mx:
                        self.table.setItem(j[1] - mn, 3, QTableWidgetItem(f'Группа {k}'))
        except FolderScan.ErrorFile as e:
            self.show_error(str(e))
        except ValueError:
            self.show_error('Введите число')

    def filter_cleaning(self):
        """Сбросить фильтр и показать полный список элементов и общую статистику."""
        self.max_size.clear()
        self.min_size.clear()
        self.delete_nums.clear()
        self.visible_files = self.res[:]
        self.fill_table()

        self.files_count.setText(f'''Количество файлов/папок: {len(self.res)}
Суммарный вес файлов: {round(sum(i[1] for i in self.res if i[1] >= 0) / 1024, 1)} КБ''')

        has_files = bool(self.res)
        self.file_selection.setEnabled(has_files)
        self.clear_filters.setEnabled(has_files)
        self.delete_button.setEnabled(has_files and not self.loaded_result)
        self.delete_repeats_button.setEnabled(bool(self.repeats) and not self.loaded_result)

    def fill_table(self):
        """Заполнить таблицу полным результатом и номерами групп дубликатов."""
        self.table.setRowCount(len(self.res))
        for i in range(len(self.res)):
            self.table.setItem(i, 0, QTableWidgetItem(os.path.basename(self.res[i][0])))
            self.table.setItem(i, 1,
                               QTableWidgetItem('-1' if self.res[i][1] < 0
                                                else str(round(self.res[i][1] / 1024, 1))))
            self.table.setItem(i, 2, QTableWidgetItem(str(self.res[i][2])))
            self.table.setItem(i, 3, QTableWidgetItem('-'))
        k = 0
        for group in self.repeats:
            k += 1
            for file in group:
                self.table.setItem(file[1], 3, QTableWidgetItem(f'Группа {k}'))

    def remove_selected_files(self):
        """Запросить подтверждение и удалить файлы по номерам строк текущей таблицы."""
        try:
            if not self.visible_files:
                raise FolderScan.ErrorFile('В таблице нет файлов')
            nums = self.delete_nums.text()
            files = self.visible_files[:]
            indices = FolderScan.parse_file_numbers(nums, files)
            message = QMessageBox(self)
            message.setWindowTitle('Удаление файлов')
            message.setIcon(QMessageBox.Icon.Warning)
            message.setText(f'''Удалить файлы: {len(indices)}?
Файлы будут удалены с диска''')
            message.setDetailedText('\n'.join(files[i][0] for i in indices))
            message.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            message.setDefaultButton(QMessageBox.StandardButton.No)
            if message.exec() != QMessageBox.StandardButton.Yes:
                return
            deleted_files, errors = FolderScan.delete_files(nums, files)
            self.finish_deletion(deleted_files, errors)
        except FolderScan.ErrorFile as e:  # может быть вызвана 208 и 222
            self.show_error(str(e))

    def remove_all_repeats(self):
        """Запросить подтверждение и удалить дубликаты во всей папке, оставив первый файл каждой группы."""
        try:
            if not self.repeats:
                raise FolderScan.ErrorFile('Повторы не найдены')
            # Берутся все группы папки, фильтр размера не учитывается,
            # в каждой группе остаётся первый файл
            files = [file for group in self.repeats for file in group[1:]]
            nums = ','.join(str(i + 1) for i in range(len(files)))
            FolderScan.parse_file_numbers(nums, files)

            message = QMessageBox(self)
            message.setWindowTitle('Удаление повторов')
            message.setIcon(QMessageBox.Icon.Warning)
            message.setText(f'''Удалить повторяющиеся файлы: {len(files)}?
В каждой группе останется первый файл
Операция относится ко всей папке, независимо от фильтра
Файлы будут удалены с диска''')
            message.setDetailedText('\n'.join(file[0] for file in files))
            message.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            message.setDefaultButton(QMessageBox.StandardButton.No)
            if message.exec() != QMessageBox.StandardButton.Yes:
                return

            deleted_files, errors = FolderScan.delete_repeats(self.repeats)
            self.finish_deletion(deleted_files, errors)

        except FolderScan.ErrorFile as e:
            self.show_error(str(e))

    def finish_deletion(self, deleted_files, errors):
        """Обновить результат после удаления файлов и показать сведения об ошибках.

        :param deleted_files: список путей успешно удалённых файлов.
        :param errors: список сообщений об ошибках удаления.
        """
        deleted_paths = set(deleted_files)
        self.res = [file for file in self.res if file[0] not in deleted_paths]
        positions = {file[0]: i for i, file in enumerate(self.res)}
        new_repeats = []
        for group in self.repeats:
            remaining = [(file[0], positions[file[0]]) for file in group if file[0] in positions]
            if len(remaining) > 1:
                new_repeats.append(remaining)
        self.repeats = new_repeats
        self.main = (self.main[0], sum(file[1] for file in self.res if file[1] >= 0), self.main[2])
        self.filter_cleaning()
        if errors:
            message = QMessageBox(self)
            message.setWindowTitle('Результат удаления')
            message.setIcon(QMessageBox.Icon.Warning)
            message.setText(f'''Удалено файлов: {len(deleted_files)}
Не удалось удалить: {len(errors)}''')
            message.setDetailedText('\n'.join(errors))
            message.exec()
        else:
            QMessageBox.information(self, 'Удаление завершено', f'Удалено файлов: {len(deleted_files)}')

    def open_folder(self, row, column):
        """Запустить сканирование каталога, выбранного двойным щелчком в таблице.

        :param row: индекс строки в текущем отображаемом списке.
        :param column: индекс столбца, по которому выполнен двойной щелчок.
        """
        if self.scan_thread is not None and self.scan_thread.isRunning():
            return
        if not 0 <= row < len(self.visible_files):
            return
        folder_path = self.visible_files[row][0]
        if os.path.isdir(folder_path):
            self.choose_folder(folder_path)

    def go_up(self):
        """Запустить сканирование родительской папки текущего каталога."""
        if not self.current_path:
            return
        parent = os.path.dirname(self.current_path)
        if parent != self.current_path:
            self.choose_folder(parent)

    def make_funny(self):
        """Создать элементы главного окна и задать их начальное состояние."""
        self.table = FileTable()
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'folderscan-logo.svg')
        self.cont1 = BackgroundWidget(image_path)
        self.files_count = QLabel('Количество файлов/папок: -\nСуммарный вес файлов: -')
        self.min_size = QLineEdit()
        self.max_size = QLineEdit()
        self.delete_nums = QLineEdit()
        self.delete_button = QPushButton('Удалить файлы')
        self.delete_repeats_button = QPushButton('Удалить все повторы')
        self.file_selection = QPushButton('Выбрать файлы по размеру')
        self.open_button = QPushButton('Выбрать папку')
        self.up_button = QPushButton('На уровень выше')
        self.clear_filters = QPushButton('Сбросить фильтр')
        self.save_button = QPushButton('Сохранить результат в .db')
        self.load_button = QPushButton('Загрузить результат из .db')
        self.game_button = QPushButton('Занять себя')
        self.current_path_label = QLabel('Текущая папка: не выбрана')
        size_form = QFormLayout()
        size_form.addRow('Минимальный размер файла в КБ:', self.min_size)
        size_form.addRow('Максимальный размер файла в КБ:', self.max_size)
        delete_form = QFormLayout()
        delete_form.addRow('Номера файлов для удаления:', self.delete_nums)
        db_row = QHBoxLayout()
        db_row.addWidget(self.save_button)
        db_row.addWidget(self.load_button)
        filter_row = QHBoxLayout()
        filter_row.addWidget(self.file_selection)
        filter_row.addWidget(self.clear_filters)
        file_row = QHBoxLayout()
        file_row.addWidget(self.delete_button)
        file_row.addWidget(self.delete_repeats_button)
        self.layout1 = QVBoxLayout(self.cont1)
        self.layout1.addWidget(self.open_button)
        self.layout1.addLayout(db_row)
        self.layout1.addWidget(self.files_count)
        self.layout1.addLayout(size_form)
        self.layout1.addLayout(filter_row)
        self.layout1.addLayout(delete_form)
        self.layout1.addLayout(file_row)
        self.layout1.addWidget(self.up_button)
        self.layout1.addWidget(self.game_button)
        self.layout1.addWidget(self.current_path_label)
        self.layout1.addWidget(self.table)
        self.file_selection.setEnabled(False)
        self.clear_filters.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.delete_repeats_button.setEnabled(False)
        self.up_button.setEnabled(False)
        self.current_path_label.setWordWrap(True)
        self.delete_nums.setPlaceholderText('Например: 1,3-5,8')
        self.setCentralWidget(self.cont1)
        self.resize(960, 700)
        self.setWindowIcon(QIcon(image_path))
        self.setWindowTitle('FolderScan')
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.game = Game()


class FileTable(QTableWidget):
    """Таблица результатов с четырьмя столбцами без редактирования ячеек."""
    def __init__(self):
        """Настроить столбцы таблицы и запретить редактирование."""
        super().__init__()
        self.setColumnCount(4)
        self.setRowCount(1)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setHorizontalHeaderLabels(('Имя', 'Вес КБ', 'Дата', 'Группа'))


class ScanThread(QThread):
    """Поток сканирования с сигналами результата и сообщения об ошибке."""
    result_ready = pyqtSignal(object, object, object)
    error = pyqtSignal(str)

    def __init__(self, path):
        """Создать поток для сканирования выбранной папки.

        :param path: путь к папке для сканирования.
        """
        super().__init__()
        self.path = path

    def run(self):
        """Выполнить сканирование и передать результат либо текст ошибки через сигнал."""
        try:
            self.result_ready.emit(*FolderScan.scan(self.path))
        except Exception as e:
            self.error.emit(str(e))


def except_hook(cls, exception, traceback):
    """Передать необработанное исключение стандартному обработчику Python.

    :param cls: класс исключения.
    :param exception: объект исключения.
    :param traceback: объект трассировки исключения.
    """
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    sys.excepthook = except_hook
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())