# organization_card.py
import sys
import os
from PyQt6.QtWidgets import QApplication, QFrame, QVBoxLayout, QWidget
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.uic import loadUi


class OrganizationCard(QFrame):
    """Карточка организации на основе загруженного UI файла"""

    # Сигналы для взаимодействия с главным окном
    edit_clicked = pyqtSignal(dict)  # Передаем данные организации
    delete_clicked = pyqtSignal(int)  # Передаем ID организации

    def __init__(self, organization_data=None, parent=None):
        super().__init__(parent)

        # Загружаем UI дизайн
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)
        else:
            raise FileNotFoundError(f"UI файл не найден: {ui_path}")

        # Сохраняем данные
        self.organization_data = organization_data or {}
        self.organization_id = self.organization_data.get('id', 0)

        # Настраиваем карточку
        self.setup_card()

        # Подключаем сигналы кнопок
        if hasattr(self, 'editBtn'):
            self.editBtn.clicked.connect(self.on_edit_clicked)
        if hasattr(self, 'deleteBtn'):
            self.deleteBtn.clicked.connect(self.on_delete_clicked)

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        # Путь относительно текущего файла
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Поднимаемся на уровень выше до client/windows/system/organisations/
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'organisations', 'organization_card.ui')
        return os.path.normpath(ui_path)

    def setup_card(self):
        """Заполняет карточку данными"""
        if not self.organization_data:
            return

        # Заполняем название организации
        if hasattr(self, 'nameLabel'):
            name = self.organization_data.get('name', '')
            self.nameLabel.setText(name if name else 'Название не указано')

        # Заполняем УНП
        if hasattr(self, 'unpLabel'):
            unp = self.organization_data.get('unp', '')
            self.unpLabel.setText(f"УНП: {unp}" if unp else "УНП: не указан")

        # Заполняем адрес
        if hasattr(self, 'addressLabel'):
            address = self.organization_data.get('address', '')
            self.addressLabel.setText(address if address else "Адрес не указан")

        # Заполняем телефон
        if hasattr(self, 'phoneLabel'):
            phone = self.organization_data.get('phone', '')
            self.phoneLabel.setText(phone if phone else "Телефон не указан")

        # Заполняем email
        if hasattr(self, 'emailLabel'):
            email = self.organization_data.get('email', '')
            self.emailLabel.setText(email if email else "Email не указан")

        # Заполняем директора
        if hasattr(self, 'directorLabel'):
            director = self.organization_data.get('director', '')
            self.directorLabel.setText(f"Директор: {director}" if director else "Директор: не назначен")

    def on_edit_clicked(self):
        """Обработчик кнопки редактирования"""
        self.edit_clicked.emit(self.organization_data)

    def on_delete_clicked(self):
        """Обработчик кнопки удаления"""
        self.delete_clicked.emit(self.organization_id)

    def update_data(self, new_data):
        """Обновляет данные карточки"""
        self.organization_data.update(new_data)
        self.setup_card()

    def get_data(self):
        """Возвращает данные организации"""
        return self.organization_data



# Точка входа для тестирования
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Тест отдельной карточки
    test_data = {
        'id': 1,
        'name': 'ОАО "МАЗ" - Минский автомобильный завод',
        'unp': '100123456',
        'address': 'г. Минск, ул. Социалистическая, 42',
        'phone': '+375 17 276-20-20',
        'email': 'info@maz.by',
        'director': 'Иванов И.И.'
    }

    # Создаем и показываем карточку
    card = OrganizationCard(test_data)
    card.setWindowTitle("Тест карточки организации")
    card.edit_clicked.connect(lambda data: print(f"Редактировать: {data['name']}"))
    card.delete_clicked.connect(lambda org_id: print(f"Удалить ID: {org_id}"))
    card.show()

    # Альтернативно, показать панель со всеми карточками
    # panel = OrganizationsPanel()
    # panel.setWindowTitle("Организации")
    # panel.resize(1000, 600)
    # panel.show()

    sys.exit(app.exec())