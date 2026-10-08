# client/windows/system/departments/department_type_dialog.py

"""
Диалог создания/редактирования типа отдела (Цех, Управление, Бюро, ...).
UI загружается из ui/system/departments/department_type_dialog.ui
"""

import os
import sys

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from client.core.themes import apply_theme_to_widget


class DepartmentTypeDialog(QDialog):
    def __init__(self, parent=None, item=None):
        super().__init__(parent)
        self.item = dict(item) if item else {}

        self._load_ui()
        self._setup_window()
        self._populate_fields()
        self.saveButton.clicked.connect(self._on_save_clicked)

    def _load_ui(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.normpath(
            os.path.join(current_dir, "..", "..", "..", "ui", "system", "departments", "department_type_dialog.ui")
        )
        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI файл не найден: {ui_path}")

        uic.loadUi(ui_path, self)
        apply_theme_to_widget(self)

    def _setup_window(self):
        is_edit = self.item.get("id") is not None
        self.setWindowTitle("Редактировать тип отдела" if is_edit else "Новый тип отдела")
        self.titleLabel.setText("Редактировать тип отдела" if is_edit else "Новый тип отдела")
        self.nameEdit.setFocus()

    def _populate_fields(self):
        self.nameEdit.setText(self.item.get("name") or "")

    def reapply_theme(self):
        """Переприменить тему после set_theme()."""
        apply_theme_to_widget(self)

    def validate(self):
        errors = []
        if not self.nameEdit.text().strip():
            errors.append("Название типа отдела обязательно для заполнения")
        return errors

    def _on_save_clicked(self):
        errors = self.validate()
        if errors:
            QMessageBox.warning(self, "Ошибка валидации", "\n".join(errors))
            self.nameEdit.setFocus()
            return
        self.accept()

    def get_data(self):
        data = {"name": self.nameEdit.text().strip()}
        if self.item.get("id") is not None:
            data["id"] = self.item["id"]
        return data


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = DepartmentTypeDialog()
    if dialog.exec():
        print("Результат:", dialog.get_data())
    sys.exit(0)