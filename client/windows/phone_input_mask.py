from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit


class PhoneLineEdit(QLineEdit):
    """
    QLineEdit с поддержкой маски телефона, где курсор
    автоматически передвигается на первую свободную позицию.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Устанавливаем маску
        self.setInputMask("+375 (99) 999-99-99;_")

        # Меняем внешний вид указателя мыши (при наведении)
        self.setCursor(Qt.CursorShape.IBeamCursor)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # Перемещаем курсор на первую незаполненную позицию после клика
        self._move_cursor_to_first_free_position()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        # Перемещаем курсор при получении фокуса (например, по Tab)
        self._move_cursor_to_first_free_position()

    def _move_cursor_to_first_free_position(self):
        text = self.text()
        # Ищем первый символ подчеркивания '_'
        first_underscore = text.find("_")

        if first_underscore != -1:
            # Ставим курсор перед первым '_'
            self.setCursorPosition(first_underscore)
        else:
            # Если все заполнено, ставим в конец
            self.setCursorPosition(len(text))
