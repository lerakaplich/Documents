"""
Рендеринг строк таблицы - преобразование данных в UI
"""
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QBrush

from client.core.utils.icon_manager import icon_manager
from client.windows.documents.table.builders.cell_builders import (
    CellBuilderSignals, AttachmentCellBuilder, CommentsCellBuilder,
    TagsCellBuilder, DelegatesCellBuilder, ReplyCellBuilder
)
from client.windows.documents.table.widgets.read_checkbox import ReadCheckBox


class RowRenderer:
    """
    Преобразователь данных документа в UI элементы таблицы.
    Только рендеринг, без логики управления.
    """

    def __init__(self, table_widget, config, signals, columns_config=None):
        self._table = table_widget
        self._config = config
        self._signals = signals
        self._columns = columns_config or config.COLUMNS_CONFIG

        cell_signals = CellBuilderSignals()
        cell_signals.attachment_clicked.connect(self._on_attachment_clicked)
        cell_signals.attachment_upload.connect(self._on_attachment_upload)
        cell_signals.reply_clicked.connect(self._on_reply_clicked)
        cell_signals.reply_upload.connect(self._on_reply_upload)

        self._tags_builder = TagsCellBuilder(config.EVEN_ROW_COLOR, config.ODD_ROW_COLOR)
        self._comments_builder = CommentsCellBuilder(config.EVEN_ROW_COLOR, config.ODD_ROW_COLOR, cell_signals)
        self._attachment_builder = AttachmentCellBuilder(
            config.EVEN_ROW_COLOR, config.ODD_ROW_COLOR,
            config.SUPPORTED_FORMATS, cell_signals
        )
        self._reply_builder = ReplyCellBuilder(
            config.EVEN_ROW_COLOR, config.ODD_ROW_COLOR,
            config.SUPPORTED_FORMATS, cell_signals
        )
        self._delegates_builder = DelegatesCellBuilder(
            config.EVEN_ROW_COLOR, config.ODD_ROW_COLOR, cell_signals
        )

    def update_columns_config(self, columns_config: dict):
        """Обновить конфигурацию колонок"""
        self._columns = columns_config

    def render_row(self, row: int, document: dict):
        """
        Преобразовать документ в UI элементы строки.
        Только создание элементов, без управления таблицей.
        """
        bg_color = self._config.EVEN_ROW_COLOR if row % 2 == 0 else self._config.ODD_ROW_COLOR
        col_map = self._get_col_map()

        # Скрываем ID если есть
        self._hide_id_column(col_map)

        # Номер документа с иконкой закрепления
        self._render_reg_number(row, document, bg_color, col_map)

        # Чекбокс прочтения
        self._render_read_checkbox(row, document, bg_color, col_map)

        # Текстовые колонки
        self._render_text_columns(row, document, bg_color, col_map)

        # Списковые колонки
        self._render_list_columns(row, document, bg_color, col_map)

        # Специальные виджеты
        self._render_special_widgets(row, document, col_map)

    def _get_col_map(self) -> dict:
        """Получить маппинг названий колонок к индексам"""
        return {name: idx for idx, name in enumerate(self._columns.values())}

    def _hide_id_column(self, col_map: dict):
        """Скрыть колонку ID если она есть"""
        col = col_map.get("ID")
        if col is not None:
            self._table.setColumnHidden(col, True)

    def _render_reg_number(self, row: int, document: dict, bg_color, col_map: dict):
        """Рендеринг номера документа с иконкой закрепления"""
        col = col_map.get("Номер документа")
        if col is None:
            return

        reg_number = document.get("reg_number", "")
        is_pinned = document.get("is_pinned", False)

        item = QTableWidgetItem(str(reg_number) if reg_number else "")
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        item.setBackground(QBrush(bg_color))
        item.setForeground(QBrush(self._config.TEXT_COLOR))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setData(Qt.ItemDataRole.UserRole, document)

        if is_pinned:
            pin_icon = icon_manager.get_icon('pin', QSize(16, 16))
            item.setIcon(pin_icon)

        self._table.setItem(row, col, item)

    def _render_read_checkbox(self, row: int, document: dict, bg_color, col_map: dict):
        """Рендеринг чекбокса прочтения"""
        col = col_map.get("Прочитано")
        if col is None:
            return

        read_widget = ReadCheckBox(document.get("id", 0), document.get("is_read", False))
        read_widget.state_changed.connect(self._signals.read_status_changed.emit)
        self._table.setCellWidget(row, col, read_widget)

        # Устанавливаем фон
        widget = self._table.cellWidget(row, col)
        if widget:
            widget.setStyleSheet(f"QWidget {{ background-color: {bg_color.name()}; }}")

    def _render_text_columns(self, row: int, document: dict, bg_color, col_map: dict):
        """Рендеринг текстовых колонок"""
        # Маппинг: имя колонки -> ключ в документе
        text_fields = {
            "Тема": "title",
            "Тип": "type_name",  # Используем type_name из документа
            "Дата создания": "created_at",
            "Статус": "status",
            "Краткое содержание": "about",
            "Срок исполнения": "deadline",
            "Направление": "direction",
        }

        for col_name, key in text_fields.items():
            col = col_map.get(col_name)
            if col is None:
                continue

            value = document.get(key, "") or document.get(key.lower(), "")

            # Для статуса используем человекочитаемый текст
            if key == "status":
                from client.core.data.document_data import DocumentDataConfig
                value = DocumentDataConfig.get_status_text(value) if value else ""
            # Для направления используем человекочитаемый текст
            elif key == "direction":
                from client.core.data.document_data import DocumentDataConfig
                value = DocumentDataConfig.get_direction_text(value) if value else ""
            # Для даты форматируем
            elif key == "created_at" or key == "deadline":
                if value and hasattr(value, 'strftime'):
                    value = value.strftime("%d.%m.%Y")

            item = self._create_text_item(str(value), bg_color)
            self._table.setItem(row, col, item)

    def _render_list_columns(self, row: int, document: dict, bg_color, col_map: dict):
        """Рендеринг списковых колонок"""
        list_columns = {
            "Отправители": "senders",
            "Получатели": "receivers",
            "Исполнители": "executors"
        }

        for col_name, key in list_columns.items():
            col = col_map.get(col_name)
            if col is None:
                continue

            values = document.get(key, [])
            if isinstance(values, list):
                # Если список словарей - берем имена
                if values and isinstance(values[0], dict):
                    text = ", ".join(v.get("name", str(v)) for v in values) if values else "-"
                else:
                    text = ", ".join(str(v) for v in values) if values else "-"
            else:
                text = str(values) if values else "-"

            item = self._create_text_item(text, bg_color)
            item.setToolTip(text)
            self._table.setItem(row, col, item)

    def _render_special_widgets(self, row: int, document: dict, col_map: dict):
        """Рендеринг специальных виджетов"""
        special = {
            "Хэштеги": self._tags_builder.build(row, document.get("tags", [])),
            "Комментарии": self._comments_builder.build(row, document),
            "Вложение": self._attachment_builder.build(row, document),
            "Ответ": self._reply_builder.build(row, document),
            "Делегаты": self._delegates_builder.build(row, document),
        }

        for col_name, widget in special.items():
            col = col_map.get(col_name)
            if col is not None:
                self._table.setCellWidget(row, col, widget)

    def _create_text_item(self, text: str, bg_color) -> QTableWidgetItem:
        """Создать стандартный текстовый элемент"""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        item.setBackground(QBrush(bg_color))
        item.setForeground(QBrush(self._config.TEXT_COLOR))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def _on_attachment_clicked(self, document, attachment):
        self._signals.attachment_opened.emit(
            document.get("id"),
            attachment.get('path') or attachment.get('storage_path')
        )

    def _on_attachment_upload(self, document_id, file_path):
        self._signals.attachment_added.emit(document_id, file_path)

    def _on_reply_clicked(self, reply_file):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(None, "Открытие ответа", f"Открывается: {reply_file.get('name')}")

    def _on_reply_upload(self, document_id, file_path):
        from PyQt6.QtWidgets import QMessageBox
        import os
        QMessageBox.information(None, "Загрузка ответа", f"Файл ответа загружен: {os.path.basename(file_path)}")