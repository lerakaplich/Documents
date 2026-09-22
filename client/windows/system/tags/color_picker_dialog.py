from PyQt6.QtWidgets import QDialog, QColorDialog
from PyQt6.QtCore import pyqtSignal
from PyQt6 import uic
import os
from functools import partial

from client.core.themes import apply_theme_to_widget, T


class ColorPickerDialog(QDialog):
    """Диалог выбора цвета для тега"""
    color_selected = pyqtSignal(str)

    def __init__(self, current_color=None, parent=None):
        super().__init__(parent)
        # Импортируем T локально, чтобы избежать циклического импорта на уровне модуля
        current_color = current_color or T.ACCENT_PRIMARY
        self.current_color = current_color
        self.selected_color = current_color

        ui_path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..', 'ui', 'system', 'tags', "color_picker_dialog.ui"
        )


        uic.loadUi(ui_path, self)
        apply_theme_to_widget(self)
        self.setup_connections()
        # Устанавливаем начальный цвет превью
        self.update_preview()

    def setup_connections(self):
        """Подключение всех сигналов"""
        preset_colors = [
            "#ccab6e", "#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4",
            "#f9ca24", "#f0932b", "#eb4d4b", "#6ab04c", "#7ed6df",
            "#e056fd", "#686de0", "#30336b", "#95afc0", "#22a6b3",
            "#ff9ff3", "#feca57", "#ff6b6b", "#48dbfb", "#1dd1a1"
        ]

        # Подключаем все кнопки палитры (используем partial вместо lambda)
        for i in range(20):
            btn = getattr(self, f"preset_color_btn_{i}")
            color = preset_colors[i]
            # Используем partial для корректного замыкания
            btn.clicked.connect(partial(self.on_color_preset_clicked, color))

        # Подключаем остальные кнопки
        if hasattr(self, 'custom_btn'):
            self.custom_btn.clicked.connect(self.open_color_dialog)
        if hasattr(self, 'ok_btn'):
            self.ok_btn.clicked.connect(self.accept)
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.clicked.connect(self.reject)

    def on_color_preset_clicked(self, color):
        """Обработчик выбора предустановленного цвета"""
        self.selected_color = color
        self.update_preview()

    def open_color_dialog(self):
        """Открывает стандартный диалог выбора цвета"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()
            self.update_preview()

    def update_preview(self):
        """Обновляет превью цвета"""
        if hasattr(self, 'preview_frame'):
            self.preview_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.selected_color};
                    border-radius: 8px;
                    border: 2px solid {T.BORDER_LIGHT};
                }}
            """)

    def get_selected_color(self):
        """Возвращает выбранный цвет"""
        return self.selected_color