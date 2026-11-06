from PyQt6.QtWidgets import QTableWidget, QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, \
    QTableWidgetItem, QMessageBox, QHeaderView, QLabel, QLineEdit
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import sys
import FolderScan
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.res = None
        self.visible_files = list()
        self.table = FileTable()
        self.cont1 = QWidget()
        self.files_count = QLabel('''Количество файлов/папок: -
Суммарный вес файлов: -
''')
        self.min_size = QLineEdit()
        self.max_size = QLineEdit()
        self.delete_nums = QLineEdit()
        self.delete_button = QPushButton('Удалить файлы')
        self.delete_repeats_button = QPushButton('Удалить все повторы')
        self.file_selection = QPushButton('Выбрать файлы по размеру')
        self.open_button = QPushButton('Выбрать папку')
        self.clear_filters = QPushButton('Сбросить фильтер')
        self.layout1 = QVBoxLayout(self.cont1)
        self.layout1.addWidget(self.open_button)
        self.layout1.addWidget(self.files_count)
        self.layout1.addWidget(QLabel('Минимальный размер файла в КБ:'))
        self.layout1.addWidget(self.min_size)
        self.layout1.addWidget(QLabel('Максимальный размер файла в КБ:'))
        self.layout1.addWidget(self.max_size)
        self.layout1.addWidget(self.file_selection)
        self.layout1.addWidget(self.clear_filters)
        self.file_selection.setEnabled(False)
        self.clear_filters.setEnabled(False)
        self.layout1.addWidget(QLabel('Номера файлов для удаления:'))
        self.layout1.addWidget(self.delete_nums)
        self.layout1.addWidget(self.delete_button)
        self.layout1.addWidget(self.delete_repeats_button)
        self.delete_button.setEnabled(False)
        self.delete_repeats_button.setEnabled(False)
        self.layout1.addWidget(self.table)
        self.setCentralWidget(self.cont1)
        self.open_button.clicked.connect(self.choose_folder)
        self.file_selection.clicked.connect(self.show_slice)
        self.clear_filters.clicked.connect(self.filter_cleaning)
        self.delete_button.clicked.connect(self.remove_selected_files)
        self.delete_repeats_button.clicked.connect(self.remove_all_repeats)
        self.delete_nums.setPlaceholderText('Например: 1,3-5,8')
        self.scan_thread = None
        self.resize(960, 540)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)

    def choose_folder(self):
        self.file_selection.setEnabled(False)
        self.clear_filters.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.delete_repeats_button.setEnabled(False)
        path = QFileDialog.getExistingDirectory()
        if not path:
            if self.res:
                self.file_selection.setEnabled(True)
                self.clear_filters.setEnabled(True)
                self.delete_button.setEnabled(True)
                self.delete_repeats_button.setEnabled(True)
            return
        self.scan_thread = ScanThread(path)
        self.scan_thread.result_ready.connect(self.show_result)
        self.open_button.setEnabled(False)
        self.open_button.setText('Сканирование')
        self.scan_thread.finished.connect(lambda: self.open_button.setEnabled(True))
        self.scan_thread.error.connect(self.show_error)
        self.scan_thread.start()

    def show_result(self, res, repeat, main):
        self.res, self.repeats, self.main = res, repeat, main
        self.visible_files = self.res[:]
        self.delete_nums.clear()
        self.table.setRowCount(len(self.res))
        for i in range(len(self.res)):
            self.table.setItem(i, 0, QTableWidgetItem(str(os.path.basename(self.res[i][0]))))
            self.table.setItem(i, 1, QTableWidgetItem(str(round(self.res[i][1] / 1024, 1))))
            self.table.setItem(i, 2, QTableWidgetItem(str(self.res[i][2])))
            self.table.setItem(i, 3, QTableWidgetItem('-'))
        if self.repeats:
            k = 0
            for i in self.repeats:
                k += 1
                for j in i:
                    self.table.setItem(j[1], 3, QTableWidgetItem(f'Группа {k}'))
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle('Сканирование папки')
        message.setText('Сканирование завершено')
        message.setWindowFlags(message.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.open_button.setText('Выбрать папку')
        self.file_selection.setEnabled(True)
        self.clear_filters.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.delete_repeats_button.setEnabled(True)
        self.files_count.setText(f'''Количество файлов/папок: {len(self.res)}
Суммарный вес файлов: {round(sum(i[-2] for i in self.res) / 1024, 1)} КБ
''')
        message.exec()

    def show_error(self, e):
        QMessageBox.critical(self, 'Ошибка', e)
        self.open_button.setText('Выбрать папку')
        if self.res:
            self.file_selection.setEnabled(True)
            self.clear_filters.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.delete_repeats_button.setEnabled(bool(self.repeats))

    def closeEvent(self, event):
        if self.scan_thread is not None and self.scan_thread.isRunning():
            event.ignore()
            QMessageBox.critical(self, 'Ошибка',
                                 'Сканирование ещё выполняется. Дождитесь завершения.')

    def show_slice(self):
        try:
            x1, x2 = self.min_size.text(), self.max_size.text()
            if not x1:
                x1 = 0
            if not x2:
                x2 = self.res[0][1] / 1024
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
                self.table.setItem(k, 1, QTableWidgetItem(str(round(self.res[i][1] / 1024, 1))))
                self.table.setItem(k, 2, QTableWidgetItem(str(self.res[i][2])))
                self.table.setItem(k, 3, QTableWidgetItem('-'))
                k += 1
            self.files_count.setText(f'''Количество файлов/папок: {mx - mn}
Суммарный вес файлов: {round(sum(i[-2] for i in self.res[mn: mx]) / 1024, 1)} КБ
''')
            k = 0
            for i in self.repeats:
                k += 1
                for j in i:
                    if mn <= j[1] < mx:
                        self.table.setItem(j[1] - mn, 3, QTableWidgetItem(f'Группа {k}'))
        except FolderScan.ErrorFile as e:
            self.show_error(str(e))
        except ValueError as e:
            self.show_error('Введите число')

    def filter_cleaning(self):
        self.max_size.clear()
        self.min_size.clear()
        self.delete_nums.clear()
        self.visible_files = self.res[:]
        self.table.setRowCount(len(self.res))
        for i in range(len(self.res)):
            self.table.setItem(i, 0, QTableWidgetItem(os.path.basename(self.res[i][0])))
            self.table.setItem(i, 1, QTableWidgetItem(str(round(self.res[i][1] / 1024, 1))))
            self.table.setItem(i, 2, QTableWidgetItem(self.res[i][2]))
            self.table.setItem(i, 3, QTableWidgetItem('-'))
        k = 0
        for group in self.repeats:
            k += 1
            for file in group:
                self.table.setItem(file[1], 3, QTableWidgetItem(f'Группа {k}'))

        self.files_count.setText(f'''Количество файлов/папок: {len(self.res)}\n
Суммарный вес файлов:
{round(sum(i[1] for i in self.res) / 1024, 1)} КБ''')
        has_files = bool(self.res)
        self.file_selection.setEnabled(has_files)
        self.clear_filters.setEnabled(has_files)
        self.delete_button.setEnabled(has_files)
        self.delete_repeats_button.setEnabled(bool(self.repeats))

    def remove_selected_files(self):
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
        except FolderScan.ErrorFile as e:
            self.show_error(str(e))

    def remove_all_repeats(self):
        try:
            if not self.repeats:
                raise FolderScan.ErrorFile('Повторы не найдены')
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
        deleted_paths = set(deleted_files)
        self.res = [file for file in self.res if file[0] not in deleted_paths]
        positions = {file[0]: i for i, file in enumerate(self.res)}

        new_repeats = []
        for group in self.repeats:
            remaining = [(file[0], positions[file[0]]) for file in group if file[0] in positions]
            if len(remaining) > 1:
                new_repeats.append(remaining)

        self.repeats = new_repeats
        self.main = (self.main[0], sum(file[1] for file in self.res), self.main[2])
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
            QMessageBox.information(
                self, 'Удаление завершено', f'Удалено файлов: {len(deleted_files)}')


class FileTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(4)
        self.setRowCount(1)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setHorizontalHeaderLabels(('Имя', 'Вес КБ', 'Дата', 'Группа'))


class ScanThread(QThread):
    result_ready = pyqtSignal(object, object, object)
    error = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            self.result_ready.emit(*FolderScan.scan(self.path))
        except Exception as e:
            self.error.emit(str(e))


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    sys.excepthook = except_hook
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
