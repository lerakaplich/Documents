from PyQt6.QtWidgets import QWidget, QCheckBox, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
import os


class ReadCheckBox(QWidget):
    """Виджет чекбокса для отметки о прочтении"""

    state_changed = pyqtSignal(int, bool)  # document_id, is_read

    def __init__(self, document_id, is_read=False, parent=None):
        super().__init__(parent)

        self.document_id = document_id

        # Создаем layout с минимальными отступами
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Создаем чекбокс
        self.readCheckBox = QCheckBox()
        self.readCheckBox.setChecked(is_read)
        self.readCheckBox.stateChanged.connect(self.on_state_changed)
        layout.addWidget(self.readCheckBox)

        # Применяем стили с прозрачным фоном для контейнера
        self.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)

        # Получаем путь к директории с иконками относительно текущего файла
        # Текущий файл: windows/documents/table/widgets/read_checkbox.py
        # Поднимаемся на 4 уровня вверх: widgets -> table -> documents -> windows -> client
        icons_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), 'icons')

        # Используем прямые слеши для путей в CSS
        unchecked_icon = os.path.join(icons_dir, 'cb_unchecked.svg').replace('\\', '/')
        checked_icon = os.path.join(icons_dir, 'cb_checked.svg').replace('\\', '/')

        # ИСПРАВЛЕННЫЕ СТИЛИ: Используем относительные пути к иконкам
        self.readCheckBox.setStyleSheet(f"""
            QCheckBox {{
                color: #1B232A;
                spacing: 0px;
                font-size: 12px;
                background: transparent;
            }}

            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                image: url("{unchecked_icon}");
            }}

            QCheckBox::indicator:checked {{
                image: url("{checked_icon}");
            }}
        """)

    def on_state_changed(self, state):
        """Обработка изменения состояния чекбокса"""
        # В PyQt6 state может быть объектом Qt.CheckState, приводим к bool через сравнение
        is_checked = state == Qt.CheckState.Checked.value or state == Qt.CheckState.Checked
        self.state_changed.emit(self.document_id, is_checked)

    def set_read_state(self, is_read):
        """Установка состояния без эмита сигнала"""
        self.readCheckBox.blockSignals(True)
        self.readCheckBox.setChecked(is_read)
        self.readCheckBox.blockSignals(False)