from PyQt6 import QtWidgets, QtCore, uic
import os
import sys


class EmailEditWindow(QtWidgets.QDialog):
    """Стильное окно редактирования email в стиле профиля"""

    email_updated = QtCore.pyqtSignal(str)

    def __init__(self, current_email="", parent=None):
        super().__init__(parent)

        # Загружаем UI из файла
        ui_path = os.path.join(os.path.dirname(__file__), "../../../ui/profile/user_data/email_edit_window.ui")
        uic.loadUi(ui_path, self)

        # Устанавливаем текущий email
        self.emailInput.setText(current_email)

        # Подключаем сигнал
        self.saveButton.clicked.connect(self.save_email)

        # Делаем окно модальным
        self.setModal(True)

    def save_email(self):
        email = self.emailInput.text().strip()

        # Простая проверка email, если он не пустой
        if email and '@' not in email:
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("Ошибка")
            msg_box.setText("Введите корректный email адрес (с @)")
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

        self.email_updated.emit(email)
        self.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Создаем окно с примерным email
    window = EmailEditWindow("user@example.com")


    # Подключаем сигнал для вывода в консоль
    def on_email_updated(email):
        print(f"Email обновлен: {email}")


    window.email_updated.connect(on_email_updated)

    # Показываем окно
    window.show()

    sys.exit(app.exec())