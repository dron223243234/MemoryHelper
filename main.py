from PyQt6.QtWidgets import QTableWidget, QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, \
    QTableWidgetItem, QMessageBox, QHeaderView, QLabel
from PyQt6.QtCore import QThread, pyqtSignal
import sys
from FolderScan import scan
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.table = FileTable()
        self.cont1 = QWidget()
        self.FilesCount = QLabel('''Количество файлов/папок: -''')
        self.OpenButton = QPushButton('Выбрать папку')
        self.layout1 = QVBoxLayout(self.cont1)
        self.layout1.addWidget(self.OpenButton)
        self.layout1.addWidget(self.FilesCount)
        self.layout1.addWidget(self.table)
        self.setCentralWidget(self.cont1)
        self.OpenButton.clicked.connect(self.choose_folder)
        self.scan_thread = None
        self.resize(960, 540)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory()
        if not path:
            return
        self.scan_thread = ScanThread(path)
        self.scan_thread.result_ready.connect(self.show_result)
        self.OpenButton.setEnabled(False)
        self.OpenButton.setText('Сканирование')
        self.scan_thread.finished.connect(lambda: self.OpenButton.setEnabled(True))
        self.scan_thread.error.connect(self.show_error)
        self.scan_thread.start()

    def show_result(self, res, repeat, main):
        self.res, self.repeats, self.main = res, repeat, main
        self.table.setRowCount(len(self.res))
        for i in range(len(self.res)):
            self.table.setItem(i, 0, QTableWidgetItem(str(os.path.basename(self.res[i][0]))))
            self.table.setItem(i, 1, QTableWidgetItem(str(round(self.res[i][1] / 1024, 1))))
            self.table.setItem(i, 2, QTableWidgetItem(str(self.res[i][2])))
        self.OpenButton.setText('Выбрать папку')
        self.FilesCount.setText(f'Количество файлов/папок: {len(self.res)}')

    def show_error(self, e):
        QMessageBox.critical(self, 'Ошибка сканирования', e)
        self.OpenButton.setText('Выбрать папку')

    def closeEvent(self, event):
        if self.scan_thread is not None and self.scan_thread.isRunning():
            event.ignore()
            QMessageBox.critical(self, 'Ошибка сканирования',
                                 'Сканирование ещё выполняется. Дождитесь завершения.')


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
