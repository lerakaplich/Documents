import os
import sys
from typing import List, Dict, Any
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QApplication, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QTimer
from PyQt6.uic import loadUi

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class DirectionGroup(QWidget):
    """Виджет для группы направлений с анимацией"""

    def __init__(self, group_name: str, parent=None):
        super().__init__(parent)
        self.group_name = group_name
        self.is_expanded = True
        self.content_height = 0

        # Создаем layout для группы
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Кнопка-переключатель группы
        self.toggle_btn = QPushButton(f"▼ {group_name}")
        self.toggle_btn.setStyleSheet("""
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
        self.toggle_btn.clicked.connect(self.toggle_content)
        self.main_layout.addWidget(self.toggle_btn)

        # Контейнер для кнопок направлений (с анимацией)
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
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

            # Меняем иконку
            self.toggle_btn.setText(f"▶ {self.group_name}")
            self.is_expanded = False
        else:
            # Показываем контент с анимацией
            # Временно убираем ограничение, чтобы получить реальную высоту
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

            # Меняем иконку
            self.toggle_btn.setText(f"▼ {self.group_name}")
            self.is_expanded = True

        # Добавляем мини-анимацию нажатия на кнопку
        self.animate_button_press()

    def animate_button_press(self):
        """Мини-анимация при нажатии на кнопку"""
        original_style = self.toggle_btn.styleSheet()

        # Эффект нажатия
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A4A54;
                color: #DDB87A;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                text-align: left;
            }
        """)

        # Возвращаем исходный стиль через 100мс
        QTimer.singleShot(100, lambda: self.toggle_btn.setStyleSheet(original_style))

        # Эффект пульсации (изменение размера кнопки)
        pulse_animation = QPropertyAnimation(self.toggle_btn, b"geometry")
        pulse_animation.setDuration(150)
        pulse_animation.setEasingCurve(QEasingCurve.Type.OutBounce)

        # Сохраняем исходную геометрию
        original_geometry = self.toggle_btn.geometry()

        # Создаем немного увеличенную геометрию
        expanded_geometry = original_geometry.adjusted(-2, -1, 2, 1)

        # Настраиваем анимацию
        pulse_animation.setStartValue(original_geometry)
        pulse_animation.setKeyValueAt(0.5, expanded_geometry)
        pulse_animation.setEndValue(original_geometry)
        pulse_animation.start()

    def add_direction(self, direction_name: str, callback):
        """Добавляет направление в группу"""
        btn = QPushButton(direction_name)
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

        # Добавляем мини-анимацию при клике на направление
        def on_click():
            self.animate_direction_button(btn)
            callback(direction_name)

        btn.clicked.connect(on_click)
        self.content_layout.addWidget(btn)
        self.direction_buttons.append(btn)
        return btn

    def animate_direction_button(self, button):
        """Анимация при клике на кнопку направления"""
        # Визуальный эффект нажатия
        original_style = button.styleSheet()
        button.setStyleSheet("""
            QPushButton {
                background-color: #DDB87A;
                color: #1B232A;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 13px;
                text-align: left;
            }
        """)

        QTimer.singleShot(150, lambda: button.setStyleSheet(original_style))

        # Анимация смещения
        shift_animation = QPropertyAnimation(button, b"geometry")
        shift_animation.setDuration(100)
        shift_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        original_geometry = button.geometry()
        shifted_geometry = original_geometry.adjusted(5, 0, 5, 0)

        shift_animation.setStartValue(original_geometry)
        shift_animation.setEndValue(shifted_geometry)
        shift_animation.start()

        # Возвращаем обратно
        QTimer.singleShot(100, lambda: shift_animation.setEndValue(original_geometry))

    def clear_directions(self):
        """Очищает все направления в группе"""
        for btn in self.direction_buttons:
            btn.deleteLater()
        self.direction_buttons.clear()

    def set_compact_mode(self, compact: bool):
        """Устанавливает компактный режим (для свернутой панели)"""
        if compact:
            self.toggle_btn.setText("▼" if self.is_expanded else "▶")
        else:
            self.toggle_btn.setText(f"{'▼' if self.is_expanded else '▶'} {self.group_name}")