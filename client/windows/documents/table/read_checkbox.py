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

        # Применяем стили с прозрачным фоном
        self.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)

        self.readCheckBox.setStyleSheet("""
            QCheckBox {
                color: #1B232A;
                spacing: 0px;
                font-size: 12px;
                background: transparent;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #B0B0B0;
                border-radius: 3px;
                background-color: transparent;
            }

            QCheckBox::indicator:checked {
                background-color: #CCAB6E;
                border-color: #CCAB6E;
            }

            QCheckBox::indicator:hover {
                border-color: #CCAB6E;
            }
        """)

    def on_state_changed(self, state):
        """Обработка изменения состояния чекбокса"""
        is_checked = state == 2  # Qt.Checked = 2
        self.state_changed.emit(self.document_id, is_checked)

    def set_read_state(self, is_read):
        """Установка состояния без эмита сигнала"""
        self.readCheckBox.blockSignals(True)
        self.readCheckBox.setChecked(is_read)
        self.readCheckBox.blockSignals(False)