# client/windows/system/tags/tag_card.py

import sys
import os
from PyQt6.QtWidgets import QApplication, QFrame, QMessageBox
from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi

from client.windows.system.tags.color_picker_dialog import ColorPickerDialog


class TagCard(QFrame):
    """Карточка тега на основе загруженного UI файла"""

    # Сигналы для взаимодействия с главным окном
    edit_clicked = pyqtSignal(dict)
    delete_clicked = pyqtSignal(int)
    color_changed = pyqtSignal(int, str)  # ID тега, новый цвет

    def __init__(self, tag_data=None, parent=None):
        super().__init__(parent)

        # Загружаем UI дизайн
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)
        else:
            raise FileNotFoundError(f"UI файл не найден: {ui_path}")

        # Сохраняем данные
        self.tag_data = tag_data or {}
        self.tag_id = self.tag_data.get('id', 0)

        # Настраиваем карточку
        self.setup_card()

        # Подключаем сигналы кнопок
        self.setup_connections()

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'tags', 'tag_card.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Подключение сигналов кнопок"""
        if hasattr(self, 'editBtn'):
            self.editBtn.clicked.connect(self.on_edit_clicked)
        if hasattr(self, 'deleteBtn'):
            self.deleteBtn.clicked.connect(self.on_delete_clicked)
        if hasattr(self, 'colorButton'):
            self.colorButton.clicked.connect(self.on_color_button_clicked)

    def setup_card(self):
        """Заполняет карточку данными"""
        if not self.tag_data:
            return

        # Заполняем название тега
        if hasattr(self, 'nameLabel'):
            name = self.tag_data.get('name', '')
            self.nameLabel.setText(name if name else 'Без названия')

        # Заполняем количество документов
        if hasattr(self, 'countLabel'):
            count = self.tag_data.get('documents_count', 0)
            if count % 10 == 1 and count % 100 != 11:
                word = "документ"
            elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
                word = "документа"
            else:
                word = "документов"
            self.countLabel.setText(f"{count} {word}" if count > 0 else "нет документов")

        # Устанавливаем цвет кружочка
        if hasattr(self, 'colorButton'):
            color = self.tag_data.get('color', '#CCAB6E')
            self.set_color(color)

    def set_color(self, color):
        """Устанавливает цвет кружочка-индикатора"""
        if hasattr(self, 'colorButton'):
            self.colorButton.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border-radius: 10px;
                    border: 2px solid #E8DCC8;
                }}
                QPushButton:hover {{
                    border: 2px solid {color};
                }}
            """)
            self.tag_data['color'] = color

    def on_color_button_clicked(self):
        """Обработчик клика по кружочку цвета"""
        current_color = self.tag_data.get('color', '#CCAB6E')
        dialog = ColorPickerDialog(current_color=current_color, parent=self)

        if dialog.exec() == ColorPickerDialog.DialogCode.Accepted:
            new_color = dialog.get_selected_color()
            self.set_color(new_color)
            # Испускаем сигнал с ID и новым цветом
            self.color_changed.emit(self.tag_id, new_color)

    def on_edit_clicked(self):
        self.edit_clicked.emit(self.tag_data)

    def on_delete_clicked(self):
        self.delete_clicked.emit(self.tag_id)

    def update_data(self, new_data):
        self.tag_data.update(new_data)
        self.setup_card()

    def get_data(self):
        return self.tag_data