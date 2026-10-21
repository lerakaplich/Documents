# client/windows/documents/comments/comment_dialog.py
"""
Диалог для просмотра и добавления комментариев к документу.

Источник правды — сервер:
    GET  /comments/{document_id}        → [{"id", "text", "created_at" (ISO, UTC), "author_fio"}, ...]
    POST /comments/{document_id}/edit   (form-поле text) → {"status": "success", ...}
POST возвращает только статус, поэтому после добавления список перечитывается с сервера
(так в нём появляются настоящие id, время и ФИО автора).
"""

import json
import os
import re
from datetime import datetime

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from PyQt6.uic import loadUi

from client.core.state.app_state import AppState
from client.core.themes import T, apply_theme_to_widget
from client.services.comment_service import CommentService

ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)

_FALLBACK_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%Y-%m-%d")


def parse_dt(value) -> datetime | None:
    """
    Любое представление времени → наивный datetime в ЛОКАЛЬНОМ часовом поясе (или None).
    Сервер отдаёт ISO в UTC ('2026-10-19T13:34:30.634016Z') — переводим в локальное время.
    Наивные значения считаем уже локальными.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            dt = None
            for fmt in _FALLBACK_FORMATS:
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return None
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


def format_dt(value) -> str:
    dt = parse_dt(value)
    if dt is not None:
        return dt.strftime("%d.%m.%Y %H:%M")
    return str(value) if value else "Только что"


def split_api_error(exc: Exception) -> tuple[int | None, str]:
    """
    Разбирает исключение клиента вида 'Ошибка 403: {"detail":"..."}'
    → (403, "...") — код ответа и человекочитаемый текст без сырого JSON.
    Если у исключения есть status_code/detail (типизированная ошибка) — берём их.
    """
    status = getattr(exc, "status_code", None)
    detail = getattr(exc, "detail", None)
    message = str(exc)

    if status is None:
        m = re.match(r"\s*Ошибка\s+(\d{3})\s*:\s*(.*)", message, re.DOTALL)
        if m:
            status = int(m.group(1))
            message = m.group(2)

    if detail is None:
        try:
            payload = json.loads(message)
            detail = payload.get("detail") if isinstance(payload, dict) else None
        except (ValueError, TypeError):
            detail = None
        # текст мог быть обрезан клиентом (response.text[:200]) — достаём detail регуляркой
        if detail is None:
            m = re.search(r'"detail"\s*:\s*"([^"]*)', message)
            detail = m.group(1) if m else message

    if not isinstance(detail, str):
        detail = str(detail)
    return status, detail.strip()


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
        author_name = comment.get("author_fio") or comment.get("author_name") or comment.get("author") or "Неизвестный"
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
        sep_label.setStyleSheet(f"color: {T.TEXT_TERTIARY}; background-color: transparent;")
        header_layout.addWidget(sep_label)

        # Время (локальное, dd.MM.yyyy HH:mm)
        time_label = QLabel(format_dt(comment.get("created_at")))
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
        text_label.setText(comment.get("text", ""))
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
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


class CommentDialog(QDialog):
    comment_added = pyqtSignal(dict)

    def __init__(self, document_data, parent=None, current_user=None, http_client=None):
        super().__init__(parent)
        self.document_data = document_data
        self.current_user = current_user or self._get_default_user()
        self._comments_cache = []
        self._input_locked = False
        self.http_client = http_client or AppState().http_client
        self.comment_service = CommentService(self.http_client)

        ui_path = os.path.join(ROOT_DIR, "client", "ui", "documents", "comments_dialog.ui")
        loadUi(ui_path, self)
        apply_theme_to_widget(self)

        self._setup_ui()
        self._load_comments_from_server()
        self._connect_signals()
        self._apply_permissions()

    def _get_default_user(self) -> dict:
        """Возвращает тестового пользователя"""
        return {
            "id": 1,
            "full_name": "Иванов И.И.",
            "last_name": "Иванов",
            "first_name": "Иван",
            "middle_name": "Иванович",
        }

    def _setup_ui(self):
        """Настройка UI элементов"""
        doc_number = self.document_data.get("reg_number", self.document_data.get("number", "Без номера"))

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
        # Комментарии разной высоты: плавная прокрутка по пикселям, без горизонтальной полосы
        self.commentsListWidget.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.commentsListWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.commentsListWidget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        # Настраиваем размеры
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        # Устанавливаем фокус на поле ввода
        self.commentTextEdit.setFocus()

    # ─────────────────────── загрузка ───────────────────────

    def _fetch_comments(self, doc_id) -> list | None:
        """Комментарии с сервера; None — если запрос не удался."""
        try:
            return list(self.comment_service.get_comments(doc_id) or [])
        except Exception as e:
            print(f"[CommentDialog] Ошибка загрузки комментариев: {e}")
            return None

    def _load_comments_from_server(self):
        doc_id = self.document_data.get("id")
        if doc_id:
            server_comments = self._fetch_comments(doc_id)
            if server_comments is not None:
                # Сервер — источник правды: локальные копии не домешиваем (иначе после
                # повторного открытия окна комментарии дублировались бы).
                self.document_data["comments"] = server_comments
        self._load_comments()

    @staticmethod
    def _sort_key(comment: dict) -> datetime:
        return parse_dt(comment.get("created_at")) or datetime.min

    def _load_comments(self):
        """Загрузка комментариев в список"""
        self.commentsListWidget.clear()

        comments = self.document_data.get("comments", []) or []
        self._comments_cache = list(comments)

        if not comments:
            item = QListWidgetItem("Нет комментариев")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            item.setSizeHint(QSize(0, 60))  # высота, ширина = по вьюпорту
            self.commentsListWidget.addItem(item)
            return

        sorted_comments = sorted(comments, key=self._sort_key)  # старые сверху, новые снизу

        for i, comment in enumerate(sorted_comments):
            self._add_comment_to_list(comment, show_separator=i < len(sorted_comments) - 1)

        self._refit_items()
        self.commentsListWidget.scrollToBottom()

    def _add_comment_to_list(self, comment: dict, show_separator: bool = True):
        """Добавление комментария в список"""
        item = QListWidgetItem()
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        widget = CommentItemWidget(comment, show_separator=show_separator)
        item.setSizeHint(self._item_size(widget))

        self.commentsListWidget.addItem(item)
        self.commentsListWidget.setItemWidget(item, widget)

    # ─────────────────────── размеры элементов ───────────────────────

    def _item_size(self, widget: QWidget) -> QSize:
        """
        Высота элемента с учётом переноса текста: sizeHint() виджета с QLabel(wordWrap)
        без заданной ширины считает текст в одну строку и обрезает длинные комментарии.
        """
        width = max(self.commentsListWidget.viewport().width(), 200)
        layout = widget.layout()
        if layout is not None and layout.hasHeightForWidth():
            height = layout.heightForWidth(width)
        else:
            height = widget.sizeHint().height()
        return QSize(width, max(height, widget.minimumSizeHint().height()))

    def _refit_items(self):
        """Пересчёт высоты всех комментариев под текущую ширину списка."""
        lst = self.commentsListWidget
        for row in range(lst.count()):
            item = lst.item(row)
            widget = lst.itemWidget(item)
            if widget is not None:
                item.setSizeHint(self._item_size(widget))

    def showEvent(self, event):
        super().showEvent(event)
        self._refit_items()  # ширина списка известна только после показа

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refit_items()

    # ─────────────────────── ввод и отправка ───────────────────────

    def _connect_signals(self):
        """Подключение сигналов"""
        self.sendButton.clicked.connect(self._on_send_clicked)

        # Отправка по Ctrl+Enter
        self.commentTextEdit.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Обработка событий для поля ввода"""
        if (
            obj is self.commentTextEdit
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self._on_send_clicked()
            return True
        return super().eventFilter(obj, event)

    def _apply_permissions(self):
        """Если сервер заранее сообщил, что замечания вносить нельзя (can_comment=False) — блокируем ввод."""
        if self.document_data.get("can_comment") is False:
            self._lock_input("У вас нет прав на внесение замечаний к этому документу.")

    def _lock_input(self, reason: str):
        """Блокирует поле ввода и кнопку отправки; просмотр комментариев остаётся доступным."""
        self._input_locked = True
        self.commentTextEdit.setReadOnly(True)
        self.commentTextEdit.clear()
        self.commentTextEdit.setPlaceholderText(reason)
        self.sendButton.setEnabled(False)
        self.sendButton.setToolTip(reason)

    def _on_send_clicked(self):
        text = self.commentTextEdit.toPlainText().strip()
        if self._input_locked or not text or not self.sendButton.isEnabled():
            return

        doc_id = self.document_data.get("id")
        if not doc_id:
            QMessageBox.warning(self, "Комментарий", "Документ не сохранён на сервере — комментарий добавить нельзя.")
            return

        known_ids = {c.get("id") for c in self.document_data.get("comments", []) or []}

        self.sendButton.setEnabled(False)
        try:
            try:
                self.comment_service.add_comment(doc_id, text)
            except Exception as e:
                status, detail = split_api_error(e)
                if status == 403:
                    # Нет прав — штатная ситуация: без traceback, права до закрытия окна не изменятся
                    print(f"[CommentDialog] Нет прав на замечания к документу {doc_id}")
                    self._lock_input(detail)
                    QMessageBox.information(self, "Комментарий", detail)
                else:
                    print(f"[CommentDialog] Не удалось отправить комментарий: {e}")
                    QMessageBox.warning(self, "Комментарий", f"Не удалось отправить комментарий:\n{detail}")
                return

            # POST отдаёт только статус — перечитываем список и находим новый комментарий
            fresh = self._fetch_comments(doc_id)
        finally:
            if not self._input_locked:
                self.sendButton.setEnabled(True)

        added = [c for c in (fresh or []) if c.get("id") not in known_ids]
        if not added:
            # Текст из поля не стираем, чтобы его можно было отправить повторно
            QMessageBox.warning(
                self,
                "Комментарий",
                "Сервер не подтвердил добавление комментария. Проверьте соединение и попробуйте ещё раз.",
            )
            return

        self.document_data["comments"] = fresh
        self.document_data["last_comment_text"] = text
        self._load_comments()
        self.commentTextEdit.clear()
        self.commentTextEdit.setFocus()

        self.comment_added.emit(max(added, key=self._sort_key))

    def get_comments(self) -> list:
        """Получить все комментарии"""
        return self.document_data.get("comments", [])