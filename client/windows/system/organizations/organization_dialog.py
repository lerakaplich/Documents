# client/windows/system/organizations/organization_dialog.py

import os
import sys
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox


def load_ui(ui_filename):
    """Загружает UI файл из стандартной структуры папок"""
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Формируем путь к UI файлу
    ui_path = os.path.join(
        current_dir, '..', '..', '..', 'ui', 'system', 'organizations', ui_filename
    )
    ui_path = os.path.normpath(ui_path)

    if not os.path.exists(ui_path):
        raise FileNotFoundError(f"UI файл не найден: {ui_path}")

    return ui_path


import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog


class OrganizationDialog(QDialog):
    def __init__(self, parent=None, item=None):
        super().__init__(parent)

        self.item = item if item is not None else {}

        # Загружаем UI
        ui_path = self.get_ui_path()
        uic.loadUi(ui_path, self)

        # Устанавливаем иконки программно
        self.setup_icons()
        self.setup_ui()
        self.load_data()

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(
            current_dir, '..', '..', '..', 'ui', 'system', 'organizations', 'organization_dialog.ui'
        )
        return os.path.normpath(ui_path)

    def setup_icons(self):
        """Устанавливает иконки для чекбокса программно"""
        if hasattr(self, 'smdoSubscriberCheckbox'):
            # Получаем путь к папке с иконками
            current_dir = os.path.dirname(os.path.abspath(__file__))
            icons_dir = os.path.normpath(os.path.join(current_dir, '..', '..', '..', 'icons'))

            # Формируем пути к иконкам с прямыми слешами для CSS
            unchecked_path = os.path.join(icons_dir, 'cb_unchecked.svg').replace('\\', '/')
            checked_path = os.path.join(icons_dir, 'cb_checked.svg').replace('\\', '/')

            # Устанавливаем стили программно
            self.smdoSubscriberCheckbox.setStyleSheet(f"""
                QCheckBox {{
                    color: #1B232A;
                    spacing: 8px;
                    font-size: 13px;
                    background: transparent;
                }}

                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    image: url({unchecked_path});
                }}

                QCheckBox::indicator:checked {{
                    image: url({checked_path});
                }}
            """)

    def setup_ui(self):
        """Настройка UI"""
        # Подключаем сигналы
        if hasattr(self, 'saveButton'):
            self.saveButton.clicked.connect(self.save_organization)

        # Устанавливаем фокус на первое поле
        if hasattr(self, 'fullNameEdit'):
            self.fullNameEdit.setFocus()

        # Дополнительные настройки для поля УНП (только цифры)
        if hasattr(self, 'unpEdit'):
            self.unpEdit.textChanged.connect(self.validate_unp)

        # Настройка заголовка
        is_edit = self.item.get('id') is not None
        self.setWindowTitle("Редактировать организацию" if is_edit else "Добавить организацию")

        if hasattr(self, 'titleLabel'):
            self.titleLabel.setText("Редактировать организацию" if is_edit else "Новая организация")

    # client/windows/system/organizations/organization_dialog.py

    # client/windows/system/organizations/organization_dialog.py

    def load_data(self):
        """Загружает данные в поля"""
        if not self.item:
            return

        print(f"[DEBUG] Загрузка данных в диалог: {self.item}")

        # Полное наименование
        full_name = (
                self.item.get('full_name') or
                self.item.get('fullName') or
                self.item.get('name') or
                ''
        )
        if hasattr(self, 'fullNameEdit'):
            self.fullNameEdit.setText(full_name)
            print(f"[DEBUG] fullNameEdit установлен: {full_name}")

        # Краткое наименование
        short_name = (
                self.item.get('short_name') or
                self.item.get('shortName') or
                ''
        )
        if hasattr(self, 'shortNameEdit'):
            self.shortNameEdit.setText(short_name)

        # УНП
        unp = self.item.get('unp') or ''
        if hasattr(self, 'unpEdit'):
            self.unpEdit.setText(unp)

        # Адрес
        address = self.item.get('address') or ''
        if hasattr(self, 'addressEdit'):
            self.addressEdit.setText(address)

        # ТЕЛЕФОН - ПРОВЕРЯЕМ ВСЕ ВАРИАНТЫ
        phone = self.item.get('phone')
        if phone is None or phone == '':
            phone = self.item.get('phone_number')
        if phone is None or phone == '':
            phone = self.item.get('phoneNumber')
        if phone is None:
            phone = ''

        # Принудительно преобразуем в строку
        phone = str(phone) if phone else ''

        if hasattr(self, 'phoneEdit'):
            self.phoneEdit.setText(phone)
            print(f"[DEBUG] phoneEdit установлен: '{phone}' (тип: {type(phone)})")
        else:
            print("[WARNING] phoneEdit не найден в UI!")

        # Email
        email = self.item.get('email') or ''
        if hasattr(self, 'emailEdit'):
            self.emailEdit.setText(email)

        # Директор
        director = (
                self.item.get('director') or
                self.item.get('director_name') or
                ''
        )
        if hasattr(self, 'directorEdit'):
            self.directorEdit.setText(director)

        # Код СМДО
        smdo_code = self.item.get('smdo_code') or ''
        if hasattr(self, 'smdoCodeEdit'):
            self.smdoCodeEdit.setText(smdo_code)

        # Подписчик СМДО
        is_subscriber = self.item.get('is_subscriber', False)
        if hasattr(self, 'smdoSubscriberCheckbox'):
            self.smdoSubscriberCheckbox.setChecked(is_subscriber)

        print(f"[DEBUG] Загрузка данных завершена")

    def validate_unp(self, text):
        """Ограничиваем ввод только цифрами для поля УНП"""
        # Убираем всё, кроме цифр
        digits_only = ''.join(filter(str.isdigit, text))
        if text != digits_only:
            self.unpEdit.setText(digits_only)

    def save_organization(self):
        """Сохранение организации"""
        # Собираем данные из полей
        data = {}

        if hasattr(self, 'fullNameEdit'):
            data['full_name'] = self.fullNameEdit.text().strip()

        if hasattr(self, 'shortNameEdit'):
            data['short_name'] = self.shortNameEdit.text().strip()

        if hasattr(self, 'unpEdit'):
            data['unp'] = self.unpEdit.text().strip()

        if hasattr(self, 'addressEdit'):
            data['address'] = self.addressEdit.text().strip()

        # Телефон - сохраняем и как phone и как phone_number
        if hasattr(self, 'phoneEdit'):
            phone = self.phoneEdit.text().strip()
            data['phone'] = phone
            data['phone_number'] = phone if phone else None  # Если пусто, отправляем None

        if hasattr(self, 'emailEdit'):
            data['email'] = self.emailEdit.text().strip()

        if hasattr(self, 'directorEdit'):
            data['director'] = self.directorEdit.text().strip()

        if hasattr(self, 'smdoCodeEdit'):
            data['smdo_code'] = self.smdoCodeEdit.text().strip()

        if hasattr(self, 'smdoSubscriberCheckbox'):
            data['is_subscriber'] = self.smdoSubscriberCheckbox.isChecked()

        # Проверяем обязательные поля
        full_name = data.get('full_name', '')
        if not full_name:
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Полное наименование обязательно для заполнения."
            )
            if hasattr(self, 'fullNameEdit'):
                self.fullNameEdit.setFocus()
                self.fullNameEdit.setStyleSheet("border: 2px solid #D22730; border-radius: 6px; padding: 8px;")
            return

        # Сохраняем в item (сохраняем все поля для совместимости)
        self.item.update(data)

        # Также сохраняем имя в поле name для совместимости с сервером
        if 'full_name' in data and data['full_name']:
            self.item['name'] = data['full_name']

        # Сохраняем телефон в phone_number для сервера
        if 'phone' in data:
            self.item['phone_number'] = data['phone'] if data['phone'] else None

        print(f"[DEBUG] Сохранение организации: {data}")

        # Закрываем диалог
        self.accept()

    def get_data(self):
        """Возвращает данные организации"""
        return self.item


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Тест с данными для редактирования
    test_data = {
        'id': 1,
        'full_name': 'ОАО "МАЗ" - Минский автомобильный завод',
        'short_name': 'ОАО "МАЗ"',
        'unp': '100123456',
        'address': 'г. Минск, ул. Социалистическая, 42',
        'phone': '+375 17 276-20-20',
        'email': 'info@maz.by',
        'director': 'Иванов И.И.',
        'smdo_code': 'MAZ_001',
        'is_subscriber': True
    }

    dialog = OrganizationDialog(item=test_data)
    if dialog.exec():
        print("Результат:", dialog.get_data())

    sys.exit(app.exec())