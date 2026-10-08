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
    QLabel,
    QMenu,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.uic import loadUi

from client.core.config import config
from client.core.http_client import HttpClient
from client.core.state.app_state import AppState
from client.core.themes import T, apply_theme_to_widget, get_menu_style
from client.core.utils.context_menu import SEPARATOR, attach_context_menu
from client.services.employee_service import EmployeeService
from client.services.org_service import get_org_service
from client.windows.animations.animated_notification import NotificationManager
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.common import count_text, make_avatar, normalize_employee
from client.windows.system.system_actions import SystemActions
from client.windows.system.system_utils import collect_paths, org_label, to_tree, work_phone
from client.windows.system.table_utils import ResizableColumns, header_label

logger = logging.getLogger(__name__)

COL_NAME, COL_POSITION, COL_DEPARTMENT, COL_PHONE, COL_EMAIL = range(5)
HEADERS = ["ФИО", "Должность", "Отдел", "Рабочий телефон", "Email"]
COL_KEYS = {  # столбцы, по которым можно сортировать кликом по заголовку
    COL_NAME: "full_name",
    COL_POSITION: "position",
    COL_DEPARTMENT: "dept_path",
    COL_PHONE: "work_phone",
    COL_EMAIL: "email",
}
COLUMN_WEIGHTS = [290, 190, 260, 150, 200]
SETTINGS_KEY = "system_employees"  # ключ раскладки (ширина/порядок столбцов) в настройках
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
    employees_changed = pyqtSignal()  # сотрудника добавили / изменили / удалили

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
        self._dept_paths: dict[int, str] = {}  # id отдела -> "МАЗ / НТЦ / Телематика"

        # Состояние
        self.current_sort = "А→Я"
        self._sort_col = -1  # сортировка кликом по заголовку (-1 — нет)
        self._sort_asc = True
        self.is_loading = False
        self._hover_row = -1

        # Инициализация
        self.init_ui()
        self.setup_connections()

        # Создаем менеджер уведомлений
        self.notification_manager = NotificationManager(self, max_visible=3)

        # Действия (диалоги + сервисы)
        self.system_actions = SystemActions(self, self.http_client)
        self.system_actions.message.connect(self._on_action_message)
        self.system_actions.employees_changed.connect(self._on_employees_changed)

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
        t.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        h = t.horizontalHeader()
        h.setHighlightSections(False)
        h.setSectionsClickable(True)
        h.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        h.sectionClicked.connect(self._on_header_clicked)
        # ширину столбцов тянут мышью, столбцы можно переставлять; раскладка запоминается
        self._columns = ResizableColumns(t, COLUMN_WEIGHTS, settings_key=SETTINGS_KEY)

        t.cellEntered.connect(lambda row, _col: self._set_hover_row(row))
        t.cellDoubleClicked.connect(lambda row, _col: self._edit_row(row))
        attach_context_menu(t, self._row_menu_items)
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

    def _on_action_message(self, kind: str, text: str):
        {"success": self.show_success_notification, "error": self.show_error_notification}.get(
            kind, self.show_info_notification
        )(text)

    # ==================== ЗАГРУЗКА ДАННЫХ ====================

    def load_employees(self, notify: bool = True):
        """Загрузить сотрудников из API"""
        if self.is_loading:
            return

        self.is_loading = True

        try:
            raw_employees = self.employee_service.get_all_employees()
            self._load_dept_paths()
            self.employees = [self._prepare(e) for e in raw_employees]

            self.is_loading = False
            self._rebuild_org_combo()
            self.update_display()
            self.data_loaded.emit()

            if notify and self.employees:
                self.show_success_notification(f"Загружено {len(self.employees)} сотрудников")

        except Exception as e:
            self.is_loading = False

            logger.exception(f"Ошибка загрузки сотрудников: {e}")

            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось загрузить сотрудников")

    def _on_employees_changed(self):
        """Сотрудника добавили / изменили / удалили — перезагружаем и сообщаем остальным вкладкам"""
        self.load_employees(notify=False)
        self.employees_changed.emit()

    def _load_dept_paths(self):
        """Пути отделов «МАЗ / НТЦ / Телематика» по структуре всех организаций"""
        paths: dict[int, str] = {}
        try:
            org_service = get_org_service(self.http_client)
            for org in org_service.get_all_organizations():
                tree = to_tree(org_service.get_org_structure(org["id"]))
                paths.update(collect_paths(org_label(org), tree))
        except Exception as e:
            logger.exception(f"Не удалось загрузить структуру для путей отделов: {e}")
        self._dept_paths = paths

    def _prepare(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Данные сотрудника для таблицы: нормализация + исходные данные + вычисляемые поля"""
        emp = dict(normalize_employee(raw))  # копия: исходный dict с сервера не трогаем
        emp["_raw"] = raw  # исходные данные нужны диалогу редактирования
        emp["work_phone"] = work_phone(emp)
        emp["dept_path"] = self._dept_path(emp)
        return emp

    def _dept_path(self, emp: dict[str, Any]) -> str:
        positions = emp.get("positions") or []
        dep_id = positions[0].get("department_id") if positions else None
        path = self._dept_paths.get(dep_id) if dep_id is not None else None
        if path:
            return path
        # путь по структуре не нашёлся — собираем из того, что есть
        return " / ".join(p for p in (emp.get("organization"), emp.get("department")) if p)

    def _rebuild_org_combo(self):
        current = self.orgCombo.currentText()
        orgs = sorted({e["organization"] for e in self.employees if e.get("organization")})
        self.orgCombo.blockSignals(True)
        self.orgCombo.clear()
        self.orgCombo.addItems([ALL_ORGS, *orgs])
        self.orgCombo.setCurrentIndex(max(self.orgCombo.findText(current), 0))
        self.orgCombo.blockSignals(False)
        # сам фильтр узкий (как поиск), а выпадающий список раскрывается под длинные названия
        popup = self.orgCombo.view()
        popup.setMinimumWidth(max(self.orgCombo.width(), popup.sizeHintForColumn(0) + 30))

    # ==================== СОРТИРОВКА ====================

    def show_sort_menu(self):
        """Показать меню сортировки"""
        menu = QMenu(self)
        menu.setStyleSheet(get_menu_style())

        sort_options = {
            "А→Я (по ФИО)": self.sort_by_name_asc,
            "Я→А (по ФИО)": self.sort_by_name_desc,
            "По должности": self.sort_by_position,
            "По отделу": self.sort_by_department,
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
        return sorted(employees, key=lambda x: (not x.get("dept_path"), x.get("dept_path", "").lower()))

    def _on_header_clicked(self, col: int):
        """Клик по заголовку: сортировка по столбцу, повторный клик — в обратную сторону"""
        if col not in COL_KEYS:
            return
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col, self._sort_asc = col, True
        self.current_sort = "А→Я"
        self.btnSort.setText("Сортировка ▼")
        self._refresh_headers()
        self.update_reset_button_visibility()
        self.update_display()

    def _refresh_headers(self):
        """Подписи заголовков со стрелкой у столбца, по которому идёт сортировка"""
        self.employeesTable.setHorizontalHeaderLabels(
            [header_label(title, col, self._sort_col, self._sort_asc) for col, title in enumerate(HEADERS)]
        )

    def apply_sort(self, sort_func, sort_name):
        self.current_sort = sort_name
        self._sort_col = -1
        self._refresh_headers()
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
        return self.current_sort != "А→Я" or self._sort_col in COL_KEYS

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
        self._sort_col = -1
        self._sort_asc = True
        self._refresh_headers()
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
                    for key in ("full_name", "position", "dept_path", "work_phone", "email")
                )
            ]

        # Сортировка кликом по заголовку (пустые значения всегда в конце)
        if self._sort_col in COL_KEYS:
            key = COL_KEYS[self._sort_col]
            filled = [e for e in filtered if e.get(key)]
            empty = [e for e in filtered if not e.get(key)]
            filled.sort(key=lambda e: str(e[key]).lower(), reverse=not self._sort_asc)
            return filled + empty

        # Сортировка из меню
        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "А→Я (по ФИО)": self.sort_by_name_asc,
            "Я→А (по ФИО)": self.sort_by_name_desc,
            "По должности": self.sort_by_position,
            "По отделу": self.sort_by_department,
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
        t.setItem(row, COL_DEPARTMENT, self._text_item(emp.get("dept_path", "")))
        t.setItem(row, COL_PHONE, self._text_item(emp.get("work_phone", "")))
        t.setItem(row, COL_EMAIL, self._text_item(emp.get("email", ""), muted=True))

    @staticmethod
    def _transparent(widget: QWidget) -> QWidget:
        """Ячейка не перехватывает мышь, чтобы таблица видела hover и ПКМ по строке."""
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

    def _set_hover_row(self, row: int):
        """Подсветка строки под курсором"""
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
        self._hover_row = row

    def _edit_row(self, row: int):
        if 0 <= row < len(self.filtered_employees):
            self.on_edit_employee(self.filtered_employees[row])

    # ==================== КОНТЕКСТНОЕ МЕНЮ ====================

    def _row_menu_items(self, pos):
        """Меню по правой кнопке на строке сотрудника"""
        row = self.employeesTable.rowAt(pos.y())
        if not 0 <= row < len(self.filtered_employees):
            return None
        self._set_hover_row(row)
        emp = self.filtered_employees[row]
        return [
            ("Редактировать", lambda: self.on_edit_employee(emp)),
            SEPARATOR,
            ("Удалить", lambda: self.on_delete_employee(emp)),
        ]

    # ==================== РАБОТА С СОТРУДНИКАМИ (CRUD) ====================

    def on_add_employee(self):
        self.system_actions.add_employee()

    def on_edit_employee(self, employee: dict[str, Any]):
        self.system_actions.edit_employee(employee)

    def on_delete_employee(self, employee: dict[str, Any]):
        self.system_actions.delete_employee(employee)

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
