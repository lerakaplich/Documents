# collapsible_group.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QEasingCurve, QPropertyAnimation, QTimer


class CollapsibleGroup(QWidget):
    """Виджет с возможностью сворачивания/разворачивания с анимацией"""

    def __init__(self, title, is_expanded=False, parent=None):
        super().__init__(parent)

        self.is_expanded = is_expanded
        self.content_widgets = []
        self._content_height = 0

        # Главный layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        self.header = QPushButton()
        self.header.setStyleSheet("""
            QPushButton {
                text-align: left;
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 14px;
                font-weight: bold;
                color: #333;
            }
            QPushButton:hover {
                background-color: #E9ECEF;
            }
        """)
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(self.toggle)

        # Контент
        self.content_area = QWidget()
        self.content_area.setStyleSheet("background-color: transparent;")
        self.content_area_layout = QVBoxLayout(self.content_area)
        self.content_area_layout.setSpacing(10)
        self.content_area_layout.setContentsMargins(15, 10, 15, 10)
        # УБИРАЕМ AlignTop - это причина проблемы!
        # self.content_area_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Добавляем в основной layout
        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.content_area)

        # Анимация для высоты контента
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.finished.connect(self._on_animation_finished)

        # Настройка начального состояния
        self.set_title(title)

        # Устанавливаем начальное состояние
        if is_expanded:
            self.content_area.setVisible(True)
            self.content_area.setMaximumHeight(0)  # Будет обновлено при добавлении виджетов
        else:
            self.content_area.setVisible(False)
            self.content_area.setMaximumHeight(0)

    def set_title(self, title):
        self.header_text = title
        self.update_arrow()

    def update_arrow(self):
        if self.is_expanded:
            self.header.setText(f"  ▼ {self.header_text}")
        else:
            self.header.setText(f"  ▶ {self.header_text}")

    def calculate_content_height(self):
        """Вычисляет необходимую высоту для контента"""
        if not self.content_widgets:
            return 0

        # Сохраняем текущее состояние
        was_visible = self.content_area.isVisible()
        old_max_height = self.content_area.maximumHeight()

        # Временно показываем и убираем ограничения для расчета
        self.content_area.setVisible(True)
        self.content_area.setMaximumHeight(16777215)

        # Принудительно обновляем геометрию
        self.content_area_layout.activate()

        # Даем время на обновление
        QApplication.processEvents()

        # Получаем рекомендуемую высоту
        height = self.content_area.sizeHint().height()

        # Восстанавливаем состояние
        self.content_area.setMaximumHeight(old_max_height)
        if not was_visible:
            self.content_area.setVisible(False)

        return max(height, 10)

    def update_content_height(self):
        """Обновляет сохраненную высоту контента"""
        if self.content_widgets:
            self._content_height = self.calculate_content_height()
        else:
            self._content_height = 0
        return self._content_height

    def toggle(self):
        """Переключает состояние"""
        self.set_expanded(not self.is_expanded, animated=True)

    def set_expanded(self, expanded, animated=True):
        """Устанавливает состояние развернутости"""
        if self.is_expanded == expanded and self._content_height > 0:
            return

        self.is_expanded = expanded
        self.update_arrow()

        if expanded:
            # Обновляем высоту перед разворачиванием
            self.update_content_height()

            if self._content_height <= 0:
                self.content_area.setVisible(False)
                return

            if animated:
                self.animation.stop()
                self.content_area.setVisible(True)
                self.animation.setStartValue(0)
                self.animation.setEndValue(self._content_height)
                self.animation.start()
            else:
                self.content_area.setVisible(True)
                self.content_area.setMaximumHeight(self._content_height)
        else:
            if animated and self.content_area.isVisible():
                self.animation.stop()
                current_height = self.content_area.height()
                self.animation.setStartValue(current_height)
                self.animation.setEndValue(0)
                self.animation.start()
            else:
                self.content_area.setMaximumHeight(0)
                self.content_area.setVisible(False)

    def _on_animation_finished(self):
        """Обработчик завершения анимации"""
        if not self.is_expanded:
            self.content_area.setMaximumHeight(0)
            self.content_area.setVisible(False)

    def add_widget(self, widget):
        """Добавляет виджет в контент"""
        # Устанавливаем правильную политику размера для добавляемого виджета
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        self.content_area_layout.addWidget(widget)
        self.content_widgets.append(widget)

        # Если группа развернута, обновляем высоту
        if self.is_expanded:
            QTimer.singleShot(10, self._delayed_height_update)

    def _delayed_height_update(self):
        """Отложенное обновление высоты после добавления виджетов"""
        if self.is_expanded and self.content_widgets:
            new_height = self.update_content_height()
            if new_height > 0:
                self.content_area.setVisible(True)
                self.content_area.setMaximumHeight(new_height)
                # Принудительно обновляем布局
                self.content_area_layout.activate()
                self.content_area.updateGeometry()

    def remove_widget(self, widget):
        """Удаляет виджет из контента"""
        if widget in self.content_widgets:
            self.content_widgets.remove(widget)
            self.content_area_layout.removeWidget(widget)
            widget.deleteLater()

            if self.is_expanded:
                QTimer.singleShot(10, self._delayed_height_update)

    def clear_content(self):
        """Очищает весь контент"""
        for widget in self.content_widgets:
            widget.deleteLater()
        self.content_widgets.clear()

        if self.is_expanded:
            self._content_height = 0
            self.content_area.setMaximumHeight(0)
            self.content_area.setVisible(False)