import sys
import os
from PyQt6.QtWidgets import QApplication, QFrame, QVBoxLayout, QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.uic import loadUi

from client.core.themes import T, apply_theme_to_widget


class EmployeeCard(QFrame):
    """Карточка сотрудника на основе загруженного UI файла"""

    # Сигналы для взаимодействия с главным окном
    edit_clicked = pyqtSignal(dict)  # Передаем данные сотрудника
    delete_clicked = pyqtSignal(int)  # Передаем ID сотрудника

    def __init__(self, employee_data=None, parent=None):
        super().__init__(parent)

        # Загружаем UI дизайн
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)
            apply_theme_to_widget(self)
        else:
            print(f"UI файл не найден: {ui_path}")
            self.setup_placeholder()

        # Сохраняем данные
        self.employee_data = employee_data or {}
        self.employee_id = self.employee_data.get('id', 0)

        # Настраиваем карточку
        self.setup_card()

        # Подключаем сигналы кнопок
        if hasattr(self, 'editBtn'):
            self.editBtn.clicked.connect(self.on_edit_clicked)
        if hasattr(self, 'deleteBtn'):
            self.deleteBtn.clicked.connect(self.on_delete_clicked)

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'employees', 'employee_card.ui')

        return os.path.normpath(ui_path)

    def setup_card(self):
        """Заполняет карточку данными"""
        if not self.employee_data:
            return

        # Заполняем ФИО с порядковым номером
        if hasattr(self, 'nameLabel'):
            name = self.employee_data.get('full_name', '')
            number = self.employee_data.get('display_number', '')
            if number and name:
                self.nameLabel.setText(f"{number}. {name}")
            elif name:
                self.nameLabel.setText(name)
            else:
                self.nameLabel.setText("ФИО не указано")

        # Заполняем должность
        if hasattr(self, 'positionLabel'):
            position = self.employee_data.get('position', '')
            self.positionLabel.setText(position if position else "Должность не указана")

        # Заполняем отдел/компанию
        if hasattr(self, 'departmentLabel'):
            company = self.employee_data.get('company', '')
            department = self.employee_data.get('department', '')
            subdivision = self.employee_data.get('subdivision', '')

            parts = [p for p in [company, department, subdivision] if p]
            if parts:
                self.departmentLabel.setText(", ".join(parts))
            else:
                self.departmentLabel.setText("Место работы не указано")

        # Заполняем рабочий телефон
        if hasattr(self, 'workPhoneLabel'):
            work_phone = self.employee_data.get('work_phone', '')
            if work_phone:
                self.workPhoneLabel.setText(f"📞 {work_phone}")
            else:
                self.workPhoneLabel.setText("📞 не указан")

        # Заполняем email
        if hasattr(self, 'emailLabel'):
            email = self.employee_data.get('email', '')
            if email:
                self.emailLabel.setText(f"✉ {email}")
            else:
                self.emailLabel.setText("✉ не указан")

        # Заполняем права доступа
        if hasattr(self, 'rightsLabel'):
            rights = self.employee_data.get('rights', '')
            if rights:
                self.rightsLabel.setText(rights)
                if rights.lower() == 'администратор':
                    color = T.ACCENT_PRIMARY
                elif rights.lower() == 'пользователь':
                    color = T.TEXT_SUCCESS
                else:
                    color = T.TEXT_MUTED_ALT
                self.rightsLabel.setStyleSheet(
                    f"border: none; font-size: 12px; font-weight: bold; "
                    f"color: {color}; background-color: transparent;"
                )
            else:
                self.rightsLabel.setText("Права не назначены")
                self.rightsLabel.setStyleSheet(
                    f"border: none; font-size: 12px; font-weight: bold; "
                    f"color: {T.TEXT_DANGER}; background-color: transparent;"
                )

    def on_edit_clicked(self):
        """Обработчик кнопки редактирования"""
        self.edit_clicked.emit(self.employee_data)

    def on_delete_clicked(self):
        """Обработчик кнопки удаления"""
        self.delete_clicked.emit(self.employee_id)

    def update_data(self, new_data):
        """Обновляет данные карточки"""
        self.employee_data.update(new_data)
        self.setup_card()

    def set_display_number(self, number):
        """Устанавливает порядковый номер для отображения"""
        self.employee_data['display_number'] = str(number)
        self.setup_card()

    def setup_placeholder(self):
        """Создает простую версию карточки, если UI не найден"""
        layout = QVBoxLayout(self)

        self.nameLabel = QLabel("Employee (UI not found)")
        self.nameLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.nameLabel)

        self.positionLabel = QLabel("Должность")
        layout.addWidget(self.positionLabel)

        self.departmentLabel = QLabel("Отдел")
        layout.addWidget(self.departmentLabel)

        self.workPhoneLabel = QLabel("📞 Рабочий телефон")
        layout.addWidget(self.workPhoneLabel)

        self.emailLabel = QLabel("✉ Email")
        layout.addWidget(self.emailLabel)

        self.rightsLabel = QLabel("Права")
        layout.addWidget(self.rightsLabel)

        buttons_layout = QHBoxLayout()
        self.editBtn = QPushButton("Редактировать")
        self.deleteBtn = QPushButton("Удалить")
        buttons_layout.addWidget(self.editBtn)
        buttons_layout.addWidget(self.deleteBtn)
        layout.addLayout(buttons_layout)

        self.editBtn.clicked.connect(self.on_edit_clicked)
        self.deleteBtn.clicked.connect(self.on_delete_clicked)


# Точка входа для тестирования
if __name__ == '__main__':
    app = QApplication(sys.argv)

    test_data = {
        'id': 1,
        'display_number': '1',
        'full_name': 'Иванов Иван Иванович',
        'position': 'Генеральный директор',
        'company': 'ОАО МАЗ',
        'department': 'Управление персоналом',
        'subdivision': 'Отдел кадров',
        'work_phone': '101',
        'email': 'i.ivanov@maz.by',
        'rights': 'Администратор'
    }

    card = EmployeeCard(test_data)
    card.setWindowTitle("Тест карточки сотрудника")
    card.edit_clicked.connect(lambda data: print(f"Редактировать: {data['full_name']}"))
    card.delete_clicked.connect(lambda emp_id: print(f"Удалить ID: {emp_id}"))
    card.show()

    sys.exit(app.exec())