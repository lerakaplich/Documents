from PyQt6 import QtWidgets, QtCore, uic
import os
import sys

from client.core.themes import get_manager, get_message_box_style


class EmailEditWindow(QtWidgets.QDialog):
    """Окно редактирования email в стиле PeriodDialog."""

    email_updated = QtCore.pyqtSignal(str)

    def __init__(self, current_email="", parent=None):
        super().__init__(parent)

        ui_path = os.path.join(
            os.path.dirname(__file__),
            "../../../ui/settings/user_data/email_edit_window.ui",
        )
        uic.loadUi(ui_path, self)

        self._apply_styles()

        self.emailInput.setText(current_email)

        self.saveButton.clicked.connect(self.save_email)
        self.setModal(True)

    # ─────────── Стили (как в PeriodDialog) ───────────

    def _apply_styles(self):
        t = get_manager().current

        self.setStyleSheet(f"QDialog {{ background-color: {t.BG_DIALOG}; }}")

        self.titleLabel.setStyleSheet(
            f"color: {t.TEXT_PRIMARY}; font-size: 20px; font-weight: bold; "
            f"background: transparent; padding: 0 0 4px 0;"
        )

        self.emailInput.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {t.BORDER_DEFAULT};
                border-radius: 6px;
                padding: 6px 10px;
                background-color: {t.BG_INPUT};
                color: {t.TEXT_PRIMARY};
                font-size: 14px;
                min-height: 26px;
            }}
            QLineEdit:hover {{
                border-color: {t.ACCENT_PRIMARY};
            }}
            QLineEdit:focus {{
                border: 2px solid {t.ACCENT_PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {t.TEXT_TERTIARY};
            }}
        """)

        self.saveButton.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.ACCENT_PRIMARY};
                color: {t.TEXT_ON_ACCENT};
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                padding: 0 20px;
                min-height: 42px;
            }}
            QPushButton:hover {{
                background-color: {t.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {t.ACCENT_PRESSED};
            }}
        """)

    def reapply_theme(self):
        self._apply_styles()

    # ─────────── Логика ───────────

    def save_email(self):
        email = self.emailInput.text().strip()

        if email and '@' not in email:
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("Ошибка")
            msg_box.setText("Введите корректный email адрес (с @)")
            msg_box.setStyleSheet(get_message_box_style())
            msg_box.exec()
            return

        self.email_updated.emit(email)
        self.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = EmailEditWindow("user@example.com")
    window.email_updated.connect(lambda e: print(f"Email обновлен: {e}"))
    window.show()
    sys.exit(app.exec())