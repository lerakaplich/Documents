import os
import sys
from typing import List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QApplication,
    QSpacerItem, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal
from PyQt6.uic import loadUi

from client.windows.left_panel.direction_group import DirectionGroup

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LeftPanel(QWidget):
    """Левая панель с динамическими группами направлений и анимацией сворачивания"""

    # Сигналы
    direction_clicked = pyqtSignal(str, str)
    profile_clicked = pyqtSignal()
    all_documents_clicked = pyqtSignal()
    system_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumWidth(50)
        self.setMaximumWidth(280)
        self.is_expanded = True

        # Загружаем UI
        ui_path = os.path.join(ROOT_DIR, "ui", "left_panel.ui")
        if os.path.exists(ui_path):
            loadUi(ui_path, self)


        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Скрываем старые виджеты
        for widget_name in ['externalWidget', 'internalWidget']:
            if hasattr(self, widget_name):
                widget = getattr(self, widget_name)
                widget.hide()
                widget.deleteLater()

        self.groups: Dict[str, DirectionGroup] = {}

        self.setup_groups_container()
        self.setup_buttons()

        # Анимация
        self.collapse_animation = QPropertyAnimation(self, b"panelWidth")
        self.collapse_animation.setDuration(300)
        self.collapse_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.collapse_animation.finished.connect(self.on_animation_finished)

        self.load_test_data()

    def create_fallback_ui(self):
        """Создает UI с разделением на верхнюю и нижнюю части"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ====================== ВЕРХНЯЯ ЧАСТЬ ======================
        self.top_widget = QWidget()
        top_layout = QVBoxLayout(self.top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        self.profileBtn = QPushButton("👤 Мой профиль")
        self.profileBtn.setStyleSheet(self._get_button_style())
        self.profileBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        top_layout.addWidget(self.profileBtn)

        self.allDocsBtn = QPushButton("📄 Все документы")
        self.allDocsBtn.setStyleSheet(self._get_button_style())
        self.allDocsBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        top_layout.addWidget(self.allDocsBtn)

        # ScrollArea
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setStyleSheet("border: none; background-color: transparent;")

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scrollArea.setWidget(scroll_content)

        top_layout.addWidget(self.scrollArea)
        top_layout.addStretch(1)

        main_layout.addWidget(self.top_widget)

        # ====================== НИЖНЯЯ ЧАСТЬ (всегда внизу) ======================
        self.bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(self.bottom_widget)
        bottom_layout.setContentsMargins(8, 8, 8, 12)
        bottom_layout.setSpacing(6)

        self.systemBtn = QPushButton("⚙️ Система")
        self.systemBtn.setStyleSheet(self._get_button_style())
        self.systemBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom_layout.addWidget(self.systemBtn)

        self.hidePanelBtn = QPushButton("◀ Скрыть панель")
        self.hidePanelBtn.setStyleSheet(self._get_collapse_button_style())
        self.hidePanelBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        bottom_layout.addWidget(self.hidePanelBtn)

        main_layout.addWidget(self.bottom_widget)

    def _get_button_style(self):
        return """
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
            """

    def _get_collapse_button_style(self):
        return """
                QPushButton {
                    background-color: #2A3A44;
                    color: #DDB87A;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 12px;
                    font-size: 12px;
                    text-align: center;
                }
                QPushButton:hover {
                    background-color: #3A4A54;
                }
            """

    def _get_compact_button_style(self):
        return """
                QPushButton {
                    background-color: transparent;
                    color: #DDB87A;
                    border: none;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 20px;
                    text-align: center;
                    min-height: 42px;
                }
                QPushButton:hover {
                    background-color: #3A4A54;
                }
            """

    def setup_buttons(self):
        if hasattr(self, 'profileBtn'):
            self.profileBtn.clicked.connect(self.on_profile_clicked)
        if hasattr(self, 'allDocsBtn'):
            self.allDocsBtn.clicked.connect(self.on_all_documents_clicked)
        if hasattr(self, 'systemBtn'):
            self.systemBtn.clicked.connect(self.on_system_clicked)
        if hasattr(self, 'hidePanelBtn'):
            self.hidePanelBtn.clicked.connect(self.toggle_panel)


    def setup_groups_container(self):
        """Создает контейнер для групп направлений в scrollArea"""
        try:
            if not hasattr(self, 'scrollArea'):
                print("Ошибка: в UI нет scrollArea")
                return

            scroll_content = self.scrollArea.widget()
            if not scroll_content:
                scroll_content = QWidget()
                scroll_content.setObjectName("scrollContent")
                self.scrollArea.setWidget(scroll_content)

            scroll_layout = scroll_content.layout()
            if not scroll_layout:
                scroll_layout = QVBoxLayout(scroll_content)
                scroll_layout.setSpacing(10)
                scroll_layout.setContentsMargins(0, 0, 0, 0)

            # Создаем контейнер для групп
            self.groups_container = QWidget()
            self.groups_container.setObjectName("groupsContainer")
            self.groups_layout = QVBoxLayout(self.groups_container)
            self.groups_layout.setSpacing(10)
            self.groups_layout.setContentsMargins(0, 0, 0, 0)

            # Добавляем в начало scroll_layout
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

    # ========== АНИМАЦИЯ ==========

    @pyqtProperty(int)
    def panelWidth(self):
        """Свойство для анимации ширины панели"""
        return self.width()

    @panelWidth.setter
    def panelWidth(self, width):
        """Установщик ширины для анимации"""
        self.setFixedWidth(width)

    def toggle_panel(self):
        """Сворачивает/разворачивает панель с анимацией"""
        print(f"LeftPanel: toggle_panel, текущее состояние: {self.is_expanded}")

        self.collapse_animation.stop()

        if self.is_expanded:
            # Сворачиваем
            self.collapse_animation.setStartValue(280)
            self.collapse_animation.setEndValue(50)
            self.is_expanded = False
            self.toggle_buttons_visibility(False)
        else:
            # Разворачиваем
            self.collapse_animation.setStartValue(50)
            self.collapse_animation.setEndValue(280)
            self.is_expanded = True
            self.toggle_buttons_visibility(True)

        self.collapse_animation.start()

    def on_animation_finished(self):
        """Обработчик завершения анимации"""
        print(f"LeftPanel: анимация завершена, ширина: {self.width()}")

        # Принудительно обновляем геометрию
        self.updateGeometry()
        if self.parent():
            self.parent().update()

    def toggle_buttons_visibility(self, visible: bool):
        """Только скрываем/показываем контент, не трогаем структуру layout"""
        # Верхние кнопки
        if hasattr(self, 'profileBtn'):
            self.profileBtn.setText("👤 Мой профиль" if visible else "👤")
            self.profileBtn.setStyleSheet(self._get_button_style() if visible else self._get_compact_button_style())

        if hasattr(self, 'allDocsBtn'):
            self.allDocsBtn.setText("📄 Все документы" if visible else "📄")
            self.allDocsBtn.setStyleSheet(self._get_button_style() if visible else self._get_compact_button_style())

        # Нижние кнопки
        if hasattr(self, 'systemBtn'):
            self.systemBtn.setText("⚙️ Система" if visible else "⚙️")
            self.systemBtn.setStyleSheet(self._get_button_style() if visible else self._get_compact_button_style())

        if hasattr(self, 'hidePanelBtn'):
            self.hidePanelBtn.setText("◀ Скрыть панель" if visible else "▶")

        # Главное — скрываем только содержимое групп
        if hasattr(self, 'scrollArea'):
            self.scrollArea.setVisible(visible)

        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()

    # ========== ОБРАБОТЧИКИ КНОПОК ==========

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

    def on_direction_clicked(self, direction_name: str, group_name: str):
        """Обработчик клика по направлению"""
        print(f"Выбрано направление: {direction_name} (группа: {group_name})")
        self.direction_clicked.emit(direction_name, group_name)

    # ========== УПРАВЛЕНИЕ ГРУППАМИ ==========

    def expand_all_groups(self):
        """Разворачивает все группы"""
        for group in self.groups.values():
            if not group.is_expanded:
                group.toggle_content()

    def collapse_all_groups(self):
        """Сворачивает все группы"""
        for group in self.groups.values():
            if group.is_expanded:
                group.toggle_content()

    def expand(self):
        """Развернуть панель программно"""
        if not self.is_expanded:
            self.toggle_panel()

    def collapse(self):
        """Свернуть панель программно"""
        if self.is_expanded:
            self.toggle_panel()


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = LeftPanel()
    window.setWindowTitle("Left Panel Test")
    window.setStyleSheet("background-color: #2A3A44;")
    window.show()

    sys.exit(app.exec())