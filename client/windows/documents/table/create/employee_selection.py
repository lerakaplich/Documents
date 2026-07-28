import os
from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QFrame, QTreeWidget, QPushButton,
                             QLineEdit, QSpacerItem, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi


class EmployeeSelection:
    """UI компоненты диалога выбора сотрудников"""

    @staticmethod
    def load_ui(dialog: QDialog, ui_path: str) -> bool:
        """Загружает UI из файла"""
        if os.path.exists(ui_path):
            loadUi(ui_path, dialog)
            return True
        return False


    @staticmethod
    def apply_checkbox_styles(dialog: QDialog, root_dir: str):
        """Применяет стили для чекбоксов с иконками"""
        images_dir = os.path.join(root_dir, "icons").replace("\\", "/")

        if hasattr(dialog, 'treeWidget'):


            # Добавляем стили для чекбоксов
            checkbox_style = f"""
                QTreeWidget::indicator {{
                    width: 18px;
                    height: 18px;
                }}
                QTreeWidget::indicator:unchecked {{
                    image: url('{images_dir}/cb_unchecked.png');
                }}
                QTreeWidget::indicator:checked {{
                    image: url('{images_dir}/cb_checked.png');
                }}
                QTreeWidget::indicator:indeterminate {{
                    image: url('{images_dir}/cb_partial.png');
                }}
            """

            # Если есть существующий стиль, добавляем к нему
            current_style = dialog.treeWidget.styleSheet() or ""
            if current_style:
                dialog.treeWidget.setStyleSheet(current_style + checkbox_style)
            else:
                dialog.treeWidget.setStyleSheet(checkbox_style)

    @staticmethod
    def get_ui_path() -> str:
        """Определяет путь к UI файлу"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = base_dir
        for _ in range(4):
            root_dir = os.path.dirname(root_dir)
        return os.path.join(root_dir, "ui", "documents", "create", "employee_selection_dialog.ui")