# client/windows/profile/overtime/overtime_pagination_manager.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt


class OvertimePaginationManager:
    """Управление пагинацией для вкладок 'Мои' и 'Все' переработки."""

    def __init__(self, parent=None):
        self.parent = parent
        self.page_size = 50
        self.my_current_page = 1
        self.all_current_page = 1

        # Ссылки на панели и их содержимое
        self.my_bar = None
        self.all_bar = None
        self.my_page_label = None
        self.all_page_label = None
        self.my_prev_btn = None
        self.my_next_btn = None
        self.all_prev_btn = None
        self.all_next_btn = None

    # ==================== СОЗДАНИЕ UI ====================

    def setup_bars(self, my_container, all_container, change_page_callback):
        """Создаёт панели пагинации под карточками.
        change_page_callback(tab, delta) вызывается при клике ◀/▶."""
        (self.my_bar,
         self.my_prev_btn,
         self.my_next_btn,
         self.my_page_label) = self._attach(my_container, 'my', change_page_callback)

        (self.all_bar,
         self.all_prev_btn,
         self.all_next_btn,
         self.all_page_label) = self._attach(all_container, 'all', change_page_callback)

    def _attach(self, container, tab_key, callback):
        if not container:
            return None, None, None, None

        bar, prev_btn, next_btn, page_label = self._create_bar()

        # Панель идёт сразу после карточек
        if hasattr(container, 'main_layout'):
            container.main_layout.addWidget(bar)
        else:
            tab = container.parentWidget()
            while tab is not None and tab.objectName() not in ("tabMyOvertime", "tabAllOvertime"):
                tab = tab.parentWidget()
            if tab and tab.layout():
                tab.layout().addWidget(bar)

        bar.setVisible(False)

        prev_btn.clicked.connect(lambda: callback(tab_key, -1))
        next_btn.clicked.connect(lambda: callback(tab_key, +1))

        return bar, prev_btn, next_btn, page_label

    def _create_bar(self):
        from client.core.themes import get_manager
        t = get_manager().current

        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        layout.addStretch()

        btn_style = f"""
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
        bar.setStyleSheet(f"background-color: {t.BG_CARD};")

        prev_btn = QPushButton("◀")
        prev_btn.setFixedSize(32, 32)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setStyleSheet(btn_style)

        page_label = QLabel("Страница 1 из 1")
        page_label.setStyleSheet(
            f"font-size: 13px; color: {t.TEXT_PRIMARY}; font-weight: 500;"
        )
        page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_label.setMinimumWidth(200)

        next_btn = QPushButton("▶")
        next_btn.setFixedSize(32, 32)
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.setStyleSheet(btn_style)

        layout.addWidget(prev_btn)
        layout.addWidget(page_label)
        layout.addWidget(next_btn)
        layout.addStretch()

        return bar, prev_btn, next_btn, page_label

    # ==================== СОСТОЯНИЕ ====================

    def current_page(self, tab: str) -> int:
        return self.my_current_page if tab == 'my' else self.all_current_page

    def set_page(self, tab: str, page: int):
        if tab == 'my':
            self.my_current_page = page
        else:
            self.all_current_page = page

    def reset(self, tab: str):
        self.set_page(tab, 1)

    # ==================== ОБНОВЛЕНИЕ МЕТОК ====================

    def update_labels(self, my_pagination: dict, all_pagination: dict):
        self._update_one(self.my_bar, self.my_page_label,
                         self.my_prev_btn, self.my_next_btn, my_pagination)
        self._update_one(self.all_bar, self.all_page_label,
                         self.all_prev_btn, self.all_next_btn, all_pagination)

    def _update_one(self, bar, page_label, prev_btn, next_btn, p):
        if bar is None or page_label is None:
            return

        pages = p.get('pages', 1) or 1
        total = p.get('total', 0)

        # Если страница одна (или данных нет) — прячем всю панель
        if pages <= 1:
            bar.setVisible(False)
            return

        bar.setVisible(True)
        page_label.setText(
            f"Страница {p['page']} из {pages}  (всего: {total})"
        )
        prev_btn.setEnabled(p['page'] > 1)
        next_btn.setEnabled(p['page'] < pages)

    def reapply_theme(self):
        """Перерисовать стили кнопок и метки под актуальную тему."""
        from client.core.themes import get_manager
        t = get_manager().current

        btn_style = f"""
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

        for btn in (self.my_prev_btn, self.my_next_btn,
                    self.all_prev_btn, self.all_next_btn):
            if btn is not None:
                btn.setStyleSheet(btn_style)

        for bar in (self.my_bar, self.all_bar):
            if bar is not None:
                bar.setStyleSheet(f"background-color: {t.BG_CARD};")

        label_style = f"font-size: 13px; color: {t.TEXT_PRIMARY}; font-weight: 500;"
        for label in (self.my_page_label, self.all_page_label):
            if label is not None:
                label.setStyleSheet(label_style)

