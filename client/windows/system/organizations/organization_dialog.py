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
        self.btnSave.clicked.connect(self.save_organization)
        self.lineEditUNP.setFocus()

    def save_organization(self):
        print("Сохранение организации...")

        data = {
            'unp': self.lineEditUNP.text().strip(),
            'smdo_code': self.lineEditSmdoCode.text().strip(),
            'name': self.lineEditName.text().strip(),
            'phone': self.lineEditPhone.text().strip(),
            'address': self.lineEditAddress.text().strip(),
            'email': self.lineEditEmail.text().strip(),
            'is_subscriber': self.checkBoxSubscriber.isChecked()
        }

        print(f"Данные: {data}")
        self.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    dialog = OrganizationDialog()
    dialog.show()

    sys.exit(app.exec())