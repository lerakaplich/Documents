"""
Менеджер сортировки таблицы
"""

from PyQt6.QtCore import QObject, Qt, pyqtSignal

from client.core.sorting.sorters import (
    DateSorter,
    DelegatesSorter,
    NumericSorter,
    ReadStatusSorter,
    StatusSorter,
    TagsSorter,
    TextSorter,
)


class SortingManager(QObject):
    """Менеджер сортировки таблицы"""

    # Сигнал об изменении сортировки
    sorting_changed = pyqtSignal(str, bool)  # column_name, reverse

    # Маппинг колонок на типы сортировки
    COLUMN_SORTERS = {
        "ID": NumericSorter,
        "Номер документа": TextSorter,
        "Тема": TextSorter,
        "Тип": TextSorter,
        "Дата": DateSorter,
        "Статус": StatusSorter,
        "Отправители": TextSorter,
        "Получатели": TextSorter,
        "Исполнители": TextSorter,
        "Делегаты": DelegatesSorter,
        "Хэштеги": TagsSorter,
        "Комментарии": TextSorter,
        "Вложение": TextSorter,
        "Ответ": TextSorter,
        "Прочитано": ReadStatusSorter,
        "Краткое содержание": TextSorter,
        "Срок исполнения": DateSorter,
        "Направление": TextSorter,
        "Входящий номер": TextSorter,
        "Входящая дата": DateSorter,
    }

    def __init__(self, table_widget, columns_config):
        super().__init__()
        self.table_widget = table_widget
        self.columns_config = columns_config
        self.current_column = None
        self.current_reverse = False

        # Создаем обратный маппинг: индекс колонки -> имя колонки
        self.column_index_to_name = dict(enumerate(columns_config.values()))

        # Подключаем сигнал клика по заголовку
        self.table_widget.horizontalHeader().sectionClicked.connect(self.on_header_clicked)

    def on_header_clicked(self, logical_index: int):
        """
        Обработка клика по заголовку колонки

        Args:
            logical_index: логический индекс колонки
        """
        column_name = self.column_index_to_name.get(logical_index)
        if not column_name:
            return

        # Определяем направление сортировки
        if self.current_column == column_name:
            # Если клик по той же колонке - меняем направление
            self.current_reverse = not self.current_reverse
        else:
            # Новая колонка - сортируем по возрастанию
            self.current_column = column_name
            self.current_reverse = False

        # Применяем сортировку
        self.apply_sorting()

        # Отправляем сигнал
        self.sorting_changed.emit(column_name, self.current_reverse)

    def apply_sorting(self) -> list[dict] | None:
        """
        Применение сортировки к данным таблицы

        Returns:
            Optional[List[dict]]: отсортированные данные или None
        """
        if not self.current_column:
            return None

        # Получаем все данные из таблицы
        documents = []
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, 0)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data:
                    documents.append(doc_data)

        if not documents:
            return None

        # Получаем сортировщик для колонки
        sorter_class = self.COLUMN_SORTERS.get(self.current_column, TextSorter)
        sorter = sorter_class(reverse=self.current_reverse)

        # Определяем ключ для сортировки
        key = self._get_sort_key(self.current_column)

        # Сортируем данные
        sorted_documents = sorter.sort(documents, key)

        # Обновляем таблицу
        self._update_table(sorted_documents)

        # Обновляем индикатор сортировки в заголовке
        self._update_sort_indicator()

        return sorted_documents

    def _get_sort_key(self, column_name: str) -> str:
        """
        Получение ключа для сортировки по имени колонки

        Args:
            column_name: имя колонки

        Returns:
            str: ключ для сортировки
        """
        # Маппинг колонок на ключи в данных
        key_mapping = {
            "ID": "id",
            "Номер документа": "reg_number",
            "Тема": "title",
            "Тип": "type",
            "Дата": "date",
            "Статус": "status",
            "Отправители": "senders",
            "Получатели": "receivers",
            "Исполнители": "executors",
            "Делегаты": "delegates",
            "Хэштеги": "tags",
            "Комментарии": "comments",
            "Вложение": "attachments",
            "Ответ": "reply_file",
            "Прочитано": "is_read",
            "Краткое содержание": "about",
            "Срок исполнения": "deadline",
            "Направление": "direction",
            "Входящий номер": "incoming_number",
            "Входящая дата": "incoming_date",
        }

        return key_mapping.get(column_name, column_name.lower())

    def _update_table(self, documents: list[dict]):
        """
        Обновление таблицы с отсортированными данными

        Args:
            documents: отсортированные документы
        """
        self.table_widget.setRowCount(0)
        self.table_widget.setRowCount(len(documents))

        # Используем row_filler из родительского виджета
        parent = self.table_widget.parent()
        if hasattr(parent, "row_filler"):
            for row, doc in enumerate(documents):
                parent.row_filler.render_row(row, doc)

        self.table_widget.resizeRowsToContents()

    def _update_sort_indicator(self):
        """Обновление индикатора сортировки в заголовке"""
        header = self.table_widget.horizontalHeader()

        # Сначала убираем все индикаторы
        for _i in range(header.count()):
            header.setSortIndicatorShown(False)

        if self.current_column:
            # Находим индекс колонки
            for idx, name in enumerate(self.column_index_to_name.values()):
                if name == self.current_column:
                    # Показываем индикатор
                    header.setSortIndicatorShown(True)
                    header.setSortIndicator(
                        idx,
                        Qt.SortOrder.DescendingOrder if self.current_reverse else Qt.SortOrder.AscendingOrder,
                    )
                    break

    def sort_by_column(self, column_name: str, reverse: bool = False):
        """
        Сортировка по указанной колонке

        Args:
            column_name: имя колонки
            reverse: обратный порядок
        """
        self.current_column = column_name
        self.current_reverse = reverse
        self.apply_sorting()

    def reset_sorting(self):
        """Сброс сортировки"""
        self.current_column = None
        self.current_reverse = False

        # Убираем индикатор
        header = self.table_widget.horizontalHeader()
        header.setSortIndicatorShown(False)

        # Перезагружаем данные
        parent = self.table_widget.parent()
        if hasattr(parent, "load_test_data"):
            parent.load_test_data()
