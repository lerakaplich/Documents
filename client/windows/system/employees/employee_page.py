# client/windows/system/employees/employee_page.py

import logging
import os
import sys
from typing import Any

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.uic import loadUi

from client.core.config import config
from client.core.http_client import HttpClient
from client.core.state.app_state import AppState
from client.core.themes import T, apply_theme_to_widget, get_menu_style
from client.services.employee_service import EmployeeService
from client.windows.animations.animated_notification import NotificationManager
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.common import badge_style, count_text, make_avatar, normalize_employee

logger = logging.getLogger(__name__)

COL_NAME, COL_POSITION, COL_DEPARTMENT, COL_PHONE, COL_EMAIL, COL_ROLE, COL_ACTIONS = range(7)
HEADERS = ["ФИО", "Должность", "Подразделение", "Телефон", "Email", "Роль", ""]
ALL_ORGS = "Все организации"
EMPLOYEE_FORMS = ("сотрудник", "сотрудника", "сотрудников")


class _LeaveFilter(QObject):
    """Снимает подсветку строки, когда курсор ушёл с таблицы."""

    def __init__(self, page):
        super().__init__(page)
        self.page = page

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Leave:
            vp = self.page.employeesTable.viewport()
            if not vp.rect().contains(vp.mapFromGlobal(QCursor.pos())):
                self.page._set_hover_row(-1)
        return False


class EmployeesPage(QWidget):
    """Страница сотрудников с поиском, фильтром по организации и сортировкой"""

    data_loaded = pyqtSignal()
    employees_changed = pyqtSignal()

    def __init__(self, parent=None, http_client: HttpClient | None = None):
        super().__init__(parent)

        # Используем переданный HttpClient или создаем новый
        if http_client is None:
            app_state = AppState()
            if app_state.http_client:
                self.http_client = app_state.http_client
            else:
                self.http_client = HttpClient(config.base_url)
        else:
            self.http_client = http_client

        self.employee_service = EmployeeService(self.http_client)

        # Данные
        self.employees: list[dict[str, Any]] = []
        self.filtered_employees: list[dict[str, Any]] = []

        # Состояние
        self.current_sort = "А→Я"
        self.is_loading = False
        self._hover_row = -1
        self._action_widgets: dict[int, QWidget] = {}

        # Инициализация
        self.init_ui()
        self.setup_connections()

        # Создаем менеджер уведомлений
        self.notification_manager = NotificationManager(self, max_visible=3)

        # Загружаем данные
        QTimer.singleShot(100, self.load_employees)

    def init_ui(self):
        """Инициализация UI из файла"""
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)
            apply_theme_to_widget(self)

        self._setup_table()

        # Создаем плавающую кнопку
        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.on_add_employee)

        # Подключаемся к скроллу
        self.employeesTable.verticalScrollBar().valueChanged.connect(self.on_scroll)

        # Скрываем кнопку сброса при старте
        self.btnResetFilters.hide()
        self.emptyLabel.hide()

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, "..", "..", "..", "ui", "system", "employees", "employee_page.ui")
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Настройка сигналов"""
        self.btnSort.clicked.connect(self.show_sort_menu)
        self.searchEdit.textChanged.connect(self.on_search_changed)
        self.orgCombo.currentIndexChanged.connect(self.on_search_changed)
        self.btnResetFilters.clicked.connect(self.reset_all_filters)

    def _setup_table(self):
        t = self.employeesTable
        t.setColumnCount(len(HEADERS))
        t.setHorizontalHeaderLabels(HEADERS)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(48)
        t.setShowGrid(False)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        t.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        t.setMouseTracking(True)
        t.setTextElideMode(Qt.TextElideMode.ElideRight)
        t.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        h = t.horizontalHeader()
        h.setHighlightSections(False)
        h.setSectionsClickable(False)
        h.setStretchLastSection(False)
        for col, width in {COL_NAME: 290, COL_POSITION: 190, COL_PHONE: 110, COL_EMAIL: 200, COL_ROLE: 130}.items():
            h.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            t.setColumnWidth(col, width)
        h.setSectionResizeMode(COL_DEPARTMENT, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(COL_ACTIONS, QHeaderView.ResizeMode.Fixed)
        t.setColumnWidth(COL_ACTIONS, 80)

        t.cellEntered.connect(lambda row, _col: self._set_hover_row(row))
        t.cellDoubleClicked.connect(lambda row, _col: self._edit_row(row))
        self._leave_filter = _LeaveFilter(self)
        t.viewport().installEventFilter(self._leave_filter)

    # ==================== УВЕДОМЛЕНИЯ ====================

    def show_success_notification(self, message: str):
        """Показать уведомление об успехе"""
        self.notification_manager.show_notification(f"✅ {message}", duration=2500)

    def show_error_notification(self, message: str):
        """Показать уведомление об ошибке"""
        self.notification_manager.show_notification(f"❌ {message}", duration=3000)

    def show_info_notification(self, message: str):
        """Показать информационное уведомление"""
        self.notification_manager.show_notification(f"ℹ️ {message}", duration=2500)

    # ==================== ЗАГРУЗКА ДАННЫХ ====================

    def load_employees(self):
        """Загрузить сотрудников из API"""
        if self.is_loading:
            return

        self.is_loading = True

        try:
            raw_employees = self.employee_service.get_all_employees()
            self.employees = [normalize_employee(e) for e in raw_employees]

            self.is_loading = False
            self._rebuild_org_combo()
            self.update_display()
            self.data_loaded.emit()

            if self.employees:
                self.show_success_notification(f"Загружено {len(self.employees)} сотрудников")

        except Exception as e:
            self.is_loading = False

            logger.exception(f"Ошибка загрузки сотрудников: {e}")

            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось загрузить сотрудников")

    def _rebuild_org_combo(self):
        current = self.orgCombo.currentText()
        orgs = sorted({e["organization"] for e in self.employees if e.get("organization")})
        self.orgCombo.blockSignals(True)
        self.orgCombo.clear()
        self.orgCombo.addItems([ALL_ORGS, *orgs])
        self.orgCombo.setCurrentIndex(max(self.orgCombo.findText(current), 0))
        self.orgCombo.blockSignals(False)

    # ==================== СОРТИРОВКА ====================

    def show_sort_menu(self):
        """Показать меню сортировки"""
        menu = QMenu(self)
        menu.setStyleSheet(get_menu_style())

        sort_options = {
            "А→Я (по ФИО)": self.sort_by_name_asc,
            "Я→А (по ФИО)": self.sort_by_name_desc,
            "По должности": self.sort_by_position,
            "По подразделению": self.sort_by_department,
        }

        for name, func in sort_options.items():
            action = menu.addAction(name)
            action.triggered.connect(lambda checked, f=func, n=name: self.apply_sort(f, n))

        menu.exec(self.btnSort.mapToGlobal(self.btnSort.rect().bottomLeft()))

    def sort_by_name_asc(self, employees):
        return sorted(employees, key=lambda x: x.get("full_name", "").lower())

    def sort_by_name_desc(self, employees):
        return sorted(employees, key=lambda x: x.get("full_name", "").lower(), reverse=True)

    def sort_by_position(self, employees):
        # сотрудники без должности — в конце
        return sorted(employees, key=lambda x: (not x.get("position"), x.get("position", "").lower()))

    def sort_by_department(self, employees):
        return sorted(employees, key=lambda x: (not x.get("department"), x.get("department", "").lower()))

    def apply_sort(self, sort_func, sort_name):
        self.current_sort = sort_name
        short_name = sort_name.split("(")[0].strip() if "(" in sort_name else sort_name
        self.btnSort.setText(f"Сортировка ▼ ({short_name})")
        self.update_reset_button_visibility()
        self.update_display()
        self.show_info_notification(f"Сортировка: {short_name}")

    # ==================== ПОИСК И ФИЛЬТРЫ ====================

    def on_search_changed(self, *_):
        self.update_reset_button_visibility()
        self.update_display()

    def has_active_filters(self):
        if self.searchEdit.text().strip():
            return True
        if self.orgCombo.currentText() not in ("", ALL_ORGS):
            return True
        return self.current_sort != "А→Я"

    def update_reset_button_visibility(self):
        if self.has_active_filters():
            self.btnResetFilters.show()
        else:
            self.btnResetFilters.hide()

    def reset_all_filters(self):
        self.searchEdit.blockSignals(True)
        self.searchEdit.clear()
        self.searchEdit.blockSignals(False)
        self.orgCombo.blockSignals(True)
        self.orgCombo.setCurrentIndex(0)
        self.orgCombo.blockSignals(False)
        self.current_sort = "А→Я"
        self.btnSort.setText("Сортировка ▼")
        self.btnResetFilters.hide()
        self.update_display()
        self.show_info_notification("Фильтры сброшены")

    def filter_and_sort_employees(self):
        """Фильтрация и сортировка сотрудников"""
        filtered = self.employees.copy()

        # Организация
        org = self.orgCombo.currentText()
        if org and org != ALL_ORGS:
            filtered = [e for e in filtered if e.get("organization") == org]

        # Поиск
        search_text = self.searchEdit.text().strip().lower()
        if search_text:
            filtered = [
                e
                for e in filtered
                if any(
                    search_text in str(e.get(key, "")).lower()
                    for key in ("full_name", "position", "department", "phone", "email", "role")
                )
            ]

        # Сортировка
        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "А→Я (по ФИО)": self.sort_by_name_asc,
            "Я→А (по ФИО)": self.sort_by_name_desc,
            "По должности": self.sort_by_position,
            "По подразделению": self.sort_by_department,
        }

        sort_func = sort_methods.get(self.current_sort, self.sort_by_name_asc)
        return sort_func(filtered)

    # ==================== ОТОБРАЖЕНИЕ ====================

    def update_display(self):
        """Обновление таблицы сотрудников"""
        self.filtered_employees = self.filter_and_sort_employees()

        t = self.employeesTable
        t.setUpdatesEnabled(False)
        t.clearContents()
        t.setRowCount(len(self.filtered_employees))
        self._hover_row = -1
        self._action_widgets.clear()

        for row, emp in enumerate(self.filtered_employees):
            self._fill_row(row, emp)

        t.setUpdatesEnabled(True)

        self.countLabel.setText(count_text(len(self.filtered_employees), EMPLOYEE_FORMS))
        self.emptyLabel.setVisible(not self.filtered_employees)
        t.setVisible(bool(self.filtered_employees))

        self.position_floating_button()

    def _text_item(self, text: str, muted: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(text or "—")
        item.setToolTip(text or "")
        if muted or not text:
            item.setForeground(QBrush(QColor(T.TEXT_ACCENT_SOFT)))
        return item

    def _fill_row(self, row: int, emp: dict[str, Any]):
        t = self.employeesTable

        name_item = QTableWidgetItem()
        name_item.setData(Qt.ItemDataRole.UserRole, emp.get("id"))
        t.setItem(row, COL_NAME, name_item)
        t.setCellWidget(row, COL_NAME, self._name_cell(emp["full_name"]))

        positions_count = len(emp.get("positions", []))
        position_text = emp.get("position", "")
        if positions_count > 1:
            position_text = f"{position_text} (+{positions_count - 1})"
        t.setItem(row, COL_POSITION, self._text_item(position_text))
        t.setItem(row, COL_DEPARTMENT, self._text_item(emp.get("department", "")))
        t.setItem(row, COL_PHONE, self._text_item(emp.get("phone", "")))
        t.setItem(row, COL_EMAIL, self._text_item(emp.get("email", ""), muted=True))

        t.setItem(row, COL_ROLE, QTableWidgetItem())
        t.setCellWidget(row, COL_ROLE, self._role_cell(emp.get("role", "")))

        t.setItem(row, COL_ACTIONS, QTableWidgetItem())
        actions = self._actions_cell(emp)
        actions.setVisible(False)
        t.setCellWidget(row, COL_ACTIONS, actions)
        self._action_widgets[row] = actions

    @staticmethod
    def _transparent(widget: QWidget) -> QWidget:
        """Ячейка не перехватывает мышь, чтобы таблица видела hover по строке."""
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        widget.setStyleSheet("background: transparent;")
        return widget

    def _name_cell(self, full_name: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(make_avatar(full_name))
        lbl = QLabel(full_name)
        lbl.setStyleSheet(
            f"border: none; background: transparent; font-size: 13px; font-weight: 600; color: {T.TEXT_DARK_STRONG};"
        )
        lay.addWidget(lbl, 1)
        return self._transparent(w)

    def _role_cell(self, role: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 0, 0, 0)
        badge = QLabel(role or "—")
        badge.setStyleSheet(badge_style("ok" if role == "Пользователь" else "neutral"))
        lay.addWidget(badge)
        lay.addStretch(1)
        return self._transparent(w)

    def _actions_cell(self, emp: dict[str, Any]) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(2)
        lay.addStretch(1)
        for text, tip, hover_bg, hover_fg, slot in (
            ("✎", "Редактировать", T.BTN_EDIT_BG, T.ACCENT_PRIMARY, lambda _=False, e=emp: self.on_edit_employee(e)),
            (
                "✕",
                "Удалить",
                T.BTN_DELETE_BG,
                T.BTN_DELETE_TEXT,
                lambda _=False, e=emp: self.on_delete_employee(e.get("id")),
            ),
        ):
            btn = QPushButton(text)
            btn.setFixedSize(28, 28)
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; border-radius: 6px;"
                f" color: {T.TEXT_ACCENT_SOFT}; font-size: 15px; }}"
                f"QPushButton:hover {{ background-color: {hover_bg}; color: {hover_fg}; }}"
            )
            btn.clicked.connect(slot)
            lay.addWidget(btn)
        w.setStyleSheet("background: transparent;")
        return w

    def _set_hover_row(self, row: int):
        """Подсветка строки под курсором и показ её кнопок ✎ ✕"""
        if row == self._hover_row:
            return
        hover = QColor(T.BG_HOVER_ALT)
        for r, color in ((self._hover_row, None), (row, hover if hover.isValid() else None)):
            if r < 0 or r >= self.employeesTable.rowCount():
                continue
            brush = QBrush(color) if color else QBrush()
            for c in range(self.employeesTable.columnCount()):
                item = self.employeesTable.item(r, c)
                if item:
                    item.setBackground(brush)
        for r, w in self._action_widgets.items():
            w.setVisible(r == row)
        self._hover_row = row

    def _edit_row(self, row: int):
        if 0 <= row < len(self.filtered_employees):
            self.on_edit_employee(self.filtered_employees[row])

    # ==================== РАБОТА С СОТРУДНИКАМИ (CRUD) ====================
    # TODO: в EmployeeService пока нет create/update/delete и диалога сотрудника.
    # Когда будут — по аналогии с DocumentTypesPage (DocumentTypeDialog + DeleteDialog).

    def on_add_employee(self):
        self.show_info_notification("Добавление сотрудника пока не подключено")

    def on_edit_employee(self, employee: dict[str, Any]):
        self.show_info_notification("Редактирование сотрудника пока не подключено")

    def on_delete_employee(self, employee_id):
        self.show_info_notification("Удаление сотрудника пока не подключено")

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def position_floating_button(self):
        if hasattr(self, "floating_btn"):
            margin = 20
            x = self.width() - self.floating_btn.width() - margin
            y = self.height() - self.floating_btn.height() - margin
            self.floating_btn.update_base_position(x, y)
            self.floating_btn.raise_()

    def on_scroll(self, value):
        if hasattr(self, "floating_btn"):
            self.floating_btn.hide_with_animation()
            self.floating_btn.start_hide_timer()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_floating_button()

        if hasattr(self, "notification_manager"):
            self.notification_manager.container.setGeometry(0, 0, self.width(), self.height())

    def get_all_employees(self):
        return self.employees.copy()

    def get_filtered_employees(self):
        return self.filtered_employees.copy()


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = QWidget()
    window.setWindowTitle("Тест - Сотрудники")
    window.setGeometry(100, 100, 1200, 700)

    employees_page = EmployeesPage()

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(employees_page)

    window.show()
    sys.exit(app.exec())
