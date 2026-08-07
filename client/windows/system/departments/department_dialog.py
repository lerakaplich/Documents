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

    def __init__(self, parent=None, department_data=None):
        """
        Инициализация диалога

        Args:
            parent: Родительский виджет
            department_data: Данные отдела для редактирования (dict)
        """
        super().__init__(parent)

        # Сохраняем данные отдела
        self.department_data = department_data or {}
        self.is_edit_mode = bool(self.department_data.get('id'))

        # Загружаем UI
        self._load_ui()

        # Настраиваем окно
        self._setup_window()

        # Заполняем тестовыми данными
        self._load_test_data()

        # Заполняем поля данными отдела
        self._populate_fields()

        # Подключаем сигналы
        self._connect_signals()

    def _load_ui(self):
        """Загружает UI из файла"""
        # Определяем путь к UI файлу
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '../../../ui/system/departments/department_dialog.ui')
        ui_path = os.path.normpath(ui_path)

        if os.path.exists(ui_path):
            try:
                uic.loadUi(ui_path, self)
                print(f"[DEBUG] UI файл успешно загружен: {ui_path}")
            except Exception as e:
                print(f"[ERROR] Ошибка загрузки UI: {e}")
                self._setup_fallback_ui()
        else:
            print(f"[ERROR] UI файл не найден: {ui_path}")
            self._setup_fallback_ui()

    def _setup_fallback_ui(self):
        """Создает UI программно, если файл .ui не найден"""
        from PyQt6.QtWidgets import (
            QVBoxLayout, QHBoxLayout, QGridLayout,
            QGroupBox, QLabel, QLineEdit, QComboBox,
            QPushButton, QScrollArea, QWidget
        )

        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Заголовок
        self.title_label = QLabel("Новый отдел")
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #1B232A; margin-bottom: 10px;")
        main_layout.addWidget(self.title_label)

        # ScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background-color: transparent;")

        # Контент скролла
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(5, 5, 15, 5)

        # GroupBox с информацией
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

        # GridLayout для полей
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(15, 15, 15, 15)
        grid_layout.setSpacing(10)

        # Название
        name_label = QLabel("Название *:")
        name_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(name_label, 0, 0)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите название отдела")
        self.name_edit.setMinimumHeight(32)
        self.name_edit.setMaximumHeight(32)
        grid_layout.addWidget(self.name_edit, 0, 1)

        # Организация
        org_label = QLabel("Организация *:")
        org_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(org_label, 1, 0)

        self.organization_combo = QComboBox()
        self.organization_combo.setPlaceholderText("Выберите организацию")
        self.organization_combo.setMinimumHeight(32)
        self.organization_combo.setMaximumHeight(32)
        grid_layout.addWidget(self.organization_combo, 1, 1)

        # Родительский отдел
        parent_label = QLabel("Родительский отдел:")
        parent_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(parent_label, 2, 0)

        self.parent_department_combo = QComboBox()
        self.parent_department_combo.setPlaceholderText("Выберите родительский отдел")
        self.parent_department_combo.setMinimumHeight(32)
        self.parent_department_combo.setMaximumHeight(32)
        grid_layout.addWidget(self.parent_department_combo, 2, 1)

        # Тип отдела
        type_label = QLabel("Тип отдела *:")
        type_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(type_label, 3, 0)

        self.type_combo = QComboBox()
        self.type_combo.setPlaceholderText("Выберите тип отдела")
        self.type_combo.setMinimumHeight(32)
        self.type_combo.setMaximumHeight(32)
        grid_layout.addWidget(self.type_combo, 3, 1)

        # Номер отдела
        number_label = QLabel("Номер отдела:")
        number_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(number_label, 4, 0)

        self.department_number_edit = QLineEdit()
        self.department_number_edit.setPlaceholderText("Введите номер отдела")
        self.department_number_edit.setMinimumHeight(32)
        self.department_number_edit.setMaximumHeight(32)
        grid_layout.addWidget(self.department_number_edit, 4, 1)

        # Телефон
        phone_label = QLabel("Телефон:")
        phone_label.setStyleSheet("color: #1B232A; font-weight: 500;")
        grid_layout.addWidget(phone_label, 5, 0)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+375 XX XXX-XX-XX")
        self.phone_edit.setMinimumHeight(32)
        self.phone_edit.setMaximumHeight(32)
        grid_layout.addWidget(self.phone_edit, 5, 1)

        # Руководитель
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

        # Кнопка сохранения
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
            QPushButton:hover {
                background-color: #b8945a;
            }
            QPushButton:pressed {
                background-color: #a07d4a;
            }
        """)
        main_layout.addWidget(self.save_button)

        # Сохраняем ссылки для удобства
        self.scroll_area = scroll_area
        self.scroll_content = scroll_content
        self.scroll_layout = scroll_layout
        self.group_box = group_box

    def _setup_window(self):
        """Настраивает окно диалога"""
        # Устанавливаем заголовок
        if self.is_edit_mode:
            self.setWindowTitle("Редактировать отдел")
            if hasattr(self, 'title_label'):
                self.title_label.setText("Редактировать отдел")
        else:
            self.setWindowTitle("Добавить отдел")
            if hasattr(self, 'title_label'):
                self.title_label.setText("Новый отдел")

        # Устанавливаем размер
        self.resize(580, 499)

    def _load_test_data(self):
        """Загружает тестовые данные для комбобоксов"""
        # Тестовые организации
        organizations = [
            {"id": 1, "name": "ООО Телематика"},
            {"id": 2, "name": "ООО ТехноСервис"},
            {"id": 3, "name": "ОАО СтройИнвест"}
        ]

        # Заполняем комбобокс организаций
        if hasattr(self, 'organization_combo'):
            self.organization_combo.clear()
            for org in organizations:
                self.organization_combo.addItem(org['name'], org['id'])

        # Тестовые отделы для родительского отдела
        departments = [
            {"id": 1, "name": "Администрация"},
            {"id": 2, "name": "Бухгалтерия"},
            {"id": 3, "name": "Отдел разработки"},
            {"id": 4, "name": "Отдел продаж"}
        ]

        # Заполняем комбобокс родительских отделов
        if hasattr(self, 'parent_department_combo'):
            self.parent_department_combo.clear()
            self.parent_department_combo.addItem("Нет (корневой отдел)", None)
            for dept in departments:
                self.parent_department_combo.addItem(dept['name'], dept['id'])

        # Тестовые типы отделов
        department_types = [
            {"id": 1, "name": "Административный"},
            {"id": 2, "name": "Производственный"},
            {"id": 3, "name": "Финансовый"},
            {"id": 4, "name": "Кадровый"}
        ]

        # Заполняем комбобокс типов
        if hasattr(self, 'type_combo'):
            self.type_combo.clear()
            for dept_type in department_types:
                self.type_combo.addItem(dept_type['name'], dept_type['id'])

        # Тестовые руководители
        employees = [
            {"id": 1, "name": "Иванов Иван Иванович"},
            {"id": 2, "name": "Петрова Мария Сергеевна"},
            {"id": 3, "name": "Сидоров Алексей Петрович"},
            {"id": 4, "name": "Козлова Елена Викторовна"}
        ]

        # Заполняем комбобокс руководителей
        if hasattr(self, 'head_combo'):
            self.head_combo.clear()
            self.head_combo.addItem("Не выбран", None)
            for emp in employees:
                self.head_combo.addItem(emp['name'], emp['id'])

    def _populate_fields(self):
        """Заполняет поля данными отдела (для режима редактирования)"""
        if not self.department_data:
            return

        # Название
        if hasattr(self, 'name_edit'):
            self.name_edit.setText(self.department_data.get('name', ''))

        # Организация
        if hasattr(self, 'organization_combo'):
            org_id = self.department_data.get('organization_id')
            if org_id is not None:
                index = self.organization_combo.findData(org_id)
                if index >= 0:
                    self.organization_combo.setCurrentIndex(index)

        # Родительский отдел
        if hasattr(self, 'parent_department_combo'):
            parent_id = self.department_data.get('parent_department_id')
            if parent_id is not None:
                index = self.parent_department_combo.findData(parent_id)
                if index >= 0:
                    self.parent_department_combo.setCurrentIndex(index)

        # Тип отдела
        if hasattr(self, 'type_combo'):
            type_id = self.department_data.get('type_id')
            if type_id is not None:
                index = self.type_combo.findData(type_id)
                if index >= 0:
                    self.type_combo.setCurrentIndex(index)

        # Номер отдела
        if hasattr(self, 'department_number_edit'):
            self.department_number_edit.setText(self.department_data.get('department_number', ''))

        # Телефон
        if hasattr(self, 'phone_edit'):
            self.phone_edit.setText(self.department_data.get('phone', ''))

        # Руководитель
        if hasattr(self, 'head_combo'):
            head_id = self.department_data.get('head_id')
            if head_id is not None:
                index = self.head_combo.findData(head_id)
                if index >= 0:
                    self.head_combo.setCurrentIndex(index)

    def _connect_signals(self):
        """Подключает сигналы"""
        if hasattr(self, 'save_button'):
            self.save_button.clicked.connect(self._on_save_clicked)

    def _on_save_clicked(self):
        """Обработчик нажатия кнопки Сохранить"""
        # Валидация
        errors = self.validate()

        if errors:
            error_text = "\n".join(errors)
            QMessageBox.warning(self, "Ошибка валидации", f"Пожалуйста, исправьте следующие ошибки:\n\n{error_text}")
            return

        # Получаем данные
        data = self.get_data()

        # Сохраняем и закрываем
        self.accept()

    def get_data(self):
        """
        Возвращает данные из формы

        Returns:
            dict: Данные отдела
        """
        data = {}

        # Основные поля
        if hasattr(self, 'name_edit'):
            data['name'] = self.name_edit.text().strip()

        if hasattr(self, 'organization_combo'):
            data['organization_id'] = self.organization_combo.currentData()

        if hasattr(self, 'parent_department_combo'):
            data['parent_department_id'] = self.parent_department_combo.currentData()

        if hasattr(self, 'type_combo'):
            data['type_id'] = self.type_combo.currentData()

        if hasattr(self, 'department_number_edit'):
            data['department_number'] = self.department_number_edit.text().strip()

        if hasattr(self, 'phone_edit'):
            data['phone'] = self.phone_edit.text().strip()

        if hasattr(self, 'head_combo'):
            data['head_id'] = self.head_combo.currentData()

        # Если это редактирование, добавляем ID
        if self.is_edit_mode and 'id' in self.department_data:
            data['id'] = self.department_data['id']

        return data

    def validate(self):
        """
        Валидация данных

        Returns:
            list: Список ошибок
        """
        errors = []

        # Проверяем название
        if hasattr(self, 'name_edit'):
            name = self.name_edit.text().strip()
            if not name:
                errors.append("Название отдела обязательно для заполнения")

        # Проверяем организацию
        if hasattr(self, 'organization_combo'):
            org_id = self.organization_combo.currentData()
            if org_id is None:
                errors.append("Выберите организацию")

        # Проверяем тип отдела
        if hasattr(self, 'type_combo'):
            type_id = self.type_combo.currentData()
            if type_id is None:
                errors.append("Выберите тип отдела")

        return errors


def main():
    """Точка входа для тестирования диалога"""
    app = QApplication(sys.argv)

    # Тест: создание нового отдела
    print("=== Тест: Создание нового отдела ===")
    dialog = DepartmentDialog()
    if dialog.exec():
        print("Получены данные:", dialog.get_data())
    else:
        print("Отмена")

    # Тест: редактирование существующего отдела
    print("\n=== Тест: Редактирование отдела ===")
    test_data = {
        'id': 1,
        'name': 'Отдел разработки',
        'organization_id': 1,
        'parent_department_id': 1,
        'type_id': 2,
        'department_number': 'DEV-001',
        'phone': '+375 29 123-45-67',
        'head_id': 3
    }

    dialog_edit = DepartmentDialog(department_data=test_data)
    if dialog_edit.exec():
        print("Получены данные:", dialog_edit.get_data())
    else:
        print("Отмена")

    sys.exit(0)


if __name__ == "__main__":
    main()