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
        """Применяет стили для чекбоксов с иконками темы."""
        from client.core.themes import get_manager
        from client.core.themes.icon_utils import icon_path

        _t = get_manager().current
        checked = icon_path("cb_checked", _t.ICON_COLOR)
        unchecked = icon_path("cb_unchecked", _t.ICON_COLOR)
        partial = icon_path("cb_partial", _t.ICON_COLOR)

        if hasattr(dialog, 'treeWidget'):
            checkbox_style = f"""
                QTreeWidget::indicator {{
                    width: 18px; height: 18px;
                }}
                QTreeWidget::indicator:unchecked {{
                    image: url({unchecked});
                }}
                QTreeWidget::indicator:checked {{
                    image: url({checked});
                }}
                QTreeWidget::indicator:indeterminate {{
                    image: url({partial});
                }}
            """
            current_style = dialog.treeWidget.styleSheet() or ""
            dialog.treeWidget.setStyleSheet(current_style + checkbox_style)

    @staticmethod
    def get_ui_path() -> str:
        """Определяет путь к UI файлу"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = base_dir
        for _ in range(4):
            root_dir = os.path.dirname(root_dir)
        return os.path.join(root_dir, "ui", "documents", "create", "employee_selection_dialog.ui")