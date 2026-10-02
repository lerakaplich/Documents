from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from client.core.themes import get_manager


class AnimatedNotification(QFrame):
    """Универсальное всплывающее уведомление с анимацией.

    Два режима:
    - обычный: дочерний виджет родителя, координаты — внутри родителя;
    - floating: отдельное безрамочное окно «поверх всех», координаты
      считаются от родителя через mapToGlobal. Нужен для диалогов, чтобы
      уведомление не пряталось за модальным окном.

    Ширина = min(max_width, ширина родителя - отступы), высота — по тексту.
    """

    closed = pyqtSignal()

    MAX_WIDTH = 400
    MIN_WIDTH = 160
    MIN_HEIGHT = 70
    SIDE_MARGIN = 15
    H_PADDING = 15
    V_PADDING = 10

    def __init__(self, parent=None, message="", duration=3000, floating=False):
        super().__init__(parent)

        self.duration = duration
        self.is_closing = False
        self.floating = floating
        self._anchor = parent

        if floating:
            self.setWindowFlags(
                Qt.WindowType.Tool
                | Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.WindowDoesNotAcceptFocus
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        _t = get_manager().current
        # Фон рисуем сами в paintEvent: стили не рисуют фон у прозрачных
        # top-level окон
        self._bg_color = QColor(_t.ACCENT_PRIMARY)
        self._radius = 16

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(self.H_PADDING, self.V_PADDING, self.H_PADDING, self.V_PADDING)
        self.layout.setSpacing(5)

        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                color: {_t.TEXT_ON_ACCENT};
                font-size: 18px;
                font-weight: 600;
            }}
        """)
        self.layout.addWidget(self.message_label, 1)

        self.fit_to_parent()

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        self.setup_animations()

        if duration > 0:
            self.auto_close_timer = QTimer(self)
            self.auto_close_timer.setSingleShot(True)
            self.auto_close_timer.timeout.connect(self.start_fade_out)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._bg_color)
        painter.drawRoundedRect(self.rect(), self._radius, self._radius)
        painter.end()

    # ─────────── Размер и координаты ───────────

    def fit_to_parent(self):
        """Подгоняет ширину под родителя, а высоту — под текст."""
        parent = self._anchor
        available = parent.width() - 2 * self.SIDE_MARGIN if parent else self.MAX_WIDTH
        width = max(self.MIN_WIDTH, min(self.MAX_WIDTH, available))

        text_width = width - 2 * self.H_PADDING
        text_height = self.message_label.heightForWidth(text_width)
        if text_height < 0:
            text_height = self.message_label.sizeHint().height()

        height = max(self.MIN_HEIGHT, text_height + 2 * self.V_PADDING)
        self.setFixedSize(width, height)

    def _pos(self, x, y):
        """Локальные координаты родителя -> координаты для move()."""
        if self.floating and self._anchor is not None:
            return self._anchor.mapToGlobal(QPoint(x, y))
        return QPoint(x, y)

    def setup_animations(self):
        self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(400)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(2000)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.finished.connect(self._on_fade_out_finished)

        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(400)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.show_group = QParallelAnimationGroup(self)
        self.show_group.addAnimation(self.fade_in_animation)
        self.show_group.addAnimation(self.slide_animation)

    def move_to(self, x, y):
        """Переместить уведомление (x, y — локальные координаты родителя)."""
        target = self._pos(x, y)
        if self.show_group.state() == QParallelAnimationGroup.State.Running:
            self.slide_animation.setEndValue(target)
        else:
            self.move(target)

    def show_notification(self, x, y):
        """Показать уведомление с анимацией (всплывает снизу)"""
        end = self._pos(x, y)
        start = QPoint(end.x(), end.y() + 80)

        self.slide_animation.setStartValue(start)
        self.slide_animation.setEndValue(end)

        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)

        self.move(start)
        self.opacity_effect.setOpacity(0.0)
        self.show()
        self.raise_()

        self.show_group.start()

        if self.duration > 0:
            QTimer.singleShot(500, self.start_auto_close_timer)

    def start_auto_close_timer(self):
        if hasattr(self, "auto_close_timer") and not self.is_closing:
            self.auto_close_timer.start(self.duration)

    def start_fade_out(self):
        if self.is_closing:
            return

        self.is_closing = True

        if hasattr(self, "auto_close_timer"):
            self.auto_close_timer.stop()

        current_opacity = self.opacity_effect.opacity()
        self.fade_out_animation.setStartValue(current_opacity)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.start()

    def close_notification(self):
        """Закрыть уведомление (вызывается менеджером при переполнении)"""
        self.start_fade_out()

    def _on_fade_out_finished(self):
        self.hide()
        self.closed.emit()
        self.deleteLater()

    def set_message(self, message):
        self.message_label.setText(message)
        self.fit_to_parent()


class NotificationManager(QObject):
    """Менеджер для управления несколькими уведомлениями.

    floating=False — уведомления внутри parent_widget (как во вкладке).
    floating=True  — уведомления отдельными окнами поверх всего, внизу
                     parent_widget по центру (для диалогов).
    """

    def __init__(self, parent_widget, max_visible=3, floating=False):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.max_visible = max_visible
        self.floating = floating
        self.active_notifications = []
        self.notification_spacing = 5
        self.bottom_margin = 30

        self.container = None
        if not floating:
            # Прозрачный контейнер для уведомлений
            self.container = QWidget(parent_widget)
            self.container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self._sync_container()
            self.container.raise_()

        # Следим за размером/положением родителя
        parent_widget.installEventFilter(self)

    @classmethod
    def for_widget(cls, widget, max_visible=3, floating=False):
        """Один общий менеджер на виджет (повторные вызовы возвращают тот же)."""
        attr = "_shared_notification_manager_floating" if floating else "_shared_notification_manager"
        manager = getattr(widget, attr, None)
        if manager is None:
            manager = cls(widget, max_visible=max_visible, floating=floating)
            setattr(widget, attr, manager)
        return manager

    @classmethod
    def for_dialog(cls, dialog, max_visible=3):
        """Менеджер для диалога: уведомления показываются внизу ГЛАВНОГО окна
        по центру, отдельными окнами поверх диалога."""
        parent = dialog.parentWidget()
        anchor = parent.window() if parent is not None else dialog
        return cls.for_widget(anchor, max_visible=max_visible, floating=True)

    def eventFilter(self, obj, event):
        if obj is self.parent_widget and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
            QEvent.Type.Move,
        ):
            self._relayout()
        return False  # событие не перехватываем

    def _area(self):
        return self.parent_widget if self.floating else self.container

    def _sync_container(self):
        """Контейнер всегда равен по размеру родителю."""
        if self.container is not None:
            self.container.setGeometry(0, 0, self.parent_widget.width(), self.parent_widget.height())

    def _relayout(self):
        self._sync_container()
        for notification in self.active_notifications:
            notification.fit_to_parent()
        self._update_notifications_position()

    def _positions(self):
        """Позиции (x, y) уведомлений: стопка снизу вверх, по центру (локальные координаты)."""
        area = self._area()
        parent_width = area.width()
        parent_height = area.height()

        result = []
        bottom = parent_height - self.bottom_margin
        for notification in self.active_notifications:
            x = (parent_width - notification.width()) // 2
            y = bottom - notification.height()
            result.append((x, y))
            bottom = y - self.notification_spacing
        return result

    def _update_notifications_position(self):
        for notification, (x, y) in zip(self.active_notifications, self._positions()):
            notification.move_to(x, y)

    def show_notification(self, message, duration=3000):
        """Показать новое уведомление"""
        while len(self.active_notifications) >= self.max_visible:
            oldest = self.active_notifications.pop(0)
            oldest.close_notification()

        if self.container is not None:
            self._sync_container()
            self.container.raise_()
            owner = self.container
        else:
            owner = self.parent_widget

        notification = AnimatedNotification(owner, message, duration, floating=self.floating)
        notification.closed.connect(lambda: self._remove_notification(notification))

        self.active_notifications.append(notification)
        self._update_notifications_position()  # сдвигаем предыдущие вверх

        x, y = self._positions()[-1]
        notification.show_notification(x, y)

        return notification

    def _remove_notification(self, notification):
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
            self._update_notifications_position()


# Пример использования
if __name__ == "__main__":
    import sys

    from PyQt6.QtWidgets import (
        QApplication,
        QMainWindow,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
    )

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
                duration=3000,
            )
            self.counter += 1

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())