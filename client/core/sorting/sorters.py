"""
Реализации различных сортировщиков
"""

from datetime import datetime

from client.core.sorting.base import BaseSorter


class TextSorter(BaseSorter):
    """Сортировка по текстовым полям"""

    def sort(self, data: list[dict], key: str) -> list[dict]:
        return sorted(
            data,
            key=lambda x: str(self._get_value(x, key) or "").lower(),
            reverse=self.reverse,
        )


class NumericSorter(BaseSorter):
    """Сортировка по числовым полям"""

    def sort(self, data: list[dict], key: str) -> list[dict]:
        def get_numeric_value(item):
            value = self._get_value(item, key)
            try:
                return float(value) if value is not None else float("inf")
            except (ValueError, TypeError):
                return float("inf")

        return sorted(data, key=get_numeric_value, reverse=self.reverse)


class DateSorter(BaseSorter):
    """Сортировка по датам"""

    def sort(self, data: list[dict], key: str) -> list[dict]:
        def get_date_value(item):
            value = self._get_value(item, key)
            if value is None:
                return datetime.min

            if isinstance(value, datetime):
                return value

            if isinstance(value, str):
                try:
                    # Пробуем разные форматы дат
                    for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S"]:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                except (ValueError, TypeError):
                    pass

            return datetime.min

        return sorted(data, key=get_date_value, reverse=self.reverse)


class StatusSorter(BaseSorter):
    """Сортировка по статусу с приоритетами"""

    # Приоритеты статусов (чем меньше число, тем выше приоритет)
    STATUS_PRIORITY = {
        "Выполнено": 0,
        "На исполнении": 1,
        "На контроле": 2,
        "На подписи": 3,
        "Зарегистрирован": 4,
        "Черновик": 5,
        "Отклонен": 6,
        "Отозван": 7,
    }

    def sort(self, data: list[dict], key: str) -> list[dict]:
        def get_status_priority(item):
            status = self._get_value(item, key)
            if status is None:
                return 999
            return self.STATUS_PRIORITY.get(str(status), 999)

        return sorted(data, key=get_status_priority, reverse=self.reverse)


class DelegatesSorter(BaseSorter):
    """Сортировка по делегатам (количество)"""

    def sort(self, data: list[dict], key: str) -> list[dict]:
        def get_delegates_count(item):
            delegates = self._get_value(item, key)
            if delegates is None:
                return 0
            if isinstance(delegates, list):
                return len(delegates)
            return 1 if delegates else 0

        return sorted(data, key=get_delegates_count, reverse=self.reverse)


class TagsSorter(BaseSorter):
    """Сортировка по тегам (количество)"""

    def sort(self, data: list[dict], key: str) -> list[dict]:
        def get_tags_count(item):
            tags = self._get_value(item, key)
            if tags is None:
                return 0
            if isinstance(tags, list):
                return len(tags)
            return 1 if tags else 0

        return sorted(data, key=get_tags_count, reverse=self.reverse)


class ReadStatusSorter(BaseSorter):
    """Сортировка по статусу прочтения"""

    def sort(self, data: list[dict], key: str) -> list[dict]:
        def get_read_status(item):
            value = self._get_value(item, key)
            # True (прочитано) идет после False (не прочитано) при сортировке по возрастанию
            return 0 if value else 1

        return sorted(data, key=get_read_status, reverse=self.reverse)
