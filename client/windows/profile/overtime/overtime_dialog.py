import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QDate, QTime, Qt

from client.services.overtime_service import OvertimeService

from PyQt6.QtWidgets import QTimeEdit



class OvertimeDialog(QDialog):
    def __init__(self, parent=None, readonly=False, overtime_service=None, current_employee_id=None):
        super().__init__(parent)
        self.readonly = readonly
        self.result_data = None
        self.overtime_service = overtime_service
        self.current_employee_id = current_employee_id
        self.overtime_id = None
        # в __init__ OvertimeDialog
        self._employee_id_by_name = {}
        self._employee_id_to_name = {}

        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        ui_path = os.path.join(root_dir, 'ui', 'profile', 'overtime', 'overtime_dialog.ui')

        # Если UI файл не найден, создаем диалог программно

        uic.loadUi(ui_path, self)

        self.setModal(True)
        self.setWindowTitle("Оформление переработки" if not readonly else "Просмотр переработки")
        self._setup_time_edits()
        # Подключаем сигналы
        self.btnSave.clicked.connect(self.accept)

        # Настраиваем режим редактирования
        self.set_edit_mode(self.readonly)

        # Загружаем сотрудников для выбора (если есть сервис)
        if self.overtime_service and not readonly:
            self._load_employees()

    def _setup_time_edits(self):
        """Перенастраивает QTimeEdit: стрелки шагают на 30 минут, дефолты и дата = сегодня."""

        def make_step(edit):
            """Возвращает функцию stepBy для конкретного QTimeEdit."""

            def stepBy(steps: int):
                new_time = edit.time().addSecs(steps * 30 * 60)
                edit.setTime(new_time)

            return stepBy

        # Переопределяем stepBy у существующих виджетов (не подменяем их)
        if hasattr(self, 'timeStart'):
            self.timeStart.stepBy = make_step(self.timeStart)
            self.timeStart.setDisplayFormat("HH:mm")
            self.timeStart.setTime(QTime(16, 30))

        if hasattr(self, 'timeEnd'):
            self.timeEnd.stepBy = make_step(self.timeEnd)
            self.timeEnd.setDisplayFormat("HH:mm")
            self.timeEnd.setTime(QTime(17, 0))

        if hasattr(self, 'dateEdit'):
            self.dateEdit.setDate(QDate.currentDate())

    def _create_ui_programmatically(self):
        """Создает UI программно если файл не найден"""
        from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout,
                                     QLabel, QComboBox, QDateEdit, QTimeEdit,
                                     QTextEdit, QPushButton, QFrame)

        self.setMinimumSize(500, 450)
        self.setMaximumSize(600, 550)

        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Форма
        form_widget = QFrame()
        form_widget.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(15, 15, 15, 15)

        # Сотрудник
        self.comboEmployee = QComboBox()
        self.comboEmployee.setEditable(True)
        self.comboEmployee.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #CED4DA;
                border-radius: 4px;
                min-height: 25px;
            }
            QComboBox:hover {
                border-color: #CCAB6E;
            }
        """)
        form_layout.addRow("Сотрудник:", self.comboEmployee)

        # Дата
        self.dateEdit = QDateEdit()
        self.dateEdit.setCalendarPopup(True)
        self.dateEdit.setDate(QDate.currentDate())
        self.dateEdit.setStyleSheet("""
            QDateEdit {
                padding: 6px;
                border: 1px solid #CED4DA;
                border-radius: 4px;
                min-height: 25px;
            }
            QDateEdit:hover {
                border-color: #CCAB6E;
            }
        """)
        form_layout.addRow("Дата:", self.dateEdit)

        # Время начала
        self.timeStart = QTimeEdit()
        self.timeStart.setTime(QTime(18, 0))
        self.timeStart.setStyleSheet("""
            QTimeEdit {
                padding: 6px;
                border: 1px solid #CED4DA;
                border-radius: 4px;
                min-height: 25px;
            }
            QTimeEdit:hover {
                border-color: #CCAB6E;
            }
        """)
        form_layout.addRow("Время начала:", self.timeStart)

        # Время окончания
        self.timeEnd = QTimeEdit()
        self.timeEnd.setTime(QTime(20, 0))
        self.timeEnd.setStyleSheet("""
            QTimeEdit {
                padding: 6px;
                border: 1px solid #CED4DA;
                border-radius: 4px;
                min-height: 25px;
            }
            QTimeEdit:hover {
                border-color: #CCAB6E;
            }
        """)
        form_layout.addRow("Время окончания:", self.timeEnd)

        # Описание
        self.descriptionEdit = QTextEdit()
        self.descriptionEdit.setPlaceholderText("Введите описание переработки...")
        self.descriptionEdit.setMinimumHeight(100)
        self.descriptionEdit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #CED4DA;
                border-radius: 4px;
                padding: 6px;
            }
            QTextEdit:focus {
                border-color: #CCAB6E;
            }
        """)
        form_layout.addRow("Описание:", self.descriptionEdit)

        main_layout.addWidget(form_widget)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btnCancel = QPushButton("Отмена")
        self.btnCancel.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
            QPushButton:pressed {
                background-color: #4E555B;
            }
        """)
        self.btnCancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btnCancel)

        self.btnSave = QPushButton("Сохранить")
        self.btnSave.setStyleSheet("""
            QPushButton {
                background-color: #CCAB6E;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #B89A5A;
            }
            QPushButton:pressed {
                background-color: #A88A4A;
            }
            QPushButton:disabled {
                background-color: #D4C4A8;
            }
        """)
        self.btnSave.clicked.connect(self.accept)
        button_layout.addWidget(self.btnSave)

        main_layout.addLayout(button_layout)

        # Применяем стили для диалога
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                font-size: 13px;
                font-weight: 500;
                color: #333;
            }
        """)

    def _load_employees(self):
        try:
            from client.services.employee_service import EmployeeService
            service = EmployeeService(self.overtime_service.client)
            employees = service.get_all_employees()

            print(f"🔍 Получено {len(employees)} сотрудников")
            if employees:
                print(f"🔍 Пример записи: {employees[0]}")  # ← ключевой лог

            self.comboEmployee.clear()
            self._employee_id_by_name = {}
            self._employee_id_to_name = {}

            if not employees:
                me = service.get_my_profile()
                employees = [me]

            for emp in employees:
                # Пробуем full_name, потом last_name+first_name+patronymic, потом fallback
                full_name = (emp.get('full_name') or '').strip()
                if not full_name:
                    full_name = f"{emp.get('last_name', '')} {emp.get('first_name', '')} {emp.get('patronymic', '')}".strip()
                if not full_name:
                    full_name = f"ID {emp.get('id')}"

                emp_id = emp.get('id')
                self.comboEmployee.addItem(full_name)
                if emp_id is not None:
                    self._employee_id_by_name[full_name] = emp_id
                    self._employee_id_to_name[emp_id] = full_name

            if self.current_employee_id in self._employee_id_to_name:
                self.comboEmployee.setCurrentText(self._employee_id_to_name[self.current_employee_id])

            print(f"🔍 Загружено в combo: {self.comboEmployee.count()} элементов")
        except Exception as e:
            print(f"Ошибка загрузки сотрудников: {e}")
            import traceback
            traceback.print_exc()

    def get_selected_employee_id(self) -> int:
        name = self.comboEmployee.currentText()
        return self._employee_id_by_name.get(name, self.current_employee_id)

    def set_edit_mode(self, readonly):
        """Устанавливает режим редактирования"""
        self.comboEmployee.setEnabled(not readonly)
        self.dateEdit.setEnabled(not readonly)
        self.timeStart.setEnabled(not readonly)
        self.timeEnd.setEnabled(not readonly)
        self.descriptionEdit.setReadOnly(readonly)
        self.btnSave.setEnabled(not readonly)

        if readonly:
            self.btnSave.setText("Закрыть")
            self.btnSave.setStyleSheet("""
                QPushButton {
                    background-color: #6C757D;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 20px;
                    font-size: 13px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #5A6268;
                }
                QPushButton:pressed {
                    background-color: #4E555B;
                }
            """)
            self.btnCancel.setVisible(False)

    def set_data(self, data):
        self.overtime_id = data.get('id')

        # Сотрудник — ищем по employee_id, а не по имени
        emp_id = data.get('employee_id') or data.get('raw_data', {}).get('employee_id')
        if emp_id and emp_id in self._employee_id_to_name:
            self.comboEmployee.setCurrentText(self._employee_id_to_name[emp_id])
        else:
            # fallback по имени
            employee = data.get('employee_name', '')
            index = self.comboEmployee.findText(employee)
            if index >= 0:
                self.comboEmployee.setCurrentIndex(index)
            else:
                self.comboEmployee.setEditText(employee)

        # Дата
        date_str = data.get('date', '')
        try:
            date = QDate.fromString(date_str, "dd.MM.yyyy")
            if date.isValid():
                self.dateEdit.setDate(date)
        except:
            pass

        # Время начала
        time_start_str = data.get('start_time', '')
        try:
            time_start = QTime.fromString(time_start_str, "HH:mm")
            if time_start.isValid():
                self.timeStart.setTime(time_start)
        except:
            pass

        # Время окончания
        time_end_str = data.get('end_time', '')
        try:
            time_end = QTime.fromString(time_end_str, "HH:mm")
            if time_end.isValid():
                self.timeEnd.setTime(time_end)
        except:
            pass

        # Описание
        self.descriptionEdit.setPlainText(data.get('description', ''))

    def get_data_from_ui(self):
        """Собирает данные из формы"""
        return {
            'employee_name': self.comboEmployee.currentText(),
            'date': self.dateEdit.date().toString("dd.MM.yyyy"),
            'start_time': self.timeStart.time().toString("HH:mm"),
            'end_time': self.timeEnd.time().toString("HH:mm"),
            'description': self.descriptionEdit.toPlainText().strip()
        }

    def validate_data(self, data):
        if not data['employee_name']:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите сотрудника")
            return False

        if not data['date']:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите дату")
            return False

        if not data['start_time'] or not data['end_time']:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, укажите время начала и окончания")
            return False

        start = QTime.fromString(data['start_time'], "HH:mm")
        end = QTime.fromString(data['end_time'], "HH:mm")

        if not start.isValid() or not end.isValid():
            QMessageBox.warning(self, "Ошибка", "Некорректное значение времени")
            return False

        if start >= end:
            QMessageBox.warning(self, "Ошибка", "Время начала должно быть меньше времени окончания")
            return False

        diff_minutes = start.secsTo(end) // 60
        if diff_minutes % 30 != 0:
            QMessageBox.warning(
                self, "Ошибка",
                "Продолжительность переработки должна быть кратна 30 минутам "
                "(0.5 ч, 1 ч, 1.5 ч, 2 ч, 2.5 ч ...).\n"
                f"Сейчас: {diff_minutes} мин."
            )
            return False

        return True

    def accept(self):
        """Обработчик сохранения"""
        if self.readonly:
            super().accept()
            return

        data = self.get_data_from_ui()

        if not self.validate_data(data):
            return

        self.result_data = data
        super().accept()

    def reject(self):
        """Обработчик отмены"""
        self.result_data = None
        super().reject()