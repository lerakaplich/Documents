"""
Модуль управления колонками таблицы
"""
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtCore import Qt, QTimer
from typing import Dict, List, Optional

from client.core.settings.settings_manager import SettingsManager


class ColumnManager:
    """Класс для управления колонками таблицы с поддержкой разных типов документов"""

    def __init__(self, table_widget, columns_config, doc_type: str = None):
        self.table_widget = table_widget
        self.columns_config = columns_config
        self.doc_type = doc_type or "default"
        self.settings = SettingsManager()

        self._is_restoring = False
        self._is_saving = False
        self._save_timer = None

        self.settings.set_current_document_type(self.doc_type)
        self._enable_column_management()
        self.restore_all()

    def _enable_column_management(self):
        header = self.table_widget.horizontalHeader()
        header.setSectionsMovable(True)
        header.setDragEnabled(True)
        header.setDragDropMode(QHeaderView.DragDropMode.InternalMove)
        header.setDropIndicatorShown(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        header.sectionMoved.connect(self._on_section_moved)
        header.sectionResized.connect(self._on_section_resized)

    def _on_section_moved(self, logicalIndex: int, oldVisualIndex: int, newVisualIndex: int):
        if self._is_restoring:
            return
        self._schedule_save()

    def _on_section_resized(self, logicalIndex: int, oldSize: int, newSize: int):
        if self._is_restoring:
            return
        self._schedule_save()

    def _schedule_save(self):
        if self._is_saving:
            return

        if self._save_timer is not None:
            self._save_timer.stop()

        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save)
        self._save_timer.start(500)

    def _do_save(self):
        if self._is_saving or self._is_restoring:
            return

        self._is_saving = True
        try:
            self._save_column_order()
            self._save_column_sizes()
            self._save_column_visibility()
        finally:
            self._is_saving = False

    # ============ ВНУТРЕННИЕ МЕТОДЫ СОХРАНЕНИЯ ============

    def _save_column_order(self):
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
            print(f"[ColumnManager] Saved column order for '{self.doc_type}': {len(column_order)} columns")
        except Exception as e:
            print(f"[ColumnManager] Error saving column order: {e}")

    def _save_column_sizes(self):
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
                print(f"[ColumnManager] Saved column sizes for '{self.doc_type}': {len(column_sizes)} columns")
        except Exception as e:
            print(f"[ColumnManager] Error saving column sizes: {e}")

    def _save_column_visibility(self):
        try:
            header = self.table_widget.horizontalHeader()
            hidden_columns = []
            for visual_idx in range(header.count()):
                logical_idx = header.logicalIndex(visual_idx)
                if header.isSectionHidden(logical_idx):
                    hidden_columns.append(logical_idx)
            self.settings.set_hidden_columns(hidden_columns, self.doc_type)
            print(f"[ColumnManager] Saved hidden columns for '{self.doc_type}': {len(hidden_columns)}")
        except Exception as e:
            print(f"[ColumnManager] Error saving column visibility: {e}")

    # ============ ПУБЛИЧНЫЕ МЕТОДЫ СОХРАНЕНИЯ ============

    def save_column_order(self):
        if self._is_saving or self._is_restoring:
            return
        self._save_column_order()

    def save_column_sizes(self):
        if self._is_saving or self._is_restoring:
            return
        self._save_column_sizes()

    def save_column_visibility(self):
        if self._is_saving or self._is_restoring:
            return
        self._save_column_visibility()

    # ============ ВОССТАНОВЛЕНИЕ ============

    def _restore_column_visibility(self):
        """Внутреннее восстановление видимости (без проверки флагов)"""
        try:
            hidden_columns = self.settings.get_hidden_columns(self.doc_type)
            header = self.table_widget.horizontalHeader()

            for logical_idx in range(header.count()):
                header.setSectionHidden(logical_idx, False)

            if isinstance(hidden_columns, list):
                for logical_idx in hidden_columns:
                    if isinstance(logical_idx, int) and logical_idx < header.count():
                        header.setSectionHidden(logical_idx, True)
            print(f"[ColumnManager] Restored hidden columns for '{self.doc_type}': {len(hidden_columns) if hidden_columns else 0}")
        except Exception as e:
            print(f"[ColumnManager] Error restoring column visibility: {e}")

    def _restore_column_order(self):
        """Внутреннее восстановление порядка (без проверки флагов)"""
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
                    print(f"[ColumnManager] Restored column order for '{self.doc_type}': {len(target_order)} columns")
        except Exception as e:
            print(f"[ColumnManager] Error restoring column order: {e}")

    def _restore_column_sizes(self):
        """Внутреннее восстановление размеров (без проверки флагов)"""
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
            print(f"[ColumnManager] Applied column sizes for '{self.doc_type}': {len(column_sizes)} columns")
        except Exception as e:
            print(f"[ColumnManager] Error applying column sizes: {e}")

    # ============ ПУБЛИЧНЫЕ МЕТОДЫ ВОССТАНОВЛЕНИЯ ============

    def restore_column_visibility(self):
        if self._is_restoring:
            return
        self._restore_column_visibility()

    def restore_column_order(self):
        if self._is_restoring:
            return
        self._restore_column_order()

    def restore_column_sizes(self):
        if self._is_restoring:
            return
        self._restore_column_sizes()

    # ============ ВСЕСТОРОННЕЕ ============

    def restore_all(self):
        if self._is_restoring:
            return

        print(f"[ColumnManager] Restoring all settings for '{self.doc_type}'...")
        self._is_restoring = True

        try:
            # Используем внутренние методы (без проверки флагов)
            self._restore_column_visibility()
            self._restore_column_order()
            QTimer.singleShot(100, self._restore_column_sizes)
            QTimer.singleShot(1000, lambda: setattr(self, '_is_restoring', False))
        except Exception as e:
            print(f"[ColumnManager] Error during restore: {e}")
            self._is_restoring = False

    def save_all(self):
        if self._is_saving or self._is_restoring:
            return

        print(f"[ColumnManager] Saving all settings for '{self.doc_type}'...")
        self._is_saving = True
        try:
            self._save_column_visibility()
            self._save_column_order()
            self._save_column_sizes()
        except Exception as e:
            print(f"[ColumnManager] Error saving all: {e}")
        finally:
            self._is_saving = False

    # ============ ОБНОВЛЕНИЕ ТИПА ============

    def set_doc_type(self, doc_type: str):
        doc_type = doc_type or "default"

        if self.doc_type == doc_type:
            return

        self.save_all()
        self.doc_type = doc_type
        self.settings.set_current_document_type(doc_type)
        self.restore_all()

        print(f"[ColumnManager] Switched to doc_type: {doc_type}")

    # ============ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ============

    def reset_column_sizes(self):
        default_widths = {
            "ID": 50, "Прочитано": 80, "Номер документа": 130,
            "Тема": 250, "Тип": 100, "Дата создания": 120,
            "Статус": 120, "Направление": 120, "Отправители": 150,
            "Получатели": 150, "Исполнители": 150, "Делегаты": 150,
            "Хэштеги": 180, "Комментарии": 200, "Вложение": 100,
            "Ответ": 100, "Краткое содержание": 200, "Срок исполнения": 120
        }

        try:
            self._is_restoring = True
            header = self.table_widget.horizontalHeader()
            for logical_idx, col_name in enumerate(self.columns_config.values()):
                if col_name in default_widths:
                    header.resizeSection(logical_idx, default_widths[col_name])
        finally:
            self._is_restoring = False

    def reset_column_order(self):
        try:
            self._is_restoring = True
            header = self.table_widget.horizontalHeader()
            original_order = list(range(header.count()))

            for new_visual_idx, logical_idx in enumerate(original_order):
                current_visual = header.visualIndex(logical_idx)
                if current_visual != new_visual_idx:
                    header.moveSection(current_visual, new_visual_idx)
        finally:
            self._is_restoring = False

    def reset_column_visibility(self):
        try:
            self._is_restoring = True
            header = self.table_widget.horizontalHeader()
            for logical_idx in range(header.count()):
                header.setSectionHidden(logical_idx, False)
        finally:
            self._is_restoring = False