import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import QDate, QTime

class OvertimeDialog(QDialog):
    def __init__(self, parent=None, readonly=False):
        super().__init__(parent)
        self.readonly = readonly
        self.result_data = None

        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        ui_path = os.path.join(root_dir, 'ui', 'profile', 'overtime', 'overtime_dialog.ui')
        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI-файл не найден: {ui_path}")
        uic.loadUi(ui_path, self)

        self.setModal(True)
        self.setWindowTitle("Оформление переработки" if not readonly else "Просмотр переработки")

        self.btnSave.clicked.connect(self.accept)

        self.set_edit_mode(self.readonly)

    def set_edit_mode(self, readonly):
        self.comboEmployee.setEnabled(not readonly)
        self.dateEdit.setEnabled(not readonly)
        self.timeStart.setEnabled(not readonly)
        self.timeEnd.setEnabled(not readonly)
        self.descriptionEdit.setReadOnly(False)
        self.btnSave.setEnabled(True)

    def set_data(self, data):
        # Используем правильный ключ 'employee_name'
        employee = data.get('employee_name', '')
        date_str = data.get('date', '')
        time_start_str = data.get('start_time', '')
        time_end_str = data.get('end_time', '')
        description = data.get('description', '')

        # Устанавливаем сотрудника (если есть в списке – выбираем, иначе вводим текст)
        index = self.comboEmployee.findText(employee)
        if index >= 0:
            self.comboEmployee.setCurrentIndex(index)
        else:
            self.comboEmployee.setEditText(employee)

        # Устанавливаем дату
        try:
            date = QDate.fromString(date_str, "dd.MM.yyyy")
            if date.isValid():
                self.dateEdit.setDate(date)
        except:
            pass

        # Устанавливаем время начала
        try:
            time_start = QTime.fromString(time_start_str, "HH:mm")
            if time_start.isValid():
                self.timeStart.setTime(time_start)
        except:
            pass

        # Устанавливаем время окончания
        try:
            time_end = QTime.fromString(time_end_str, "HH:mm")
            if time_end.isValid():
                self.timeEnd.setTime(time_end)
        except:
            pass

        self.descriptionEdit.setPlainText(description)

    def get_data_from_ui(self):
        # Возвращаем данные с ключами, соответствующими структуре (можно оставить 'employee')
        return {
            'employee': self.comboEmployee.currentText(),
            'date': self.dateEdit.date().toString("dd.MM.yyyy"),
            'time_start': self.timeStart.time().toString("HH:mm"),
            'time_end': self.timeEnd.time().toString("HH:mm"),
            'description': self.descriptionEdit.toPlainText()
        }

    def accept(self):
        self.result_data = self.get_data_from_ui()
        super().accept()