import os
import sys

from PyQt6.QtWidgets import QWidget, QApplication
from PySide6.QtWidgets import QMainWindow, QHBoxLayout

from windows.left_panel.left_panel import LeftPanel

# Определяем корневую директорию проекта
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


# Импортируем наш класс (если он в отдельном файле)
# from left_panel import LeftPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Документооборот МАЗ")
        self.setGeometry(100, 100, 1200, 800)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем левую панель (передаем ROOT_DIR глобально)
        global ROOT_DIR
        self.left_panel = LeftPanel()

        # Правый контент (пока пустой, можно добавить что-то)
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: #F5F5F5;")

        # Добавляем виджеты в layout
        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(self.content_widget, 1)

        # Подключаем кнопку скрытия панели
        self.left_panel.hidePanelBtn.clicked.connect(self.toggle_left_panel)

        # Подключаем другие кнопки (пример)
        self.left_panel.profileBtn.clicked.connect(lambda: print("Мой профиль"))
        self.left_panel.allDocsBtn.clicked.connect(lambda: print("Все документы"))
        self.left_panel.systemBtn.clicked.connect(lambda: print("Система"))

    def toggle_left_panel(self):
        """Скрывает/показывает левую панель"""
        if self.left_panel.isVisible():
            self.left_panel.hide()
            self.left_panel.hidePanelBtn.setText("▶ Показать панель")
        else:
            self.left_panel.show()
            self.left_panel.hidePanelBtn.setText("◀ Скрыть панель")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())