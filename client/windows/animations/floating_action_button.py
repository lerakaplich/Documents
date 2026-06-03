from PyQt6.QtWidgets import QPushButton

from PyQt6.QtCore import Qt, pyqtSignal, QEasingCurve, QPropertyAnimation, QTimer, QPoint, QParallelAnimationGroup
from PyQt6.QtWidgets import QGraphicsOpacityEffect


class FloatingActionButton(QPushButton):
    """Плавающая кнопка действия с анимацией появления/исчезновения"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(56, 56)
        self.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 28px;
                font-size: 24px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #b8944f;
            }
            QPushButton:pressed {
                background-color: #a07d3f;
            }
        """)
        self.setText("+")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Сохраняем базовую позицию
        self.base_position = QPoint(0, 0)

        # Создаем эффект прозрачности для плавной анимации
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Анимация прозрачности
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(400)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Анимация позиции (всплытие/погружение)
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(400)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Группа анимаций для одновременного выполнения
        self.show_animation_group = QParallelAnimationGroup()
        self.show_animation_group.addAnimation(self.fade_animation)
        self.show_animation_group.addAnimation(self.slide_animation)

        # Таймер для скрытия кнопки после остановки скролла
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.show_with_animation)

        # Флаг состояния
        self.is_visible = True
        self.offset = 20  # Смещение для анимации всплытия

    def update_base_position(self, x, y):
        """Обновить базовую позицию кнопки"""
        self.base_position = QPoint(x, y)
        if self.is_visible:
            self.move(x, y)

    def show_with_animation(self):
        """Показать кнопку с анимацией всплытия снизу"""
        if not self.is_visible:
            # Останавливаем все текущие анимации
            self.show_animation_group.stop()

            # Настраиваем анимацию прозрачности
            self.fade_animation.setStartValue(self.opacity_effect.opacity())
            self.fade_animation.setEndValue(1.0)

            # Настраиваем анимацию позиции (всплытие снизу)
            start_pos = QPoint(self.base_position.x(), self.base_position.y() + self.offset)
            end_pos = self.base_position

            self.slide_animation.setStartValue(start_pos)
            self.slide_animation.setEndValue(end_pos)

            # Перемещаем кнопку в начальную позицию перед анимацией
            self.move(start_pos)
            self.opacity_effect.setOpacity(0.0)
            self.show()

            # Запускаем группу анимаций
            self.show_animation_group.start()

            self.is_visible = True

    def hide_with_animation(self):
        """Скрыть кнопку с анимацией погружения вниз"""
        if self.is_visible:
            # Останавливаем все текущие анимации
            self.show_animation_group.stop()

            # Настраиваем анимацию прозрачности
            self.fade_animation.setStartValue(self.opacity_effect.opacity())
            self.fade_animation.setEndValue(0.0)

            # Настраиваем анимацию позиции (погружение вниз)
            start_pos = self.pos()
            end_pos = QPoint(self.base_position.x(), self.base_position.y() + self.offset)

            self.slide_animation.setStartValue(start_pos)
            self.slide_animation.setEndValue(end_pos)

            # Запускаем группу анимаций
            self.show_animation_group.start()

            self.is_visible = False

    def start_hide_timer(self):
        """Запустить таймер для показа кнопки после остановки скролла"""
        self.hide_timer.stop()  # Останавливаем предыдущий таймер
        self.hide_timer.start(1000)  # Показываем через 1 секунду после остановки скролла

    def stop_hide_timer(self):
        """Остановить таймер"""
        self.hide_timer.stop()