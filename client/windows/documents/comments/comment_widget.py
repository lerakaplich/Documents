"""
Виджет для отображения одного комментария
"""

from datetime import datetime
from typing import Dict, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QSizePolicy


class CommentWidget(QWidget):
    """Виджет для отображения одного комментария"""

    def __init__(self, comment_data: Dict[str, Any], parent=None):
        super().__init__(parent)

        self.comment_data = comment_data
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Главный лейаут виджета комментария
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(6)

        # Верхняя строка: автор + время
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # Получаем данные в формате API
        author = comment_data.get('author_fio', 'Неизвестный')
        self.author_label = QLabel(author)
        self.author_label.setObjectName("authorLabel")
        font = self.author_label.font()
        font.setBold(True)
        self.author_label.setFont(font)
        top_layout.addWidget(self.author_label)

        top_layout.addStretch()

        # Обработка даты
        time_str = comment_data.get('created_at', '')
        if time_str:
            try:
                dt_str = str(time_str).replace('Z', '+00:00')
                dt = datetime.fromisoformat(dt_str)
                time_str = dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                pass
        else:
            time_str = 'Неизвестно'

        self.time_label = QLabel(time_str)
        self.time_label.setObjectName("timeLabel")
        self.time_label.setStyleSheet("color: #999; font-size: 11px;")
        top_layout.addWidget(self.time_label)

        layout.addLayout(top_layout)

        # Текст комментария
        text = comment_data.get('text', '')
        self.text_label = QLabel(text)
        self.text_label.setObjectName("textLabel")
        self.text_label.setWordWrap(True)
        self.text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout.addWidget(self.text_label)

        # Разделитель (только если это не последний комментарий)
        # Добавляем всегда, но он тонкий
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setStyleSheet("""
            background-color: #EAEAEA; 
            max-height: 1px; 
            border: none; 
            margin-top: 8px;
            margin-bottom: 2px;
        """)
        layout.addWidget(divider)

        # Устанавливаем политику размера
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Устанавливаем минимальную высоту
        self.setMinimumHeight(60)