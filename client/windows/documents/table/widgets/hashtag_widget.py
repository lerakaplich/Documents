from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QRectF, QSize
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QFontMetrics


class HashtagWidget(QWidget):
    """Виджет для отображения хэштега с цветным фоном и прозрачным родительским фоном"""

    def __init__(self, tag_name, tag_color, parent=None):
        super().__init__(parent)

        self.tag_name = tag_name
        self.tag_color = tag_color
        self.display_text = f"#{self.tag_name}"

        # Определяем контрастные цвета
        self.text_color, self.border_color = self.get_contrast_colors(self.tag_color)

        # Настройка размеров
        self.setFixedHeight(24)

        # Настройка шрифта
        self.font = QFont()
        self.font.setPointSize(9)
        self.font.setBold(True)

        # Вычисляем ширину под текст
        self.update_width()

        self.setObjectName("HashtagWidget")

        # Прозрачный фон для самого виджета
        self.setStyleSheet("""
            QWidget#HashtagWidget {
                background: transparent;
                border: none;
            }
        """)

        # Запрещаем виджету сжиматься и растягиваться
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def update_width(self):
        """Пересчёт ширины виджета под текст"""
        fm = QFontMetrics(self.font)
        text_width = fm.horizontalAdvance(self.display_text)
        # padding 10px слева + 10px справа + 2px на границу
        total_width = text_width + 24
        self.setFixedWidth(total_width)

    def get_contrast_colors(self, hex_color):
        """
        Определение контрастных цветов для текста и границы
        """
        hex_color = hex_color.lstrip('#')

        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

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
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)

        # Рисуем фон с радиусом 5px (как у кнопок)
        painter.setBrush(QBrush(QColor(self.tag_color)))
        painter.setPen(QPen(self.border_color, 2))
        painter.drawRoundedRect(rect, 5, 5)

        # Рисуем текст
        painter.setFont(self.font)
        painter.setPen(self.text_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.display_text)

        painter.end()

    def update_style(self):
        """Обновление стилей (перерисовка)"""
        self.text_color, self.border_color = self.get_contrast_colors(self.tag_color)
        self.update()