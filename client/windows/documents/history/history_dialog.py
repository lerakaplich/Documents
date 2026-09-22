# client/windows/documents/history/history_dialog.py
"""
Диалог для просмотра истории документа
"""
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QListWidgetItem, QWidget, QHBoxLayout,
    QLabel, QVBoxLayout, QFrame, QApplication, QPushButton, QListWidget
)
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

from client.core.themes import apply_theme_to_widget, get_manager

ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)


def parse_datetime(value) -> datetime:
    """
    Универсальный парсер даты/времени

    Args:
        value: строка или datetime объект

    Returns:
        datetime: объект datetime
    """
    if value is None:
        return datetime.now()

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S.%f",
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y %H:%M:%S",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except (ValueError, TypeError):
                continue

        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass

        print(f"[parse_datetime] Не удалось распарсить: {value}")
        return datetime.now()

    return datetime.now()


class HistoryItemWidget(QWidget):
    """Виджет для отображения одного события в истории"""

    def __init__(self, event: dict, parent=None, show_separator: bool = True):
        super().__init__(parent)
        self.event = event
        self.show_separator = show_separator

        _t = get_manager().current

        # Основной вертикальный layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Верхняя строка: время
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Время события
        time_label = QLabel()
        created_at = event.get('created_at')
        if created_at:
            if isinstance(created_at, datetime):
                time_str = created_at.strftime("%d.%m.%Y %H:%M")
            else:
                try:
                    dt = parse_datetime(created_at)
                    time_str = dt.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    time_str = str(created_at)
        else:
            time_str = "Дата не указана"

        time_label.setText(time_str)
        time_label.setStyleSheet(f"""
            QLabel {{
                color: {_t.TEXT_TERTIARY};
                font-size: 11px;
                background-color: transparent;
            }}
        """)
        header_layout.addWidget(time_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Текст события
        event_text = self._format_event_text(event)
        text_label = QLabel()
        text_label.setText(event_text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"""
            QLabel {{
                color: {_t.TEXT_HEADING};
                font-size: 14px;
                background-color: transparent;
                padding-left: 0px;
            }}
        """)
        layout.addWidget(text_label)

        # Разделитель между событиями
        if show_separator:
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet(f"""
                QFrame {{
                    color: {_t.BORDER_LIGHT};
                    background-color: {_t.SEPARATOR_BG};
                    max-height: 1px;
                    border: none;
                    margin-top: 4px;
                    margin-bottom: 0px;
                }}
            """)
            layout.addWidget(separator)

        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

    def _format_event_text(self, event: dict) -> str:
        """Форматирует текст события в зависимости от типа"""
        event_type = event.get('type', 'unknown')

        if event_type == 'redirect':
            from_user = event.get('from_user', 'Неизвестный пользователь')
            to_user = event.get('to_user', 'Неизвестный пользователь')
            return f'Пользователь {from_user} перенаправил документ пользователю {to_user}'

        elif event_type == 'comment':
            user = event.get('user', 'Неизвестный пользователь')
            text = event.get('text', '')
            return f'Пользователь {user} оставил комментарий «{text}»'

        elif event_type == 'status_change':
            user = event.get('user', 'Неизвестный пользователь')
            old_status = event.get('old_status', 'Неизвестный статус')
            new_status = event.get('new_status', 'Неизвестный статус')
            return f'Пользователь {user} изменил статус документа с "{old_status}" на "{new_status}"'

        elif event_type == 'created':
            user = event.get('user', 'Неизвестный пользователь')
            return f'Пользователь {user} создал документ'

        else:
            user = event.get('user', 'Неизвестный пользователь')
            text = event.get('text', '')
            return f'Пользователь {user} {text}'

    def reapply_theme(self):
        """Перекрасить стили под текущую тему."""
        _t = get_manager().current

        for child in self.findChildren(QLabel):
            ss = child.styleSheet()
            if "font-size: 11px" in ss:
                child.setStyleSheet(f"""
                    QLabel {{
                        color: {_t.TEXT_TERTIARY};
                        font-size: 11px;
                        background-color: transparent;
                    }}
                """)
            else:
                child.setStyleSheet(f"""
                    QLabel {{
                        color: {_t.TEXT_HEADING};
                        font-size: 14px;
                        background-color: transparent;
                        padding-left: 0px;
                    }}
                """)

        for sep in self.findChildren(QFrame):
            sep.setStyleSheet(f"""
                QFrame {{
                    color: {_t.BORDER_LIGHT};
                    background-color: {_t.SEPARATOR_BG};
                    max-height: 1px;
                    border: none;
                    margin-top: 4px;
                    margin-bottom: 0px;
                }}
            """)


class HistoryDialog(QDialog):
    """
    Диалог просмотра истории документа
    """

    def __init__(self, document_data: dict, parent=None, current_user: dict = None):
        super().__init__(parent)

        self.document_data = document_data
        self.current_user = current_user or self._get_default_user()

        # Загружаем UI
        ui_path = os.path.join(ROOT_DIR, "client", "ui", "documents", "history_dialog.ui")

        if not os.path.exists(ui_path):
            print(f"Ошибка: UI файл не найден по пути: {ui_path}")
            self._setup_fallback_ui()
        else:
            try:
                loadUi(ui_path, self)
                apply_theme_to_widget(self)
                self._setup_ui()
                self._load_history()
                self._connect_signals()
            except Exception as e:
                print(f"Ошибка загрузки UI: {e}")
                import traceback
                traceback.print_exc()
                self._setup_fallback_ui()

    def _get_default_user(self) -> dict:
        """Возвращает тестового пользователя"""
        return {
            'id': 1,
            'full_name': 'Иванов И.И.',
            'last_name': 'Иванов',
            'first_name': 'Иван',
            'middle_name': 'Иванович'
        }

    def _setup_fallback_ui(self):
        """Создает простой интерфейс если UI файл не найден"""
        _t = get_manager().current

        self.setWindowTitle("История документа")
        self.setModal(True)
        self.setMinimumSize(700, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title_label = QLabel("История документа")
        title_label.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {_t.TEXT_PRIMARY};"
        )
        layout.addWidget(title_label)

        doc_number = self.document_data.get('reg_number', self.document_data.get('number', 'Без номера'))
        doc_info = QLabel(f"Документ: №{doc_number}")
        doc_info.setStyleSheet(f"color: {_t.TEXT_MUTED};")
        layout.addWidget(doc_info)

        self.historyListWidget = QListWidget()
        self.historyListWidget.setMinimumHeight(300)
        self.historyListWidget.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {_t.BORDER_LIGHT};
                border-radius: 8px;
                background-color: {_t.BG_SURFACE_SUBTLE};
                padding: 6px 0px;
            }}
            QListWidget::item {{
                padding: 0px;
                margin: 0px;
            }}
        """)
        layout.addWidget(self.historyListWidget)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.closeButton = QPushButton("Закрыть")
        self.closeButton.setMinimumSize(120, 44)
        self.closeButton.setStyleSheet(f"""
            QPushButton {{
                background-color: {_t.BTN_DARK_BG};
                color: {_t.TEXT_ON_ACCENT};
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {_t.BTN_DARK_HOVER_BG};
                color: {_t.TEXT_BLACK};
            }}
            QPushButton:pressed {{
                background-color: {_t.BTN_DARK_PRESSED_BG};
            }}
        """)
        button_layout.addWidget(self.closeButton)

        layout.addLayout(button_layout)

        self._load_history()
        self.closeButton.clicked.connect(self.accept)

    def _setup_ui(self):
        """Настройка UI элементов"""
        doc_number = self.document_data.get('reg_number', self.document_data.get('number', 'Без номера'))
        if hasattr(self, 'docInfoLabel'):
            self.docInfoLabel.setText(f"Документ №{doc_number}")

        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

    def _load_history(self):
        """Загрузка истории в список"""
        if not hasattr(self, 'historyListWidget'):
            print("Ошибка: historyListWidget не найден")
            return

        self.historyListWidget.clear()

        history = self.document_data.get('history', [])

        if not history:
            history = self._generate_history_from_data()

        if not history:
            item = QListWidgetItem("История пуста")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.historyListWidget.addItem(item)
            return

        def get_sort_key(event):
            created_at = event.get('created_at')
            if created_at is None:
                return datetime.min

            if isinstance(created_at, str):
                try:
                    return parse_datetime(created_at)
                except Exception:
                    return datetime.min

            if isinstance(created_at, datetime):
                return created_at

            return datetime.min

        try:
            sorted_history = sorted(history, key=get_sort_key, reverse=False)
        except Exception as e:
            print(f"[HistoryDialog] Error sorting history: {e}")
            sorted_history = history

        for i, event in enumerate(sorted_history):
            show_separator = (i < len(sorted_history) - 1)
            self._add_event_to_list(event, show_separator)

        self.historyListWidget.scrollToBottom()

    def _generate_history_from_data(self) -> List[Dict]:
        """Генерирует историю из имеющихся данных документа"""
        history = []

        created_at = self.document_data.get('created_at')
        if created_at:
            creator = self.document_data.get('creator', self._get_default_user())
            if isinstance(creator, dict):
                creator_name = creator.get('full_name', creator.get('name', 'Неизвестный пользователь'))
            else:
                creator_name = str(creator)

            if isinstance(created_at, str):
                try:
                    created_at = parse_datetime(created_at)
                except Exception:
                    created_at = datetime.now()
            elif not isinstance(created_at, datetime):
                created_at = datetime.now()

            history.append({
                'type': 'created',
                'user': creator_name,
                'created_at': created_at
            })

        redirects = self.document_data.get('redirects', [])
        for redirect in redirects:
            redirected_at = redirect.get('redirected_at', datetime.now())
            if isinstance(redirected_at, str):
                try:
                    redirected_at = parse_datetime(redirected_at)
                except Exception:
                    redirected_at = datetime.now()

            history.append({
                'type': 'redirect',
                'from_user': redirect.get('from_user', 'Неизвестный пользователь'),
                'to_user': redirect.get('to_user', 'Неизвестный пользователь'),
                'created_at': redirected_at
            })

        comments = self.document_data.get('comments', [])
        for comment in comments:
            comment_time = comment.get('created_at', datetime.now())
            if isinstance(comment_time, str):
                try:
                    comment_time = parse_datetime(comment_time)
                except Exception:
                    comment_time = datetime.now()

            history.append({
                'type': 'comment',
                'user': comment.get('author_name', comment.get('author', 'Неизвестный пользователь')),
                'text': comment.get('text', ''),
                'created_at': comment_time
            })

        status_changes = self.document_data.get('status_changes', [])
        for change in status_changes:
            changed_at = change.get('changed_at', datetime.now())
            if isinstance(changed_at, str):
                try:
                    changed_at = parse_datetime(changed_at)
                except Exception:
                    changed_at = datetime.now()

            history.append({
                'type': 'status_change',
                'user': change.get('user', 'Неизвестный пользователь'),
                'old_status': change.get('old_status', ''),
                'new_status': change.get('new_status', ''),
                'created_at': changed_at
            })

        try:
            history.sort(key=lambda x: x.get('created_at', datetime.now()))
        except Exception as e:
            print(f"[HistoryDialog] Error sorting generated history: {e}")

        return history

    def _add_event_to_list(self, event: dict, show_separator: bool = True):
        """Добавление события в список"""
        try:
            item = QListWidgetItem()
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

            widget = HistoryItemWidget(event, show_separator=show_separator)

            item.setSizeHint(widget.sizeHint())

            self.historyListWidget.addItem(item)
            self.historyListWidget.setItemWidget(item, widget)
        except Exception as e:
            print(f"[HistoryDialog] Error adding event to list: {e}")
            try:
                item = QListWidgetItem(str(event))
                self.historyListWidget.addItem(item)
            except:
                pass

    def _connect_signals(self):
        """Подключение сигналов"""
        if hasattr(self, 'closeButton'):
            self.closeButton.clicked.connect(self.accept)

    def get_history(self) -> list:
        """Получить всю историю"""
        return self.document_data.get('history', [])

    def reapply_theme(self):
        """Переприменить тему после set_theme()."""
        apply_theme_to_widget(self)

        if hasattr(self, 'historyListWidget'):
            for i in range(self.historyListWidget.count()):
                item = self.historyListWidget.item(i)
                widget = self.historyListWidget.itemWidget(item)
                if widget and hasattr(widget, "reapply_theme"):
                    widget.reapply_theme()