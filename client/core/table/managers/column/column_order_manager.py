from typing import Dict

from client.core.settings.settings_manager import SettingsManager


class ColumnOrderManager:
    """Управление порядком колонок"""

    def __init__(self, table_widget, settings: SettingsManager, doc_type: str, columns_config: Dict):
        self.table_widget = table_widget
        self.settings = settings
        self.doc_type = doc_type
        self.columns_config = columns_config

    def save(self):
        """Сохраняет порядок колонок"""
        try:
            header = self.table_widget.horizontalHeader()
            column_order = []
            for visual_idx in range(header.count()):
                logical_idx = header.logicalIndex(visual_idx)
                column_name = self.columns_config.get(logical_idx, f"Column_{logical_idx}")
                column_order.append({
                    'logical_index': logical_idx,
                    'name': column_name
                })
            self.settings.set_column_order(column_order, self.doc_type)
        except Exception as e:
            print(f"[ColumnOrderManager] Error saving: {e}")

    def restore(self):
        """Восстанавливает порядок колонок"""
        try:
            column_order = self.settings.get_column_order(self.doc_type)
            if not column_order:
                return

            header = self.table_widget.horizontalHeader()
            if isinstance(column_order, list) and len(column_order) > 0:
                if isinstance(column_order[0], dict):
                    target_order = []
                    for col_info in column_order:
                        logical_idx = col_info.get('logical_index')
                        if logical_idx is not None and logical_idx < header.count():
                            target_order.append(logical_idx)

                    for new_visual_idx, logical_idx in enumerate(target_order):
                        current_visual = header.visualIndex(logical_idx)
                        if current_visual != new_visual_idx:
                            header.moveSection(current_visual, new_visual_idx)
        except Exception as e:
            print(f"[ColumnOrderManager] Error restoring: {e}")

    def reset(self):
        """Сбрасывает порядок колонок"""
        try:
            header = self.table_widget.horizontalHeader()
            original_order = list(range(header.count()))

            for new_visual_idx, logical_idx in enumerate(original_order):
                current_visual = header.visualIndex(logical_idx)
                if current_visual != new_visual_idx:
                    header.moveSection(current_visual, new_visual_idx)
        except Exception as e:
            print(f"[ColumnOrderManager] Error resetting: {e}")