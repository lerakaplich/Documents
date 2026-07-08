"""
Модуль управления колонками таблицы
"""
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtCore import Qt, QTimer
from typing import Dict, List, Optional

from client.core.settings.settings_manager import SettingsManager


class ColumnVisibilityManager:
    """Управление видимостью колонок"""

    def __init__(self, table_widget, settings: SettingsManager, doc_type: str):
        self.table_widget = table_widget
        self.settings = settings
        self.doc_type = doc_type

    def save(self):
        """Сохраняет видимость колонок"""
        try:
            header = self.table_widget.horizontalHeader()
            hidden_columns = []
            for visual_idx in range(header.count()):
                logical_idx = header.logicalIndex(visual_idx)
                if header.isSectionHidden(logical_idx):
                    hidden_columns.append(logical_idx)
            self.settings.set_hidden_columns(hidden_columns, self.doc_type)
        except Exception as e:
            print(f"[ColumnVisibilityManager] Error saving: {e}")

    def restore(self):
        """Восстанавливает видимость колонок"""
        try:
            hidden_columns = self.settings.get_hidden_columns(self.doc_type)
            header = self.table_widget.horizontalHeader()

            for logical_idx in range(header.count()):
                header.setSectionHidden(logical_idx, False)

            if isinstance(hidden_columns, list):
                for logical_idx in hidden_columns:
                    if isinstance(logical_idx, int) and logical_idx < header.count():
                        header.setSectionHidden(logical_idx, True)
        except Exception as e:
            print(f"[ColumnVisibilityManager] Error restoring: {e}")

    def reset(self):
        """Сбрасывает видимость колонок"""
        try:
            header = self.table_widget.horizontalHeader()
            for logical_idx in range(header.count()):
                header.setSectionHidden(logical_idx, False)
        except Exception as e:
            print(f"[ColumnVisibilityManager] Error resetting: {e}")








