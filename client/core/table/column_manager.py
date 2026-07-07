"""
Модуль управления колонками таблицы
"""
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtCore import Qt
from typing import Dict, List, Optional

from client.core.settings.settings_manager import SettingsManager
from client.core.settings.settings_keys import SettingsKeys


class ColumnManager:
    """Класс для управления колонками таблицы с поддержкой разных типов документов"""

    def __init__(self, table_widget, columns_config, doc_type: str = None):
        """
        Инициализация менеджера колонок

        Args:
            table_widget: виджет таблицы
            columns_config: словарь {логический_индекс: название_колонки}
            doc_type: тип документа (для сохранения настроек отдельно)
        """
        self.table_widget = table_widget
        self.columns_config = columns_config
        self.doc_type = doc_type or "default"
        self.settings = SettingsManager()

        # Устанавливаем текущий тип документа в настройках
        self.settings.set_current_document_type(self.doc_type)

        # Включаем управление колонками
        self._enable_column_management()

        # Восстанавливаем сохраненное состояние
        self.restore_all()

    def _enable_column_management(self):
        """Включение всех возможностей управления колонками"""
        header = self.table_widget.horizontalHeader()

        # Разрешаем перемещение колонок
        header.setSectionsMovable(True)
        header.setDragEnabled(True)
        header.setDragDropMode(QHeaderView.DragDropMode.InternalMove)
        header.setDropIndicatorShown(True)

        # Разрешаем изменение размера колонок
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # Подключаем сигналы
        header.sectionMoved.connect(self._on_section_moved)
        header.sectionResized.connect(self._on_section_resized)

    def _on_section_moved(self, logicalIndex: int, oldVisualIndex: int, newVisualIndex: int):
        """Обработка перемещения колонки"""
        self.save_column_order()
        self.save_column_visibility()

    def _on_section_resized(self, logicalIndex: int, oldSize: int, newSize: int):
        """Обработка изменения размера колонки"""
        self.save_column_sizes()
        self.save_column_visibility()

    # ============ СОХРАНЕНИЕ ПОРЯДКА КОЛОНОК ============

    def save_column_order(self):
        """Сохранение порядка колонок"""
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
            print(f"[ColumnManager] Saved column order for type '{self.doc_type}': {len(column_order)} columns")
        except Exception as e:
            print(f"[ColumnManager] Error saving column order: {e}")


    def restore_column_order(self):
        """Восстановление порядка колонок для текущего типа документа"""
        try:
            column_order = self.settings.get_column_order(self.doc_type)

            if not column_order:
                print(f"[ColumnManager] No saved column order for '{self.doc_type}', using default")
                return

            header = self.table_widget.horizontalHeader()

            # Проверяем формат данных
            if isinstance(column_order, list) and len(column_order) > 0:
                if isinstance(column_order[0], str):
                    # Старый формат: список имен колонок
                    name_to_index = {name: idx for idx, name in self.columns_config.items()}
                    for new_visual_idx, col_name in enumerate(column_order):
                        if col_name in name_to_index:
                            logical_idx = name_to_index[col_name]
                            if logical_idx < header.count():
                                current_visual = header.visualIndex(logical_idx)
                                if current_visual != new_visual_idx:
                                    header.moveSection(current_visual, new_visual_idx)
                    print(f"[ColumnManager] Restored column order from old format")
                elif isinstance(column_order[0], dict):
                    # Новый формат: список словарей
                    for new_visual_idx, col_info in enumerate(column_order):
                        logical_idx = col_info.get('logical_index')
                        if logical_idx is not None and logical_idx < header.count():
                            current_visual = header.visualIndex(logical_idx)
                            if current_visual != new_visual_idx:
                                header.moveSection(current_visual, new_visual_idx)
                    print(f"[ColumnManager] Restored column order for '{self.doc_type}': {len(column_order)} columns")
        except Exception as e:
            print(f"[ColumnManager] Error restoring column order: {e}")

    # ============ СОХРАНЕНИЕ РАЗМЕРОВ КОЛОНОК ============

    def save_column_sizes(self):
        """Сохранение размеров колонок для текущего типа документа"""
        try:
            header = self.table_widget.horizontalHeader()
            column_sizes = {}

            for visual_idx in range(header.count()):
                logical_idx = header.logicalIndex(visual_idx)
                size = header.sectionSize(logical_idx)
                if size > 0:
                    column_sizes[str(logical_idx)] = size

            self.settings.set_column_widths(column_sizes, self.doc_type)
            print(f"[ColumnManager] Saved column sizes for '{self.doc_type}': {len(column_sizes)} columns")
        except Exception as e:
            print(f"[ColumnManager] Error saving column sizes: {e}")

    def restore_column_sizes(self):
        """Восстановление размеров колонок для текущего типа документа"""
        try:
            column_sizes = self.settings.get_column_widths(self.doc_type)

            if not column_sizes:
                print(f"[ColumnManager] No saved column sizes for '{self.doc_type}', using default")
                self.reset_column_sizes()
                return

            # Используем QTimer для отложенного применения
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self._apply_column_sizes(column_sizes))

            print(f"[ColumnManager] Scheduled column sizes restoration for '{self.doc_type}'")
        except Exception as e:
            print(f"[ColumnManager] Error restoring column sizes: {e}")
            self.reset_column_sizes()

    def _apply_column_sizes(self, column_sizes: dict):
        """Применить размеры колонок (вызывается после инициализации)"""
        try:
            header = self.table_widget.horizontalHeader()
            restored_count = 0

            for logical_idx_str, size in column_sizes.items():
                try:
                    logical_idx = int(logical_idx_str)
                    if logical_idx < header.count() and size > 0:
                        header.resizeSection(logical_idx, size)
                        restored_count += 1
                except (ValueError, TypeError):
                    continue

            print(f"[ColumnManager] Applied column sizes for '{self.doc_type}': {restored_count} columns")
        except Exception as e:
            print(f"[ColumnManager] Error applying column sizes: {e}")

    # ============ СОХРАНЕНИЕ ВИДИМОСТИ КОЛОНОК ============

    def save_column_visibility(self):
        """Сохранение видимости колонок для текущего типа документа"""
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

    def restore_column_visibility(self):
        """Восстановление видимости колонок для текущего типа документа"""
        try:
            hidden_columns = self.settings.get_hidden_columns(self.doc_type)

            if hidden_columns is None:
                print(f"[ColumnManager] No saved column visibility for '{self.doc_type}', showing all")
                header = self.table_widget.horizontalHeader()
                for logical_idx in range(header.count()):
                    header.setSectionHidden(logical_idx, False)
                self.save_column_visibility()
                return

            if not hidden_columns:
                return

            header = self.table_widget.horizontalHeader()

            if isinstance(hidden_columns, list) and len(hidden_columns) > 0:
                if isinstance(hidden_columns[0], dict):
                    for col_info in hidden_columns:
                        if isinstance(col_info, dict):
                            logical_idx = col_info.get('logical_index')
                            is_visible = col_info.get('visible', True)
                            if logical_idx is not None and logical_idx < header.count():
                                header.setSectionHidden(logical_idx, not is_visible)
                    print(f"[ColumnManager] Restored visibility from old format")
                elif isinstance(hidden_columns[0], int):
                    for logical_idx in range(header.count()):
                        header.setSectionHidden(logical_idx, False)
                    for logical_idx in hidden_columns:
                        if isinstance(logical_idx, int) and logical_idx < header.count():
                            header.setSectionHidden(logical_idx, True)
                    print(f"[ColumnManager] Restored hidden columns for '{self.doc_type}': {len(hidden_columns)}")
        except Exception as e:
            print(f"[ColumnManager] Error restoring column visibility: {e}")

    # ============ ВСЕСТОРОННЕЕ ВОССТАНОВЛЕНИЕ ============

    def restore_all(self):
        """Восстановление всех настроек колонок для текущего типа документа"""
        print(f"[ColumnManager] Restoring all column settings for '{self.doc_type}'...")
        self.restore_column_visibility()
        self.restore_column_order()
        self.restore_column_sizes()
        print(f"[ColumnManager] Restore completed for '{self.doc_type}'")

    def save_all(self):
        """Сохранение всех настроек колонок для текущего типа документа"""
        print(f"[ColumnManager] Saving all column settings for '{self.doc_type}'...")
        self.save_column_visibility()
        self.save_column_order()
        self.save_column_sizes()
        print(f"[ColumnManager] Save completed for '{self.doc_type}'")

    # ============ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ============

    def get_column_visual_order(self) -> List[str]:
        """Получение текущего визуального порядка колонок"""
        header = self.table_widget.horizontalHeader()
        visual_order = []

        for visual_idx in range(header.count()):
            logical_idx = header.logicalIndex(visual_idx)
            column_name = self.columns_config.get(logical_idx, str(logical_idx))
            visual_order.append(column_name)

        return visual_order

    def reset_all(self):
        """Сброс всех настроек колонок для текущего типа документа"""
        self.reset_column_sizes()
        self.reset_column_order()
        self.reset_column_visibility()

        # Очищаем сохраненные настройки для текущего типа
        self.settings.clear_document_type_settings(self.doc_type)
        print(f"[ColumnManager] Reset all settings for '{self.doc_type}'")

    def reset_column_sizes(self):
        """Сброс размеров колонок к значениям по умолчанию"""
        default_widths = {
            "ID": 50,
            "Прочитано": 80,
            "Номер документа": 130,
            "Тема": 250,
            "Тип": 100,
            "Дата": 90,
            "Статус": 120,
            "Отправители": 150,
            "Получатели": 150,
            "Исполнители": 150,
            "Делегаты": 150,
            "Хэштеги": 180,
            "Комментарии": 200,
            "Вложение": 100,
            "Ответ": 100,
            "Краткое содержание": 200,
            "Срок исполнения": 120,
            "Направление": 120,
            "Входящий номер": 120,
            "Входящая дата": 120,
        }

        header = self.table_widget.horizontalHeader()
        for logical_idx, col_name in enumerate(self.columns_config.values()):
            if col_name in default_widths:
                header.resizeSection(logical_idx, default_widths[col_name])
        print(f"[ColumnManager] Reset column sizes to default for '{self.doc_type}'")

    def reset_column_order(self):
        """Сброс порядка колонок к исходному"""
        header = self.table_widget.horizontalHeader()
        original_order = list(range(header.count()))

        for new_visual_idx, logical_idx in enumerate(original_order):
            current_visual = header.visualIndex(logical_idx)
            if current_visual != new_visual_idx:
                header.moveSection(current_visual, new_visual_idx)
        print(f"[ColumnManager] Reset column order to default for '{self.doc_type}'")

    def reset_column_visibility(self):
        """Показать все колонки"""
        header = self.table_widget.horizontalHeader()
        for logical_idx in range(header.count()):
            header.setSectionHidden(logical_idx, False)
        print(f"[ColumnManager] Reset column visibility for '{self.doc_type}'")

    def toggle_column_visibility(self, logical_index: int):
        """Переключить видимость колонки"""
        header = self.table_widget.horizontalHeader()
        is_hidden = header.isSectionHidden(logical_index)
        header.setSectionHidden(logical_index, not is_hidden)
        self.save_column_visibility()

    def set_column_visible(self, logical_index: int, visible: bool):
        """Установить видимость колонки"""
        header = self.table_widget.horizontalHeader()
        header.setSectionHidden(logical_index, not visible)
        self.save_column_visibility()

    def is_column_visible(self, logical_index: int) -> bool:
        """Проверить видимость колонки"""
        header = self.table_widget.horizontalHeader()
        return not header.isSectionHidden(logical_index)