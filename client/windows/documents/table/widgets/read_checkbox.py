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
                /* Картинка для НЕнажатого состояния */
                image: url("D:/Documents/client/images/cb_unchecked.png");
            }

            QCheckBox::indicator:checked {
                /* Картинка для НАЖАТОГО состояния */
                image: url("D:/Documents/client/images/cb_checked.png");
            }

            /* Если хотите добавить эффект при наведении, можно использовать другой файл,
               либо убрать этот блок, чтобы при наведении ничего не менялось */
            QCheckBox::indicator:hover {
                /* image: url("D:/Documents/client/images/cb_hover.png"); */
            }
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