import os
import sys
from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QDialog


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


class OrganizationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        try:
            # Загружаем UI
            ui_path = load_ui('organization_dialog.ui')
            uic.loadUi(ui_path, self)
        except Exception as e:
            print(f"Ошибка загрузки UI: {e}")
            raise

        # Настройка интерфейса
        self.setup_ui()

    def setup_ui(self):
        # Подключаем сигналы
        self.saveButton.clicked.connect(self.save_organization)

        # Устанавливаем фокус на первое поле
        self.fullNameEdit.setFocus()

        # Дополнительные настройки для поля УНП (только цифры)
        self.unpEdit.textChanged.connect(self.validate_unp)

    def validate_unp(self, text):
        """Ограничиваем ввод только цифрами для поля УНП"""
        # Убираем всё, кроме цифр
        digits_only = ''.join(filter(str.isdigit, text))
        if text != digits_only:
            self.unpEdit.setText(digits_only)

    def save_organization(self):
        """Сохранение организации"""
        print("Сохранение организации...")

        # Собираем данные из полей
        data = {
            'full_name': self.fullNameEdit.text().strip(),
            'phone': self.phoneEdit.text().strip(),
            'address': self.addressEdit.text().strip(),
            'email': self.emailEdit.text().strip(),
            'unp': self.unpEdit.text().strip(),
            'smdo_code': self.smdoCodeEdit.text().strip(),
            'is_subscriber': self.smdoSubscriberCheckbox.isChecked()
        }

        # Проверяем обязательные поля
        if not data['full_name']:
            print("Ошибка: Полное наименование обязательно для заполнения")
            self.fullNameEdit.setFocus()
            self.fullNameEdit.setStyleSheet("border: 2px solid #D22730; border-radius: 6px; padding: 8px;")
            return

        print(f"Данные: {data}")

        # Здесь можно добавить логику сохранения в БД

        # Закрываем диалог с успехом
        self.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    dialog = OrganizationDialog()
    dialog.show()

    sys.exit(app.exec())