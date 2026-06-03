import os
import sys
from typing import List, Dict, Any
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, QEasingCurve, pyqtSignal
from PyQt6.uic import loadUi

from client.windows.animations.collapse_animation import CollapseAnimation
from client.windows.left_panel.direction_group import DirectionGroup

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LeftPanel(QWidget):
    """Левая панель с динамическими группами направлений"""

    # Сигнал при выборе направления
    direction_clicked = pyqtSignal(str, str)  # (direction_name, group_name)
    profile_clicked = pyqtSignal()  # Сигнал для открытия профиля
    all_documents_clicked = pyqtSignal()  # Сигнал для всех документов
    system_clicked = pyqtSignal()  # Сигнал для системы

    def __init__(self, parent=None):
        super().__init__(parent)

        try:
            print("LeftPanel: начало инициализации...")

            # Устанавливаем минимальную и максимальную ширину
            self.setMinimumWidth(50)
            self.setMaximumWidth(280)

            # Текущее состояние (развернута или свернута)
            self.is_expanded = True

            # Загружаем UI
            ui_path = os.path.join(ROOT_DIR, "ui", "left_panel.ui")
            print(f"LeftPanel: загрузка UI из {ui_path}")
            print(f"LeftPanel: файл существует - {os.path.exists(ui_path)}")

            if os.path.exists(ui_path):
                loadUi(ui_path, self)
                print("LeftPanel: UI загружен успешно")
            else:
                print(f"LeftPanel: UI файл не найден, создаем fallback UI")
                self.create_fallback_ui()

            # Включаем стилизацию фона
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

            # Скрываем старые виджеты
            if hasattr(self, 'externalWidget'):
                self.externalWidget.hide()
                self.externalWidget.deleteLater()

            if hasattr(self, 'internalWidget'):
                self.internalWidget.hide()
                self.internalWidget.deleteLater()

            # Контейнер для групп направлений
            self.groups: Dict[str, DirectionGroup] = {}

            # Создаем контейнер для групп в scrollArea
            self.setup_groups_container()

            # Подключаем кнопки
            self.setup_buttons()

            # Создаем анимацию используя универсальный класс
            self.collapse_animation = CollapseAnimation(
                self,
                collapsed_size=50,
                expanded_size=280,
                duration=300,
                easing_curve=QEasingCurve.Type.InOutCubic,
                orientation="horizontal"
            )

            # Подключаем сигналы анимации
            self.collapse_animation.state_changed.connect(self.on_animation_state_changed)
            self.collapse_animation.animation_finished.connect(self.on_animation_finished)

            # Изначально панель развернута
            self.setFixedWidth(280)

            # Загружаем тестовые данные
            self.load_test_data()

            print("LeftPanel: инициализация завершена успешно")

        except Exception as e:
            print(f"LeftPanel: ошибка при инициализации - {e}")
            import traceback
            traceback.print_exc()
            raise

    def create_fallback_ui(self):
        """Создает простой UI если файл не найден"""
        from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QScrollArea

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Кнопка профиля
        self.profileBtn = QPushButton("👤 Мой профиль")
        self.profileBtn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #3A4A54;
                color: #DDB87A;
            }
        """)
        main_layout.addWidget(self.profileBtn)

        # Кнопка всех документов
        self.allDocsBtn = QPushButton("📄 Все документы")
        self.allDocsBtn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #3A4A54;
                color: #DDB87A;
            }
        """)
        main_layout.addWidget(self.allDocsBtn)

        # Кнопка системы
        self.systemBtn = QPushButton("⚙️ Система")
        self.systemBtn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #3A4A54;
                color: #DDB87A;
            }
        """)
        main_layout.addWidget(self.systemBtn)

        # ScrollArea для групп
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setStyleSheet("border: none; background-color: transparent;")
        main_layout.addWidget(self.scrollArea)

        # Кнопка скрытия панели
        self.hidePanelBtn = QPushButton("◀ Скрыть панель")
        self.hidePanelBtn.setStyleSheet("""
            QPushButton {
                background-color: #2A3A44;
                color: #DDB87A;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 12px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #3A4A54;
            }
        """)
        main_layout.addWidget(self.hidePanelBtn)

    def setup_buttons(self):
        """Настройка кнопок"""
        if hasattr(self, 'profileBtn'):
            self.profileBtn.clicked.connect(self.on_profile_clicked)

        if hasattr(self, 'allDocsBtn'):
            self.allDocsBtn.clicked.connect(self.on_all_documents_clicked)

        if hasattr(self, 'systemBtn'):
            self.systemBtn.clicked.connect(self.on_system_clicked)

        if hasattr(self, 'hidePanelBtn'):
            self.hidePanelBtn.clicked.connect(self.toggle_panel)

    def on_profile_clicked(self):
        """Обработчик клика по кнопке профиля"""
        print("Нажата кнопка профиля")
        self.profile_clicked.emit()

    def on_all_documents_clicked(self):
        """Обработчик клика по кнопке всех документов"""
        print("Нажата кнопка всех документов")
        self.all_documents_clicked.emit()

    def on_system_clicked(self):
        """Обработчик клика по кнопке системы"""
        print("Нажата кнопка системы")
        self.system_clicked.emit()

    def setup_groups_container(self):
        """Создает контейнер для групп направлений в scrollArea"""
        try:
            from PyQt6.QtWidgets import QVBoxLayout

            if not hasattr(self, 'scrollArea'):
                print("Ошибка: в UI нет scrollArea")
                return

            scroll_content = self.scrollArea.widget()
            if not scroll_content:
                print("Ошибка: нет widget в scrollArea")
                return

            scroll_layout = scroll_content.layout()
            if not scroll_layout:
                print("Ошибка: нет layout в scrollContent")
                scroll_layout = QVBoxLayout(scroll_content)
                scroll_layout.setSpacing(10)
                scroll_layout.setContentsMargins(0, 0, 0, 0)

            # Создаем контейнер для групп
            self.groups_container = QWidget()
            self.groups_layout = QVBoxLayout(self.groups_container)
            self.groups_layout.setSpacing(10)
            self.groups_layout.setContentsMargins(0, 0, 0, 0)

            # Добавляем контейнер в scrollLayout
            scroll_layout.insertWidget(0, self.groups_container)

            print("LeftPanel: контейнер для групп создан")

        except Exception as e:
            print(f"LeftPanel: ошибка при создании контейнера групп - {e}")

    def add_group(self, group_name: str) -> DirectionGroup:
        """Добавляет новую группу направлений"""
        if group_name in self.groups:
            return self.groups[group_name]

        group = DirectionGroup(group_name)
        self.groups[group_name] = group
        self.groups_layout.addWidget(group)
        return group

    def add_direction(self, group_name: str, direction_name: str, metadata: Dict[str, Any] = None):
        """Добавляет направление в указанную группу"""
        group = self.add_group(group_name)
        group.add_direction(direction_name, lambda name: self.on_direction_clicked(name, group_name))

    def clear_all_directions(self):
        """Очищает все направления и группы"""
        for group in self.groups.values():
            group.clear_directions()
        self.groups.clear()

        while self.groups_layout.count():
            item = self.groups_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def load_from_data(self, data: List[Dict[str, Any]]):
        """Загружает направления из данных"""
        self.clear_all_directions()

        for group_data in data:
            group_name = group_data.get("group", "Без группы")
            directions = group_data.get("directions", [])

            for direction in directions:
                direction_name = direction.get("name") or direction.get("enam")
                if direction_name:
                    self.add_direction(group_name, direction_name, direction)

    def load_test_data(self):
        """Загружает тестовые данные"""
        test_data = [
            {
                "group": "Внешние документы",
                "directions": [
                    {"name": "Входящие документы", "type": "incoming"},
                    {"name": "Исходящие документы", "type": "outgoing"},
                    {"name": "Договоры", "type": "contract"},
                ]
            },
            {
                "group": "Внутренние документы",
                "directions": [
                    {"name": "Приказы", "type": "order"},
                    {"name": "Распоряжения", "type": "command"},
                    {"name": "Акты", "type": "act"},
                    {"name": "Протоколы", "type": "protocol"},
                    {"name": "Служебные записки", "type": "memo"},
                ]
            },
            {
                "group": "Финансовые документы",
                "directions": [
                    {"name": "Счета", "type": "invoice"},
                    {"name": "Накладные", "type": "waybill"},
                    {"name": "Акты сверки", "type": "reconciliation"},
                ]
            }
        ]

        self.load_from_data(test_data)

    def toggle_panel(self):
        """Сворачивает/разворачивает панель"""
        self.collapse_animation.toggle()

    def on_animation_state_changed(self, is_expanded):
        """Обработчик изменения состояния анимации"""
        print(f"LeftPanel: состояние изменилось на {'развернуто' if is_expanded else 'свернуто'}")
        self.is_expanded = is_expanded

        # Обновляем текст кнопки
        if hasattr(self, 'hidePanelBtn'):
            if is_expanded:
                self.hidePanelBtn.setText("◀ Скрыть панель")
            else:
                self.hidePanelBtn.setText("▶")

        # Обновляем видимость элементов
        self.toggle_buttons_visibility(is_expanded)

    def on_animation_finished(self):
        """Обработчик завершения анимации"""
        print("LeftPanel: анимация завершена")

    def toggle_buttons_visibility(self, visible):
        """Показывает/скрывает тексты на кнопках при сворачивании"""
        if hasattr(self, 'profileBtn'):
            self.profileBtn.setText("👤" if not visible else "Мой профиль")

        if hasattr(self, 'allDocsBtn'):
            self.allDocsBtn.setText("📄" if not visible else "Все документы")

        if hasattr(self, 'systemBtn'):
            self.systemBtn.setText("⚙️" if not visible else "Система")

        # Обновляем группы направлений
        for group in self.groups.values():
            group.set_compact_mode(not visible)

        # Показываем/скрываем контейнер с группами
        if hasattr(self, 'groups_container'):
            self.groups_container.setVisible(visible)

    def on_direction_clicked(self, direction_name: str, group_name: str):
        """Обработчик клика по направлению"""
        print(f"Выбрано направление: {direction_name} (группа: {group_name})")
        self.direction_clicked.emit(direction_name, group_name)

    def expand(self):
        """Развернуть панель программно"""
        self.collapse_animation.expand()

    def collapse(self):
        """Свернуть панель программно"""
        self.collapse_animation.collapse()


# Пример запуска для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = LeftPanel()
    window.setWindowTitle("Left Panel Test")
    window.show()

    sys.exit(app.exec())