from PyQt6.QtWidgets import QTableWidget, QApplication
import sys


class MainWindow(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(3)
        self.setRowCount(1)
        self.setHorizontalHeaderLabels(('Файл', 'Размер, КБ', 'Последние изменение'))
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    sys.excepthook = except_hook
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())

