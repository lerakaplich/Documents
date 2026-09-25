"""
Модуль с построителями ячеек таблицы
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QSpacerItem, QSizePolicy, QMenu, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QAction, QFont
import os

from client.core.themes import T
from client.windows.documents.table.widgets.hashtag_widget import HashtagWidget
import logging
logger = logging.getLogger("AppDebug")

class CellBuilderSignals(QObject):
    """Сигналы для построителей ячеек"""
    attachment_clicked = pyqtSignal(dict, dict)  # document_data, attachment
    attachment_upload = pyqtSignal(int, str)  # document_id, file_path
    reply_clicked = pyqtSignal(dict)  # reply_file
    reply_upload = pyqtSignal(int, str)  # document_id, file_path
    comment_clicked = pyqtSignal(dict)  # document_data
    delegate_added = pyqtSignal(dict)
    redirect_requested = pyqtSignal(int, list)

class TagsCellBuilder:
    """Построитель ячейки с хэштегами"""

    def __init__(self, even_color, odd_color):
        self.even_color = even_color
        self.odd_color = odd_color

    def build(self, row, tags):
        """Создание виджета с хэштегами"""
        container = QWidget()
        container.setObjectName("tagsContainer")

        # Делаем фон прозрачным
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("""
            QWidget#tagsContainer {
                background-color: transparent;
                border: none;
            }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if tags:
            for tag in tags:
                tag_widget = HashtagWidget(tag["name"], tag["color"])
                layout.addWidget(tag_widget)
                tag_widget.update_style()

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout.addItem(spacer)

        return container


# client/windows/documents/table/builders/cell_builders.py

class ElidedLabel(QLabel):
    """QLabel с автоматическим обрезанием текста и цветом из темы."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setWordWrap(False)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred
        )
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._apply_theme()

    def _apply_theme(self):
        from client.core.themes import get_manager
        t = get_manager().current
        self.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                border: none;
                color: {t.TEXT_BLACK};
                font-size: 12px;
                padding: 4px 6px;
            }}
        """)

    def reapply_theme(self):
        self._apply_theme()

    def set_full_text(self, text):
        self._full_text = text
        self.update_elided_text()

    def update_elided_text(self):
        if not self._full_text:
            self.setText("")
            return
        available_width = self.width() - 12
        if available_width <= 0:
            available_width = 100
        font_metrics = self.fontMetrics()
        elided_text = font_metrics.elidedText(
            self._full_text,
            Qt.TextElideMode.ElideRight,
            available_width
        )
        self.setText(elided_text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_elided_text()


class CommentsCellBuilder:
    """Билдер ячейки с комментариями"""

    def __init__(self, even_color, odd_color, signals):
        self.even_color = even_color
        self.odd_color = odd_color
        self.signals = signals

    def build(self, row, document):
        widget = QWidget()
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        comments = document.get("comments", [])
        last_comment_text = document.get("last_comment_text", "")

        # ВАЖНО: реестр документов (GET /documents/documents/) отдаёт только
        # last_comment_text, полный список comments сюда не приходит.
        # Раньше условие было `if comments:`, из-за чего строка с уже
        # существующим последним комментарием показывала кнопку "Добавить".
        if comments or last_comment_text:
            text_to_show = last_comment_text
            if not text_to_show and comments:
                text_to_show = comments[-1].get('text', '')

            label = ElidedLabel()
            label.set_full_text(text_to_show)
            label.setToolTip(f"Последний комментарий: {text_to_show}")

            layout.addWidget(label)
            widget.setCursor(Qt.CursorShape.PointingHandCursor)

            def on_cell_pressed(event):
                if event.button() == Qt.MouseButton.LeftButton:
                    if self.signals and hasattr(self.signals, 'comment_clicked'):
                        self.signals.comment_clicked.emit(document)
                    event.accept()

            widget.mousePressEvent = on_cell_pressed
        else:
            btn = QPushButton("Добавить")
            btn.setProperty("_cell_role", "comments_add")
            btn.setStyleSheet(self._button_style())
            btn.clicked.connect(
                lambda checked: self.signals.comment_clicked.emit(document)
            )
            layout.addWidget(btn)

        return widget

    @staticmethod
    def _button_style():
        """Добавить комментарий — тёплый акцентный (не совпадает с темой)."""
        from client.core.themes import get_manager
        t = get_manager().current
        return f"""
            QPushButton {{
                background-color: {t.BG_CARD_ELEVATED};
                color: {t.TEXT_ACCENT_DARK};
                border: 1px solid {t.TEXT_ACCENT_DARK};
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {t.TEXT_ACCENT_DARK};
                color: {t.TEXT_ON_ACCENT};
                border-color: {t.TEXT_ACCENT_DARK};
            }}
            QPushButton:pressed {{
                background-color: {t.TEXT_ACCENT_DARK_STRONG};
                border-color: {t.TEXT_ACCENT_DARK_STRONG};
            }}
        """

    def reapply_theme(self):
        # Делегируем в ячейку — но проще перекрашивать «на лету» в row_renderer,
        # если перерисовываем таблицу целиком. См. пункт 3.
        pass

class AttachmentCellBuilder:

    def __init__(self, even_color, odd_color, supported_formats, signals, attachment_service=None):
        self.even_color = even_color
        self.odd_color = odd_color
        self.supported_formats = supported_formats
        self.signals = signals
        # Может отсутствовать (например, тестовый запуск без http_client) —
        # тогда падаем обратно на document.get("attachments", []), если он есть.
        self.attachment_service = attachment_service

    def build(self, row, document):
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("""
            QWidget { background-color: transparent; border: none; }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Реестр документов (GET /documents/documents/) не отдаёт список файлов —
        # только флаг has_attachments. Реальный список подгружаем по клику
        # (см. _show_attachments_menu), а не заранее для каждой строки.
        has_attachments = document.get("has_attachments", bool(document.get("attachments")))

        if has_attachments:
            btn = QPushButton("Вложения")
            btn.setStyleSheet(self._open_style())
            btn.setProperty("document", document)
            btn.clicked.connect(lambda checked, b=btn: self._show_attachments_menu(b))
        else:
            btn = QPushButton("Загрузить")
            btn.setStyleSheet(self._upload_style())
            btn.setProperty("document_id", document.get("id"))
            btn.clicked.connect(lambda checked, b=btn: self._upload_attachment(b))

        layout.addWidget(btn)
        return container

    @staticmethod
    def _upload_style():
        """Загрузить вложение — зелёный, «призыв добавить»."""
        from client.core.themes import get_manager
        t = get_manager().current
        return f"""
            QPushButton {{
                background-color: {t.BG_CARD_ELEVATED};
                color: {t.TEXT_SUCCESS};
                border: 1px solid {t.TEXT_SUCCESS};
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {t.TEXT_SUCCESS};
                color: {t.TEXT_ON_ACCENT};
                border-color: {t.TEXT_SUCCESS};
            }}
            QPushButton:pressed {{
                background-color: {t.ACCENT_PRESSED_DEEP};
                border-color: {t.ACCENT_PRESSED_DEEP};
            }}
        """

    @staticmethod
    def _open_style():
        """Открыть вложение — нейтральный, спокойный."""
        from client.core.themes import get_manager
        t = get_manager().current
        return f"""
            QPushButton {{
                background-color: {t.BTN_SECONDARY_BG};
                color: {t.TEXT_PRIMARY};
                border: 1px solid {t.BORDER_DEFAULT};
                border-radius: 5px;
                font-size: 11px;
                font-weight: 500;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {t.BTN_SECONDARY_HOVER_BG};
                border-color: {t.TEXT_ACCENT_DARK};
                color: {t.TEXT_ACCENT_DARK};
            }}
            QPushButton:pressed {{
                background-color: {t.BTN_SECONDARY_PRESSED_BG};
            }}
        """

    def _show_attachments_menu(self, button):
        from client.core.themes import get_menu_style
        document = button.property("document")
        if not document:
            return

        attachments = self._fetch_attachments(document)
        if not attachments:
            QMessageBox.information(
                button, "Вложения",
                "Не удалось получить список вложений (или их нет)."
            )
            return

        menu = QMenu()
        menu.setStyleSheet(get_menu_style())

        for attachment in attachments:
            file_name = attachment.get("file_name") or attachment.get("name") or "Без имени"
            file_icon = "📄" if not file_name.lower().endswith('.pdf') else "📕"
            action = QAction(f"{file_icon} {file_name}", menu)
            action.triggered.connect(
                lambda checked, a=attachment, d=document:
                self.signals.attachment_clicked.emit(d, a)
            )
            menu.addAction(action)

        menu.addSeparator()
        add_action = QAction("➕ Добавить файл", menu)
        add_action.triggered.connect(lambda checked: self._upload_attachment_for(document.get("id")))
        menu.addAction(add_action)

        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def _fetch_attachments(self, document: dict) -> list:
        """Получить реальный список вложений документа (по клику, не заранее)."""
        doc_id = document.get("id")
        if self.attachment_service and doc_id:
            return self.attachment_service.get_attachments(doc_id)
        # Фолбэк для окружений без сервиса (например, автономный тестовый запуск)
        return document.get("attachments", [])

    def _upload_attachment(self, button):
        document_id = button.property("document_id")
        self._upload_attachment_for(document_id)

    def _upload_attachment_for(self, document_id):
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Выберите файл для загрузки", "",
            "Документы (*.pdf *.docx *.doc *.txt *.tif);;PDF (*.pdf);;Word (*.docx *.doc);;Текст (*.txt);;TIFF (*.tif)"
        )
        if file_path:
            self.signals.attachment_upload.emit(document_id, file_path)


"""
Модуль заполнения строк таблицы
"""
import os

from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox, QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush


# client/windows/documents/table/builders/cell_builders.py

class DelegatesCellBuilder:
    """Построитель ячейки с делегатами"""

    def __init__(self, even_color, odd_color, signals=None):
        self.even_color = even_color
        self.odd_color = odd_color
        self.signals = signals

    def build(self, row, document):
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("""
            QWidget { background-color: transparent; border: none; }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        delegates = document.get("delegates", [])
        doc_id = document.get("id", 0)

        if delegates:
            processed_names = []
            for d in delegates:
                if isinstance(d, dict):
                    processed_names.append(d.get("name", ""))
                else:
                    processed_names.append(str(d))

            delegates_text = ", ".join(filter(None, processed_names)) if processed_names else "-"

            label = ElidedLabel()
            label.set_full_text(delegates_text)
            label.setToolTip(f"Делегаты: {delegates_text}")

            layout.addWidget(label)
            container.setCursor(Qt.CursorShape.PointingHandCursor)

            def on_cell_pressed(event):
                if event.button() == Qt.MouseButton.LeftButton:
                    if self.signals and hasattr(self.signals, 'redirect_requested'):
                        self.signals.redirect_requested.emit(doc_id, delegates)
                    event.accept()

            container.mousePressEvent = on_cell_pressed
        else:
            btn = QPushButton("Добавить")
            btn.setStyleSheet(self._button_style())
            btn.clicked.connect(
                lambda checked: self.signals.redirect_requested.emit(doc_id, [])
            )
            layout.addWidget(btn)

        return container

    @staticmethod
    def _button_style():
        """Добавить делегата — красный (важное действие)."""
        from client.core.themes import get_manager
        t = get_manager().current
        return f"""
            QPushButton {{
                background-color: {t.BG_CARD_ELEVATED};
                color: {t.ACCENT_DANGER};
                border: 1px solid {t.ACCENT_DANGER};
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {t.ACCENT_DANGER};
                color: {t.TEXT_ON_ACCENT};
                border-color: {t.ACCENT_DANGER};
            }}
            QPushButton:pressed {{
                background-color: {t.ACCENT_DANGER_PRESSED};
                border-color: {t.ACCENT_DANGER_PRESSED};
            }}
        """


class ReplyCellBuilder:

    def __init__(self, even_color, odd_color, supported_formats, signals):
        self.even_color = even_color
        self.odd_color = odd_color
        self.supported_formats = supported_formats
        self.signals = signals

    def build(self, row, document):
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("""
            QWidget { background-color: transparent; border: none; }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        reply_file = document.get("reply_file")

        if reply_file:
            btn = QPushButton("Открыть")
            btn.setStyleSheet(self._open_style())
            btn.clicked.connect(
                lambda checked, rf=reply_file: self.signals.reply_clicked.emit(rf)
            )
        else:
            btn = QPushButton("Загрузить")
            btn.setStyleSheet(self._upload_style())
            btn.clicked.connect(
                lambda checked, did=document.get("id"): self._upload_reply(did)
            )

        layout.addWidget(btn)
        return container

    @staticmethod
    def _upload_style():
        """Загрузить ответ — зелёный, как вложение."""
        from client.core.themes import get_manager
        t = get_manager().current
        return f"""
            QPushButton {{
                background-color: {t.BG_CARD_ELEVATED};
                color: {t.TEXT_SUCCESS};
                border: 1px solid {t.TEXT_SUCCESS};
                border-radius: 5px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {t.TEXT_SUCCESS};
                color: {t.TEXT_ON_ACCENT};
                border-color: {t.TEXT_SUCCESS};
            }}
            QPushButton:pressed {{
                background-color: {t.ACCENT_PRESSED_DEEP};
                border-color: {t.ACCENT_PRESSED_DEEP};
            }}
        """

    @staticmethod
    def _open_style():
        """Открыть ответ — нейтральный."""
        from client.core.themes import get_manager
        t = get_manager().current
        return f"""
            QPushButton {{
                background-color: {t.BTN_SECONDARY_BG};
                color: {t.TEXT_PRIMARY};
                border: 1px solid {t.BORDER_DEFAULT};
                border-radius: 5px;
                font-size: 11px;
                font-weight: 500;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {t.BTN_SECONDARY_HOVER_BG};
                border-color: {t.TEXT_ACCENT_DARK};
                color: {t.TEXT_ACCENT_DARK};
            }}
            QPushButton:pressed {{
                background-color: {t.BTN_SECONDARY_PRESSED_BG};
            }}
        """

    def _upload_reply(self, document_id):
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Выберите файл ответа", "",
            "Документы (*.pdf *.docx *.doc *.txt *.tif);;PDF (*.pdf);;Word (*.docx *.doc);;Текст (*.txt);;TIFF (*.tif)"
        )
        if file_path:
            self.signals.reply_upload.emit(document_id, file_path)