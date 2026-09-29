"""
Базовый класс для сортировки данных
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseSorter(ABC):
    """Базовый абстрактный класс для сортировщиков"""

    def __init__(self, reverse: bool = False):
        self.reverse = reverse

    @abstractmethod
    def sort(self, data: list[dict], key: str) -> list[dict]:
        """
        Сортировка данных

        Args:
            data: список словарей с данными
            key: ключ для сортировки

        Returns:
            List[dict]: отсортированный список
        """

    def _get_value(self, item: dict, key: str) -> Any:
        """
        Получение значения по ключу с поддержкой вложенных ключей

        Args:
            item: словарь с данными
            key: ключ (может быть с точками для вложенных)

        Returns:
            Any: значение
        """
        if "." in key:
            keys = key.split(".")
            value = item
            for k in keys:
                value = value.get(k, None)
                if value is None:
                    break
            return value
        return item.get(key, None)
