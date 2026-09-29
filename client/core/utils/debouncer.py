from PyQt6.QtCore import QTimer


class Debouncer:
    """Debouncer для отложенного выполнения действий (поиск, фильтрация)"""

    def __init__(self, delay_ms: int = 300):
        self.delay_ms = delay_ms
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.callback = None
        self.timer.timeout.connect(self._on_timeout)

    def trigger(self):
        """Запускает или сбрасывает таймер"""
        self.timer.start(self.delay_ms)

    def _on_timeout(self):
        if self.callback:
            self.callback()

    def cancel(self):
        """Отменяет выполнение"""
        self.timer.stop()
