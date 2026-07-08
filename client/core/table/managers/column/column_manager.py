from typing import Dict

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QHeaderView

from client.core.settings.settings_manager import SettingsManager
from client.core.table.managers.column.column_order_manager import ColumnOrderManager
from client.core.table.managers.column.column_size_manager import ColumnSizeManager
from client.core.table.managers.column.column_visibility_manager import ColumnVisibilityManager


class ColumnManager:
    """Координатор управления состоянием колонок"""

    def __init__(self, table_widget, columns_config: Dict, doc_type: str = None):
        self.table_widget = table_widget
        self.columns_config = columns_config
        self.doc_type = doc_type or "default"
        self.settings = SettingsManager()

        self._is_restoring = False
        self._is_saving = False
        self._save_timer = None

        # Инициализация специализированных менеджеров
        self.visibility_manager = ColumnVisibilityManager(
            table_widget, self.settings, self.doc_type
        )
        self.order_manager = ColumnOrderManager(
            table_widget, self.settings, self.doc_type, columns_config
        )
        self.size_manager = ColumnSizeManager(
            table_widget, self.settings, self.doc_type, columns_config
        )

        self.settings.set_current_document_type(self.doc_type)
        self._enable_column_management()
        self.restore_all()

    def _enable_column_management(self):
        """Включает управление колонками"""
        header = self.table_widget.horizontalHeader()
        header.setSectionsMovable(True)
        header.setDragEnabled(True)
        header.setDragDropMode(QHeaderView.DragDropMode.InternalMove)
        header.setDropIndicatorShown(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        header.sectionMoved.connect(self._on_section_moved)
        header.sectionResized.connect(self._on_section_resized)

    def _on_section_moved(self, logicalIndex: int, oldVisualIndex: int, newVisualIndex: int):
        """Обработчик перемещения секции"""
        if self._is_restoring:
            return
        self._schedule_save()

    def _on_section_resized(self, logicalIndex: int, oldSize: int, newSize: int):
        """Обработчик изменения размера секции"""
        if self._is_restoring:
            return
        self._schedule_save()

    def _schedule_save(self):
        """Планирует сохранение с задержкой"""
        if self._is_saving:
            return

        if self._save_timer is not None:
            self._save_timer.stop()

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.save_all)
        self._save_timer.start(500)

    def restore_all(self):
        """Восстанавливает все настройки колонок"""
        if self._is_restoring:
            return

        self._is_restoring = True
        try:
            self.visibility_manager.restore()
            self.order_manager.restore()
            QTimer.singleShot(100, self.size_manager.restore)
            QTimer.singleShot(1000, lambda: setattr(self, '_is_restoring', False))
        except Exception as e:
            print(f"[ColumnManager] Error during restore: {e}")
            self._is_restoring = False

    def save_all(self):
        """Сохраняет все настройки колонок"""
        if self._is_saving or self._is_restoring:
            return

        self._is_saving = True
        try:
            self.visibility_manager.save()
            self.order_manager.save()
            self.size_manager.save()
        except Exception as e:
            print(f"[ColumnManager] Error saving all: {e}")
        finally:
            self._is_saving = False

    def set_doc_type(self, doc_type: str):
        """Обновляет тип документа"""
        doc_type = doc_type or "default"
        if self.doc_type == doc_type:
            return

        self.save_all()
        self.doc_type = doc_type
        self.settings.set_current_document_type(doc_type)

        # Обновляем тип в специализированных менеджерах
        self.visibility_manager.doc_type = doc_type
        self.order_manager.doc_type = doc_type
        self.size_manager.doc_type = doc_type

        self.restore_all()

    def reset_all(self):
        """Сбрасывает все настройки колонок"""
        self.visibility_manager.reset()
        self.order_manager.reset()
        self.size_manager.reset()

    def save_column_order(self):
        """Сохраняет порядок колонок"""
        self.order_manager.save()

    def save_column_sizes(self):
        """Сохраняет размеры колонок"""
        self.size_manager.save()

    def save_column_visibility(self):
        """Сохраняет видимость колонок"""
        self.visibility_manager.save()

    def restore_column_order(self):
        """Восстанавливает порядок колонок"""
        if not self._is_restoring:
            self.order_manager.restore()

    def restore_column_sizes(self):
        """Восстанавливает размеры колонок"""
        if not self._is_restoring:
            self.size_manager.restore()

    def restore_column_visibility(self):
        """Восстанавливает видимость колонок"""
        if not self._is_restoring:
            self.visibility_manager.restore()

    def reset_column_order(self):
        """Сбрасывает порядок колонок"""
        self.order_manager.reset()

    def reset_column_sizes(self):
        """Сбрасывает размеры колонок"""
        self.size_manager.reset()

    def reset_column_visibility(self):
        """Сбрасывает видимость колонок"""
        self.visibility_manager.reset()