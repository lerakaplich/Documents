# client/windows/documents/redirect/redirect_dialog.py
"""
Диалог перенаправления документа.

Полностью самостоятельный — собственная логика выбора сотрудников
через дерево (HierarchyBuilder + SelectionManager + TreeBuilder),
плюс поле для комментария.

Сигнал: redirect_confirmed(list_of_employee_ids, comment_text)
"""
import os
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import QDialog, QTreeWidgetItem, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt

from client.core.org_structure.hierarchy_builder import HierarchyBuilder
from client.core.org_structure.selection_manager import SelectionManager
from client.core.org_structure.tree_builder import TreeBuilder
from client.core.org_structure.employee_selection_data_loader import (
    EmployeeSelectionDataLoader,
)
from client.core.themes import apply_theme_to_widget, get_manager
from client.core.themes.icon_utils import icon_path


class RedirectDialog(QDialog):
    """
    Диалог перенаправления документа.

    Args:
        current_recipients: список делегатов (dict с 'id' или строка с именем)
        all_employees:      опционально — список сотрудников с сервера
        parent:             родительское окно
        http_client:        HTTP-клиент (если не передан — берётся из AppState)
    """

    redirect_confirmed = pyqtSignal(list, str)

    def __init__(self,
                 current_recipients: list,
                 all_employees: Optional[list] = None,
                 parent=None,
                 http_client=None):

        super().__init__(parent)

        self._updating = False
        self.http_client = http_client or self._resolve_http_client()

        # ─── предзаполненные ID ───
        self.preselected_ids = self._extract_ids(current_recipients)

        # ─── загрузка данных ───
        self.organizations: List[Dict] = []
        self.departments: List[Dict] = []
        self.employees: List[Dict] = []

        self._load_data(all_employees)

        # ─── инициализация логики ───
        self._init_data()

        # ─── UI ───
        self._init_ui()
        self._populate_tree()
        self._connect_signals()
        self._update_selection_info()

    # ─────────── Вспомогательные ───────────

    @staticmethod
    def _resolve_http_client():
        try:
            from client.core.state.app_state import AppState
            return AppState().http_client
        except Exception:
            return None

    @staticmethod
    def _extract_ids(current_recipients: list) -> List[int]:
        """Достаём ID из текущих делегатов (dict или строк)."""
        ids: List[int] = []
        for emp in current_recipients or []:
            if isinstance(emp, dict) and emp.get("id") is not None:
                ids.append(emp["id"])
        return ids

    def _load_data(self, all_employees: Optional[list]):
        """Грузим организации / отделы / сотрудников."""
        if self.http_client:
            print("[RedirectDialog] Загрузка данных с сервера...")
            try:
                loader = EmployeeSelectionDataLoader(self.http_client)
                self.organizations = loader.load_organizations()
                self.departments = loader.load_departments_flat()
                self.employees = loader.load_employees()
                print(
                    f"[RedirectDialog] Загружено: "
                    f"орг={len(self.organizations)}, "
                    f"отд={len(self.departments)}, "
                    f"сотр={len(self.employees)}"
                )
                if self.employees:
                    emp0 = self.employees[0]
                    print(f"[RedirectDialog] пример сотрудника: "
                          f"id={emp0.get('id')}, "
                          f"name={emp0.get('name')!r}, "
                          f"positions={emp0.get('positions')}")
            except Exception as e:
                print(f"[RedirectDialog] Ошибка загрузки: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("[RedirectDialog] http_client не задан — данные не загружены")

        # Сотрудники снаружи — используем их, если с сервера ничего не пришло
        if all_employees and not self.employees:
            self.employees = list(all_employees)
            print(f"[RedirectDialog] сотрудники взяты снаружи: "
                  f"{len(self.employees)}")

    # ─────────── Инициализация логики ───────────

    def _init_data(self):
        self.builder = HierarchyBuilder(
            self.organizations, self.departments, self.employees
        )
        self.org_hierarchy = self.builder.build()

        self.selection_manager = SelectionManager(
            self.builder.organizations,
            self.builder.departments,
            self.builder.employees,
        )

        # Предзаполнение
        if self.preselected_ids:
            typed = []
            for node_id in self.preselected_ids:
                t = self._resolve_node_type(node_id)
                if t is not None:
                    typed.append((t, node_id))
            if typed:
                self.selection_manager.set_selected(typed)

        self.tree_builder = TreeBuilder(self.org_hierarchy, self.selection_manager)

    def _resolve_node_type(self, node_id):
        if node_id in self.builder.organizations:
            return 1
        if node_id in self.builder.departments:
            return 2
        if node_id in self.builder.employees:
            return 3
        return None

    # ─────────── UI ───────────

    def _load_ui(self):
        """Путь к .ui."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # поднимаемся до client/
        # client/windows/documents/redirect/ → client/
        client_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(current_dir))
        )
        return os.path.join(
            client_dir, "ui", "documents", "redirect_dialog.ui"
        )

    def _init_ui(self):
        from PyQt6.uic import loadUi

        ui_path = self._load_ui()
        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI файл не найден: {ui_path}")

        loadUi(ui_path, self)
        apply_theme_to_widget(self)

        # Заголовок
        if hasattr(self, "titleLabel"):
            self.titleLabel.setText("Перенаправление документа")

        # Настройка дерева
        if hasattr(self, "treeWidget"):
            self.treeWidget.setHeaderLabel("Структура организации")
            self.treeWidget.setIndentation(20)
            self.treeWidget.setItemsExpandable(True)

        # Чекбоксы из темы
        self._apply_checkbox_styles()

    def _apply_checkbox_styles(self):
        if not hasattr(self, "treeWidget"):
            return
        _t = get_manager().current
        checked = icon_path("cb_checked", _t.ICON_COLOR)
        unchecked = icon_path("cb_unchecked", _t.ICON_COLOR)
        partial = icon_path("cb_partial", _t.ICON_COLOR)

        cb_style = f"""
            QTreeWidget::indicator {{
                width: 18px; height: 18px;
            }}
            QTreeWidget::indicator:unchecked {{
                image: url({unchecked});
            }}
            QTreeWidget::indicator:checked {{
                image: url({checked});
            }}
            QTreeWidget::indicator:indeterminate {{
                image: url({partial});
            }}
        """
        current = self.treeWidget.styleSheet() or ""
        self.treeWidget.setStyleSheet(current + cb_style)

    def _connect_signals(self):
        if hasattr(self, "searchEdit"):
            self.searchEdit.textChanged.connect(self._on_search)
        if hasattr(self, "btnSearch"):
            self.btnSearch.clicked.connect(self._on_search_clicked)
        if hasattr(self, "treeWidget"):
            self.treeWidget.itemChanged.connect(self._on_tree_item_changed)
        if hasattr(self, "sendButton"):
            self.sendButton.clicked.connect(self._on_send)

    # ─────────── Дерево ───────────

    def _populate_tree(self, filter_text: str = ""):
        if not hasattr(self, "treeWidget"):
            return

        self.treeWidget.blockSignals(True)
        try:
            self.treeWidget.clear()
            items = self.tree_builder.build_tree(filter_text)

            for item in items:
                self.treeWidget.addTopLevelItem(item)
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get("id") and data.get("id") > 0:
                    node_id = data["id"]
                    if self.selection_manager.is_selected(node_id):
                        item.setCheckState(0, Qt.CheckState.Checked)
                    else:
                        item.setCheckState(0, Qt.CheckState.Unchecked)
                    self._set_checkboxes_recursive(item)

            self._sync_all_checkboxes()
        finally:
            self.treeWidget.blockSignals(False)

    def _set_checkboxes_recursive(self, item):
        for i in range(item.childCount()):
            child = item.child(i)
            child_data = child.data(0, Qt.ItemDataRole.UserRole)
            if child_data and child_data.get("id") and child_data.get("id") > 0:
                node_id = child_data["id"]
                child.setCheckState(
                    0,
                    Qt.CheckState.Checked
                    if self.selection_manager.is_selected(node_id)
                    else Qt.CheckState.Unchecked,
                )
            self._set_checkboxes_recursive(child)

    def _sync_all_checkboxes(self):
        def sync_item(item):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("id") and data.get("id") > 0:
                node_id = data["id"]
                is_sel = self.selection_manager.is_selected(node_id)
                item.setCheckState(
                    0, Qt.CheckState.Checked if is_sel else Qt.CheckState.Unchecked
                )
            for i in range(item.childCount()):
                sync_item(item.child(i))

        for i in range(self.treeWidget.topLevelItemCount()):
            sync_item(self.treeWidget.topLevelItem(i))

    def _on_tree_item_changed(self, item, column):
        if self._updating:
            return
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return

        new_state = item.checkState(column)
        is_checked = (new_state == Qt.CheckState.Checked)

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        node_id = data.get("id")
        node_type = data.get("type")
        if node_id is None or node_id < 0 or node_type is None:
            return

        self._updating = True
        try:
            self.selection_manager.toggle(node_id, is_checked, node_type)

            all_descendants = self._get_all_descendants(item)
            desc_pairs = set()
            for child_item in all_descendants:
                cd = child_item.data(0, Qt.ItemDataRole.UserRole)
                if cd and cd.get("id") and cd.get("id") > 0:
                    t = cd.get("type")
                    if t is not None:
                        desc_pairs.add((t, cd["id"]))

            for t, cid in desc_pairs:
                self.selection_manager.toggle(cid, is_checked, t)

            for child_item in all_descendants:
                cd = child_item.data(0, Qt.ItemDataRole.UserRole)
                if cd and cd.get("id") and cd.get("id") > 0:
                    child_item.setCheckState(
                        0,
                        Qt.CheckState.Checked if is_checked
                        else Qt.CheckState.Unchecked,
                    )

            if item.parent():
                self._update_parent_checks_only(item.parent())

            self._update_selection_info()
        finally:
            self._updating = False

    def _update_parent_checks_only(self, item):
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return
        checked = 0
        total = 0
        for i in range(item.childCount()):
            ch = item.child(i)
            if ch.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                total += 1
                if ch.checkState(0) == Qt.CheckState.Checked:
                    checked += 1
        if total == 0:
            return
        new_state = (Qt.CheckState.Checked if checked == total
                     else Qt.CheckState.Unchecked)
        item.setCheckState(0, new_state)
        if item.parent():
            self._update_parent_checks_only(item.parent())

    def _get_all_descendants(self, item):
        out = []
        for i in range(item.childCount()):
            child = item.child(i)
            out.append(child)
            out.extend(self._get_all_descendants(child))
        return out

    # ─────────── Поиск ───────────

    def _on_search(self, text: str):
        self._populate_tree(text)

    def _on_search_clicked(self):
        if hasattr(self, "searchEdit"):
            self._populate_tree(self.searchEdit.text())

    # ─────────── Инфо-лейбл ───────────

    def _update_selection_info(self):
        if not hasattr(self, "selectionInfoLabel"):
            return
        items = self.selection_manager.get_selected_items()

        org_c = dept_c = emp_c = 0
        for t, _ in items:
            if t == 1:   org_c += 1
            elif t == 2: dept_c += 1
            elif t == 3: emp_c += 1

        total = len(items)
        if total == 0:
            self.selectionInfoLabel.setText("Выбрано: 0 элементов")
            return

        parts = [f"Выбрано: {total} элементов"]
        if org_c:  parts.append(f"организаций: {org_c}")
        if dept_c: parts.append(f"отделов: {dept_c}")
        if emp_c:  parts.append(f"сотрудников: {emp_c}")
        self.selectionInfoLabel.setText(" (".join(parts) + ")")

    # ─────────── Отправка ───────────

    def _on_send(self):
        """Собираем ID выбранных сотрудников и комментарий → сигнал."""
        employee_ids = []
        for t, node_id in self.selection_manager.get_selected_items():
            if t == 3:
                employee_ids.append(node_id)

        # Если выбраны отделы/организации — соберём из них сотрудников
        if not employee_ids:
            for t, node_id in self.selection_manager.get_selected_items():
                if t == 2:  # department
                    for emp_id, emp in self.builder.employees.items():
                        for pos in (emp.get("positions") or []):
                            if pos.get("department_id") == node_id:
                                employee_ids.append(emp_id)
                                break
                elif t == 1:  # organization
                    for emp_id, emp in self.builder.employees.items():
                        for pos in (emp.get("positions") or []):
                            # отдел принадлежит этой организации?
                            dept_id = pos.get("department_id")
                            dept = self.builder.departments.get(dept_id)
                            if dept and dept.get("organization_id") == node_id:
                                employee_ids.append(emp_id)
                                break

        # Убираем дубли, сохраняя порядок
        seen = set()
        employee_ids = [x for x in employee_ids
                        if not (x in seen or seen.add(x))]

        if not employee_ids:
            QMessageBox.warning(
                self, "Внимание",
                "Не выбрано ни одного сотрудника для перенаправления."
            )
            return

        comment = ""
        if hasattr(self, "commentTextEdit"):
            comment = self.commentTextEdit.toPlainText().strip()

        print(f"[RedirectDialog] ID сотрудников: {employee_ids}, "
              f"комментарий: {comment!r}")

        self.redirect_confirmed.emit(employee_ids, comment)
        self.accept()

    # ─────────── Тема ───────────

    def reapply_theme(self):
        apply_theme_to_widget(self)
        self._apply_checkbox_styles()