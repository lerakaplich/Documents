from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel


class CountBadge(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # клики идут в кнопку
        self.setFixedHeight(18)
        self.setMinimumWidth(18)
        self.setStyleSheet(
            "background:#E5484D; color:white; border-radius:9px;"
            "font-size:11px; font-weight:bold; padding:0 6px;"
        )
        self.hide()

    def set_count(self, n: int):
        if n <= 0:
            self.hide()
        else:
            self.setText("99+" if n > 99 else str(n))
            self.show()