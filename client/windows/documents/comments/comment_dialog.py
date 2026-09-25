# client/windows/documents/comments/comment_dialog.py
"""
Диалог для просмотра и добавления комментариев к документу
"""
import os
from datetime import datetime
from PyQt6.QtWidgets import QDialog, QListWidgetItem, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QFrame
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.uic import loadUi

from client.core.themes import apply_theme_to_widget, T

ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)


class CommentItemWidget(QWidget):
    """Виджет для отображения одного комментария в списке"""

    def __init__(self, comment: dict, parent=None, show_separator: bool = True):
        super().__init__(parent)

        self.comment = comment

        # Основной вертикальный layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Верхняя строка: автор и время
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Имя автора (жирный)
        author_label = QLabel()
        author_name = comment.get('author_fio') or comment.get('author_name') or comment.get('author') or 'Неизвестный'
        author_label.setText(author_name)
        author_label.setStyleSheet(f"""
            QLabel {{
                font-weight: bold;
                font-size: 13px;
                color: {T.TEXT_PRIMARY};
                background-color: transparent;
            }}
        """)
        header_layout.addWidget(author_label)

        # Разделитель
        sep_label = QLabel("•")
        sep_label.setStyleSheet(
            f"color: {T.TEXT_TERTIARY}; background-color: transparent;"
        )
        header_layout.addWidget(sep_label)

        # Время
        time_label = QLabel()
        created_at = comment.get('created_at')
        if created_at:
            if isinstance(created_at, datetime):
                time_str = created_at.strftime("%d.%m.%Y %H:%M")
            else:
                time_str = str(created_at)
        else:
            time_str = "Только что"
        time_label.setText(time_str)
        time_label.setStyleSheet(f"""
            QLabel {{
                color: {T.TEXT_TERTIARY};
                font-size: 11px;
                background-color: transparent;
            }}
        """)
        header_layout.addWidget(time_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Текст комментария
        text_label = QLabel()
        text = comment.get('text', '')
        text_label.setText(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"""
            QLabel {{
                color: {T.TEXT_HEADING};
                font-size: 14px;
                background-color: transparent;
                padding-left: 0px;
            }}
        """)
        layout.addWidget(text_label)

        # Разделитель между комментариями (светло-серый)
        if show_separator:
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet(f"""
                QFrame {{
                    color: {T.BORDER_LIGHT};
                    background-color: {T.SEPARATOR_BG};
                    max-height: 1px;
                    border: none;
                    margin-top: 4px;
                    margin-bottom: 0px;
                }}
            """)
            layout.addWidget(separator)

        # Устанавливаем общий стиль для виджета
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)


from client.core.state.app_state import AppState
from client.services.comment_service import CommentService

class CommentDialog(QDialog):
    comment_added = pyqtSignal(dict)
    def __init__(self, document_data, parent=None, current_user=None, http_client=None):
        super().__init__(parent)
        self.document_data = document_data
        self.current_user = current_user or self._get_default_user()
        self._comments_cache = []
        self.http_client = http_client or AppState().http_client
        self.comment_service = CommentService(self.http_client)

        ui_path = os.path.join(ROOT_DIR, "client", "ui", "documents", "comments_dialog.ui")
        loadUi(ui_path, self)
        apply_theme_to_widget(self)

        self._setup_ui()
        self._load_comments_from_server()   # ← вместо self._load_comments()
        self._connect_signals()

    def _get_default_user(self) -> dict:
        """Возвращает тестового пользователя"""
        return {
            'id': 1,
            'full_name': 'Иванов И.И.',
            'last_name': 'Иванов',
            'first_name': 'Иван',
            'middle_name': 'Иванович'
        }

    def _setup_ui(self):
        """Настройка UI элементов"""
        # Устанавливаем заголовок
        doc_number = self.document_data.get('reg_number', self.document_data.get('number', 'Без номера'))
        doc_title = self.document_data.get('title', self.document_data.get('subject', 'Без темы'))

        self.docInfoLabel.setText(f"Документ №{doc_number}")
        self.commentsListWidget.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {T.BORDER_LIGHT};
                border-radius: 8px;
                background-color: {T.BG_SURFACE_SUBTLE};
                padding: 6px 0px;
            }}
            QListWidget::item {{
                padding: 0px;
                margin: 0px;
                width: 100%;
            }}
        """)
        # Настраиваем размеры
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        # Устанавливаем фокус на поле ввода
        self.commentTextEdit.setFocus()

    def _load_comments_from_server(self):
        doc_id = self.document_data.get("id")
        if not doc_id:
            self._load_comments()
            return

        try:
            server_comments = self.comment_service.get_comments(doc_id) or []
        except Exception as e:
            print(f"[CommentDialog] Ошибка загрузки комментариев: {e}")
            server_comments = []

        # Локальные (добавленные в этой сессии) — оставляем тоже
        local = self.document_data.get("comments", []) or []
        server_ids = {c.get("id") for c in server_comments}
        merged = list(server_comments) + [c for c in local if c.get("id") not in server_ids]

        self.document_data["comments"] = merged
        self._load_comments()

    def _load_comments(self):
        """Загрузка комментариев в список"""
        self.commentsListWidget.clear()

        comments = self.document_data.get('comments', [])
        self._comments_cache = comments.copy()

        if not comments:
            item = QListWidgetItem("Нет комментариев")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setSizeHint(QSize(0, 60))  # высота, ширина = по вьюпорту
            self.commentsListWidget.addItem(item)
            return
        # Функция для преобразования created_at в datetime (без часового пояса)
        def parse_created_at(comment):
            created_at = comment.get('created_at')
            if created_at is None:
                return datetime.min

            if isinstance(created_at, datetime):
                # Если дата с часовым поясом - убираем его
                if created_at.tzinfo is not None:
                    return created_at.replace(tzinfo=None)
                return created_at

            if isinstance(created_at, str):
                try:
                    # Пробуем парсить строку
                    # Сначала пробуем ISO формат с Z или +00:00
                    if created_at.endswith('Z'):
                        created_at = created_at[:-1] + '+00:00'

                    # Парсим с возможным часовым поясом
                    dt = datetime.fromisoformat(created_at)
                    # Если есть часовой пояс - убираем его
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                    return dt
                except (ValueError, TypeError):
                    # Пробуем другие форматы
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%Y-%m-%d"]:
                        try:
                            dt = datetime.strptime(created_at, fmt)
                            return dt
                        except ValueError:
                            continue
                    return datetime.min

            return datetime.min

        # Сортируем комментарии по дате
        sorted_comments = sorted(
            comments,
            key=parse_created_at,
            reverse=False
        )

        for i, comment in enumerate(sorted_comments):
            show_separator = (i < len(sorted_comments) - 1)
            self._add_comment_to_list(comment, show_separator)

        self.commentsListWidget.scrollToBottom()

    def _add_comment_to_list(self, comment: dict, show_separator: bool = True):
        """Добавление комментария в список"""
        item = QListWidgetItem()
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        # Создаем виджет для комментария
        widget = CommentItemWidget(comment, show_separator=show_separator)

        # Устанавливаем высоту элемента
        item.setSizeHint(widget.sizeHint())

        self.commentsListWidget.addItem(item)
        self.commentsListWidget.setItemWidget(item, widget)

    def _connect_signals(self):
        """Подключение сигналов"""
        self.sendButton.clicked.connect(self._on_send_clicked)

        # Отправка по Ctrl+Enter
        self.commentTextEdit.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Обработка событий для поля ввода"""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent

        if obj == self.commentTextEdit and event.type() == QEvent.Type.KeyPress:
            key_event = event
            if key_event.key() == Qt.Key.Key_Return and key_event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self._on_send_clicked()
                return True
        return super().eventFilter(obj, event)

    def _on_send_clicked(self):
        text = self.commentTextEdit.toPlainText().strip()
        if not text:
            return

        doc_id = self.document_data.get("id")

        # 1. Отправляем на сервер (если возможно)
        if doc_id:
            try:
                self.comment_service.add_comment(doc_id, text)
            except Exception as e:
                print(f"[CommentDialog] Не удалось отправить комментарий: {e}")

        # 2. Локально — как раньше
        new_comment = {
            'id': len(self._comments_cache) + 1,
            'author_fio': self.current_user.get('full_name', 'Пользователь'),
            'author': self.current_user.get('full_name', 'Пользователь'),
            'text': text,
            'created_at': datetime.now(),
            'user_id': self.current_user.get('id', 0),
        }

        # Добавляем в кеш
        self._comments_cache.append(new_comment)

        # Получаем текущее количество элементов
        count = self.commentsListWidget.count()

        # Если есть сообщение "Нет комментариев" - удаляем его
        if count == 1:
            item = self.commentsListWidget.item(0)
            if item and item.text() == "Нет комментариев":
                self.commentsListWidget.takeItem(0)
                count = 0

        # Добавляем разделитель к предыдущему последнему комментарию, если он был
        if count > 0:
            # Обновляем последний элемент - добавляем ему разделитель
            last_item = self.commentsListWidget.item(count - 1)
            if last_item:
                old_widget = self.commentsListWidget.itemWidget(last_item)
                if old_widget and hasattr(old_widget, 'comment'):
                    # Создаем новый виджет с разделителем
                    new_widget = CommentItemWidget(old_widget.comment, show_separator=True)
                    last_item.setSizeHint(new_widget.sizeHint())
                    self.commentsListWidget.setItemWidget(last_item, new_widget)

        # Добавляем новый комментарий без разделителя (он будет последним)
        self._add_comment_to_list(new_comment, show_separator=False)

        # Прокручиваем к новому комментарию
        self.commentsListWidget.scrollToBottom()

        # Очищаем поле ввода
        self.commentTextEdit.clear()

        # Эмитим сигнал
        self.comment_added.emit(new_comment)

        # Обновляем данные документа
        if 'comments' not in self.document_data:
            self.document_data['comments'] = []
        self.document_data['comments'].append(new_comment)
        self.document_data['last_comment_text'] = text

    def get_comments(self) -> list:
        """Получить все комментарии"""
        return self.document_data.get('comments', [])