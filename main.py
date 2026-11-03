from PyQt6.QtWidgets import QTableWidget, QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, \
    QTableWidgetItem, QMessageBox, QHeaderView, QLabel, QLineEdit
from PyQt6.QtCore import QThread, pyqtSignal, Qt
import sys
import FolderScan
from FolderScan import scan
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.res = None
        self.table = FileTable()
        self.cont1 = QWidget()
        self.files_count = QLabel('''Количество файлов/папок: -
Суммарный вес файлов: -
''')
        self.min_size = QLineEdit()
        self.max_size = QLineEdit()
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
        self.layout1.addWidget(self.table)
        self.setCentralWidget(self.cont1)
        self.open_button.clicked.connect(self.choose_folder)
        self.file_selection.clicked.connect(self.show_slice)
        self.clear_filters.clicked.connect(self.filter_cleaning)
        self.scan_thread = None
        self.resize(960, 540)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)

    def choose_folder(self):
        self.file_selection.setEnabled(False)
        self.clear_filters.setEnabled(False)
        path = QFileDialog.getExistingDirectory()
        if not path:
            if self.res:
                self.file_selection.setEnabled(True)
                self.clear_filters.setEnabled(True)
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
        self.table.setRowCount(len(self.res))
        for i in range(len(self.res)):
            self.table.setItem(i, 0, QTableWidgetItem(str(os.path.basename(self.res[i][0]))))
            self.table.setItem(i, 1, QTableWidgetItem(str(round(self.res[i][1] / 1024, 1))))
            self.table.setItem(i, 2, QTableWidgetItem(str(self.res[i][2])))
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle('Сканирование папки')
        message.setText('Сканирование завершено')
        message.setWindowFlags(message.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.open_button.setText('Выбрать папку')
        self.file_selection.setEnabled(True)
        self.clear_filters.setEnabled(True)
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
            k = 0
            self.table.setRowCount(mx - mn)
            for i in range(mn, mx):
                self.table.setItem(k, 0, QTableWidgetItem(str(os.path.basename(self.res[i][0]))))
                self.table.setItem(k, 1, QTableWidgetItem(str(round(self.res[i][1] / 1024, 1))))
                self.table.setItem(k, 2, QTableWidgetItem(str(self.res[i][2])))
                k += 1
            self.files_count.setText(f'''Количество файлов/папок: {mx - mn}
Суммарный вес файлов: {round(sum(i[-2] for i in self.res[mn : mx]) / 1024, 1)} КБ
''')
        except FolderScan.ErrorFile as e:
            self.show_error(str(e))
        except ValueError as e:
            self.show_error('Введите число')

    def filter_cleaning(self):
        self.table.setRowCount(len(self.res))
        self.max_size.setText('')
        self.min_size.setText('')
        for i in range(len(self.res)):
            self.table.setItem(i, 0, QTableWidgetItem(str(os.path.basename(self.res[i][0]))))
            self.table.setItem(i, 1, QTableWidgetItem(str(round(self.res[i][1] / 1024, 1))))
            self.table.setItem(i, 2, QTableWidgetItem(str(self.res[i][2])))
        self.files_count.setText(f'''Количество файлов/папок: {len(self.res)}
Суммарный вес файлов: {round(sum(i[-2] for i in self.res) / 1024, 1)} КБ
''')


class FileTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(3)
        self.setRowCount(1)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setHorizontalHeaderLabels(('Имя', 'Вес КБ', 'Дата'))


class ScanThread(QThread):
    result_ready = pyqtSignal(object, object, object)
    error = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            self.result_ready.emit(*scan(self.path))
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
