import os
import sys
from PyQt6.QtWidgets import (QDialog, QListWidgetItem, QApplication,
                             QWidget, QHBoxLayout, QLabel, QFrame)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.uic import loadUi


class RedirectDialog(QDialog):
    # Сигнал: список ID отмеченных получателей, текст комментария
    redirect_confirmed = pyqtSignal(list, str)

    def __init__(self, current_recipients: list, all_employees: list, parent=None):
        super().__init__(parent)

        # Индексируем всех сотрудников по ID и по Имени для быстрого поиска
        self.all_employees = {emp['id']: emp for emp in all_employees}
        name_to_emp = {emp['name'].strip(): emp for emp in all_employees}

        self.recipient_ids = set()
        for emp in current_recipients:
            if isinstance(emp, dict):
                # Если пришел словарь (правильный формат)
                self.recipient_ids.add(emp['id'])
                self.all_employees.setdefault(emp['id'], emp)
            elif isinstance(emp, str):
                # Если пришла просто строка с именем (ваш текущий случай)
                emp_cleaned = emp.strip()
                if emp_cleaned in name_to_emp:
                    # Нашли сотрудника по имени и взяли его ID
                    self.recipient_ids.add(name_to_emp[emp_cleaned]['id'])
                else:
                    # Если сотрудника нет в общем списке, можно временно сгенерировать фейковый ID или пропустить
                    print(f"[WARN] Текущий делегат '{emp_cleaned}' не найден в общем списке сотрудников!")

        self._init_ui()
        self._rebuild_list()
        self._connect_signals()

    def _init_ui(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = base_dir
        for _ in range(4):
            root_dir = os.path.dirname(root_dir)

        ui_path = os.path.join(root_dir, "client", "ui", "documents", "redirect", "redirect_dialog.ui")
        loadUi(ui_path, self)

        images_dir = os.path.join(root_dir, "client", "icons").replace("\\", "/")

        self.employeesListWidget.setStyleSheet(f"""
            QListWidget::indicator {{
                width: 18px;
                height: 18px;
                background-color: transparent;
            }}
            QListWidget::indicator:unchecked {{
                image: url('{images_dir}/cb_unchecked.png');
                background-color: transparent;
            }}
            QListWidget::indicator:checked {{
                image: url('{images_dir}/cb_checked.png');
                background-color: transparent;
            }}
        """)

    def _connect_signals(self):
        self.searchEdit.textChanged.connect(self._on_search_text_changed)
        self.employeesListWidget.itemChanged.connect(self._on_item_changed)
        self.sendButton.clicked.connect(self._on_send)

    def _create_separator(self, text: str) -> QWidget:
        """Создает аккуратный виджет-разделитель: линия | текст | линия"""
        container = QWidget()
        # Фиксируем высоту контейнера, чтобы Qt не сжимал его в 0 пикселей
        container.setFixedHeight(16)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(12)

        # Левая линия
        line_left = QFrame()
        line_left.setFrameShape(QFrame.Shape.HLine)
        line_left.setStyleSheet("color: #dcdcdc; background-color: #dcdcdc; max-height: 1px;")

        # Текст по центру
        label = QLabel(text)
        label.setStyleSheet("color: #888888; font-size: 12px; font-weight: normal; background: transparent;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Правая линия
        line_right = QFrame()
        line_right.setFrameShape(QFrame.Shape.HLine)
        line_right.setStyleSheet("color: #dcdcdc; background-color: #dcdcdc; max-height: 1px;")

        layout.addWidget(line_left, 1)
        layout.addWidget(label, 0)
        layout.addWidget(line_right, 1)

        return container

    # ---------- Заполнение списка ----------
    def _rebuild_list(self, filter_text: str = ""):
        """
        Полностью перестраивает список с добавлением полноценных разделительных линий.
        """
        filter_lower = filter_text.lower().strip()

        checked = []
        unchecked = []
        for emp in self.all_employees.values():
            if filter_lower and filter_lower not in emp['name'].lower():
                continue
            if emp['id'] in self.recipient_ids:
                checked.append(emp)
            else:
                unchecked.append(emp)

        checked.sort(key=lambda x: x['name'])
        unchecked.sort(key=lambda x: x['name'])

        self.employeesListWidget.blockSignals(True)
        self.employeesListWidget.clear()

        # 1. Добавляем группу "Документ перенаправлен"
        if checked:
            sep_checked = QListWidgetItem()
            sep_checked.setFlags(Qt.ItemFlag.NoItemFlags)
            # Задаем размер элемента списка вручную через QSize
            sep_checked.setSizeHint(QSize(10, 28))

            self.employeesListWidget.addItem(sep_checked)
            self.employeesListWidget.setItemWidget(sep_checked, self._create_separator("Перенаправлено (выполнено)"))

            for emp in checked:
                item = QListWidgetItem(emp['name'])
                item.setData(Qt.ItemDataRole.UserRole, emp['id'])
                item.setCheckState(Qt.CheckState.Checked)
                self.employeesListWidget.addItem(item)

        # 2. Добавляем группу "Список сотрудников"
        if unchecked:
            sep_unchecked = QListWidgetItem()
            sep_unchecked.setFlags(Qt.ItemFlag.NoItemFlags)
            # Задаем размер элемента списка вручную через QSize
            sep_unchecked.setSizeHint(QSize(10, 28))

            self.employeesListWidget.addItem(sep_unchecked)
            self.employeesListWidget.setItemWidget(sep_unchecked, self._create_separator("Ожидают перенаправления"))

            for emp in unchecked:
                item = QListWidgetItem(emp['name'])
                item.setData(Qt.ItemDataRole.UserRole, emp['id'])
                item.setCheckState(Qt.CheckState.Unchecked)
                self.employeesListWidget.addItem(item)

        self.employeesListWidget.blockSignals(False)

    def _on_search_text_changed(self, text: str):
        self._rebuild_list(text)

    def _on_item_changed(self, item: QListWidgetItem):
        emp_id = item.data(Qt.ItemDataRole.UserRole)
        if emp_id is None:
            return

        if item.checkState() == Qt.CheckState.Checked:
            self.recipient_ids.add(emp_id)
        else:
            self.recipient_ids.discard(emp_id)

        current_filter = self.searchEdit.text()
        self._rebuild_list(current_filter)

    def _on_send(self):
        recipient_ids = list(self.recipient_ids)
        comment = self.commentTextEdit.toPlainText().strip()
        self.redirect_confirmed.emit(recipient_ids, comment)
        self.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    current = [
        {"id": 1, "name": "Иванов И.И."},
        {"id": 2, "name": "Петров П.П."}
    ]
    all_emp = [
        {"id": 1, "name": "Иванов И.И."},
        {"id": 2, "name": "Петров П.П."},
        {"id": 3, "name": "Сидоров С.С."},
        {"id": 4, "name": "Кузнецов А.А."},
        {"id": 5, "name": "Смирнова Е.В."},
        {"id": 6, "name": "Фёдоров Ф.Ф."},
        {"id": 7, "name": "Алексеев А.А."},
        {"id": 8, "name": "Борисов Б.Б."},
    ]

    dialog = RedirectDialog(current, all_emp)


    def on_confirm(ids, comment):
        print("Отмеченные получатели (ID):", ids)
        print("Комментарий:", comment)


    dialog.redirect_confirmed.connect(on_confirm)
    dialog.exec()