from PyQt6.QtWidgets import QTableWidget, QApplication, QMainWindow
import sys


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.table = FileTable()
        self.setCentralWidget(self.table)


class FileTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(3)
        self.setRowCount(3)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setHorizontalHeaderLabels(('Имя', 'Вес', 'Дата'))


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    sys.excepthook = except_hook
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())

