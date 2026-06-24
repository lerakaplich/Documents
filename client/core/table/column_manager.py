"""
Модуль управления колонками таблицы
"""
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtCore import Qt, QSettings


class ColumnManager:
    """Класс для управления колонками таблицы: перемещение, размеры, сохранение состояния"""

    def __init__(self, table_widget, columns_config):
        self.table_widget = table_widget
        self.columns_config = columns_config
        self.settings = QSettings("YourCompany", "DocumentsApp")

        # Включаем перемещение колонок
        self._enable_column_moving()

        # Восстанавливаем сохраненные размеры колонок
        self._restore_column_sizes()

    def _enable_column_moving(self):
        """Включение возможности перемещения колонок"""
        header = self.table_widget.horizontalHeader()

        # Разрешаем перемещение колонок
        header.setSectionsMovable(True)

        # Разрешаем изменение размера колонок
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        # Включаем отображение индикатора перемещения
        header.setDragEnabled(True)
        header.setDragDropMode(QHeaderView.DragDropMode.InternalMove)
        header.setDropIndicatorShown(True)

        # Подключаем сигнал изменения порядка колонок
        header.sectionMoved.connect(self._on_section_moved)

        # Подключаем сигнал изменения размера колонок
        header.sectionResized.connect(self._on_section_resized)

    def _on_section_moved(self, logicalIndex, oldVisualIndex, newVisualIndex):
        """
        Обработка перемещения колонки

        Args:
            logicalIndex: логический индекс колонки
            oldVisualIndex: старый визуальный индекс
            newVisualIndex: новый визуальный индекс
        """
        # Сохраняем порядок колонок
        self._save_column_order()

    def _on_section_resized(self, logicalIndex, oldSize, newSize):
        """
        Обработка изменения размера колонки

        Args:
            logicalIndex: логический индекс колонки
            oldSize: старый размер
            newSize: новый размер
        """
        # Сохраняем размеры колонок
        self._save_column_sizes()

    def _save_column_order(self):
        """Сохранение порядка колонок"""
        header = self.table_widget.horizontalHeader()
        column_order = []

        for i in range(header.count()):
            logical_index = header.logicalIndex(i)
            column_order.append(logical_index)

        self.settings.setValue("column_order", column_order)

    def _save_column_sizes(self):
        """Сохранение размеров колонок"""
        header = self.table_widget.horizontalHeader()
        column_sizes = {}

        for i in range(header.count()):
            logical_index = header.logicalIndex(i)
            size = header.sectionSize(logical_index)
            column_sizes[str(logical_index)] = size

        self.settings.setValue("column_sizes", column_sizes)

    def _restore_column_sizes(self):
        """Восстановление размеров колонок из сохраненных настроек"""
        column_sizes = self.settings.value("column_sizes", {})
        if column_sizes:
            header = self.table_widget.horizontalHeader()
            for i in range(header.count()):
                logical_index = header.logicalIndex(i)
                size = column_sizes.get(str(logical_index))
                if size:
                    header.resizeSection(logical_index, size)

    def restore_column_order(self):
        """Восстановление порядка колонок"""
        column_order = self.settings.value("column_order", [])
        if column_order:
            header = self.table_widget.horizontalHeader()
            # Восстанавливаем порядок колонок
            for i, logical_index in enumerate(column_order):
                current_visual = header.visualIndex(logical_index)
                if current_visual != i:
                    header.moveSection(current_visual, i)

    def get_column_visual_order(self):
        """
        Получение текущего визуального порядка колонок

        Returns:
            list: список названий колонок в порядке их отображения
        """
        header = self.table_widget.horizontalHeader()
        columns = list(self.columns_config.values())
        visual_order = []

        for i in range(header.count()):
            logical_index = header.logicalIndex(i)
            if logical_index < len(columns):
                visual_order.append(columns[logical_index])

        return visual_order

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
            "Ответ": 100
        }

        header = self.table_widget.horizontalHeader()
        for i, col_name in enumerate(self.columns_config.values()):
            if col_name in default_widths:
                header.resizeSection(i, default_widths[col_name])

        # Очищаем сохраненные размеры
        self.settings.remove("column_sizes")