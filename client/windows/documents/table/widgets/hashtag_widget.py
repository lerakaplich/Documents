from PyQt6.QtCore import QRectF, QSize, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget


class HashtagWidget(QWidget):
    """Виджет для отображения хэштега с цветным фоном и прозрачным родительским фоном"""

    def __init__(self, tag_name, tag_color, parent=None):
        super().__init__(parent)

        self.tag_name = tag_name
        self.tag_color = self._normalize_color(tag_color)
        self.display_text = f"#{self.tag_name}"

        # Определяем контрастные цвета
        self.text_color, self.border_color = self.get_contrast_colors(self.tag_color)

        # Настройка размеров
        self.setFixedHeight(24)

        # Настройка шрифта.
        # ВАЖНО: нельзя называть атрибут `font` — это затирает метод QWidget.font().
        self._tag_font = QFont()
        self._tag_font.setPointSize(9)
        self._tag_font.setBold(True)

        # Вычисляем ширину под текст
        self.update_width()

        self.setObjectName("HashtagWidget")

        # Фон прозрачный: всё рисуем сами в paintEvent. Отдельный styleSheet на
        # каждый хэштег не нужен (обычный QWidget фон и так не рисует), а на
        # таблице с сотнями тегов он заметно тормозит polish/перерисовку.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Запрещаем виджету сжиматься и растягиваться
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def update_width(self):
        """Пересчёт ширины виджета под текст"""
        fm = QFontMetrics(self._tag_font)
        text_width = fm.horizontalAdvance(self.display_text)
        # padding 10px слева + 10px справа + 2px на границу + 2px запас на сглаживание
        total_width = text_width + 24
        self.setFixedWidth(total_width)

    @staticmethod
    def _normalize_color(color) -> str:
        """
        Приводит цвет к виду '#RRGGBB'. Понимает '#RGB', '#RRGGBB', имена цветов Qt
        ('red'); для None/мусора возвращает нейтральный серый, а не падает.
        """
        default = "#808080"
        if not color:
            return default
        qc = QColor(str(color).strip())
        if not qc.isValid():
            return default
        return qc.name()  # всегда '#rrggbb'

    def get_contrast_colors(self, hex_color):
        """
        Определение контрастных цветов для текста и границы
        """
        qc = QColor(self._normalize_color(hex_color))
        r, g, b = qc.red(), qc.green(), qc.blue()

        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

        if luminance > 0.6:
            border_r = int(r * 0.6)
            border_g = int(g * 0.6)
            border_b = int(b * 0.6)
            border_color = QColor(border_r, border_g, border_b)
            text_color = QColor("#1B232A")
        else:
            border_r = min(255, r + int((255 - r) * 0.4))
            border_g = min(255, g + int((255 - g) * 0.4))
            border_b = min(255, b + int((255 - b) * 0.4))
            border_color = QColor(border_r, border_g, border_b)
            text_color = QColor("#FFFFFF")

        return text_color, border_color

    def sizeHint(self):
        """Подсказка размера для layout'ов"""
        return QSize(self.width(), 24)

    def minimumSizeHint(self):
        """Минимальный размер"""
        return QSize(self.width(), 24)

    def paintEvent(self, event):
        """Отрисовка хэштега с фоном, границей и текстом"""
        painter = QPainter(self)
        try:
            self._paint(painter)
        finally:
            painter.end()

    def _paint(self, painter: QPainter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)

        # Рисуем фон с радиусом 5px (как у кнопок)
        painter.setBrush(QBrush(QColor(self.tag_color)))
        painter.setPen(QPen(self.border_color, 2))
        painter.drawRoundedRect(rect, 5, 5)

        # Рисуем текст
        painter.setFont(self._tag_font)
        painter.setPen(self.text_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.display_text)

    def update_style(self):
        """Обновление стилей (перерисовка)"""
        self.tag_color = self._normalize_color(self.tag_color)
        self.text_color, self.border_color = self.get_contrast_colors(self.tag_color)
        self.update_width()
        self.update()