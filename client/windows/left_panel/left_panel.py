import os
import sys
from typing import List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QApplication,
    QSpacerItem, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QSize
from PyQt6.QtGui import QIcon
from PyQt6.uic import loadUi

from client.core.data.document_data import DocumentDataConfig
from client.core.themes import apply_theme_to_widget, T, get_manager
from client.windows.left_panel.direction_group import DirectionGroup

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class LeftPanel(QWidget):
    """Левая панель с динамическими группами направлений и анимацией сворачивания"""

    # Сигналы
    direction_clicked = pyqtSignal(str, str)  # (direction_name, group_name)
    type_clicked = pyqtSignal(int, str)  # (type_id, type_name)
    profile_clicked = pyqtSignal()
    all_documents_clicked = pyqtSignal()
    system_clicked = pyqtSignal()
    logout_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Константы для размеров панели
        self.COLLAPSED_WIDTH = 80
        self.EXPANDED_WIDTH = 280

        self.setMinimumWidth(self.COLLAPSED_WIDTH)
        self.setMaximumWidth(self.EXPANDED_WIDTH)
        self.is_expanded = True

        # Загружаем UI
        ui_path = os.path.join(ROOT_DIR, "ui", "left_panel.ui")
        if os.path.exists(ui_path):
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)  # ← ДО loadUi
            loadUi(ui_path, self)
            apply_theme_to_widget(self)
            from client.core.themes import get_manager
            _t = get_manager().current
            self.setStyleSheet(
                f"QWidget#LeftPanel {{ background-color: {_t.SIDEBAR_BG}; }}"
            )


        # Настройка иконок для всех кнопок (унифицированный размер 20x20)
        self.setup_icons()

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

        # Загружаем данные из DocumentDataConfig
        self.load_from_data()

    def setup_icons(self):
        """Настраивает иконки для всех кнопок с единым размером"""
        icons_path = "D:/Documents/client/icons"
        icon_size = QSize(20, 20)  # Унифицированный размер для всех иконок

        icon_mapping = {
            'profileBtn': 'profile_white.svg',
            'allDocsBtn': 'folder.svg',
            'systemBtn': 'gear.svg',
            'logoutBtn': 'logout.svg',
            'hidePanelBtn': 'hide.svg'  # Добавляем иконку для скрытия панели
        }

        for btn_name, icon_file in icon_mapping.items():
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                icon_path = os.path.join(icons_path, icon_file)
                if os.path.exists(icon_path):
                    icon = QIcon(icon_path)
                    btn.setIcon(icon)
                    btn.setIconSize(icon_size)
                else:
                    print(f"Предупреждение: иконка не найдена - {icon_path}")

    def create_fallback_ui(self):
        """Создает UI с разделением на верхнюю и нижнюю части"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ВЕРХНЯЯ ЧАСТЬ
        self.top_widget = QWidget()
        top_layout = QVBoxLayout(self.top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        self.profileBtn = QPushButton("Мой профиль")
        self.profileBtn.setStyleSheet(self._get_button_style())
        self.profileBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_button_icon(self.profileBtn, "profile_white.svg", QSize(20, 20))
        top_layout.addWidget(self.profileBtn)

        self.allDocsBtn = QPushButton("Все документы")
        self.allDocsBtn.setStyleSheet(self._get_button_style())
        self.allDocsBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_button_icon(self.allDocsBtn, "folder.svg", QSize(20, 20))
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

        # НИЖНЯЯ ЧАСТЬ
        self.bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(self.bottom_widget)
        bottom_layout.setContentsMargins(8, 8, 8, 12)
        bottom_layout.setSpacing(6)

        self.systemBtn = QPushButton("Система")
        self.systemBtn.setStyleSheet(self._get_button_style())
        self.systemBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_button_icon(self.systemBtn, "gear.svg", QSize(20, 20))
        bottom_layout.addWidget(self.systemBtn)

        self.logoutBtn = QPushButton("Выйти из аккаунта")
        self.logoutBtn.setStyleSheet(self._get_button_style())
        self.logoutBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_button_icon(self.logoutBtn, "logout.svg", QSize(20, 20))
        bottom_layout.addWidget(self.logoutBtn)

        self.hidePanelBtn = QPushButton("Скрыть панель")
        self.hidePanelBtn.setStyleSheet(self._get_collapse_button_style())
        self.hidePanelBtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_button_icon(self.hidePanelBtn, "hide.svg", QSize(20, 20))
        bottom_layout.addWidget(self.hidePanelBtn)

        main_layout.addWidget(self.bottom_widget)

    def set_button_icon(self, button, icon_name, icon_size):
        """Устанавливает иконку для кнопки с указанным размером"""
        icons_path = "D:/Documents/client/icons"
        icon_path = os.path.join(icons_path, icon_name)
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            button.setIcon(icon)
            button.setIconSize(icon_size)

    def _get_button_style(self):
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {T.SIDEBAR_TEXT};
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {T.SIDEBAR_HOVER_BG};
                color: {T.SIDEBAR_HOVER_TEXT};
            }}
            QPushButton::icon {{
                width: 20px;
                height: 20px;
            }}
        """

    def _get_collapse_button_style(self):
        return f"""
            QPushButton {{
                background-color: {T.SIDEBAR_DIVIDER};
                color: {T.SIDEBAR_HOVER_TEXT};
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 12px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {T.SIDEBAR_HOVER_BG};
            }}
            QPushButton::icon {{
                width: 20px;
                height: 20px;
            }}
        """

    def _get_compact_button_style(self):
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {T.SIDEBAR_HOVER_TEXT};
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 20px;
                text-align: center;
                min-height: 42px;
            }}
            QPushButton:hover {{
                background-color: {T.SIDEBAR_HOVER_BG};
            }}
            QPushButton::icon {{
                width: 24px;
                height: 24px;
            }}
        """

    def _get_compact_logout_style(self):
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {T.SIDEBAR_HOVER_TEXT};
                border: none;
                border-radius: 5px;
                padding: 10px;
                text-align: center;
                min-height: 42px;
            }}
            QPushButton:hover {{
                background-color: {T.SIDEBAR_HOVER_BG};
            }}
            QPushButton QIcon {{
                padding: 8px;
            }}
            QPushButton::icon {{
                width: 24px;
                height: 24px;
            }}
        """

    def setup_buttons(self):
        if hasattr(self, 'profileBtn'):
            self.profileBtn.clicked.connect(self.on_profile_clicked)
        if hasattr(self, 'allDocsBtn'):
            self.allDocsBtn.clicked.connect(self.on_all_documents_clicked)
        if hasattr(self, 'systemBtn'):
            self.systemBtn.clicked.connect(self.on_system_clicked)
        if hasattr(self, 'logoutBtn'):
            self.logoutBtn.clicked.connect(self.on_logout_clicked)
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
            _t = get_manager().current
            for w in (self.scrollArea, self.scrollArea.widget(), self.groups_container):
                if w:
                    w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                    w.setStyleSheet(f"background-color: {_t.SIDEBAR_BG};")
            # Добавляем в начало scroll_layout
            scroll_layout.insertWidget(0, self.groups_container)

            print("LeftPanel: контейнер для групп создан")

        except Exception as e:
            print(f"LeftPanel: ошибка при создании контейнера групп - {e}")

    def toggle_buttons_visibility(self, visible: bool):
        """Только скрываем/показываем контент, не трогаем структуру layout"""
        # Верхние кнопки
        if hasattr(self, 'profileBtn'):
            self.profileBtn.setText("Мой профиль" if visible else "")
            self.profileBtn.setStyleSheet(self._get_button_style() if visible else self._get_compact_button_style())
            if not visible:
                self.profileBtn.setIconSize(QSize(24, 24))
            else:
                self.profileBtn.setIconSize(QSize(20, 20))

        if hasattr(self, 'allDocsBtn'):
            self.allDocsBtn.setText("Все документы" if visible else "")
            self.allDocsBtn.setStyleSheet(self._get_button_style() if visible else self._get_compact_button_style())
            if not visible:
                self.allDocsBtn.setIconSize(QSize(24, 24))
            else:
                self.allDocsBtn.setIconSize(QSize(20, 20))

        # Нижние кнопки
        if hasattr(self, 'systemBtn'):
            self.systemBtn.setText("Система" if visible else "")
            self.systemBtn.setStyleSheet(self._get_button_style() if visible else self._get_compact_button_style())
            if not visible:
                self.systemBtn.setIconSize(QSize(24, 24))
            else:
                self.systemBtn.setIconSize(QSize(20, 20))

        if hasattr(self, 'logoutBtn'):
            if visible:
                self.logoutBtn.setText("Выйти из аккаунта")
                self.logoutBtn.setStyleSheet(self._get_button_style())
                self.logoutBtn.setIconSize(QSize(20, 20))
            else:
                self.logoutBtn.setText("")
                self.logoutBtn.setStyleSheet(self._get_compact_logout_style())
                self.logoutBtn.setIconSize(QSize(24, 24))

        if hasattr(self, 'hidePanelBtn'):
            if visible:
                self.hidePanelBtn.setText("Скрыть панель")
                self.hidePanelBtn.setStyleSheet(self._get_collapse_button_style())
                self.hidePanelBtn.setIconSize(QSize(20, 20))
            else:
                self.hidePanelBtn.setText("")
                self.hidePanelBtn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {T.SIDEBAR_HOVER_TEXT};
                        border: none;
                        border-radius: 5px;
                        padding: 10px;
                        text-align: center;
                        min-height: 42px;
                    }}
                    QPushButton:hover {{
                        background-color: {T.SIDEBAR_HOVER_BG};
                    }}
                    QPushButton::icon {{
                        width: 24px;
                        height: 24px;
                    }}
                """)
                self.hidePanelBtn.setIconSize(QSize(24, 24))

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

    def on_logout_clicked(self):
        """Обработчик клика по кнопке выхода"""
        print("Нажата кнопка выхода из аккаунта")
        self.logout_clicked.emit()

    def add_group(self, group_name: str) -> DirectionGroup:
        """Добавляет новую группу направлений"""
        if group_name in self.groups:
            return self.groups[group_name]

        group = DirectionGroup(group_name)
        self.groups[group_name] = group
        self.groups_layout.addWidget(group)
        return group

    def add_direction(self, group_name: str, direction_name: str, metadata: Dict[str, Any] = None):
        """Добавляет направление (тип документа) в указанную группу"""
        group = self.add_group(group_name)

        # Сохраняем type_id в метаданных для передачи при клике
        type_id = metadata.get("type_id") if metadata else None

        def on_click(name):
            self.on_direction_clicked(name, group_name, type_id)

        group.add_direction(direction_name, on_click)

    def clear_all_directions(self):
        """Очищает все направления и группы"""
        for group in self.groups.values():
            group.clear_directions()
        self.groups.clear()

        while self.groups_layout.count():
            item = self.groups_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def load_from_data(self, data: List[Dict[str, Any]] = None):
        """
        Загружает направления из данных.
        Если данные не переданы, использует DocumentDataConfig.get_directions_data()
        """
        if data is None:
            data = DocumentDataConfig.get_directions_data()

        self.clear_all_directions()

        for group_data in data:
            group_name = group_data.get("group", "Без группы")
            directions = group_data.get("directions", [])

            for direction in directions:
                direction_name = direction.get("name")
                if direction_name:
                    self.add_direction(group_name, direction_name, direction)

        print(f"LeftPanel: загружено {len(data)} групп, {sum(len(g.get('directions', [])) for g in data)} направлений")

    def load_test_data(self):
        """Загружает тестовые данные из DocumentDataConfig"""
        self.load_from_data()

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
            self.collapse_animation.setStartValue(self.EXPANDED_WIDTH)
            self.collapse_animation.setEndValue(self.COLLAPSED_WIDTH)
            self.is_expanded = False
            self.toggle_buttons_visibility(False)
            self.update_hide_button_icon()
        else:
            self.collapse_animation.setStartValue(self.COLLAPSED_WIDTH)
            self.collapse_animation.setEndValue(self.EXPANDED_WIDTH)
            self.is_expanded = True
            self.toggle_buttons_visibility(True)

        self.collapse_animation.start()

    def on_animation_finished(self):
        """Обработчик завершения анимации"""
        print(f"LeftPanel: анимация завершена, ширина: {self.width()}")

        self.updateGeometry()
        if self.parent():
            self.parent().update()

    def on_direction_clicked(self, direction_name: str, group_name: str, type_id: int = None):
        """Обработчик клика по направлению (типу документа)"""
        print(f"Выбрано направление: {direction_name} (группа: {group_name}, type_id: {type_id})")

        if type_id is not None:
            self.type_clicked.emit(type_id, direction_name)
        else:
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

    def get_group_by_name(self, group_name: str) -> DirectionGroup:
        """Получить группу по имени"""
        return self.groups.get(group_name)

    def update_hide_button_icon(self):
        """Обновляет иконку кнопки скрытия панели в зависимости от состояния"""
        if hasattr(self, 'hidePanelBtn'):
            icons_path = "D:/Documents/client/icons"

            if self.is_expanded:
                # Панель развернута - показываем стрелку влево (свернуть)
                icon_file = "hide.svg"  # Стрелка влево
            else:
                # Панель свернута - показываем стрелку вправо (развернуть)
                icon_file = "show.svg"  # Стрелка вправо

            icon_path = os.path.join(icons_path, icon_file)
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                self.hidePanelBtn.setIcon(icon)
                self.hidePanelBtn.setIconSize(QSize(20, 20) if self.is_expanded else QSize(24, 24))


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = LeftPanel()
    window.setWindowTitle("Left Panel Test")
    window.setStyleSheet("background-color: #2A3A44;")
    window.show()

    sys.exit(app.exec())