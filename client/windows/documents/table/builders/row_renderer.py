from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QTableWidgetItem

from client.windows.documents.table.builders.table_cell_item import CellData, TableCellItem


class RowRenderer:
    """
    Преобразователь данных документа в UI элементы таблицы.
    Поддерживает как стандартные QTableWidgetItem, так и кастомные TableCellItem
    """

    def __init__(self, table_widget, config, signals, columns_config=None, http_client=None):
        self._table = table_widget
        self._config = config
        self._signals = signals
        self._columns = columns_config or config.COLUMNS_CONFIG

        # Реальный список вложений подгружается лениво по клику (см.
        # AttachmentCellBuilder), а не на каждую строку сразу — иначе это
        # N+1 запросов на каждую отрисовку таблицы.
        self._attachment_service = None
        if http_client is not None:
            from client.services.attachment_service import AttachmentService
            self._attachment_service = AttachmentService(http_client)

        # Создаем ОДИН общий экземпляр сигналов для всех билдеров ячеек
        from client.windows.documents.table.builders.cell_builders import CellBuilderSignals
        self.cell_signals = CellBuilderSignals()
        self.cell_signals.attachment_clicked.connect(self._on_attachment_clicked)
        self.cell_signals.attachment_upload.connect(self._on_attachment_upload)
        self.cell_signals.reply_clicked.connect(self._on_reply_clicked)
        self.cell_signals.reply_upload.connect(self._on_reply_upload)
        self.cell_signals.redirect_requested.connect(self._on_redirect_requested)
        # В __init__ добавь подключение сигнала (после других подключений):
        self.cell_signals.comment_clicked.connect(self._on_comment_clicked)

        # Создаем все билдеры как обычно
        from client.windows.documents.table.builders.cell_builders import (
            TagsCellBuilder, AttachmentCellBuilder, ReplyCellBuilder
        )

        self._tags_builder = TagsCellBuilder(config.get_even_row_color, config.get_odd_row_color)
        self._attachment_builder = AttachmentCellBuilder(
            config.get_even_row_color, config.get_odd_row_color,
            config.SUPPORTED_FORMATS, self.cell_signals,
            attachment_service=self._attachment_service
        )
        self._reply_builder = ReplyCellBuilder(
            config.get_even_row_color, config.get_odd_row_color,
            config.SUPPORTED_FORMATS, self.cell_signals
        )

        # Импортируем ваши билдеры
        from client.windows.documents.table.builders.cell_builders import (
            CommentsCellBuilder, DelegatesCellBuilder
        )

        # Создаем экземпляры билдеров
        self._comments_builder = CommentsCellBuilder(
            config.get_even_row_color, config.get_odd_row_color, self.cell_signals
        )
        self._delegates_builder = DelegatesCellBuilder(
            even_color=config.get_even_row_color,
            odd_color=config.get_odd_row_color,
            signals=self.cell_signals
        )

        # Кеш для TableCellItem
        self._cell_items_cache = {}

        # Флаг использования кастомных ячеек
        self._use_custom_cells = True  # Можно переключать для тестирования

    def _on_redirect_requested(self, doc_id: int, delegates: list):
        """Срабатывает при клике на делегатов в ячейке"""
        document_data = {
            "id": doc_id,
            "delegates": delegates
        }
        if hasattr(self._signals, "document_action_triggered"):
            self._signals.document_action_triggered.emit("redirect", document_data)

    def _on_comment_clicked(self, document: dict):
        """Открытие диалога комментариев"""
        if hasattr(self._signals, "document_action_triggered"):
            self._signals.document_action_triggered.emit("comment", document)

    def update_columns_config(self, columns_config: dict):
        """Обновить конфигурацию колонок"""
        self._columns = columns_config

    def render_row(self, row: int, document: dict):
        """
        Преобразовать документ в UI элементы строки.
        """
        bg_color = self._config.get_even_row_color() if row % 2 == 0 else self._config.get_odd_row_color()
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

        # Специальные виджеты - ЗДЕСЬ МЫ ВНЕДРЯЕМ НОВЫЙ ПОДХОД
        self._render_special_widgets_hybrid(row, document, col_map, bg_color)

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
        item.setForeground(QBrush(self._config.get_text_color()))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setData(Qt.ItemDataRole.UserRole, document)

        if is_pinned:
            from client.core.utils.icon_manager import icon_manager
            pin_icon = icon_manager.get_icon('pin', QSize(22, 22))
            item.setIcon(pin_icon)

        self._table.setItem(row, col, item)

    def _render_read_checkbox(self, row: int, document: dict, bg_color, col_map: dict):
        """Рендеринг чекбокса прочтения"""
        col = col_map.get("Прочитано")
        if col is None:
            return

        from client.windows.documents.table.widgets.read_checkbox import ReadCheckBox
        read_widget = ReadCheckBox(document.get("id", 0), document.get("is_read", False))
        self._table.setCellWidget(row, col, read_widget)

        # Устанавливаем фон
        widget = self._table.cellWidget(row, col)
        if widget:
            widget.setStyleSheet(f"QWidget {{ background-color: {bg_color.name()}; }}")

    def _render_text_columns(self, row: int, document: dict, bg_color, col_map: dict):
        """Рендеринг текстовых колонок"""
        text_fields = {
            "Тема": "title",
            "Тип": "type_name",
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

            if key == "status":
                from client.core.data.document_data import DocumentDataConfig
                value = DocumentDataConfig.get_status_text(value) if value else ""
            elif key == "direction":
                from client.core.data.document_data import DocumentDataConfig
                value = DocumentDataConfig.get_direction_text(value) if value else ""
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
                if values and isinstance(values[0], dict):
                    text = ", ".join(v.get("name", str(v)) for v in values) if values else "-"
                else:
                    text = ", ".join(str(v) for v in values) if values else "-"
            else:
                text = str(values) if values else "-"

            item = self._create_text_item(text, bg_color)
            item.setToolTip(text)
            self._table.setItem(row, col, item)

    # ============== НОВЫЙ МЕТОД - ГИБРИДНЫЙ РЕНДЕРИНГ ==============

    def _render_special_widgets_hybrid(self, row: int, document: dict, col_map: dict, bg_color):
        """
        ГИБРИДНЫЙ подход: используем TableCellItem для комментариев и делегатов,
        а для остальных - стандартные виджеты
        """

        # 1. Хэштеги - оставляем как есть (обычный виджет)
        col = col_map.get("Хэштеги")
        if col is not None:
            widget = self._tags_builder.build(row, document.get("tags", []))
            self._table.setCellWidget(row, col, widget)

        # 2. Комментарии - НОВЫЙ подход с TableCellItem
        col = col_map.get("Комментарии")
        if col is not None:
            if self._use_custom_cells:
                # Используем кастомную ячейку
                cell_item = self._create_comments_cell_item(row, document, bg_color)
                self._table.setItem(row, col, cell_item)

                # Создаем и устанавливаем виджет
                widget = cell_item.get_widget()
                if widget:
                    self._table.setCellWidget(row, col, widget)
            else:
                # Старый подход
                widget = self._comments_builder.build(row, document)
                self._table.setCellWidget(row, col, widget)

        # 3. Делегаты - НОВЫЙ подход с TableCellItem
        col = col_map.get("Делегаты")
        if col is not None:
            if self._use_custom_cells:
                # Используем кастомную ячейку
                cell_item = self._create_delegates_cell_item(row, document, bg_color)
                self._table.setItem(row, col, cell_item)

                # Создаем и устанавливаем виджет
                widget = cell_item.get_widget()
                if widget:
                    self._table.setCellWidget(row, col, widget)
            else:
                # Старый подход
                widget = self._delegates_builder.build(row, document)
                self._table.setCellWidget(row, col, widget)

        # 4. Вложение - оставляем как есть
        col = col_map.get("Вложение")
        if col is not None:
            widget = self._attachment_builder.build(row, document)
            self._table.setCellWidget(row, col, widget)

        # 5. Ответ - оставляем как есть
        col = col_map.get("Ответ")
        if col is not None:
            widget = self._reply_builder.build(row, document)
            self._table.setCellWidget(row, col, widget)

    def _create_comments_cell_item(self, row: int, document: dict, bg_color) -> TableCellItem:
        """Создать TableCellItem для комментариев"""
        cell_data = CellData(
            value="",
            display_text="",
            tooltip="Кликните для просмотра комментариев",
            background_color=bg_color,
            foreground_color=QColor("#1B232A"),
            widget_builder=lambda r, d: self._comments_builder.build(r, d),
            editable=False,
            user_data=document
        )

        item = TableCellItem(cell_data)
        item.set_row_data(row, document)
        return item

    def _create_delegates_cell_item(self, row: int, document: dict, bg_color) -> TableCellItem:
        """Создать TableCellItem для делегатов"""
        cell_data = CellData(
            value="",
            display_text="",
            tooltip="Кликните для управления делегатами",
            background_color=bg_color,
            foreground_color=QColor("#1B232A"),
            widget_builder=lambda r, d: self._delegates_builder.build(r, d),
            editable=False,
            user_data=document
        )

        item = TableCellItem(cell_data)
        item.set_row_data(row, document)
        return item

    def _create_text_item(self, text: str, bg_color) -> QTableWidgetItem:
        """Создать стандартный текстовый элемент"""
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        item.setBackground(QBrush(bg_color))
        item.setForeground(QBrush(self._config.get_text_color()))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def _on_attachment_clicked(self, document, attachment):
        # У сервера нет рабочего одиночного preview_url (см. предупреждение в
        # attachment_service.py) — постраничного просмотра пока не существует.
        # Показываем то немногое, что реально можно узнать: число страниц.
        name = attachment.get("name") or attachment.get("file_name") or "Файл"
        attachment_id = attachment.get("id")

        pages = None
        if self._attachment_service and attachment_id:
            pages = self._attachment_service.get_page_count(attachment_id)

        from PyQt6.QtWidgets import QMessageBox
        if pages is not None:
            QMessageBox.information(
                None, "Вложение",
                f"{name}\nСтраниц: {pages}\n\nПостраничный просмотр пока не реализован."
            )
        else:
            QMessageBox.information(None, "Вложение", f"{name}\n\nПросмотр пока не реализован.")

        self._signals.attachment_opened.emit(
            document.get("id"),
            attachment.get('path') or attachment.get('storage_path') or attachment.get('preview_url') or ""
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