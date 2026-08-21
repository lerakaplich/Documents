import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QDate, QTime, Qt
from PyQt6.QtGui import QIcon


class OvertimeDialog(QDialog):
    def __init__(self, parent=None, readonly=False, overtime_service=None, current_employee_id=None):
        super().__init__(parent)
        self.readonly = readonly
        self.result_data = None
        self.overtime_service = overtime_service
        self.current_employee_id = current_employee_id
        self.overtime_id = None

        # Получаем корневую директорию
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        self.icons_dir = os.path.join(root_dir, 'icons')

        ui_path = os.path.join(root_dir, 'ui', 'profile', 'overtime', 'overtime_dialog.ui')

        # Если UI файл не найден, создаем диалог программно
        if not os.path.exists(ui_path):
            self._create_ui_programmatically()
        else:
            uic.loadUi(ui_path, self)
            # Применяем иконки после загрузки UI
            self._apply_icons_to_ui()

        self.setModal(True)
        self.setWindowTitle("Оформление переработки" if not readonly else "Просмотр переработки")

        # Подключаем сигналы
        self.btnSave.clicked.connect(self.accept)

        # Настраиваем режим редактирования
        self.set_edit_mode(self.readonly)

        # Загружаем сотрудников для выбора (если есть сервис)
        if self.overtime_service and not readonly:
            self._load_employees()

    def _get_icon_path(self, icon_name):
        """Возвращает путь к иконке"""
        return os.path.join(self.icons_dir, icon_name).replace('\\', '/')

    def _apply_icons_to_ui(self):
        """Применяет иконки к элементам UI"""
        try:
            # Получаем пути к иконкам
            calendar_icon = self._get_icon_path('calendar_date.svg')
            down_arrow = self._get_icon_path('down_arrow.svg')
            up_arrow = self._get_icon_path('up_arrow.svg')

            # Применяем стили для QDateEdit
            self.dateEdit.setStyleSheet(f"""
                QDateEdit {{
                    border-radius: 10px;
                    border: 1px solid #CCAB6E;
                    padding: 5px;
                    background-color: white;
                    color: #1B232A;
                }}
                QDateEdit:hover {{
                    border: 1px solid #998664;
                }}
                QDateEdit:focus {{
                    border: 2px solid #CCAB6E;
                }}
                QDateEdit::drop-down {{
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 30px;
                    border: none;
                }}
                QDateEdit::down-arrow {{
                    image: url({calendar_icon});
                    width: 18px;
                    height: 18px;
                    margin-right: 8px;
                }}
            """)

            # Применяем стили для QTimeEdit (начало)
            self.timeStart.setStyleSheet(f"""
                QTimeEdit {{
                    border-radius: 10px;
                    border: 1px solid #CCAB6E;
                    padding: 5px;
                    background-color: white;
                    color: #1B232A;
                }}
                QTimeEdit:hover {{
                    border: 1px solid #998664;
                }}
                QTimeEdit:focus {{
                    border: 2px solid #CCAB6E;
                }}
                QTimeEdit::drop-down {{
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 30px;
                    border: none;
                }}
                QTimeEdit::up-button, QTimeEdit::down-button {{
                    width: 30px;
                    border: none;
                    background: transparent;
                }}
                QTimeEdit::up-arrow {{
                    image: url({up_arrow});
                    width: 16px;
                    height: 16px;
                    margin-right: 6px;
                }}
                QTimeEdit::down-arrow {{
                    image: url({down_arrow});
                    width: 16px;
                    height: 16px;
                    margin-right: 6px;
                }}
            """)

            # Применяем стили для QTimeEdit (конец)
            self.timeEnd.setStyleSheet(f"""
                QTimeEdit {{
                    border-radius: 10px;
                    border: 1px solid #CCAB6E;
                    padding: 5px;
                    background-color: white;
                    color: #1B232A;
                }}
                QTimeEdit:hover {{
                    border: 1px solid #998664;
                }}
                QTimeEdit:focus {{
                    border: 2px solid #CCAB6E;
                }}
                QTimeEdit::drop-down {{
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 30px;
                    border: none;
                }}
                QTimeEdit::up-button, QTimeEdit::down-button {{
                    width: 30px;
                    border: none;
                    background: transparent;
                }}
                QTimeEdit::up-arrow {{
                    image: url({up_arrow});
                    width: 16px;
                    height: 16px;
                    margin-right: 6px;
                }}
                QTimeEdit::down-arrow {{
                    image: url({down_arrow});
                    width: 16px;
                    height: 16px;
                    margin-right: 6px;
                }}
            """)

            # Применяем стили для QComboBox
            self.comboEmployee.setStyleSheet(f"""
                QComboBox {{
                    border-radius: 10px;
                    border: 1px solid #CCAB6E;
                    padding: 5px;
                    background-color: white;
                    color: #1B232A;
                }}
                QComboBox:hover {{
                    border: 1px solid #998664;
                }}
                QComboBox:focus {{
                    border: 2px solid #CCAB6E;
                }}
                QComboBox::drop-down {{
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 30px;
                    border: none;
                }}
                QComboBox::down-arrow {{
                    image: url({down_arrow});
                    width: 16px;
                    height: 16px;
                    margin-right: 6px;
                }}
                QComboBox QAbstractItemView {{
                    border-radius: 6px;
                    background-color: white;
                    color: #1B232A;
                    padding: 4px;
                    outline: none;
                    border: 1px solid #CCAB6E;
                }}
                QComboBox QAbstractItemView::item {{
                    padding: 8px;
                    color: #1B232A;
                    border: none;
                    outline: none;
                }}
                QComboBox QAbstractItemView::item:hover {{
                    background-color: #e3f2fd;
                    color: #1B232A;
                }}
                QComboBox QAbstractItemView::item:selected {{
                    background-color: #e3f2fd;
                    color: #1B232A;
                }}
                QComboBox QAbstractItemView::item:focus {{
                    outline: none;
                    border: none;
                }}
            """)

        except Exception as e:
            print(f"Ошибка при применении иконок: {e}")

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

        # Получаем пути к иконкам
        down_arrow = self._get_icon_path('down_arrow.svg')
        calendar_icon = self._get_icon_path('calendar_date.svg')
        up_arrow = self._get_icon_path('up_arrow.svg')

        # Сотрудник
        self.comboEmployee = QComboBox()
        self.comboEmployee.setEditable(True)
        self.comboEmployee.setStyleSheet(f"""
            QComboBox {{
                padding: 6px;
                border: 1px solid #CED4DA;
                border-radius: 4px;
                min-height: 25px;
            }}
            QComboBox:hover {{
                border-color: #CCAB6E;
            }}
            QComboBox::down-arrow {{
                image: url({down_arrow});
                width: 16px;
                height: 16px;
                margin-right: 6px;
            }}
        """)
        form_layout.addRow("Сотрудник:", self.comboEmployee)

        # Дата
        self.dateEdit = QDateEdit()
        self.dateEdit.setCalendarPopup(True)
        self.dateEdit.setDate(QDate.currentDate())
        self.dateEdit.setStyleSheet(f"""
            QDateEdit {{
                padding: 6px;
                border: 1px solid #CED4DA;
                border-radius: 4px;
                min-height: 25px;
            }}
            QDateEdit:hover {{
                border-color: #CCAB6E;
            }}
            QDateEdit::down-arrow {{
                image: url({calendar_icon});
                width: 18px;
                height: 18px;
                margin-right: 8px;
            }}
        """)
        form_layout.addRow("Дата:", self.dateEdit)

        # Время начала
        self.timeStart = QTimeEdit()
        self.timeStart.setTime(QTime(18, 0))
        self.timeStart.setStyleSheet(f"""
            QTimeEdit {{
                padding: 6px;
                border: 1px solid #CED4DA;
                border-radius: 4px;
                min-height: 25px;
            }}
            QTimeEdit:hover {{
                border-color: #CCAB6E;
            }}
            QTimeEdit::up-arrow {{
                image: url({up_arrow});
                width: 16px;
                height: 16px;
                margin-right: 6px;
            }}
            QTimeEdit::down-arrow {{
                image: url({down_arrow});
                width: 16px;
                height: 16px;
                margin-right: 6px;
            }}
        """)
        form_layout.addRow("Время начала:", self.timeStart)

        # Время окончания
        self.timeEnd = QTimeEdit()
        self.timeEnd.setTime(QTime(20, 0))
        self.timeEnd.setStyleSheet(f"""
            QTimeEdit {{
                padding: 6px;
                border: 1px solid #CED4DA;
                border-radius: 4px;
                min-height: 25px;
            }}
            QTimeEdit:hover {{
                border-color: #CCAB6E;
            }}
            QTimeEdit::up-arrow {{
                image: url({up_arrow});
                width: 16px;
                height: 16px;
                margin-right: 6px;
            }}
            QTimeEdit::down-arrow {{
                image: url({down_arrow});
                width: 16px;
                height: 16px;
                margin-right: 6px;
            }}
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
        """Загружает список сотрудников для выбора"""
        try:
            # Здесь можно загрузить список сотрудников через EmployeeService
            # Пока добавляем тестовых сотрудников
            employees = [
                "Иванов Иван Иванович",
                "Петров Петр Петрович",
                "Сидорова Анна Сергеевна"
            ]
            self.comboEmployee.addItems(employees)

            # Если есть текущий сотрудник, выбираем его
            if self.current_employee_id:
                # В реальном приложении нужно найти сотрудника по ID
                pass
        except Exception as e:
            print(f"Ошибка загрузки сотрудников: {e}")

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
        """Заполняет диалог данными для редактирования"""
        # Сохраняем ID переработки
        self.overtime_id = data.get('id')

        # Сотрудник
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
        description = data.get('description', '')
        self.descriptionEdit.setPlainText(description)

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
        """Проверяет корректность данных"""
        if not data['employee_name']:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите сотрудника")
            return False

        if not data['date']:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите дату")
            return False

        if not data['start_time'] or not data['end_time']:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, укажите время начала и окончания")
            return False

        # Проверяем, что время начала меньше времени окончания
        start = QTime.fromString(data['start_time'], "HH:mm")
        end = QTime.fromString(data['end_time'], "HH:mm")
        if start.isValid() and end.isValid() and start >= end:
            QMessageBox.warning(self, "Ошибка", "Время начала должно быть меньше времени окончания")
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