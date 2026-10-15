# client/windows/system/employees/employee_pagination_manager.py
import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

logger = logging.getLogger(__name__)


class EmployeePaginationManager:
    """Панель ◀ Страница X из Y ▶ под таблицей сотрудников (как в переработках).

    Страницы считаются на клиенте: сотрудники грузятся целиком, а поиск, фильтр по
    организации и сортировка работают по всему списку, поэтому режем уже готовый результат.
    """

    def __init__(self):
        self.bar = None
        self.prev_btn = None
        self.next_btn = None
        self.page_label = None

    # ==================== СОЗДАНИЕ UI ====================

    def setup_bar(self, layout, change_page_callback):
        """Добавляет панель в конец layout (под таблицу).
        change_page_callback(delta) вызывается при клике ◀ / ▶."""
        self.bar, self.prev_btn, self.next_btn, self.page_label = self._create_bar()
        if layout is None:
            logger.warning("Пагинация сотрудников: у контейнера таблицы нет layout, панель не добавлена")
            return
        layout.addWidget(self.bar)
        self.bar.setVisible(False)
        self.prev_btn.clicked.connect(lambda: change_page_callback(-1))
        self.next_btn.clicked.connect(lambda: change_page_callback(+1))

    @staticmethod
    def _theme():
        from client.core.themes import get_manager

        return get_manager().current

    def _btn_style(self, t) -> str:
        return f"""
            QPushButton {{
                border: none;
                border-radius: 8px;
                background-color: {t.ACCENT_PRIMARY};
                color: {t.TEXT_ON_ACCENT};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t.ACCENT_HOVER_SOFT};
                color: {t.TEXT_ON_ACCENT};
            }}
            QPushButton:pressed {{
                background-color: {t.ACCENT_PRESSED_DEEP};
                color: {t.TEXT_ON_ACCENT};
            }}
            QPushButton:disabled {{
                background-color: {t.BG_PRESSED_LIGHT};
                color: {t.TEXT_ON_ACCENT};
            }}
        """

    def _create_bar(self):
        t = self._theme()

        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        layout.addStretch()
        bar.setStyleSheet(f"background-color: {t.BG_CARD};")

        prev_btn = QPushButton("◀")
        prev_btn.setFixedSize(32, 32)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setStyleSheet(self._btn_style(t))

        page_label = QLabel("Страница 1 из 1")
        page_label.setStyleSheet(f"font-size: 13px; color: {t.TEXT_PRIMARY}; font-weight: 500;")
        page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_label.setMinimumWidth(200)

        next_btn = QPushButton("▶")
        next_btn.setFixedSize(32, 32)
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.setStyleSheet(self._btn_style(t))

        layout.addWidget(prev_btn)
        layout.addWidget(page_label)
        layout.addWidget(next_btn)
        layout.addStretch()
        return bar, prev_btn, next_btn, page_label

    # ==================== ОБНОВЛЕНИЕ ====================

    def update(self, page: int, pages: int, total: int):
        if self.bar is None:
            return
        # одна страница (или данных нет) — прячем всю панель
        if pages <= 1:
            self.bar.setVisible(False)
            return
        self.bar.setVisible(True)
        self.page_label.setText(f"Страница {page} из {pages}  (всего: {total})")
        self.prev_btn.setEnabled(page > 1)
        self.next_btn.setEnabled(page < pages)

    def reapply_theme(self):
        """Перерисовать стили панели под актуальную тему."""
        if self.bar is None:
            return
        t = self._theme()
        for btn in (self.prev_btn, self.next_btn):
            btn.setStyleSheet(self._btn_style(t))
        self.bar.setStyleSheet(f"background-color: {t.BG_CARD};")
        self.page_label.setStyleSheet(f"font-size: 13px; color: {t.TEXT_PRIMARY}; font-weight: 500;")
