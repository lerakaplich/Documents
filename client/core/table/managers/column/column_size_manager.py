from typing import Dict

from client.core.settings.settings_manager import SettingsManager


class ColumnSizeManager:
    """Управление размерами колонок"""

    DEFAULT_WIDTHS = {
        "ID": 50, "Прочитано": 80, "Номер документа": 130,
        "Тема": 250, "Тип": 100, "Дата создания": 120,
        "Статус": 120, "Направление": 120, "Отправители": 150,
        "Получатели": 150, "Исполнители": 150, "Делегаты": 150,
        "Хэштеги": 180, "Комментарии": 200, "Вложение": 100,
        "Ответ": 100, "Краткое содержание": 200, "Срок исполнения": 120
    }

    def __init__(self, table_widget, settings: SettingsManager, doc_type: str, columns_config: Dict):
        self.table_widget = table_widget
        self.settings = settings
        self.doc_type = doc_type
        self.columns_config = columns_config

    def save(self):
        """Сохраняет размеры колонок"""
        try:
            header = self.table_widget.horizontalHeader()
            column_sizes = {}
            for visual_idx in range(header.count()):
                logical_idx = header.logicalIndex(visual_idx)
                size = header.sectionSize(logical_idx)
                if size > 0:
                    column_sizes[str(logical_idx)] = size
            if column_sizes:
                self.settings.set_column_widths(column_sizes, self.doc_type)
        except Exception as e:
            print(f"[ColumnSizeManager] Error saving: {e}")

    def restore(self):
        """Восстанавливает размеры колонок"""
        try:
            column_sizes = self.settings.get_column_widths(self.doc_type)
            if not column_sizes:
                return

            header = self.table_widget.horizontalHeader()
            for logical_idx_str, size in column_sizes.items():
                try:
                    logical_idx = int(logical_idx_str)
                    if logical_idx < header.count() and size > 0:
                        header.resizeSection(logical_idx, size)
                except (ValueError, TypeError):
                    continue
        except Exception as e:
            print(f"[ColumnSizeManager] Error restoring: {e}")

    def reset(self):
        """Сбрасывает размеры колонок до значений по умолчанию"""
        try:
            header = self.table_widget.horizontalHeader()
            for logical_idx, col_name in enumerate(self.columns_config.values()):
                if col_name in self.DEFAULT_WIDTHS:
                    header.resizeSection(logical_idx, self.DEFAULT_WIDTHS[col_name])
        except Exception as e:
            print(f"[ColumnSizeManager] Error resetting: {e}")