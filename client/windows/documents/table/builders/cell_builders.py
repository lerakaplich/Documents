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

class CommentsCellBuilder:
    """Билдер ячейки с комментариями"""

    def __init__(self, even_color, odd_color, signals):
        self.even_color = even_color
        self.odd_color = odd_color
        self.signals = signals

    def build(self, row, document):
        """Создание виджета с комментариями"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        comments = document.get("comments", [])
        last_comment_text = document.get("last_comment_text", "")

        if comments:
            # Берем последний комментарий
            last_comment = comments[-1]

            # Поддержка обоих форматов: author или employee_id
            if 'author' in last_comment:
                author = last_comment['author']
            elif 'employee_id' in last_comment:
                # Здесь можно получить имя сотрудника по ID
                # Пока используем заглушку
                author = f"Сотрудник {last_comment['employee_id']}"
            else:
                author = "Автор"

            comment_text = last_comment.get('text', '')

            # Если есть текст последнего комментария - показываем его
            if last_comment_text:
                label = QLabel(last_comment_text[:30] + "..." if len(last_comment_text) > 30 else last_comment_text)
                # Делаем фон прозрачным
                label.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        border: none;
                        color: #333;
                        font-size: 11px;
                    }
                """)
                label.setWordWrap(True)
                layout.addWidget(label)
        else:
            # Нет комментариев - добавляем пустой виджет для сохранения отступа
            label = QLabel("")
            label.setStyleSheet("background-color: transparent;")
            layout.addWidget(label)

        # Устанавливаем фон для всего виджета
        bg_color = self.even_color if row % 2 == 0 else self.odd_color
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color.name()};
            }}
            QWidget > QLabel {{
                background-color: transparent;
            }}
        """)

        return widget
class AttachmentCellBuilder:
    """Построитель ячейки с вложениями"""

    def __init__(self, even_color, odd_color, supported_formats, signals):
        self.even_color = even_color
        self.odd_color = odd_color
        self.supported_formats = supported_formats
        self.signals = signals

    def build(self, row, document):
        """Создание виджета с кнопкой вложения"""
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        attachments = document.get("attachments", [])

        if attachments:
            btn = QPushButton("Открыть")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFF8ED;
                    color: #CCAB6E;
                    border: 1px solid #CCAB6E;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: #CCAB6E;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #998664;
                }
            """)
            btn.setProperty("attachments", attachments)
            btn.setProperty("document", document)
            btn.clicked.connect(lambda checked, b=btn: self._show_attachments_menu(b))
        else:
            btn = QPushButton("Загрузить")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F0F8FF;
                    color: #5A8FBF;
                    border: 1px solid #5A8FBF;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: #5A8FBF;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #4A7A9E;
                }
            """)
            btn.setProperty("document_id", document.get("id"))
            btn.clicked.connect(lambda checked, b=btn: self._upload_attachment(b))

        layout.addWidget(btn)
        return container

    def _show_attachments_menu(self, button):
        """Показать меню со списком вложений"""
        attachments = button.property("attachments")
        document = button.property("document")

        if not attachments:
            return

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { 
                background-color: white; 
                border: 1px solid #c0c0c0; 
                border-radius: 5px; 
                padding: 5px; 
                color: black;
            }
            QMenu::item { 
                padding: 8px 25px 8px 15px; 
                border-radius: 3px; 
                font-size: 14px; 
            }
            QMenu::item:selected { 
                background-color: #e3f2fd; 
            }
            QMenu::separator { 
                height: 1px; 
                background: #e0e0e0; 
                margin: 5px 10px; 
            }
        """)

        # Добавляем все файлы в меню
        for attachment in attachments:
            file_icon = "📄" if not attachment['name'].lower().endswith('.pdf') else "📕"
            action = QAction(f"{file_icon} {attachment['name']}", menu)
            action.triggered.connect(
                lambda checked, a=attachment, d=document:
                self.signals.attachment_clicked.emit(d, a)
            )
            menu.addAction(action)

        # Добавляем сепаратор
        menu.addSeparator()

        # Добавляем опцию загрузки нового файла
        add_action = QAction("➕ Добавить файл", menu)
        add_action.triggered.connect(lambda checked: self._upload_attachment(button))
        menu.addAction(add_action)

        # Показываем меню под кнопкой
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def _upload_attachment(self, button):
        """Загрузить вложение"""
        document_id = button.property("document_id")

        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Выберите файл для загрузки",
            "",
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
        """
        Создание виджета с делегатами

        Args:
            row: номер строки
            document: данные документа

        Returns:
            QWidget: виджет с делегатами
        """
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        delegates = document.get("delegates", [])
        doc_id = document.get("id", 0)

        if delegates:
            # Превращаем элементы (строки или словари) в читаемые имена
            processed_names = []
            for d in delegates:
                if isinstance(d, dict):
                    processed_names.append(d.get("name", ""))
                else:
                    processed_names.append(str(d))

            delegates_text = ", ".join(filter(None, processed_names)) if processed_names else "-"

            label = QLabel(delegates_text)
            label.setStyleSheet("""
                QLabel {
                    color: #1B232A;
                    font-size: 12px;
                    padding: 4px 6px;
                    background-color: transparent;
                    border: none;
                }
            """)
            label.setWordWrap(True)
            label.setToolTip(f"Делегаты: {delegates_text}")
            layout.addWidget(label)

            container.setCursor(Qt.CursorShape.PointingHandCursor)

            # Явный безопасный обработчик события мыши
            def on_cell_pressed(event):
                if event.button() == Qt.MouseButton.LeftButton:
                    if self.signals and hasattr(self.signals, 'redirect_requested'):
                        self.signals.redirect_requested.emit(doc_id, delegates)
                    event.accept()

            container.mousePressEvent = on_cell_pressed
        else:
            # Если делегатов нет - показываем вашу оригинальную кнопку "Добавить"
            btn = QPushButton("Добавить")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFF0F5;
                    color: #D87093;
                    border: 1px solid #D87093;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: #D87093;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #B05A7A;
                }
            """)
            btn.clicked.connect(
                lambda checked: self.signals.redirect_requested.emit(doc_id, [])
            )
            layout.addWidget(btn)

        return container


class ReplyCellBuilder:
    """Построитель ячейки с ответом"""

    def __init__(self, even_color, odd_color, supported_formats, signals):
        self.even_color = even_color
        self.odd_color = odd_color
        self.supported_formats = supported_formats
        self.signals = signals

    def build(self, row, document):
        """Создание виджета с кнопкой ответа"""
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        reply_file = document.get("reply_file")

        if reply_file:
            btn = QPushButton("Открыть")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F5F0FF;
                    color: #8B6BAE;
                    border: 1px solid #8B6BAE;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: #8B6BAE;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #6B4D8A;
                }
            """)
            btn.clicked.connect(
                lambda checked, rf=reply_file: self.signals.reply_clicked.emit(rf)
            )
        else:
            btn = QPushButton("Загрузить")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFF5F0;
                    color: #D4896B;
                    border: 1px solid #D4896B;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: #D4896B;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #B06D52;
                }
            """)
            btn.clicked.connect(
                lambda checked, did=document.get("id"): self._upload_reply(did)
            )

        layout.addWidget(btn)
        return container

    def _upload_reply(self, document_id):
        """Загрузить файл ответа"""
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Выберите файл ответа",
            "",
            "Документы (*.pdf *.docx *.doc *.txt *.tif);;PDF (*.pdf);;Word (*.docx *.doc);;Текст (*.txt);;TIFF (*.tif)"
        )

        if file_path:
            self.signals.reply_upload.emit(document_id, file_path)