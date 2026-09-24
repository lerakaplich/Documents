# client/windows/documents/stats/unanswered_stats_dialog.py

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor

from client.core.themes import get_manager


class UnansweredStatsDialog(QDialog):
    """Диалог со статистикой по неотвеченным документам."""

    def __init__(self, stats: list, parent=None):
        super().__init__(parent)
        self.stats = stats or []

        self.setWindowTitle("Статистика по неотвеченным документам")
        self.resize(1000, 600)
        self.setModal(True)

        self._build_ui()
        self._apply_theme()

    # ─────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # Заголовок + итог
        header = QHBoxLayout()

        title = QLabel("Документы без ответа")
        title.setObjectName("statsTitle")
        header.addWidget(title)

        header.addStretch()

        total_penalty = sum(int(s.get("penalty", 0) or 0) for s in self.stats)
        summary = QLabel(
            f"Всего: {len(self.stats)}  •  Общий штраф: {total_penalty}"
        )
        summary.setObjectName("statsSummary")
        header.addWidget(summary)

        root.addLayout(header)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "№", "Документ", "Тема", "Срок", "Просрочка (дн.)", "Штраф"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )

        # Заполнение
        for i, s in enumerate(self.stats):
            self.table.insertRow(i)

            reg = str(s.get("reg_number") or s.get("document_id") or "—")
            title = str(s.get("title") or s.get("about") or "—")
            deadline = str(s.get("deadline") or "—")
            days = s.get("days_overdue") or s.get("overdue_days") or 0
            penalty = s.get("penalty") or 0

            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(reg))
            self.table.setItem(i, 2, QTableWidgetItem(title))
            self.table.setItem(i, 3, QTableWidgetItem(deadline))
            self.table.setItem(i, 4, QTableWidgetItem(str(days)))
            self.table.setItem(i, 5, QTableWidgetItem(str(penalty)))

            # Подсветка просрочки красным, если > 0
            try:
                if int(days) > 0:
                    for col in range(6):
                        item = self.table.item(i, col)
                        if item:
                            item.setForeground(QBrush(QColor("#E53E3E")))
            except Exception:
                pass

        root.addWidget(self.table, 1)

        # Кнопка «Закрыть»
        buttons = QHBoxLayout()
        buttons.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.setMinimumSize(120, 36)
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)

        root.addLayout(buttons)

        # Если пусто — покажем сообщение в заголовке
        if not self.stats:
            empty = QLabel("Нет документов, требующих ответа 🎉")
            empty.setObjectName("statsEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.insertWidget(1, empty)

    # ─────────────────────────────────────────────

    def _apply_theme(self):
        t = get_manager().current
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {t.BG_DIALOG};
            }}
            QLabel#statsTitle {{
                font-size: 20px;
                font-weight: bold;
                color: {t.TEXT_PRIMARY};
                background: transparent;
            }}
            QLabel#statsSummary {{
                font-size: 14px;
                font-weight: 500;
                color: {t.TEXT_MUTED_ALT};
                background: transparent;
            }}
            QLabel#statsEmpty {{
                font-size: 16px;
                color: {t.TEXT_MUTED_ALT};
                padding: 20px;
                background: transparent;
            }}
            QTableWidget {{
                background-color: {t.BG_CARD};
                color: {t.TEXT_PRIMARY};
                gridline-color: {t.TABLE_GRID};
                border: 1px solid {t.BORDER_LIGHT};
                border-radius: 8px;
            }}
            QHeaderView::section {{
                background-color: {t.TABLE_HEADER_BG};
                color: {t.TABLE_HEADER_TEXT};
                padding: 8px;
                border: none;
                border-right: 1px solid {t.TABLE_HEADER_BORDER};
                border-bottom: 2px solid {t.TABLE_HEADER_BORDER};
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton {{
                background-color: {t.ACCENT_PRIMARY};
                color: {t.TEXT_ON_ACCENT};
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
            }}
            QPushButton:hover {{
                background-color: {t.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {t.ACCENT_PRESSED};
            }}
            QScrollBar:vertical {{
                background: {t.SCROLLBAR_BG};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {t.SCROLLBAR_HANDLE};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
        """)

    def reapply_theme(self):
        self._apply_theme()