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

from client.windows.documents.table.hashtag_widget import HashtagWidget
from client.windows.documents.table.read_checkbox import ReadCheckBox


class CellBuilderSignals(QObject):
    """Сигналы для построителей ячеек"""
    attachment_clicked = pyqtSignal(dict, dict)  # document_data, attachment
    attachment_upload = pyqtSignal(int, str)  # document_id, file_path
    reply_clicked = pyqtSignal(dict)  # reply_file
    reply_upload = pyqtSignal(int, str)  # document_id, file_path
    comment_clicked = pyqtSignal(dict)  # document_data


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

class CommentsCellBuilder:
    """Построитель ячейки с комментариями"""

    def __init__(self, even_color, odd_color, signals=None):
        self.even_color = even_color
        self.odd_color = odd_color
        self.signals = signals

    def build(self, row, document):
        """
        Создание виджета с комментариями

        Args:
            row: номер строки
            document: данные документа

        Returns:
            QWidget: виджет с комментариями
        """
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        comments = document.get("comments", [])
        doc_id = document.get("id", "")

        if comments:
            # Берем последний комментарий
            last_comment = comments[-1]

            # Создаем текст с именем автора и текстом комментария
            comment_text = f"{last_comment['author']}: {last_comment['text']}"

            # Создаем QLabel с текстом комментария
            label = QLabel(comment_text)
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

            # Добавляем тултип с полной информацией
            tooltip_lines = ["Комментарии:"]
            for comment in comments:
                tooltip_lines.append(f"  {comment['author']}: {comment['text']}")
                if 'date' in comment:
                    tooltip_lines.append(f"    (Дата: {comment['date']})")
            label.setToolTip("\n".join(tooltip_lines))

            layout.addWidget(label)

            # Если комментариев больше одного, добавляем индикатор
            if len(comments) > 1:
                count_label = QLabel(f"ещё {len(comments) - 1} коммент.")
                count_label.setStyleSheet("""
                    QLabel {
                        color: #888888;
                        font-size: 10px;
                        padding: 0px 6px;
                        background-color: transparent;
                        border: none;
                    }
                """)
                layout.addWidget(count_label)

        else:
            # Если комментариев нет - показываем кнопку "Добавить" в стиле "Открыть/Загрузить"
            btn = QPushButton("Добавить")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #F0FFF4;
                    color: #4CAF50;
                    border: 1px solid #4CAF50;
                    border-radius: 5px;
                    font-size: 11px;
                    font-weight: 500;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background-color: #4CAF50;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #388E3C;
                }
            """)
            btn.clicked.connect(
                lambda checked, doc=document: self._on_add_comment(doc)
            )

            # Выравниваем кнопку по центру
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            button_layout.addWidget(btn)
            button_layout.addStretch()
            layout.addLayout(button_layout)

        return container

    def _on_add_comment(self, document):
        """
        Обработчик добавления комментария

        Args:
            document: данные документа
        """
        if self.signals:
            self.signals.comment_clicked.emit(document)
        else:
            # Если сигналы не переданы, показываем информационное сообщение
            QMessageBox.information(
                None,
                "Добавление комментария",
                f"Добавление комментария к документу '{document.get('name', '')}'"
            )

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

        if delegates:
            # Показываем делегатов через запятую
            delegates_text = ", ".join(str(d) for d in delegates)
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
        else:
            # Если делегатов нет - показываем кнопку "Добавить"
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
                lambda checked, doc=document: self._on_add_delegate(doc)
            )
            layout.addWidget(btn)

        return container

    def _on_add_delegate(self, document):
        """
        Обработчик добавления делегата

        Args:
            document: данные документа
        """
        if self.signals and hasattr(self.signals, 'delegate_added'):
            self.signals.delegate_added.emit(document)
        else:
            QMessageBox.information(
                None,
                "Добавление делегата",
                f"Добавление делегата к документу '{document.get('name', '')}'"
            )




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