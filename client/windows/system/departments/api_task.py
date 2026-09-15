# client/windows/system/departments/api_task.py
from PyQt6.QtCore import QRunnable, QThreadPool, QObject, pyqtSignal


class _Signals(QObject):
    done = pyqtSignal(object)
    error = pyqtSignal(str)


class ApiTask(QRunnable):
    """Выполняет блокирующий вызов сервиса в фоне."""

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _Signals()

    def run(self):
        try:
            self.signals.done.emit(self.fn(*self.args, **self.kwargs))
        except Exception as e:
            self.signals.error.emit(str(e))


class TaskKeeper:
    """Держит ссылки на активные таски, чтобы их не собрал gc."""

    def __init__(self):
        self._active = set()

    def submit(self, task: ApiTask):
        self._active.add(task)
        task.signals.done.connect(lambda _: self._active.discard(task))
        task.signals.error.connect(lambda _: self._active.discard(task))
        QThreadPool.globalInstance().start(task)