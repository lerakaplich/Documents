"""
Диалоговое окно перенаправления документа.
Единый список сотрудников с чекбоксами, поиск и поле комментария.
"""
import os
import sys
from PyQt6.QtWidgets import (QDialog, QListWidgetItem, QApplication)
from PyQt6.QtCore import pyqtSignal, Qt, QFile
from PyQt6.uic import loadUi


class RedirectDialog(QDialog):
    # Сигнал: список ID отмеченных получателей, текст комментария
    redirect_confirmed = pyqtSignal(list, str)

    def __init__(self, current_recipients: list, all_employees: list, parent=None):
        """
        :param current_recipients: список словарей {'id': int, 'name': str} – уже назначенные
        :param all_employees: полный список словарей {'id': int, 'name': str} – все сотрудники
        """
        super().__init__(parent)
        # Создаём удобные структуры
        self.recipient_ids = {emp['id'] for emp in current_recipients}
        self.all_employees = {emp['id']: emp for emp in all_employees}
        # Убедимся, что все текущие получатели есть в общем списке (на всякий случай)
        for emp in current_recipients:
            self.all_employees.setdefault(emp['id'], emp)

        self._init_ui()
        self._rebuild_list()
        self._connect_signals()

    def _init_ui(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Сохраняем исходный base_dir для картинок (D:\Documents\client)
        # Если ваш файл лежит, например, в D:\Documents\client\windows, то один переход вверх:
        # project_dir = os.path.dirname(base_dir)
        # Но судя по циклу ниже, вы поднимаетесь на 4 уровня вверх.
        # Давайте найдем точный путь к images на основе вашей структуры:

        # Вычисляем корень проекта, как у вас в коде:
        root_dir = base_dir
        for _ in range(4):
            root_dir = os.path.dirname(root_dir)

        ui_path = os.path.join(root_dir, "client", "ui", "documents", "redirect", "redirect_dialog.ui")
        loadUi(ui_path, self)

        # --- НАЧАЛО БЛОКА ДЛЯ КРАСИВЫХ ЧЕКБОКСОВ ---
        # Формируем точный абсолютный путь к папке с картинками
        # Заменяем обратные слэши \ на прямые /, так как Qt Stylesheets требуют именно их
        images_dir = os.path.join(root_dir, "client", "images").replace("\\", "/")

        # Применяем стили конкретно к списку, подставляя вычисленные пути к файлам
        self.employeesListWidget.setStyleSheet(f"""
            QListWidget::indicator {{
                width: 18px;
                height: 18px;
            }}
            QListWidget::indicator:unchecked {{
                image: url('{images_dir}/cb_unchecked.png');
            }}
            QListWidget::indicator:checked {{
                image: url('{images_dir}/cb_checked.png');
            }}
        """)
        # --- КОНЕЦ БЛОКА ---

    def _connect_signals(self):
        self.searchEdit.textChanged.connect(self._on_search_text_changed)
        self.employeesListWidget.itemChanged.connect(self._on_item_changed)
        self.sendButton.clicked.connect(self._on_send)

    # ---------- Заполнение списка ----------
    def _rebuild_list(self, filter_text: str = ""):
        """
        Полностью перестраивает список с учётом текущего состояния чекбоксов и фильтра.
        Сортировка: сначала отмеченные (по алфавиту), затем неотмеченные (по алфавиту).
        """
        filter_lower = filter_text.lower().strip()

        # Разделяем всех сотрудников на две группы
        checked = []
        unchecked = []
        for emp in self.all_employees.values():
            if filter_lower and filter_lower not in emp['name'].lower():
                continue
            if emp['id'] in self.recipient_ids:
                checked.append(emp)
            else:
                unchecked.append(emp)

        # Сортировка по имени
        checked.sort(key=lambda x: x['name'])
        unchecked.sort(key=lambda x: x['name'])

        # Заполняем виджет
        self.employeesListWidget.blockSignals(True)
        self.employeesListWidget.clear()

        for emp in checked:
            item = QListWidgetItem(emp['name'])
            item.setData(Qt.ItemDataRole.UserRole, emp['id'])
            item.setCheckState(Qt.CheckState.Checked)
            self.employeesListWidget.addItem(item)

        for emp in unchecked:
            item = QListWidgetItem(emp['name'])
            item.setData(Qt.ItemDataRole.UserRole, emp['id'])
            item.setCheckState(Qt.CheckState.Unchecked)
            self.employeesListWidget.addItem(item)

        self.employeesListWidget.blockSignals(False)

    # ---------- Поиск ----------
    def _on_search_text_changed(self, text: str):
        self._rebuild_list(text)

    # ---------- Изменение чекбокса ----------
    def _on_item_changed(self, item: QListWidgetItem):
        emp_id = item.data(Qt.ItemDataRole.UserRole)
        if item.checkState() == Qt.CheckState.Checked:
            self.recipient_ids.add(emp_id)
        else:
            self.recipient_ids.discard(emp_id)

        # Перестраиваем список с сохранением текущего текста поиска
        current_filter = self.searchEdit.text()
        self._rebuild_list(current_filter)

    # ---------- Отправка ----------
    def _on_send(self):
        recipient_ids = list(self.recipient_ids)
        comment = self.commentTextEdit.toPlainText().strip()
        self.redirect_confirmed.emit(recipient_ids, comment)
        self.accept()


# ---------- Тестовый запуск ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Пример: текущие получатели (уже назначены)
    current = [
        {"id": 1, "name": "Иванов И.И."},
        {"id": 2, "name": "Петров П.П."}
    ]
    # Все сотрудники организации
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

    sys.exit(app.exec())