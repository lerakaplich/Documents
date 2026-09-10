# client/windows/system/tags/tag_dialog.py

"""
Модуль диалогового окна для создания/редактирования хэштегов
"""
import os
import sys
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QColorDialog, QMessageBox, QApplication
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

from client.windows.system.tags.color_picker_dialog import ColorPickerDialog


class TagDialog(QDialog):
    """Диалог создания/редактирования хэштега"""

    # Сопоставление названий цветов из ComboBox с HEX-кодами
    COLOR_MAP = {
        'Золотой (#ccab6e)': '#ccab6e',
        'Красный (#D22730)': '#D22730',
        'Синий (#3498db)': '#3498db',
        'Зеленый (#2ecc71)': '#2ecc71',
        'Фиолетовый (#9b59b6)': '#9b59b6',
        'Оранжевый (#e67e22)': '#e67e22'
    }

    COLOR_REVERSE_MAP = {v: k for k, v in COLOR_MAP.items()}

    # Сопоставление приоритетов
    PRIORITY_MAP = {
        '1 - Без приоритета': 'normal',
        '2 - Средний приоритет': 'important',
        '3 - Критический приоритет': 'urgent'
    }

    PRIORITY_REVERSE_MAP = {v: k for k, v in PRIORITY_MAP.items()}

    def __init__(self, parent=None, tag_id: Optional[int] = None, tag_data: Optional[Dict] = None):
        """
        Инициализация диалога

        Args:
            parent: Родительский виджет
            tag_id: ID тега для редактирования (None для создания нового)
            tag_data: Данные тега для редактирования
        """
        super().__init__(parent)
        self.tag_id = tag_id
        self.tag_data = tag_data or {}

        self._load_ui()
        self._setup_connections()
        self._load_tag_data()

        # Установка заголовка
        if tag_id or tag_data:
            self.titleLabel.setText("Редактирование хэштега")
        else:
            self.titleLabel.setText("Новый хэштег")

    def _load_ui(self):
        """Загружает UI из .ui файла"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(
            current_dir, '..', '..', '..', 'ui', 'system', 'tags', 'tag_dialog.ui'
        )
        ui_path = os.path.normpath(ui_path)

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI file not found: {ui_path}")

        loadUi(ui_path, self)

    def _setup_connections(self):
        """Настраивает сигналы и слоты"""
        self.btnSave.clicked.connect(self._on_save)
        self.colorIndicator.mousePressEvent = self._on_color_indicator_click
        self.comboBoxColor.currentTextChanged.connect(self._on_color_changed)

    def _on_color_indicator_click(self, event):
        current_color = self._get_current_color()
        dialog = ColorPickerDialog(current_color=current_color, parent=self)
        if dialog.exec() == ColorPickerDialog.DialogCode.Accepted:
            new_color = dialog.get_selected_color()
            self._set_color(new_color)

    def _on_color_changed(self, text):
        if text in self.COLOR_MAP:
            hex_color = self.COLOR_MAP[text]
            self._update_color_indicator(hex_color)

    def _get_current_color(self) -> str:
        current_text = self.comboBoxColor.currentText()
        if current_text in self.COLOR_MAP:
            return self.COLOR_MAP[current_text]

        style = self.colorIndicator.styleSheet()
        if 'background-color:' in style:
            color_part = style.split('background-color:')[1].split(';')[0].strip()
            return color_part

        return '#ccab6e'

    def _set_color(self, hex_color: str):
        self._update_color_indicator(hex_color)

        if hex_color in self.COLOR_REVERSE_MAP:
            self.comboBoxColor.setCurrentText(self.COLOR_REVERSE_MAP[hex_color])
        else:
            self.comboBoxColor.setCurrentIndex(-1)

    def _update_color_indicator(self, hex_color: str):
        self.colorIndicator.setStyleSheet(f"""
            QFrame {{
                border-radius: 16px;
                background-color: {hex_color};
                border: 2px solid #E0E0E0;
            }}
            QFrame:hover {{
                border-color: {hex_color};
            }}
        """)

    def _load_tag_data(self):
        """Загружает данные тега для редактирования"""
        if not self.tag_data and not self.tag_id:
            return

        # Если переданы данные
        if self.tag_data:
            self._fill_form(self.tag_data)
            return

        # Если есть только ID, но нет данных - используем пустые значения
        # (данные будут загружены из API в TagsPage)
        if self.tag_id:
            # Заполняем заглушками - реальные данные будут переданы через tag_data
            pass

    def _fill_form(self, data: Dict[str, Any]):
        """Заполняет форму данными"""
        # Имя
        self.lineEditName.setText(data.get('name', ''))

        # Приоритет
        priority = data.get('priority', 'normal')
        priority_text = self.PRIORITY_REVERSE_MAP.get(priority, '1 - Без приоритета')
        self.comboBoxPriority.setCurrentText(priority_text)

        # Цвет
        color = data.get('color', '#ccab6e')
        self._set_color(color)

    def _validate_input(self) -> bool:
        name = self.lineEditName.text().strip()

        if not name:
            QMessageBox.warning(self, "Ошибка валидации", "Название хэштега обязательно для заполнения")
            self.lineEditName.setFocus()
            return False

        if name.startswith('#'):
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Название хэштега не должно содержать символ # в начале"
            )
            self.lineEditName.setFocus()
            return False

        if len(name) > 100:
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Название хэштега не должно превышать 100 символов"
            )
            self.lineEditName.setFocus()
            return False

        return True

    def _on_save(self):
        if not self._validate_input():
            return

        # Данные готовы - родительский компонент сохранит их через API
        self.accept()

    def get_tag_data(self) -> Dict[str, Any]:
        """Возвращает данные тега"""
        name = self.lineEditName.text().strip()
        priority_text = self.comboBoxPriority.currentText()
        priority = self.PRIORITY_MAP.get(priority_text, 'normal')
        color = self._get_current_color()

        tag_data = {
            'name': name,
            'priority': priority,
            'color': color
        }

        if self.tag_id:
            tag_data['id'] = self.tag_id

        return tag_data


# ============================================================================
# ТЕСТОВЫЙ ЗАПУСК
# ============================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Тест: Создание нового тега
    print("=" * 50)
    print("ТЕСТ: Создание нового тега")
    dialog = TagDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("Создан тег:", dialog.get_tag_data())

    sys.exit(0)