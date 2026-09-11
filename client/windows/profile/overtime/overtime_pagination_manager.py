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
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(10)
        layout.addStretch()

        btn_style = """
            QPushButton { border: none; border-radius: 8px; background-color: #1B232A;
                          color: white; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #D9D9D6; color: black; }
            QPushButton:pressed { background-color: #B8B8B5; }
            QPushButton:disabled { background-color: #E5E5E5; color: #999999; }
        """

        prev_btn = QPushButton("◀")
        prev_btn.setFixedSize(32, 32)
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setStyleSheet(btn_style)

        page_label = QLabel("Страница 1 из 1")
        page_label.setStyleSheet("font-size: 13px; color: #4A3B28; font-weight: 500;")
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