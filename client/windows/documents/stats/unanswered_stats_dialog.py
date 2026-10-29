# client/windows/documents/stats/unanswered_stats_dialog.py
"""
Диалог со статистикой по неотвеченным документам.

Разметка и стили — в client/ui/documents/unanswered_stats_dialog.ui
(цвета — токенами темы вида {BG_DIALOG}, подставляются apply_theme_to_widget).
Здесь — загрузка .ui, заполнение таблицы и экспорт в Excel.
"""

import os
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHeaderView,
    QMessageBox,
    QTableWidgetItem,
)
from PyQt6.uic import loadUi

from client.core.state.app_state import AppState
from client.core.themes import apply_theme_to_widget, get_manager
from client.windows.documents.comments.comment_dialog import split_api_error

EXPORT_ENDPOINT = "/documents/documents/unanswered/export-excel"

# Режимы ширины колонок: №, Документ, Тема, Срок, Просрочка, Штраф
_COLUMN_MODES = (
    QHeaderView.ResizeMode.ResizeToContents,
    QHeaderView.ResizeMode.ResizeToContents,
    QHeaderView.ResizeMode.Stretch,
    QHeaderView.ResizeMode.ResizeToContents,
    QHeaderView.ResizeMode.ResizeToContents,
    QHeaderView.ResizeMode.ResizeToContents,
)


class UnansweredStatsDialog(QDialog):
    """Диалог со статистикой по неотвеченным документам."""

    def __init__(self, stats: list, parent=None, http_client=None):
        super().__init__(parent)
        self.stats = stats or []
        self.http_client = http_client or AppState().http_client

        self._load_ui()
        apply_theme_to_widget(self)

        self._setup_table()
        self._fill_summary()
        self._fill_table()
        self._connect_signals()

    # ─────────── UI ───────────

    @staticmethod
    def _ui_path() -> str:
        """client/windows/documents/stats/ → client/ui/documents/unanswered_stats_dialog.ui"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        client_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        return os.path.join(client_dir, "ui", "documents", "unanswered_stats_dialog.ui")

    def _load_ui(self):
        ui_path = self._ui_path()
        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI файл не найден: {ui_path}")
        loadUi(ui_path, self)

    def _connect_signals(self):
        self.exportButton.clicked.connect(self._export_excel)
        self.closeButton.clicked.connect(self.accept)
        # Enter не должен случайно запускать экспорт или закрывать окно
        self.exportButton.setAutoDefault(False)
        self.closeButton.setAutoDefault(False)

    def _setup_table(self):
        header = self.statsTable.horizontalHeader()
        for col, mode in enumerate(_COLUMN_MODES):
            header.setSectionResizeMode(col, mode)

    # ─────────── Данные ───────────

    def _fill_summary(self):
        total_penalty = sum(int(s.get("penalty", 0) or 0) for s in self.stats)
        self.statsSummary.setText(f"Всего: {len(self.stats)}  •  Общий штраф: {total_penalty}")
        # Если пусто — показываем сообщение над таблицей
        self.statsEmpty.setVisible(not self.stats)

    def _fill_table(self):
        overdue_brush = QBrush(QColor(get_manager().current.TEXT_DANGER))

        self.statsTable.setRowCount(0)
        for i, s in enumerate(self.stats):
            self.statsTable.insertRow(i)

            reg = str(s.get("reg_number") or s.get("document_id") or "—")
            title = str(s.get("title") or s.get("about") or "—")
            deadline = str(s.get("deadline") or "—")
            days = s.get("days_overdue") or s.get("overdue_days") or 0
            penalty = s.get("penalty") or 0

            values = (str(i + 1), reg, title, deadline, str(days), str(penalty))
            for col, value in enumerate(values):
                self.statsTable.setItem(i, col, QTableWidgetItem(value))

            # Подсветка просрочки, если > 0
            try:
                overdue = int(days) > 0
            except (TypeError, ValueError):
                overdue = False
            if overdue:
                for col in range(self.statsTable.columnCount()):
                    item = self.statsTable.item(i, col)
                    if item:
                        item.setForeground(overdue_brush)

    # ─────────── Экспорт ───────────

    def _export_excel(self):
        """Скачивает Excel с сервера, сохраняет в выбранное место и сообщает об успехе."""
        default_name = f"unanswered_documents_{date.today():%Y-%m-%d}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить таблицу", default_name, "Excel (*.xlsx)")
        if not path:
            return  # пользователь отменил выбор
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        error = None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            data = self.http_client.get_binary(EXPORT_ENDPOINT)
            with open(path, "wb") as f:
                f.write(data)
        except PermissionError:
            error = "Не удалось записать файл. Возможно, он открыт в Excel или нет прав на папку."
        except Exception as e:  # noqa: BLE001
            status, detail = split_api_error(e)
            error = detail if status == 403 else f"Не удалось получить файл:\n{detail}"
        finally:
            QApplication.restoreOverrideCursor()

        if error:
            QMessageBox.warning(self, "Экспорт", error)
            return
        QMessageBox.information(self, "Экспорт", f"Таблица сохранена:\n{os.path.normpath(path)}")

    # ─────────── Тема ───────────

    def reapply_theme(self):
        apply_theme_to_widget(self)
        self._fill_table()  # цвет подсветки просрочки берётся из темы