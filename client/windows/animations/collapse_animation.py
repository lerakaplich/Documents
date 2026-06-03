# animations.py - файл с анимациями

from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty, QObject, pyqtSignal, QPoint
from PyQt6.QtWidgets import QWidget


class CollapseAnimation(QObject):
    """Универсальная анимация сворачивания/разворачивания виджетов

    Поддерживает:
    - Горизонтальное сворачивание (по ширине)
    - Вертикальное сворачивание (по высоте)
    - Плавное изменение размера с настраиваемой длительностью
    - Разные easing curves
    """

    # Сигналы
    animation_started = pyqtSignal()
    animation_finished = pyqtSignal()
    state_changed = pyqtSignal(bool)  # True - развернут, False - свернут

    def __init__(self, target_widget, collapsed_size=50, expanded_size=280,
                 duration=300, easing_curve=QEasingCurve.Type.InOutCubic,
                 orientation="horizontal"):
        """
        Args:
            target_widget: Виджет для анимации
            collapsed_size: Размер в свернутом состоянии
            expanded_size: Размер в развернутом состоянии
            duration: Длительность анимации в мс
            easing_curve: Тип кривой easing
            orientation: "horizontal" или "vertical"
        """
        super().__init__(target_widget)

        self.target = target_widget
        self.collapsed_size = collapsed_size
        self.expanded_size = expanded_size
        self.duration = duration
        self.orientation = orientation
        self.is_expanded = True

        # Создаем анимацию
        self.animation = QPropertyAnimation(target_widget, b"animatedSize")
        self.animation.setDuration(duration)
        self.animation.setEasingCurve(easing_curve)

        # Подключаем сигналы
        self.animation.finished.connect(self._on_animation_finished)

        # Добавляем свойство animatedSize к виджету
        self._add_animated_property()

    def _add_animated_property(self):
        """Динамически добавляет свойство animatedSize к виджету"""
        # Проверяем, есть ли уже свойство
        if not hasattr(self.target.__class__, 'animatedSize'):

            def get_size(self_obj):
                if self.orientation == "horizontal":
                    return self_obj.width()
                else:
                    return self_obj.height()

            def set_size(self_obj, size):
                if self.orientation == "horizontal":
                    self_obj.setFixedWidth(size)
                else:
                    self_obj.setFixedHeight(size)

            # Создаем свойство
            prop = pyqtProperty(int, fget=get_size, fset=set_size)
            setattr(self.target.__class__, 'animatedSize', prop)

    def toggle(self):
        """Переключить состояние"""
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        """Развернуть"""
        if not self.is_expanded:
            self.animation.stop()
            self.animation.setStartValue(self.collapsed_size)
            self.animation.setEndValue(self.expanded_size)
            self.is_expanded = True
            self.state_changed.emit(True)
            self.animation_started.emit()
            self.animation.start()

    def collapse(self):
        """Свернуть"""
        if self.is_expanded:
            self.animation.stop()
            self.animation.setStartValue(self.expanded_size)
            self.animation.setEndValue(self.collapsed_size)
            self.is_expanded = False
            self.state_changed.emit(False)
            self.animation_started.emit()
            self.animation.start()

    def set_duration(self, duration):
        """Изменить длительность анимации"""
        self.duration = duration
        self.animation.setDuration(duration)

    def set_easing_curve(self, curve_type):
        """Изменить кривую easing"""
        self.animation.setEasingCurve(curve_type)

    def stop(self):
        """Остановить анимацию"""
        self.animation.stop()

    def _on_animation_finished(self):
        """Внутренний обработчик завершения анимации"""
        self.animation_finished.emit()


class FadeAnimation(QObject):
    """Анимация появления/исчезновения (прозрачность)"""

    animation_started = pyqtSignal()
    animation_finished = pyqtSignal()

    def __init__(self, target_widget, duration=300,
                 easing_curve=QEasingCurve.Type.InOutQuad):
        super().__init__(target_widget)

        self.target = target_widget
        self.duration = duration

        from PyQt6.QtWidgets import QGraphicsOpacityEffect

        # Создаем эффект прозрачности если его нет
        if not target_widget.graphicsEffect():
            self.opacity_effect = QGraphicsOpacityEffect()
            target_widget.setGraphicsEffect(self.opacity_effect)
        else:
            self.opacity_effect = target_widget.graphicsEffect()

        # Анимация прозрачности
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(duration)
        self.animation.setEasingCurve(easing_curve)
        self.animation.finished.connect(self.animation_finished.emit)

    def fade_in(self):
        """Плавно показать"""
        self.animation.stop()
        self.animation.setStartValue(self.opacity_effect.opacity())
        self.animation.setEndValue(1.0)
        self.animation_started.emit()
        self.animation.start()

    def fade_out(self):
        """Плавно скрыть"""
        self.animation.stop()
        self.animation.setStartValue(self.opacity_effect.opacity())
        self.animation.setEndValue(0.0)
        self.animation_started.emit()
        self.animation.start()

    def set_opacity(self, opacity):
        """Установить прозрачность без анимации"""
        self.opacity_effect.setOpacity(opacity)


class SlideAnimation(QObject):
    """Анимация скольжения виджета"""

    animation_started = pyqtSignal()
    animation_finished = pyqtSignal()

    def __init__(self, target_widget, duration=300,
                 easing_curve=QEasingCurve.Type.OutCubic):
        super().__init__(target_widget)

        self.target = target_widget
        self.duration = duration

        # Анимация позиции
        self.animation = QPropertyAnimation(target_widget, b"pos")
        self.animation.setDuration(duration)
        self.animation.setEasingCurve(easing_curve)
        self.animation.finished.connect(self.animation_finished.emit)

    def slide_from(self, start_pos, end_pos):
        """Скольжение из одной позиции в другую"""
        self.animation.stop()
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation_started.emit()
        self.animation.start()

    def slide_by(self, dx, dy):
        """Скольжение на заданное смещение"""
        current_pos = self.target.pos()
        end_pos = current_pos + QPoint(dx, dy) if hasattr(QPoint, '__add__') else QPoint(current_pos.x() + dx,
                                                                                         current_pos.y() + dy)
        self.slide_from(current_pos, end_pos)


class CombinedAnimation(QObject):
    """Комбинированная анимация (несколько анимаций одновременно)"""

    animation_finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt6.QtCore import QParallelAnimationGroup
        self.group = QParallelAnimationGroup()
        self.group.finished.connect(self.animation_finished.emit)

    def add_animation(self, animation):
        """Добавить анимацию в группу"""
        if hasattr(animation, 'animation'):
            self.group.addAnimation(animation.animation)

    def start(self):
        """Запустить все анимации"""
        self.group.start()

    def stop(self):
        """Остановить все анимации"""
        self.group.stop()