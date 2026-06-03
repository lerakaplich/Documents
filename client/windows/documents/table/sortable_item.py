import os
import sys
from PyQt6.QtWidgets import (QTableWidgetItem)
from PyQt6.QtCore import Qt

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SortableItem(QTableWidgetItem):
    """Поддерживает правильную сортировку чисел и дат"""

    def __lt__(self, other):
        val1 = self.data(Qt.ItemDataRole.UserRole)
        val2 = other.data(Qt.ItemDataRole.UserRole)

        if val1 is None:
            val1 = self.text()
        if val2 is None:
            val2 = other.text()

        try:
            num1 = int(val1)
            num2 = int(val2)
            return num1 < num2
        except (ValueError, TypeError):
            try:
                num1 = float(val1)
                num2 = float(val2)
                return num1 < num2
            except (ValueError, TypeError):
                try:
                    from datetime import datetime
                    if isinstance(val1, str) and '.' in val1:
                        date1 = datetime.strptime(val1, "%d.%m.%Y")
                        date2 = datetime.strptime(str(val2), "%d.%m.%Y")
                        return date1 < date2
                except:
                    pass

        return str(val1).lower() < str(val2).lower()