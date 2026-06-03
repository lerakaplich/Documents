from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsOpacityEffect, QFrame, QApplication
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer,
    QPoint, QParallelAnimationGroup, QSequentialAnimationGroup, pyqtSignal
)
from PyQt6.QtGui import QIcon, QColor, QPalette


class AnimatedNotification(QFrame):
    """Универсальное всплывающее уведомление с анимацией"""

    # Сигналы
    closed = pyqtSignal()
    action_clicked = pyqtSignal()

    # Типы уведомлений
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

    def __init__(self, parent=None, message="", notification_type=INFO,
                 duration=3000, show_action=False, action_text="Действие"):
        super().__init__(parent)

        self.notification_type = notification_type
        self.duration = duration
        self.show_action = show_action
        self.action_text = action_text

        # Настройка внешнего вида
        self.setFixedWidth(350)
        self.setMinimumHeight(60)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        # Настройка стилей в зависимости от типа
        self.setup_style()

        # Создаем layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 10, 15, 10)
        self.layout.setSpacing(10)

        # Иконка
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.layout.addWidget(self.icon_label)

        # Сообщение
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("color: #333333; font-size: 13px;")
        self.layout.addWidget(self.message_label, 1)

        # Кнопка действия (опционально)
        if show_action:
            self.action_btn = QPushButton(action_text)
            self.action_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #ccab6e;
                    border: none;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    color: #b8944f;
                    text-decoration: underline;
                }
            """)
            self.action_btn.clicked.connect(self.action_clicked.emit)
            self.layout.addWidget(self.action_btn)

        # Кнопка закрытия
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #999999;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #333333;
            }
        """)
        self.close_btn.clicked.connect(self.close_notification)
        self.layout.addWidget(self.close_btn)

        # Эффект прозрачности
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Анимации
        self.setup_animations()

        # Таймер автоматического скрытия
        if duration > 0:
            self.auto_close_timer = QTimer()
            self.auto_close_timer.setSingleShot(True)
            self.auto_close_timer.timeout.connect(self.close_notification)

    def setup_style(self):
        """Настройка стилей в зависимости от типа уведомления"""
        styles = {
            self.INFO: {
                "background": "#E3F2FD",
                "border": "#2196F3",
                "icon": "ℹ️"
            },
            self.SUCCESS: {
                "background": "#E8F5E9",
                "border": "#4CAF50",
                "icon": "✅"
            },
            self.WARNING: {
                "background": "#FFF3E0",
                "border": "#FF9800",
                "icon": "⚠️"
            },
            self.ERROR: {
                "background": "#FFEBEE",
                "border": "#F44336",
                "icon": "❌"
            }
        }

        style = styles.get(self.notification_type, styles[self.INFO])

        self.setStyleSheet(f"""
            AnimatedNotification {{
                background-color: {style["background"]};
                border-left: 4px solid {style["border"]};
                border-radius: 8px;
            }}
        """)

        if hasattr(self, 'icon_label'):
            self.icon_label.setText(style["icon"])

    def setup_animations(self):
        """Настройка анимаций"""
        # Анимация прозрачности
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Анимация позиции
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Группа для показа
        self.show_group = QParallelAnimationGroup()
        self.show_group.addAnimation(self.fade_animation)
        self.show_group.addAnimation(self.slide_animation)

    def show_notification(self, x, y, slide_from="right"):
        """Показать уведомление с анимацией

        Args:
            x, y: конечная позиция
            slide_from: направление всплытия ("right", "left", "top", "bottom")
        """
        self.show()
        self.raise_()

        # Настраиваем начальную позицию в зависимости от направления
        if slide_from == "right":
            start_x = x + 50
            start_y = y
        elif slide_from == "left":
            start_x = x - 50
            start_y = y
        elif slide_from == "top":
            start_x = x
            start_y = y - 50
        elif slide_from == "bottom":
            start_x = x
            start_y = y + 50
        else:
            start_x = x
            start_y = y

        # Настраиваем анимацию
        self.slide_animation.setStartValue(QPoint(start_x, start_y))
        self.slide_animation.setEndValue(QPoint(x, y))

        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)

        self.move(start_x, start_y)
        self.opacity_effect.setOpacity(0.0)

        # Запускаем анимацию
        self.show_group.start()

        # Запускаем таймер авто-закрытия
        if self.duration > 0:
            self.auto_close_timer.start(self.duration)

    def close_notification(self):
        """Закрыть уведомление с анимацией"""
        if hasattr(self, 'auto_close_timer'):
            self.auto_close_timer.stop()

        # Настраиваем анимацию исчезновения
        self.fade_animation.setStartValue(self.opacity_effect.opacity())
        self.fade_animation.setEndValue(0.0)

        current_pos = self.pos()
        self.slide_animation.setStartValue(current_pos)
        self.slide_animation.setEndValue(QPoint(current_pos.x() + 50, current_pos.y()))

        self.show_group.finished.connect(self._on_close_finished)
        self.show_group.start()

    def _on_close_finished(self):
        """Обработчик завершения анимации закрытия"""
        self.show_group.finished.disconnect(self._on_close_finished)
        self.hide()
        self.closed.emit()
        self.deleteLater()

    def set_message(self, message):
        """Обновить текст сообщения"""
        self.message_label.setText(message)


class NotificationManager:
    """Менеджер для управления несколькими уведомлениями"""

    def __init__(self, parent_widget, max_visible=3):
        self.parent = parent_widget
        self.max_visible = max_visible
        self.active_notifications = []
        self.notification_spacing = 10

    def show_notification(self, message, notification_type=AnimatedNotification.INFO,
                          duration=3000, slide_from="right"):
        """Показать новое уведомление"""
        # Удаляем старые уведомления если их слишком много
        while len(self.active_notifications) >= self.max_visible:
            oldest = self.active_notifications.pop(0)
            oldest.close_notification()

        # Создаем новое уведомление
        notification = AnimatedNotification(
            self.parent,
            message,
            notification_type,
            duration
        )

        # Подключаем сигнал закрытия
        notification.closed.connect(lambda: self._remove_notification(notification))

        # Вычисляем позицию
        x, y = self._calculate_position(len(self.active_notifications))

        # Показываем уведомление
        notification.show_notification(x, y, slide_from)

        # Добавляем в список активных
        self.active_notifications.append(notification)

        return notification

    def _calculate_position(self, index):
        """Вычислить позицию для нового уведомления"""
        parent_width = self.parent.width()
        parent_height = self.parent.height()

        x = parent_width - 370  # 350 ширина + 20 отступ
        y = 20 + index * (80 + self.notification_spacing)  # 60 высота + отступ

        return x, y

    def _remove_notification(self, notification):
        """Удалить уведомление из списка активных"""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)

