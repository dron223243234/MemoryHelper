from PyQt6.QtWidgets import QTableWidget, QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QFileDialog, \
    QTableWidgetItem
import sys
from FolderScan import scan
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.table = FileTable()
        self.cont1 = QWidget()
        self.OpenButton = QPushButton('Выбрать папку')
        self.layout1 = QVBoxLayout(self.cont1)
        self.layout1.addWidget(self.OpenButton)
        self.layout1.addWidget(self.table)
        self.setCentralWidget(self.cont1)
        self.OpenButton.clicked.connect(self.choose_folder)

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory()
        res, repeats, main = scan(path)
        self.table.setRowCount(len(res))
        for i in range(len(res)):
            self.table.setItem(i, 0, QTableWidgetItem(str(os.path.basename(res[i][0]))))
            self.table.setItem(i, 1, QTableWidgetItem(str(round(res[i][1] / 1024, 1))))
            self.table.setItem(i, 2, QTableWidgetItem(str(res[i][2])))


class FileTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setColumnCount(3)
        self.setRowCount(1)
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
