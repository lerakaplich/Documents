import os
import sys
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

# Определяем ROOT_DIR (как в вашем проекте)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LeftPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Путь к UI файлу
        ui_path = os.path.join(ROOT_DIR, "ui", "left_panel.ui")

        # Загружаем UI
        loadUi(ui_path, self)

        # Тестовые данные (заменят запрос к БД)
        # Здесь хранятся направления с полем enam
        self.directions = [
            {"enam": "Входящие документы", "type": "external"},
            {"enam": "Исходящие документы", "type": "external"},
            {"enam": "Договоры", "type": "external"},
            {"enam": "Приказы", "type": "internal"},
            {"enam": "Распоряжения", "type": "internal"},
            {"enam": "Акты", "type": "internal"},
            {"enam": "Протоколы", "type": "internal"},
            {"enam": "Служебные записки", "type": "internal"},
        ]

        # Настройка начальных состояний
        self.externalContent.setVisible(True)
        self.internalContent.setVisible(True)

        # Заполнение направлений из тестовых данных
        self.load_directions()

        # Подключение кнопок-переключателей
        self.externalToggleBtn.clicked.connect(self.toggle_external)
        self.internalToggleBtn.clicked.connect(self.toggle_internal)

        # Пример подключения других кнопок (по желанию)
        # self.profileBtn.clicked.connect(self.on_profile_clicked)
        # self.allDocsBtn.clicked.connect(self.on_alldocs_clicked)
        # self.systemBtn.clicked.connect(self.on_system_clicked)
        # self.hidePanelBtn.clicked.connect(self.on_hide_panel_clicked)

    def load_directions(self):
        """Загружает направления из тестовых данных в соответствующие контейнеры"""
        # Очищаем существующие кнопки
        self.clear_direction_buttons()

        # Фильтруем и добавляем кнопки для внешних направлений
        external_directions = [d for d in self.directions if d["type"] == "external"]
        for direction in external_directions:
            btn = self.create_direction_button(direction["enam"])
            self.externalContentLayout.addWidget(btn)

        # Фильтруем и добавляем кнопки для внутренних направлений
        internal_directions = [d for d in self.directions if d["type"] == "internal"]
        for direction in internal_directions:
            btn = self.create_direction_button(direction["enam"])
            self.internalContentLayout.addWidget(btn)

    def create_direction_button(self, text):
        """Создает кнопку для направления"""
        btn = QPushButton(text)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #B8C5D1;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 13px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #2A3A44;
                color: #DDB87A;
            }
            QPushButton:pressed {
                background-color: #1B232A;
            }
        """)
        btn.clicked.connect(lambda checked, t=text: self.on_direction_clicked(t))
        return btn

    def clear_direction_buttons(self):
        """Очищает все кнопки направлений из контейнеров"""
        # Очищаем externalContentLayout
        while self.externalContentLayout.count():
            item = self.externalContentLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Очищаем internalContentLayout
        while self.internalContentLayout.count():
            item = self.internalContentLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def toggle_external(self):
        """Показывает/скрывает внешние направления"""
        is_visible = self.externalContent.isVisible()
        self.externalContent.setVisible(not is_visible)

        # Меняем иконку/текст кнопки
        if not is_visible:
            self.externalToggleBtn.setText("▼ Внешние")
        else:
            self.externalToggleBtn.setText("▶ Внешные")

    def toggle_internal(self):
        """Показывает/скрывает внутренние направления"""
        is_visible = self.internalContent.isVisible()
        self.internalContent.setVisible(not is_visible)

        # Меняем иконку/текст кнопки
        if not is_visible:
            self.internalToggleBtn.setText("▼ Внутренние")
        else:
            self.internalToggleBtn.setText("▶ Внутренние")

    def on_direction_clicked(self, direction_name):
        """Обработчик клика по направлению"""
        print(f"Выбрано направление: {direction_name}")
        # Здесь можно добавить логику загрузки документов по направлению
        # Например: self.parent().load_documents_by_direction(direction_name)

    # Примеры обработчиков для других кнопок (раскомментируйте при необходимости)
    """
    def on_profile_clicked(self):
        print("Мой профиль")

    def on_alldocs_clicked(self):
        print("Все документы")

    def on_system_clicked(self):
        print("Система")

    def on_hide_panel_clicked(self):
        print("Скрыть панель")
    """


# Пример запуска для тестирования (раскомментируйте для отладки)
"""
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Создаем временную структуру папок для теста
    if not os.path.exists(os.path.join(ROOT_DIR, "ui")):
        os.makedirs(os.path.join(ROOT_DIR, "ui"))

    window = LeftPanel()
    window.show()
    sys.exit(app.exec())
"""