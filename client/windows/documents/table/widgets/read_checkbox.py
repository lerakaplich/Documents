from PyQt6.QtWidgets import QWidget, QCheckBox, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt


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

        # ИСПРАВЛЕННЫЕ СТИЛИ: Используем ваши локальные картинки
        # Обратите внимание на прямые слеши (/) вместо обратных (\)
        from client.core.themes import get_manager
        from client.core.themes.icon_utils import icon_path

        _t = get_manager().current
        checked   = icon_path("cb_checked",   _t.ICON_COLOR)
        unchecked = icon_path("cb_unchecked", _t.ICON_COLOR)

        self.readCheckBox.setStyleSheet(f"""
            QCheckBox {{
                color: {_t.TEXT_PRIMARY};
                spacing: 0px;
                font-size: 12px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                image: url({unchecked});
            }}
            QCheckBox::indicator:checked {{
                image: url({checked});
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

    def reapply_theme(self):
        from client.core.themes import get_manager
        from client.core.themes.icon_utils import icon_path

        _t = get_manager().current
        checked   = icon_path("cb_checked",   _t.ICON_COLOR)
        unchecked = icon_path("cb_unchecked", _t.ICON_COLOR)

        self.readCheckBox.setStyleSheet(f"""
            QCheckBox {{
                color: {_t.TEXT_PRIMARY};
                spacing: 0px;
                font-size: 12px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 18px; height: 18px;
                image: url({unchecked});
            }}
            QCheckBox::indicator:checked {{
                image: url({checked});
            }}
        """)