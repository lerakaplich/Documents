"""Фоновая загрузка данных для диалога выбора"""

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from PyQt6.QtWidgets import QMessageBox


class _LoadSignals(QObject):
    done = pyqtSignal(object, object)  # key, result
    failed = pyqtSignal(object, str)  # key, message


class _LoadTask(QRunnable):
    """Выполняет fn() в потоке пула и возвращает результат сигналом (в GUI-поток)."""

    def __init__(self, key, fn):
        super().__init__()
        self.key = key
        self.fn = fn
        self.signals = _LoadSignals()
        self.setAutoDelete(False)  # жизнью задачи управляет диалог

    def run(self):
        try:
            result = self.fn()
        except Exception as e:  # noqa: BLE001
            self.signals.failed.emit(self.key, str(e))
            return
        self.signals.done.emit(self.key, result)


class BackgroundLoadMixin:
    """Фоновая загрузка организаций/поиска (QThreadPool) для диалога выбора."""

    def _start_task(self, key, fn):
        if key in self._tasks:
            return
        task = _LoadTask(key, fn)
        task.signals.done.connect(self._on_task_done)
        task.signals.failed.connect(self._on_task_failed)
        self._tasks[key] = task
        self._pool.start(task)

    def _start_load(self, org_id: int):
        if not self._lazy or self.builder.is_loaded(org_id) or org_id in self._loading_orgs:
            return
        self._loading_orgs.add(org_id)
        loader = self.loader
        self._start_task(("org", org_id), lambda: loader.load_org_data(org_id))

    def _on_task_done(self, key, result):
        self._tasks.pop(key, None)
        if self._closing:
            return
        kind = key[0]

        if kind == "org":
            org_id = key[1]
            self._loading_orgs.discard(org_id)
            self.builder.add_org_data(org_id, result["departments"], result["employees"])
            self._resolve_pending()
            self._fill_org(org_id)
            self._update_selection_info()

        elif kind == "search":
            if key[1] != self._last_query:
                return  # устаревший запрос
            hits, orgs_data = result
            for org_id, data in orgs_data.items():
                self.builder.add_org_data(org_id, data["departments"], data["employees"])
                self._loading_orgs.discard(org_id)
            self._resolve_pending()
            self._show_search_results(hits)
            self._update_selection_info()

    def _on_task_failed(self, key, message):
        self._tasks.pop(key, None)
        if self._closing:
            return
        print(f"[EmployeeSelectionDialog] Ошибка загрузки {key}: {message}")
        if key[0] == "org":
            org_id = key[1]
            self._loading_orgs.discard(org_id)
            item = self._org_items.get(org_id)
            if item is not None:
                self.tree_builder.set_placeholder_text(item, "Не удалось загрузить — сверните и раскройте снова")
        elif key[0] == "search" and key[1] == self._last_query:
            self._set_search_busy(False)
            QMessageBox.warning(self, "Поиск", f"Не удалось выполнить поиск:\n{message}")
