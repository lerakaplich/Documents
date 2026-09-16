# client/windows/system/departments/department_dialog.py

"""
Модуль диалога для создания/редактирования отдела
"""
import os
import sys
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox, QApplication
from PyQt6.QtCore import Qt


class DepartmentDialog(QDialog):
    """
    Диалог для создания/редактирования отдела
    """

    # Серверный маппинг id → название. Используется, если родитель
    # не передал department_types (например, при вызове из теста).
    FALLBACK_TYPES = [
        {"id": 1, "name": "Управление"},
        {"id": 2, "name": "Отдел"},
        {"id": 3, "name": "Бюро"},
        {"id": 4, "name": "Сектор"},
        {"id": 5, "name": "Цех"},
    ]

    def __init__(self, parent=None, department_data=None, organizations=None,
                 departments=None, employees=None, department_types=None):
        """
        Args:
            parent: Родительский виджет
            department_data: Данные отдела для редактирования (dict)
            organizations: Список организаций для комбобокса
            departments: Список отделов для родительского отдела
            employees: Список сотрудников для руководителя
            department_types: Список типов отделов ({id, name}) — с сервера
        """
        super().__init__(parent)

        self.department_data = department_data or {}
        self.is_edit_mode = bool(self.department_data.get('id'))
        self.organizations = organizations or []
        self.departments = departments or []
        self.employees = employees or []
        self.department_types = department_types or self.FALLBACK_TYPES

        self._load_ui()
        self._setup_window()
        self._populate_combos()
        self._populate_fields()
        self._connect_signals()

    # ==================== UI ====================

    def _load_ui(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '../../../ui/system/departments/department_dialog.ui')
        ui_path = os.path.normpath(ui_path)

        if os.path.exists(ui_path):
            try:
                uic.loadUi(ui_path, self)
                print(f"[DEBUG] UI файл успешно загружен: {ui_path}")
                self._create_widget_aliases()
            except Exception as e:
                print(f"[ERROR] Ошибка загрузки UI: {e}")
                self._setup_fallback_ui()
        else:
            print(f"[ERROR] UI файл не найден: {ui_path}")
            self._setup_fallback_ui()

    def _create_widget_aliases(self):
        aliases = {
            'name_edit': 'nameEdit',
            'organization_combo': 'organizationCombo',
            'parent_department_combo': 'parentDepartmentCombo',
            'type_combo': 'typeCombo',
            'department_number_edit': 'departmentNumberEdit',
            'phone_edit': 'phoneEdit',
            'head_combo': 'headCombo',
            'save_button': 'saveButton',
            'title_label': 'titleLabel',
            'scroll_area': 'scrollArea',
            'scroll_content': 'scrollContent',
            'scroll_layout': 'scrollLayout',
            'group_box': 'departmentInfoGroup',
        }
        for snake, camel in aliases.items():
            if hasattr(self, camel) and not hasattr(self, snake):
                setattr(self, snake, getattr(self, camel))

    def _setup_fallback_ui(self):
        from PyQt6.QtWidgets import (
            QVBoxLayout, QHBoxLayout, QGridLayout,
            QGroupBox, QLabel, QLineEdit, QComboBox,
            QPushButton, QScrollArea, QWidget
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        self.title_label = QLabel("Новый отдел")
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #1B232A; margin-bottom: 10px;")
        main_layout.addWidget(self.title_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background-color: transparent;")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(5, 5, 15, 5)

        group_box = QGroupBox("Информация об отделе")
        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #1B232A;
            }
        """)

        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(15, 15, 15, 15)
        grid_layout.setSpacing(10)

        name_label = QLabel("Название *:")
        name_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(name_label, 0, 0)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите название отдела")
        self.name_edit.setMinimumHeight(32)
        self.name_edit.setMaximumHeight(32)
        grid_layout.addWidget(self.name_edit, 0, 1)

        org_label = QLabel("Организация *:")
        org_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(org_label, 1, 0)

        self.organization_combo = QComboBox()
        self.organization_combo.setPlaceholderText("Выберите организацию")
        self.organization_combo.setMinimumHeight(32)
        self.organization_combo.setMaximumHeight(32)
        grid_layout.addWidget(self.organization_combo, 1, 1)

        parent_label = QLabel("Родительский отдел:")
        parent_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(parent_label, 2, 0)

        self.parent_department_combo = QComboBox()
        self.parent_department_combo.setPlaceholderText("Выберите родительский отдел")
        self.parent_department_combo.setMinimumHeight(32)
        self.parent_department_combo.setMaximumHeight(32)
        grid_layout.addWidget(self.parent_department_combo, 2, 1)

        type_label = QLabel("Тип отдела *:")
        type_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(type_label, 3, 0)

        self.type_combo = QComboBox()
        self.type_combo.setPlaceholderText("Выберите тип отдела")
        self.type_combo.setMinimumHeight(32)
        self.type_combo.setMaximumHeight(32)
        grid_layout.addWidget(self.type_combo, 3, 1)

        number_label = QLabel("Номер отдела:")
        number_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(number_label, 4, 0)

        self.department_number_edit = QLineEdit()
        self.department_number_edit.setPlaceholderText("Введите номер отдела")
        self.department_number_edit.setMinimumHeight(32)
        self.department_number_edit.setMaximumHeight(32)
        grid_layout.addWidget(self.department_number_edit, 4, 1)

        phone_label = QLabel("Телефон:")
        phone_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(phone_label, 5, 0)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+375 XX XXX-XX-XX")
        self.phone_edit.setMinimumHeight(32)
        self.phone_edit.setMaximumHeight(32)
        grid_layout.addWidget(self.phone_edit, 5, 1)

        head_label = QLabel("Руководитель:")
        head_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(head_label, 6, 0)

        self.head_combo = QComboBox()
        self.head_combo.setPlaceholderText("Выберите руководителя")
        self.head_combo.setMinimumHeight(32)
        self.head_combo.setMaximumHeight(32)
        grid_layout.addWidget(self.head_combo, 6, 1)

        group_box.setLayout(grid_layout)
        scroll_layout.addWidget(group_box)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        self.save_button = QPushButton("Сохранить")
        self.save_button.setObjectName("saveButton")
        self.save_button.setMinimumSize(120, 40)
        self.save_button.setMaximumSize(16777215, 40)
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover { background-color: #b8945a; }
            QPushButton:pressed { background-color: #a07d4a; }
        """)
        main_layout.addWidget(self.save_button)

        self.scroll_area = scroll_area
        self.scroll_content = scroll_content
        self.scroll_layout = scroll_layout
        self.group_box = group_box

    def _setup_window(self):
        if self.is_edit_mode:
            self.setWindowTitle("Редактировать отдел")
            if hasattr(self, 'title_label'):
                self.title_label.setText("Редактировать отдел")
        else:
            self.setWindowTitle("Добавить отдел")
            if hasattr(self, 'title_label'):
                self.title_label.setText("Новый отдел")

        self.resize(580, 499)

    # ==================== ЗАПОЛНЕНИЕ ====================

    def _populate_combos(self):
        """Заполняет комбобоксы данными."""

        # Организации
        if hasattr(self, 'organization_combo'):
            self.organization_combo.clear()
            self.organization_combo.addItem("Выберите организацию", None)
            for org in self.organizations:
                self.organization_combo.addItem(org.get('name', ''), org.get('id'))

        # Родительские отделы
        if hasattr(self, 'parent_department_combo'):
            self.parent_department_combo.clear()
            self.parent_department_combo.addItem("Нет (корневой отдел)", None)
            for dept in self.departments:
                if self.is_edit_mode and dept.get('id') == self.department_data.get('id'):
                    continue
                self.parent_department_combo.addItem(dept.get('name', ''), dept.get('id'))

        # ⚠️ ИЗМЕНЕНО: типы отделов — из реального списка (с сервера или fallback)
        if hasattr(self, 'type_combo'):
            self.type_combo.clear()
            self.type_combo.addItem("Выберите тип", None)
            for dept_type in self.department_types:
                self.type_combo.addItem(dept_type.get('name', ''), dept_type.get('id'))

        # Руководители
        self._fill_head_combo(self.employees)

    def _fill_head_combo(self, employees):
        """Заполнить комбобокс руководителя переданным списком сотрудников."""
        if not hasattr(self, 'head_combo'):
            return
        self.head_combo.clear()
        self.head_combo.addItem("Не выбран", None)
        for emp in employees or []:
            name = f"{emp.get('last_name', '')} {emp.get('first_name', '')} {emp.get('patronymic', '')}".strip()
            if not name:
                name = emp.get('name') or emp.get('full_name') or f"Сотрудник {emp.get('id')}"
            self.head_combo.addItem(name, emp.get('id'))

    def set_head_employees(self, employees):
        """
        Публичный метод: перезаполнить список руководителей.
        Нужен, когда сотрудников отдела подгружают ПОСЛЕ создания диалога
        (например, при смене организации в режиме add).
        """
        self.employees = employees or []
        current_head = self.head_combo.currentData() if hasattr(self, 'head_combo') else None
        self._fill_head_combo(self.employees)
        # восстановить выбор, если такой сотрудник есть в новом списке
        if current_head is not None and hasattr(self, 'head_combo'):
            idx = self.head_combo.findData(current_head)
            if idx >= 0:
                self.head_combo.setCurrentIndex(idx)

    def _populate_fields(self):
        """Заполняет поля данными отдела (поддерживает оба формата ключей)."""
        if not self.department_data:
            return
        d = self.department_data

        # Название
        if hasattr(self, 'name_edit'):
            self.name_edit.setText(d.get('name', ''))

        # Организация
        if hasattr(self, 'organization_combo'):
            org_id = d.get('organization_id')
            if org_id is not None:
                idx = self.organization_combo.findData(org_id)
                if idx < 0:
                    idx = self.organization_combo.findData(str(org_id))
                if idx >= 0:
                    self.organization_combo.setCurrentIndex(idx)

        # Родительский отдел
        if hasattr(self, 'parent_department_combo'):
            parent_id = d.get('parent_id')
            if parent_id is None:
                parent_id = d.get('parent_department_id')
            if parent_id is not None:
                idx = self.parent_department_combo.findData(parent_id)
                if idx < 0:
                    idx = self.parent_department_combo.findData(str(parent_id))
                if idx >= 0:
                    self.parent_department_combo.setCurrentIndex(idx)

        # Тип отдела
        if hasattr(self, 'type_combo'):
            type_id = d.get('department_type_id')
            if type_id is None:
                type_id = d.get('type_id')
            print(f"[DEBUG] department_dialog: department_type_id из server = {type_id!r}")
            if type_id is not None:
                idx = self.type_combo.findData(type_id)
                if idx < 0:
                    idx = self.type_combo.findData(str(type_id))
                if idx < 0:
                    # сервер мог вернуть строковое имя типа вместо id
                    type_name = d.get('department_type_name') or d.get('type_name')
                    if type_name:
                        idx = self.type_combo.findText(type_name)
                if idx >= 0:
                    self.type_combo.setCurrentIndex(idx)
                else:
                    print(f"[WARN] department_type_id={type_id!r} не найден в combo")

        # Номер
        if hasattr(self, 'department_number_edit'):
            number = d.get('number')
            if number is None:
                number = d.get('department_number', '')
            self.department_number_edit.setText(str(number) if number not in (None, '') else '')

        # Телефон
        if hasattr(self, 'phone_edit'):
            phone = d.get('phone_number') or d.get('phone') or ''
            self.phone_edit.setText(phone)

        # Руководитель
        if hasattr(self, 'head_combo'):
            head_id = d.get('head_employee_id')
            if head_id is None:
                head_id = d.get('head_id')
            print(f"[DEBUG] department_dialog: head_employee_id из server = {head_id!r}")
            if head_id is not None:
                idx = self.head_combo.findData(head_id)
                if idx < 0:
                    idx = self.head_combo.findData(str(head_id))
                if idx >= 0:
                    self.head_combo.setCurrentIndex(idx)
                else:
                    print(f"[WARN] head_employee_id={head_id!r} не найден в combo")

    def _connect_signals(self):
        if hasattr(self, 'save_button'):
            self.save_button.clicked.connect(self._on_save_clicked)

    def _on_save_clicked(self):
        errors = self.validate()
        if errors:
            error_text = "\n".join(errors)
            QMessageBox.warning(self, "Ошибка валидации",
                                f"Пожалуйста, исправьте следующие ошибки:\n\n{error_text}")
            return
        self.accept()

    # ==================== ДАННЫЕ ====================

    def get_data(self):
        data = {}
        if hasattr(self, 'name_edit'):
            data['name'] = self.name_edit.text().strip()
        if hasattr(self, 'organization_combo'):
            data['organization_id'] = self.organization_combo.currentData()
        if hasattr(self, 'parent_department_combo'):
            data['parent_id'] = self.parent_department_combo.currentData()
        if hasattr(self, 'type_combo'):
            data['department_type_id'] = self.type_combo.currentData()
        if hasattr(self, 'department_number_edit'):
            data['number'] = self.department_number_edit.text().strip() or None
        if hasattr(self, 'phone_edit'):
            data['phone_number'] = self.phone_edit.text().strip() or None
        if hasattr(self, 'head_combo'):
            data['head_employee_id'] = self.head_combo.currentData()
        if self.is_edit_mode and 'id' in self.department_data:
            data['id'] = self.department_data['id']
        return data

    def validate(self):
        errors = []
        if hasattr(self, 'name_edit'):
            if not self.name_edit.text().strip():
                errors.append("Название отдела обязательно для заполнения")
        if hasattr(self, 'organization_combo'):
            if self.organization_combo.currentData() is None:
                errors.append("Выберите организацию")
        if hasattr(self, 'type_combo'):
            if self.type_combo.currentData() is None:
                errors.append("Выберите тип отдела")
        return errors


def main():
    app = QApplication(sys.argv)

    test_organizations = [
        {"id": 1, "name": "ОАО МАЗ"},
        {"id": 2, "name": "ООО ТехноСервис"}
    ]
    test_departments = [
        {"id": 2, "name": "Отдел разработки"},
        {"id": 3, "name": "Бухгалтерия"}
    ]
    test_employees = [
        {"id": 1, "last_name": "Иванов", "first_name": "Иван"},
        {"id": 2, "last_name": "Петрова", "first_name": "Мария"},
    ]
    test_types = [
        {"id": 1, "name": "Управление"},
        {"id": 2, "name": "Отдел"},
        {"id": 3, "name": "Бюро"},
        {"id": 4, "name": "Сектор"},
        {"id": 5, "name": "Цех"},
    ]

    print("=== Тест: Создание нового отдела ===")
    dialog = DepartmentDialog(
        organizations=test_organizations,
        departments=test_departments,
        employees=test_employees,
        department_types=test_types,
    )
    if dialog.exec():
        print("Получены данные:", dialog.get_data())

    print("\n=== Тест: Редактирование отдела ===")
    test_data = {
        'id': 1,
        'name': 'Отдел разработки',
        'organization_id': 1,
        'parent_id': None,
        'department_type_id': 2,
        'number': 'DEV-001',
        'phone_number': '+375 29 123-45-67',
        'head_employee_id': 2,
    }
    dialog_edit = DepartmentDialog(
        department_data=test_data,
        organizations=test_organizations,
        departments=test_departments,
        employees=test_employees,
        department_types=test_types,
    )
    if dialog_edit.exec():
        print("Получены данные:", dialog_edit.get_data())

    sys.exit(0)


if __name__ == "__main__":
    main()