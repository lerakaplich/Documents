from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QEasingCurve, QPropertyAnimation, QTimer

from client.core.themes import get_manager


class CollapsibleGroup(QWidget):
    """Виджет с возможностью сворачивания/разворачивания с анимацией"""

    def __init__(self, title, is_expanded=False, parent=None):
        super().__init__(parent)

        self.is_expanded = is_expanded
        self.content_widgets = []
        self._content_height = 0
        self._is_animating = False
        self._update_timer = None

        # Главный layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        self.header = QPushButton()
        _t = get_manager().current
        self.header.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                background-color: {_t.BG_SURFACE_HEADER};
                border: 1px solid {_t.BORDER_DEFAULT};
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 14px;
                font-weight: bold;
                color: {_t.TEXT_HEADING};
            }}
            QPushButton:hover {{
                background-color: {_t.BG_HOVER_ALT};
            }}
        """)
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(self.toggle)

        # Контент
        self.content_area = QWidget()
        self.content_area.setStyleSheet("background-color: transparent;")
        self.content_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )

        self.content_area_layout = QVBoxLayout(self.content_area)
        self.content_area_layout.setSpacing(10)
        self.content_area_layout.setContentsMargins(15, 10, 15, 10)
        # Убираем ограничение по высоте для контента
        self.content_area.setMinimumHeight(0)

        # Добавляем в основной layout
        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.content_area)

        # Анимация для высоты контента
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.finished.connect(self._on_animation_finished)

        # Настройка начального состояния
        self.set_title(title)

        # Устанавливаем начальное состояние
        if is_expanded:
            self.content_area.setVisible(True)
            self.content_area.setMaximumHeight(0)
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

        # Временно показываем для расчета
        self.content_area.setVisible(True)
        self.content_area.setMaximumHeight(16777215)

        # Принудительно обновляем геометрию
        self.content_area_layout.activate()
        self.content_area.updateGeometry()

        # Получаем рекомендуемую высоту
        height = self.content_area.sizeHint().height()

        # Если height = 0, пробуем альтернативный способ расчета
        if height == 0:
            total_height = 0
            for i in range(self.content_area_layout.count()):
                item = self.content_area_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    # Даем виджету правильно рассчитать размер
                    widget.updateGeometry()
                    widget_height = widget.sizeHint().height()
                    if widget_height > 0:
                        total_height += widget_height + self.content_area_layout.spacing()
            height = total_height if total_height > 0 else 100  # Минимальная высота

        # Восстанавливаем состояние
        self.content_area.setMaximumHeight(old_max_height)
        if not was_visible:
            self.content_area.setVisible(False)

        # Добавляем отступы
        margins = self.content_area_layout.contentsMargins()
        height += margins.top() + margins.bottom()

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

        # Если анимация уже идет, останавливаем
        if self._is_animating:
            self.animation.stop()
            self._is_animating = False

        self.is_expanded = expanded
        self.update_arrow()

        if expanded:
            # Обновляем высоту перед разворачиванием
            self.update_content_height()

            if self._content_height <= 0:
                # Если высота не рассчиталась, пробуем еще раз с задержкой
                QTimer.singleShot(50, self._retry_expand)
                return

            if animated:
                self._is_animating = True
                self.content_area.setVisible(True)
                self.animation.setStartValue(0)
                self.animation.setEndValue(self._content_height)
                self.animation.start()
            else:
                self.content_area.setVisible(True)
                self.content_area.setMaximumHeight(self._content_height)
                self.content_area.updateGeometry()
        else:
            if animated and self.content_area.isVisible() and self.content_area.height() > 0:
                self._is_animating = True
                current_height = self.content_area.height()
                if current_height <= 0:
                    current_height = self._content_height
                self.animation.setStartValue(current_height)
                self.animation.setEndValue(0)
                self.animation.start()
            else:
                self.content_area.setMaximumHeight(0)
                self.content_area.setVisible(False)
                self.content_area.updateGeometry()

    def _retry_expand(self):
        """Повторная попытка развернуть группу"""
        if self.is_expanded:
            self.update_content_height()
            if self._content_height > 0:
                self.content_area.setVisible(True)
                self.content_area.setMaximumHeight(self._content_height)
                self.content_area.updateGeometry()
            else:
                # Если все еще 0, устанавливаем минимальную высоту
                self._content_height = 100
                self.content_area.setVisible(True)
                self.content_area.setMaximumHeight(self._content_height)
                self.content_area.updateGeometry()

    def _on_animation_finished(self):
        """Обработчик завершения анимации"""
        self._is_animating = False
        if not self.is_expanded:
            self.content_area.setMaximumHeight(0)
            self.content_area.setVisible(False)
        else:
            # Разрешаем контейнеру подстраиваться под гибкий размер карточек!
            self.content_area.setMaximumHeight(16777215)  # QWIDGET_SIZE_MAX
            self.content_area.updateGeometry()

    def add_widget(self, widget):
        """Добавляет виджет в контент"""
        # Устанавливаем правильную политику размера
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred  # Изменено с Fixed на Minimum
        )

        self.content_area_layout.addWidget(widget)
        self.content_widgets.append(widget)

        # Если группа развернута, обновляем высоту с задержкой
        if self.is_expanded:
            # Отменяем предыдущий таймер
            if self._update_timer:
                self._update_timer.stop()
            self._update_timer = QTimer()
            self._update_timer.setSingleShot(True)
            self._update_timer.timeout.connect(self._delayed_height_update)
            self._update_timer.start(50)

    def _delayed_height_update(self):
        """Отложенное обновление высоты после добавления виджетов"""
        if self._update_timer:
            self._update_timer = None

        if self.is_expanded and self.content_widgets:
            new_height = self.update_content_height()

            if new_height > 0:
                self._content_height = new_height
                self.content_area.setVisible(True)
                # Если анимация не идет, даем layout'у полную свободу
                if not self._is_animating:
                    self.content_area.setMaximumHeight(16777215)
                self.content_area.updateGeometry()
                self.updateGeometry()
                if self.parent():
                    self.parent().updateGeometry()

    def remove_widget(self, widget):
        """Удаляет виджет из контента"""
        if widget in self.content_widgets:
            self.content_widgets.remove(widget)
            self.content_area_layout.removeWidget(widget)
            widget.deleteLater()

            if self.is_expanded:
                if self._update_timer:
                    self._update_timer.stop()
                self._update_timer = QTimer()
                self._update_timer.setSingleShot(True)
                self._update_timer.timeout.connect(self._delayed_height_update)
                self._update_timer.start(50)

    def clear_content(self):
        """Очищает весь контент"""
        for widget in self.content_widgets:
            widget.deleteLater()
        self.content_widgets.clear()

        if self._update_timer:
            self._update_timer.stop()
            self._update_timer = None

        if self.is_expanded:
            self._content_height = 0
            self.content_area.setMaximumHeight(0)
            self.content_area.setVisible(False)

    def showEvent(self, event):
        """Обработчик события показа виджета"""
        super().showEvent(event)
        # При показе обновляем высоту
        if self.is_expanded and self.content_widgets:
            QTimer.singleShot(100, self._delayed_height_update)