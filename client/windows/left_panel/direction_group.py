import os
import sys
from typing import List, Dict, Any
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon
from PyQt6.uic import loadUi

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ICONS_PATH = "D:/Documents/client/icons"


class DirectionGroup(QWidget):
    """Виджет для группы направлений с анимацией"""

    def __init__(self, group_name: str, parent=None):
        super().__init__(parent)
        from client.core.themes import get_manager
        _t = get_manager().current

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {_t.SIDEBAR_BG};")
        self.group_name = group_name
        self.is_expanded = True
        self.content_height = 0

        # Создаем layout для группы
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Кнопка-переключатель группы (с иконкой-стрелкой)
        self.toggle_btn = QPushButton(group_name)
        self.toggle_btn.setIconSize(QSize(16, 16))
        self.toggle_btn.setStyleSheet(self._toggle_button_style())
        self.toggle_btn.clicked.connect(self.toggle_content)
        self.main_layout.addWidget(self.toggle_btn)

        # Устанавливаем иконку согласно текущему состоянию (раскрыто → вверх)
        self._update_toggle_icon()

        # Контейнер для кнопок направлений (с анимацией)
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(
            f"QWidget {{ background-color: {_t.SIDEBAR_BG}; }}"
        )
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(5)
        self.content_layout.setContentsMargins(10, 5, 0, 5)
        self.main_layout.addWidget(self.content_widget)

        # Анимация для контента
        self.animation = QPropertyAnimation(self.content_widget, b"maximumHeight")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # Изначально показываем контент
        self.content_widget.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX

        # Список кнопок направлений
        self.direction_buttons = []

    def _toggle_button_style(self) -> str:
        """Стиль кнопки-переключателя группы."""
        from client.core.themes import get_manager
        _t = get_manager().current
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {_t.SIDEBAR_TEXT};
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {_t.SIDEBAR_HOVER_BG};
                color: {_t.SIDEBAR_HOVER_TEXT};
            }}
            QPushButton::icon {{
                margin-right: 6px;
            }}
        """

    def _update_toggle_icon(self):
        """Обновляет иконку стрелки в зависимости от состояния группы.
        Раскрыта → up.svg (можно свернуть), скрыта → down.svg (можно развернуть).
        """
        icon_file = "up.svg" if self.is_expanded else "down.svg"
        icon_path = os.path.join(ICONS_PATH, icon_file)
        if os.path.exists(icon_path):
            self.toggle_btn.setIcon(QIcon(icon_path))
        else:
            print(f"DirectionGroup: иконка не найдена — {icon_path}")

    def toggle_content(self):
        """Показывает/скрывает содержимое группы с анимацией"""
        self.animation.stop()

        if self.is_expanded:
            # Скрываем контент с анимацией
            current_height = self.content_widget.height()
            self.content_widget.updateGeometry()
            self.content_widget.setMaximumHeight(current_height)

            # Запланируем анимацию скрытия
            def animate_hide():
                self.animation.setEndValue(0)
                self.animation.start()

            QTimer.singleShot(10, animate_hide)

            self.is_expanded = False
            self._update_toggle_icon()
        else:
            # Показываем контент с анимацией
            self.content_widget.setMaximumHeight(16777215)
            self.content_widget.updateGeometry()

            # Получаем желаемую высоту
            target_height = self.content_widget.sizeHint().height()

            # Устанавливаем текущую высоту для анимации
            self.content_widget.setMaximumHeight(0)
            self.content_widget.updateGeometry()

            # Запускаем анимацию расширения
            self.animation.setEndValue(target_height)
            self.animation.start()

            self.is_expanded = True
            self._update_toggle_icon()

        # Добавляем мини-анимацию нажатия на кнопку
        self.animate_button_press()

    def animate_button_press(self):
        """Мини-анимация при нажатии на кнопку"""
        from client.core.themes import get_manager
        _t = get_manager().current

        original_style = self.toggle_btn.styleSheet()

        # Эффект нажатия
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {_t.SIDEBAR_TEXT};
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {_t.SIDEBAR_HOVER_BG};
                color: {_t.SIDEBAR_HOVER_TEXT};
            }}
            QPushButton::icon {{
                margin-right: 6px;
            }}
        """)

        # Возвращаем исходный стиль через 100мс
        QTimer.singleShot(100, lambda: self.toggle_btn.setStyleSheet(original_style))

        # Эффект пульсации (изменение размера кнопки)
        pulse_animation = QPropertyAnimation(self.toggle_btn, b"geometry")
        pulse_animation.setDuration(150)
        pulse_animation.setEasingCurve(QEasingCurve.Type.OutBounce)

        original_geometry = self.toggle_btn.geometry()
        expanded_geometry = original_geometry.adjusted(-2, -1, 2, 1)

        pulse_animation.setStartValue(original_geometry)
        pulse_animation.setKeyValueAt(0.5, expanded_geometry)
        pulse_animation.setEndValue(original_geometry)
        pulse_animation.start()

    def _direction_button_style(self) -> str:
        """Стиль кнопки направления из АКТУАЛЬНОЙ темы."""
        from client.core.themes import get_manager
        _t = get_manager().current
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {_t.SIDEBAR_TEXT};
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 13px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {_t.SIDEBAR_HOVER_BG};
                color: {_t.SIDEBAR_HOVER_TEXT};
            }}
            QPushButton:pressed {{
                background-color: {_t.SIDEBAR_BG};
            }}
        """

    def add_direction(self, direction_name: str, callback):
        """Добавляет направление в группу"""
        btn = QPushButton(direction_name)
        btn.setStyleSheet(self._direction_button_style())

        def on_click():
            self.animate_direction_button(btn)
            callback(direction_name)

        btn.clicked.connect(on_click)
        self.content_layout.addWidget(btn)
        self.direction_buttons.append(btn)
        return btn

    def animate_direction_button(self, button):
        """Анимация при клике на кнопку направления"""
        from client.core.themes import get_manager
        t = get_manager().current

        original_style = button.styleSheet()
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.SIDEBAR_HOVER_TEXT};
                color: {t.SIDEBAR_BG};
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 13px;
                text-align: left;
            }}
        """)

        QTimer.singleShot(150, lambda: button.setStyleSheet(original_style))

        shift_animation = QPropertyAnimation(button, b"geometry")
        shift_animation.setDuration(100)
        shift_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        original_geometry = button.geometry()
        shifted_geometry = original_geometry.adjusted(5, 0, 5, 0)

        shift_animation.setStartValue(original_geometry)
        shift_animation.setEndValue(shifted_geometry)
        shift_animation.start()

        QTimer.singleShot(100, lambda: shift_animation.setEndValue(original_geometry))

    def clear_directions(self):
        """Очищает все направления в группе"""
        for btn in self.direction_buttons:
            btn.deleteLater()
        self.direction_buttons.clear()

    def reapply_theme(self):
        """Вызывается при смене темы."""
        from client.core.themes import get_manager
        _t = get_manager().current

        self.setStyleSheet(f"background-color: {_t.SIDEBAR_BG};")
        self.toggle_btn.setStyleSheet(self._toggle_button_style())
        self.content_widget.setStyleSheet(
            f"QWidget {{ background-color: {_t.SIDEBAR_BG}; }}"
        )

        for btn in self.direction_buttons:
            btn.setStyleSheet(self._direction_button_style())

    def set_compact_mode(self, compact: bool):
        """Устанавливает компактный режим (для свернутой панели)"""
        if compact:
            self.toggle_btn.setText("")
        else:
            self.toggle_btn.setText(self.group_name)
        self._update_toggle_icon()