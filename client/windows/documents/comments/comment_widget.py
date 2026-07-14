"""
Диалог для просмотра и добавления комментариев к документу
"""

from datetime import datetime
from typing import Dict, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout


class CommentWidget(QWidget):
    """Виджет для отображения одного комментария"""

    def __init__(self, comment_data: Dict[str, Any], parent=None):
        super().__init__(parent)

        self.comment_data = comment_data
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # Верхняя строка: автор + время
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # Получаем данные в формате API
        author = comment_data.get('author_fio', 'Неизвестный')
        self.author_label = QLabel(author)
        self.author_label.setObjectName("authorLabel")
        top_layout.addWidget(self.author_label)

        top_layout.addStretch()

        # Обработка даты в формате ISO с Z
        time_str = comment_data.get('created_at', '')
        if time_str:
            try:
                # Убираем Z и парсим ISO формат
                dt_str = str(time_str).replace('Z', '+00:00')
                dt = datetime.fromisoformat(dt_str)
                time_str = dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                # Если не удалось распарсить, оставляем как есть
                pass
        else:
            time_str = 'Неизвестно'

        self.time_label = QLabel(time_str)
        self.time_label.setObjectName("timeLabel")
        top_layout.addWidget(self.time_label)

        layout.addLayout(top_layout)

        # Текст комментария
        text = comment_data.get('text', '')
        self.text_label = QLabel(text)
        self.text_label.setObjectName("textLabel")
        self.text_label.setWordWrap(True)
        layout.addWidget(self.text_label)