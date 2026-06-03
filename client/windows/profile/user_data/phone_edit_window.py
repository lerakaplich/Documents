from PyQt6 import QtWidgets, QtCore, uic
import os
import sys


class PhoneEditWindow(QtWidgets.QDialog):
    """Стильное окно редактирования телефона в стиле профиля"""

    phone_updated = QtCore.pyqtSignal(str)

    def __init__(self, current_phone="", parent=None):
        super().__init__(parent)

        # Загружаем UI из файла
        ui_path = os.path.join(os.path.dirname(__file__), "../../../ui/profile/user_data/phone_edit_window.ui")
        uic.loadUi(ui_path, self)

        # Убираем знак + если есть
        display_phone = current_phone.lstrip("+") if current_phone else ""

        # Устанавливаем текущий номер
        self.phoneInput.setText(display_phone)

        # Подключаем сигнал
        self.saveButton.clicked.connect(self.save_phone)

        # Делаем окно модальным
        self.setModal(True)

    def save_phone(self):
        raw_phone = self.phoneInput.text()
        cleaned = "".join(filter(str.isdigit, raw_phone))

        if len(cleaned) != 12:
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("Ошибка")
            msg_box.setText("Номер телефона должен содержать ровно 12 цифр")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                    color: black;
                }
                QMessageBox QLabel {
                    color: black;
                    background-color: transparent;
                }
                QMessageBox QPushButton {
                    color: black;
                }
            """)
            msg_box.exec()
            return

        self.phone_updated.emit(cleaned)
        self.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Создаем окно с примерным номером телефона
    window = PhoneEditWindow("375123456789")


    # Подключаем сигнал для вывода в консоль
    def on_phone_updated(phone):
        print(f"Телефон обновлен: +{phone}")


    window.phone_updated.connect(on_phone_updated)

    # Показываем окно
    window.show()

    sys.exit(app.exec())