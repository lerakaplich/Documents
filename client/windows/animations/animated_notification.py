from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsOpacityEffect, QFrame, QApplication
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer,
    QPoint, QParallelAnimationGroup, pyqtSignal
)
from PyQt6.QtGui import QIcon, QColor, QPalette

from client.core.themes import get_manager


class AnimatedNotification(QFrame):
    """Универсальное всплывающее уведомление с анимацией"""

    # Сигналы
    closed = pyqtSignal()

    def __init__(self, parent=None, message="", duration=3000):
        super().__init__(parent)

        self.duration = duration
        self.is_closing = False

        # Настройка внешнего вида
        self.setFixedWidth(400)
        self.setFixedHeight(70)  # Чуть больше высота для читаемости
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        # Делаем фон полностью прозрачным
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)

        # Отключаем возможность фокуса и кликов на уведомлении
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Золотой фон со скругленными углами
        _t = get_manager().current
        self.setStyleSheet(f"""
            AnimatedNotification {{
                background-color: {_t.ACCENT_PRIMARY};
                border-radius: 16px;
                border: none;
            }}
            QLabel {{
                background-color: {_t.ACCENT_PRIMARY};
                border-radius: 16px;
                color: {_t.TEXT_ON_ACCENT};
                font-size: 18px;
                font-weight: 600;
            }}
        """)

        # Создаем layout
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 10, 15, 10)
        self.layout.setSpacing(5)

        # Сообщение
        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet(f"""
            QLabel {{
                background-color: {_t.ACCENT_PRIMARY};
                border-radius: 16px;
                color: {_t.TEXT_ON_ACCENT};
                font-size: 18px;
                font-weight: 600;
            }}
        """)
        self.layout.addWidget(self.message_label, 1)

        # Эффект прозрачности для всего уведомления
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Анимации
        self.setup_animations()

        # Таймер автоматического закрытия
        if duration > 0:
            self.auto_close_timer = QTimer()
            self.auto_close_timer.setSingleShot(True)
            self.auto_close_timer.timeout.connect(self.start_fade_out)

    def setup_animations(self):
        """Настройка анимаций"""
        # Анимация прозрачности (появление)
        self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(400)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Анимация прозрачности (исчезновение)
        self.fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(2000)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.finished.connect(self._on_fade_out_finished)

        # Анимация позиции (выезжание снизу)
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(400)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Группа для показа
        self.show_group = QParallelAnimationGroup()
        self.show_group.addAnimation(self.fade_in_animation)
        self.show_group.addAnimation(self.slide_animation)

    def show_notification(self, x, y):
        """Показать уведомление с анимацией (всплывает снизу)"""
        self.show()
        self.raise_()

        # Начальная позиция - снизу
        start_x = x
        start_y = y + 80

        # Настраиваем анимацию появления
        self.slide_animation.setStartValue(QPoint(start_x, start_y))
        self.slide_animation.setEndValue(QPoint(x, y))

        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)

        self.move(start_x, start_y)
        self.opacity_effect.setOpacity(0.0)

        # Запускаем анимацию появления
        self.show_group.start()

        # Запускаем таймер авто-закрытия
        if self.duration > 0:
            QTimer.singleShot(500, self.start_auto_close_timer)

    def start_auto_close_timer(self):
        """Запускает таймер автоматического закрытия"""
        if hasattr(self, 'auto_close_timer') and not self.is_closing:
            self.auto_close_timer.start(self.duration)

    def start_fade_out(self):
        """Начинает анимацию исчезновения"""
        if self.is_closing:
            return

        self.is_closing = True

        if hasattr(self, 'auto_close_timer'):
            self.auto_close_timer.stop()

        current_opacity = self.opacity_effect.opacity()
        self.fade_out_animation.setStartValue(current_opacity)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.start()

    def _on_fade_out_finished(self):
        """Обработчик завершения анимации исчезновения"""
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
        self.notification_spacing = 5

        # Создаем прозрачный контейнер для уведомлений
        self.container = QWidget(parent_widget)
        self.container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.container.setGeometry(0, 0, parent_widget.width(), parent_widget.height())

        # Делаем контейнер прозрачным для кликов
        self.container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Поднимаем контейнер поверх всех виджетов
        self.container.raise_()

        # Сохраняем оригинальный resizeEvent
        self._original_resize_event = parent_widget.resizeEvent
        parent_widget.resizeEvent = self._on_parent_resize

    def _on_parent_resize(self, event):
        """Обновляет размер контейнера при изменении родителя"""
        self.container.setGeometry(0, 0, self.parent.width(), self.parent.height())
        self._update_notifications_position()
        # Вызываем оригинальный обработчик если есть
        if self._original_resize_event:
            self._original_resize_event(event)

    def _update_notifications_position(self):
        """Обновляет позиции всех активных уведомлений"""
        for i, notification in enumerate(self.active_notifications):
            x, y = self._calculate_position(i)
            notification.move(x, y)

    def show_notification(self, message, duration=3000):
        """Показать новое уведомление"""
        # Удаляем старые уведомления если их слишком много
        while len(self.active_notifications) >= self.max_visible:
            oldest = self.active_notifications.pop(0)
            oldest.close_notification()

        # Создаем новое уведомление
        notification = AnimatedNotification(
            self.container,
            message,
            duration
        )

        # Подключаем сигнал закрытия
        notification.closed.connect(lambda: self._remove_notification(notification))

        # Вычисляем позицию
        x, y = self._calculate_position(len(self.active_notifications))

        # Показываем уведомление
        notification.show_notification(x, y)

        # Добавляем в список активных
        self.active_notifications.append(notification)

        return notification

    def _calculate_position(self, index):
        """Вычислить позицию для нового уведомления (по центру снизу)"""
        parent_width = self.container.width()
        parent_height = self.container.height()

        # Получаем ширину уведомления
        notification_width = 400
        notification_height = 70  # Высота уведомления

        # Центрируем по горизонтали
        x = (parent_width - notification_width) // 2

        # Позиция снизу с учетом отступов между уведомлениями
        # Отступ от нижнего края
        bottom_margin = 30
        # Вычисляем позицию для текущего уведомления
        y = parent_height - bottom_margin - (index + 1) * (notification_height + self.notification_spacing)

        return x, y

    def _remove_notification(self, notification):
        """Удалить уведомление из списка активных"""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
            self._update_notifications_position()


# Пример использования
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QTextEdit


    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Уведомления по центру")
            self.setGeometry(100, 100, 800, 600)

            # Центральный виджет
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)

            # Текстовое поле
            text = QTextEdit()
            text.setPlainText(
                "Нажмите сюда, чтобы проверить, что уведомления не блокируют клики.\n\nВы можете взаимодействовать с этим полем, пока видны уведомления."
                "\n\nУведомления теперь:\n• По центру экрана\n• Ближе друг к другу\n• Крупный шрифт 18px"
            )
            text.setStyleSheet("border: 2px solid #ccc; border-radius: 8px; padding: 10px; font-size: 14px;")
            layout.addWidget(text)

            # Кнопка для показа уведомлений
            btn = QPushButton("Показать уведомление")
            btn.clicked.connect(self.show_notification)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ccab6e;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px;
                    font-weight: bold;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #b8944f;
                }
            """)
            layout.addWidget(btn)

            # Менеджер уведомлений
            self.notification_manager = NotificationManager(self, max_visible=3)

            # Счетчик уведомлений
            self.counter = 1

        def show_notification(self):
            self.notification_manager.show_notification(
                f"Уведомление #{self.counter}: Действие выполнено успешно!",
                duration=3000
            )
            self.counter += 1


    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())