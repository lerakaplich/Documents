# client/windows/documents/table/documents_pagination_manager.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt


class DocumentsPaginationManager:
    """Панель пагинации под таблицей документов (◀ Страница X из Y ▶).

    Оформление и поведение — как в OvertimePaginationManager, но вкладка
    одна, поэтому состояние страницы хранит не менеджер, а
    DocumentsPanelController (единый источник правды).
    """

    def __init__(self):
        self.bar = None
        self.prev_btn = None
        self.next_btn = None
        self.page_label = None

    # ==================== СОЗДАНИЕ UI ====================

    def setup_bar(self, layout, change_page_callback):
        """Создаёт панель и добавляет её в layout сразу после таблицы.
        change_page_callback(delta) вызывается при клике ◀ (-1) / ▶ (+1)."""
        self.bar, self.prev_btn, self.next_btn, self.page_label = self._create_bar()
        layout.addWidget(self.bar)
        self.bar.setVisible(False)

        self.prev_btn.clicked.connect(lambda: change_page_callback(-1))
        self.next_btn.clicked.connect(lambda: change_page_callback(+1))

    @staticmethod
    def _btn_style(t) -> str:
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

    @staticmethod
    def _label_style(t) -> str:
        return f"font-size: 13px; color: {t.TEXT_PRIMARY}; font-weight: 500;"

    def _create_bar(self):
        from client.core.themes import get_manager
        t = get_manager().current

        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        layout.addStretch()

        prev_btn = QPushButton("◀")
        prev_btn.setFixedSize(32, 32)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setStyleSheet(self._btn_style(t))

        page_label = QLabel("Страница 1 из 1")
        page_label.setStyleSheet(self._label_style(t))
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

    def update(self, p: dict):
        """p = {"page": int, "pages": int, "total": int}"""
        if self.bar is None or self.page_label is None:
            return

        pages = p.get('pages', 1) or 1
        total = p.get('total', 0)

        # Одна страница (или данных нет) — прячем всю панель
        if pages <= 1:
            self.bar.setVisible(False)
            return

        self.bar.setVisible(True)
        self.page_label.setText(f"Страница {p['page']} из {pages}  (всего: {total})")
        self.prev_btn.setEnabled(p['page'] > 1)
        self.next_btn.setEnabled(p['page'] < pages)

    def reapply_theme(self):
        """Перерисовать стили кнопок и метки под актуальную тему."""
        from client.core.themes import get_manager
        t = get_manager().current

        for btn in (self.prev_btn, self.next_btn):
            if btn is not None:
                btn.setStyleSheet(self._btn_style(t))
        if self.page_label is not None:
            self.page_label.setStyleSheet(self._label_style(t))