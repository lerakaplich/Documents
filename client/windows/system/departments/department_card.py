# department_card.py
import sys
from PyQt6.QtWidgets import QApplication, QFrame, QVBoxLayout, QWidget, QSizePolicy
from PyQt6.uic import loadUi
from PyQt6.QtCore import pyqtSignal, Qt
import os

from client.core.themes import apply_theme_to_widget


class DepartmentCard(QFrame):
    """Карточка отдела на основе загруженного UI файла"""

    # Сигналы для взаимодействия с главным окном
    edit_clicked = pyqtSignal(dict)  # Передаем данные отдела
    delete_clicked = pyqtSignal(int)  # Передаем ID отдела

    def __init__(self, department_data=None, parent=None):
        super().__init__(parent)

        # Устанавливаем фиксированную высоту для предотвращения "скамкивания"
        self.setMinimumHeight(150)
        self.setMaximumHeight(150)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed  # Фиксированная высота
        )

        # Загружаем UI дизайн
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)
            apply_theme_to_widget(self)
        else:
            print(f"UI файл не найден: {ui_path}")
            # Создаем заглушку, если файл не найден
            self.setup_placeholder()

        # Сохраняем данные отдела
        self.department_data = department_data or {}
        self.department_id = self.department_data.get('id', 0)

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
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'departments', 'department_card.ui')

        return os.path.normpath(ui_path)

    def setup_card(self):
        """Заполняет карточку данными"""
        if not self.department_data:
            return

        # Заполняем все поля из UI
        if hasattr(self, 'nameLabel'):
            self.nameLabel.setText(self.department_data.get('name', 'Название не указано'))

        if hasattr(self, 'typeLabel'):
            department_type = self.department_data.get('type', '')
            self.typeLabel.setText(f"Тип: {department_type}" if department_type else "Тип: Не указан")

        if hasattr(self, 'leaderLabel'):
            leader = self.department_data.get('leader', '')
            self.leaderLabel.setText(f"Руководитель: {leader}" if leader else "Руководитель: Не назначен")

        if hasattr(self, 'descriptionLabel'):
            description = self.department_data.get('description', '')
            self.descriptionLabel.setText(description if description else "Описание отсутствует")

        if hasattr(self, 'phoneLabel'):
            phone = self.department_data.get('phone', '')
            self.phoneLabel.setText(phone if phone else "Телефон не указан")

        if hasattr(self, 'numberLabel'):
            code = self.department_data.get('code', '')
            self.numberLabel.setText(f"Код подразделения: {code}" if code else "Код подразделения: ---")

    def on_edit_clicked(self):
        """Обработчик кнопки редактирования"""
        self.edit_clicked.emit(self.department_data)

    def on_delete_clicked(self):
        """Обработчик кнопки удаления"""
        self.delete_clicked.emit(self.department_id)

    def update_data(self, new_data):
        """Обновляет данные карточки"""
        self.department_data.update(new_data)
        self.setup_card()

    def setup_placeholder(self):
        """Создает простую версию карточки, если UI не найден"""
        layout = QVBoxLayout(self)
        from PyQt6.QtWidgets import QLabel, QPushButton

        label = QLabel("Department Card (UI not found)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self.editBtn = QPushButton("Edit")
        self.deleteBtn = QPushButton("Delete")
        layout.addWidget(self.editBtn)
        layout.addWidget(self.deleteBtn)

        self.editBtn.clicked.connect(self.on_edit_clicked)
        self.deleteBtn.clicked.connect(self.on_delete_clicked)


# Точка входа для тестирования карточки
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Тест отдельной карточки
    test_data = {
        'id': 1,
        'name': 'Отдел разработки и исследований',
        'type': 'Функциональное подразделение',
        'leader': 'Петров Сергей Алексеевич',
        'description': 'Разработка нового ПО и сопровождение существующих систем',
        'phone': '+375 29 987-65-43',
        'code': 'RND-001'
    }

    card = DepartmentCard(test_data)
    card.setWindowTitle("Тест карточки отдела")
    card.edit_clicked.connect(lambda data: print(f"Редактировать: {data['name']}"))
    card.delete_clicked.connect(lambda dept_id: print(f"Удалить ID: {dept_id}"))
    card.show()

    sys.exit(app.exec())