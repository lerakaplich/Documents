from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QComboBox


class HierarchicalDepartmentFilter(QWidget):
    """
    Виджет для динамической иерархической фильтрации по подразделениям.
    При выборе элемента на одном уровне автоматически появляется комбобокс следующего уровня.
    При изменении родительского уровня все дочерние уровни удаляются.
    """
    selectionChanged = pyqtSignal(object)  # передаёт выбранный department_id или None

    def __init__(self, parent=None, get_children_func=None):
        super().__init__(parent)
        self._get_children_func = get_children_func
        self._comboboxes = []
        self._current_selection = None

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        # Флаг, чтобы предотвратить рекурсивные вызовы
        self._updating = False

    def set_children_func(self, func):
        self._get_children_func = func

    def set_root_items(self, root_departments):
        self.clear()
        if root_departments:
            self._add_filter_level(root_departments)

    def clear(self):
        for combo in self._comboboxes:
            combo.deleteLater()
        self._comboboxes.clear()
        self._current_selection = None
        self.selectionChanged.emit(None)

    def reset(self):
        self.clear()

    def get_selected(self):
        return self._current_selection

    def _add_filter_level(self, departments):
        combo = QComboBox()
        combo.setFixedHeight(32)
        combo.setMinimumWidth(180)
        combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 8px;
                padding: 5px;
                color: black;
            }
            QComboBox:hover {
                border-color: #ccab6e;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
        """)
        combo.addItem("Все", None)
        for dept in sorted(departments, key=lambda x: x["name"]):
            combo.addItem(dept["name"], dept["id"])
        combo.currentIndexChanged.connect(self._on_combo_changed)
        self._layout.addWidget(combo)
        self._comboboxes.append(combo)

    def _remove_filters_from_level(self, level):
        """Удаляет все комбобоксы начиная с указанного уровня"""
        while len(self._comboboxes) > level:
            combo = self._comboboxes.pop()
            combo.deleteLater()

    def _on_combo_changed(self):
        """Обработчик изменения выбора в любом комбобоксе"""
        if self._updating:
            return

        self._updating = True

        try:
            # Определяем, какой комбобокс изменился
            sender = self.sender()
            if sender is None or sender not in self._comboboxes:
                self._updating = False
                return

            changed_index = self._comboboxes.index(sender)

            # Удаляем все комбобоксы после изменившегося
            self._remove_filters_from_level(changed_index + 1)

            # Определяем последний выбранный ID
            last_selected_id = None
            last_selected_level = -1

            for i, combo in enumerate(self._comboboxes):
                dept_id = combo.currentData()
                if dept_id is not None:
                    last_selected_id = dept_id
                    last_selected_level = i
                else:
                    # Если на каком-то уровне выбрано "Все", удаляем все последующие
                    self._remove_filters_from_level(i)
                    break

            # Если есть выбранный ID, загружаем его дочерние элементы
            if last_selected_id is not None and self._get_children_func:
                children = self._get_children_func(last_selected_id)
                if children:
                    self._add_filter_level(children)

            # Обновляем текущий выбор
            self._current_selection = last_selected_id
            self.selectionChanged.emit(last_selected_id)

        finally:
            self._updating = False

    def clear_selection(self):
        """Сбрасывает выбор во всех комбобоксах, но не удаляет их."""
        # Устанавливаем "Все" (индекс 0) для всех комбобоксов
        for combo in self._comboboxes:
            if combo:
                combo.blockSignals(True)  # Блокируем сигналы
                combo.setCurrentIndex(0)  # Выбираем "Все"
                combo.blockSignals(False)  # Разблокируем сигналы

        # Удаляем все комбобоксы после первого уровня (дочерние)
        while len(self._comboboxes) > 1:
            combo = self._comboboxes.pop()
            combo.deleteLater()

        self._current_selection = None
        # Эмитим сигнал с None, чтобы обновить данные
        self.selectionChanged.emit(None)