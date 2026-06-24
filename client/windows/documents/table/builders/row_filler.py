"""
Модуль заполнения строк таблицы
"""
import os

from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush

from client.windows.documents.table.builders.cell_builders import CellBuilderSignals, AttachmentCellBuilder, CommentsCellBuilder, \
    TagsCellBuilder, DelegatesCellBuilder, ReplyCellBuilder
from client.windows.documents.table.widgets.read_checkbox import ReadCheckBox


class RowFiller:
    """Класс для заполнения строк таблицы данными"""

    def __init__(self, table_widget, config, signals):
        self.table_widget = table_widget
        self.config = config
        self.signals = signals

        cell_signals = CellBuilderSignals()
        cell_signals.attachment_clicked.connect(self._on_attachment_clicked)
        cell_signals.attachment_upload.connect(self._on_attachment_upload)
        cell_signals.reply_clicked.connect(self._on_reply_clicked)
        cell_signals.reply_upload.connect(self._on_reply_upload)

        self.tags_builder = TagsCellBuilder(config.EVEN_ROW_COLOR, config.ODD_ROW_COLOR)
        self.comments_builder = CommentsCellBuilder(config.EVEN_ROW_COLOR, config.ODD_ROW_COLOR, cell_signals)
        self.attachment_builder = AttachmentCellBuilder(
            config.EVEN_ROW_COLOR, config.ODD_ROW_COLOR,
            config.SUPPORTED_FORMATS, cell_signals
        )
        self.reply_builder = ReplyCellBuilder(
            config.EVEN_ROW_COLOR, config.ODD_ROW_COLOR,
            config.SUPPORTED_FORMATS, cell_signals
        )
        self.delegates_builder = DelegatesCellBuilder(
            config.EVEN_ROW_COLOR, config.ODD_ROW_COLOR, cell_signals
        )

    def fill_row(self, row, document):
        """Заполнение одной строки таблицы"""
        bg_color = self.config.EVEN_ROW_COLOR if row % 2 == 0 else self.config.ODD_ROW_COLOR
        col_map = {name: idx for idx, name in enumerate(self.config.COLUMNS_CONFIG.values())}

        self.table_widget.setRowHeight(row, 60)  # увеличил высоту для лучшей читаемости

        # ID с иконкой закрепления
        doc_id = str(document.get("id", ""))
        is_pinned = document.get("is_pinned", False)

        if is_pinned:
            display_text = f"📌 {doc_id}"
        else:
            display_text = doc_id

        item_id = self._create_item(display_text, bg_color, Qt.AlignmentFlag.AlignCenter)
        item_id.setData(Qt.ItemDataRole.UserRole, document)
        self.table_widget.setItem(row, col_map["ID"], item_id)

        # Прочитано
        self._setup_read_checkbox(row, col_map["Прочитано"], document, bg_color)

        # Текстовые колонки (все возможные)
        self._fill_text_columns(row, document, bg_color, col_map)

        # Списковые колонки (отправители, получатели, исполнители)
        self._fill_list_columns(row, document, bg_color, col_map)

        # Специальные колонки
        self.table_widget.setCellWidget(
            row, col_map["Хэштеги"], self.tags_builder.build(row, document.get("tags", []))
        )
        self.table_widget.setCellWidget(
            row, col_map["Комментарии"], self.comments_builder.build(row, document)
        )
        self.table_widget.setCellWidget(
            row, col_map["Вложение"], self.attachment_builder.build(row, document)
        )
        self.table_widget.setCellWidget(
            row, col_map["Ответ"], self.reply_builder.build(row, document)
        )

        # Делегаты - используем специальный билдер с кнопкой
        self.table_widget.setCellWidget(
            row, col_map["Делегаты"], self.delegates_builder.build(row, document)
        )

    def _create_item(self, text, bg_color, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter):
        item = QTableWidgetItem(text)
        item.setTextAlignment(alignment)
        item.setBackground(QBrush(bg_color))
        item.setForeground(QBrush(self.config.TEXT_COLOR))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def _setup_read_checkbox(self, row, col, document, bg_color):
        read_widget = ReadCheckBox(document.get("id", 0), document.get("is_read", False))
        read_widget.state_changed.connect(self.signals.read_status_changed.emit)
        self.table_widget.setCellWidget(row, col, read_widget)
        self._set_cell_background(row, col, bg_color)

    def _fill_text_columns(self, row, document, bg_color, col_map):
        """Все текстовые поля"""
        text_fields = {
            "Номер документа": "reg_number",
            "Тема": "title",
            "Тип": "type",
            "Дата": "date",
            "Статус": "status",
            "Краткое содержание": "about",
            "Срок исполнения": "deadline",
            "Направление": "direction",
            "Входящий номер": "incoming_number",
            "Входящая дата": "incoming_date",
        }

        for col_name, key in text_fields.items():
            value = document.get(key, "") or document.get(key.lower(), "")
            item = self._create_item(str(value), bg_color)
            self.table_widget.setItem(row, col_map.get(col_name, -1), item)

    def _fill_list_columns(self, row, document, bg_color, col_map):
        """Отправители, Получатели, Исполнители"""
        list_columns = {
            "Отправители": "senders",
            "Получатели": "receivers",
            "Исполнители": "executors"
        }

        for col_name, key in list_columns.items():
            values = document.get(key, [])
            if isinstance(values, list):
                text = ", ".join(str(v) for v in values) if values else "-"
            else:
                text = str(values) if values else "-"
            item = self._create_item(text, bg_color)
            item.setToolTip(text)
            self.table_widget.setItem(row, col_map.get(col_name, -1), item)

    def _set_cell_background(self, row, col, color):
        widget = self.table_widget.cellWidget(row, col)
        if widget:
            widget.setStyleSheet(f"QWidget {{ background-color: {color.name()}; }}")

    def _on_attachment_clicked(self, document, attachment):
        self.signals.attachment_opened.emit(document.get("id"),
                                            attachment.get('path') or attachment.get('storage_path'))

    def _on_attachment_upload(self, document_id, file_path):
        self.signals.attachment_added.emit(document_id, file_path)

    def _on_reply_clicked(self, reply_file):
        QMessageBox.information(None, "Открытие ответа", f"Открывается: {reply_file.get('name')}")

    def _on_reply_upload(self, document_id, file_path):
        QMessageBox.information(None, "Загрузка ответа", f"Файл ответа загружен: {os.path.basename(file_path)}")