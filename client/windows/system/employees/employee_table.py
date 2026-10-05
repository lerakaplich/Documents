# client/windows/system/employees/employee_table.py
"""Таблица сотрудников вместо списка карточек.

Принимает те же словари, что и EmployeeCard (id, full_name, position, company,
department, subdivision, work_phone, email, rights, _raw), и отдаёт те же сигналы:
edit_clicked(dict), delete_clicked(int).
"""

import sys

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from client.core.hover_actions import DELETE_ICON, EDIT_ICON, style_icon_button, tok

COLUMNS = ["ФИО", "Должность", "Подразделение", "Телефон", "Email", "Права", ""]
COL_NAME, COL_POS, COL_DEPT, COL_PHONE, COL_EMAIL, COL_RIGHTS, COL_ACTIONS = range(7)
ROW_HEIGHT = 44
AVATAR = 28


def _initials(full_name: str) -> str:
    parts = [p for p in full_name.replace(".", " ").split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def _avatar_icon(full_name: str) -> QIcon:
    pm = QPixmap(AVATAR, AVATAR)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    bg = QColor(tok("ACCENT_PRIMARY", "#e0397f"))
    bg.setAlpha(60)
    p.setBrush(bg)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, AVATAR, AVATAR)
    p.setPen(QColor(tok("ACCENT_PRIMARY", "#e0397f")))
    f = QFont()
    f.setPointSize(8)
    f.setBold(True)
    p.setFont(f)
    p.drawText(QRectF(0, 0, AVATAR, AVATAR), Qt.AlignmentFlag.AlignCenter, _initials(full_name))
    p.end()
    return QIcon(pm)


class _RowActions(QWidget):
    """Иконки справа в строке."""

    def __init__(self, on_edit, on_delete, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(2)
        lay.addStretch()
        self.edit_btn = QPushButton()
        self.delete_btn = QPushButton()
        style_icon_button(self.edit_btn, EDIT_ICON, "Редактировать")
        style_icon_button(self.delete_btn, DELETE_ICON, "Удалить", danger=True)
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(on_edit)
        self.delete_btn.clicked.connect(on_delete)
        lay.addWidget(self.edit_btn)
        lay.addWidget(self.delete_btn)
        self.setVisible_actions(False)

    def setVisible_actions(self, visible: bool) -> None:
        self.edit_btn.setVisible(visible)
        self.delete_btn.setVisible(visible)


class EmployeeTable(QTableWidget):
    edit_clicked = pyqtSignal(dict)
    delete_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(0, len(COLUMNS), parent)
        self._employees = {}  # row -> dict
        self._group_rows = set()
        self._actions = {}  # row -> _RowActions
        self._hover_row = -1

        self.setHorizontalHeaderLabels(COLUMNS)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.setShowGrid(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIconSize(QSize(AVATAR, AVATAR))
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        hh = self.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(COL_POS, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(COL_DEPT, QHeaderView.ResizeMode.Stretch)
        for c in (COL_PHONE, COL_EMAIL, COL_RIGHTS):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(COL_ACTIONS, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(COL_NAME, 300)
        self.setColumnWidth(COL_POS, 190)
        self.setColumnWidth(COL_ACTIONS, 80)

        border = tok("BORDER_DEFAULT", "#3a3a3a")
        self.setStyleSheet(
            f"""
            QTableWidget {{
                background: transparent;
                border: none;
                color: {tok("TEXT_PRIMARY", "#ececec")};
                font-size: 13px;
            }}
            QTableWidget::item {{
                border-bottom: 1px solid {border};
                padding: 4px 8px;
            }}
            QHeaderView {{ background: transparent; }}
            QHeaderView::section {{
                background: transparent;
                color: {tok("TEXT_TERTIARY", "#9a9a9a")};
                border: none;
                border-bottom: 1px solid {border};
                padding: 6px 8px;
                font-weight: 500;
            }}
            """
        )

        self.cellEntered.connect(lambda row, _col: self._set_hover_row(row))
        self.cellDoubleClicked.connect(self._on_double_click)

    # ---------- данные ----------

    def set_employees(self, employees: list) -> None:
        self.set_groups([(None, employees)])

    def set_groups(self, groups: list) -> None:
        """groups: [(заголовок группы | None, [dict сотрудника, ...]), ...]"""
        self.clearContents()
        self._employees.clear()
        self._group_rows.clear()
        self._actions.clear()
        self._hover_row = -1

        total = sum(len(emps) for _t, emps in groups) + sum(1 for t, _e in groups if t)
        self.setRowCount(total)

        row = 0
        for title, emps in groups:
            if title:
                self._add_group_row(row, title, len(emps))
                row += 1
            for emp in emps:
                self._add_employee_row(row, emp)
                row += 1

    def _add_group_row(self, row: int, title: str, count: int) -> None:
        item = QTableWidgetItem(f"{title}  ·  {count}")
        f = item.font()
        f.setBold(True)
        item.setFont(f)
        item.setForeground(QBrush(QColor(tok("TEXT_TERTIARY", "#9a9a9a"))))
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.setItem(row, 0, item)
        self.setSpan(row, 0, 1, len(COLUMNS))
        self.setRowHeight(row, 34)
        self._group_rows.add(row)

    def _add_employee_row(self, row: int, emp: dict) -> None:
        self._employees[row] = emp

        name = emp.get("full_name") or "ФИО не указано"
        name_item = QTableWidgetItem(name)
        name_item.setIcon(_avatar_icon(name))
        self.setItem(row, COL_NAME, name_item)

        position = emp.get("position") or "—"
        self.setItem(row, COL_POS, self._text_item(position, muted=not emp.get("position")))

        parts = [p for p in (emp.get("company"), emp.get("department"), emp.get("subdivision")) if p]
        dept = ", ".join(parts)
        dept_item = self._text_item(dept or "—", muted=not dept)
        dept_item.setToolTip(dept)  # полный путь — во всплывающей подсказке
        self.setItem(row, COL_DEPT, dept_item)

        phone = emp.get("work_phone") or "—"
        self.setItem(row, COL_PHONE, self._text_item(phone, muted=not emp.get("work_phone")))
        email = emp.get("email") or "—"
        self.setItem(row, COL_EMAIL, self._text_item(email, muted=True))

        self.setCellWidget(row, COL_RIGHTS, self._rights_badge(emp.get("rights", "")))
        self.setItem(row, COL_ACTIONS, QTableWidgetItem(""))

        actions = _RowActions(
            on_edit=lambda _=False, e=emp: self.edit_clicked.emit(e),
            on_delete=lambda _=False, e=emp: self.delete_clicked.emit(e.get("id", 0)),
        )
        self.setCellWidget(row, COL_ACTIONS, actions)
        self._actions[row] = actions

    @staticmethod
    def _text_item(text: str, muted: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        if muted:
            item.setForeground(QBrush(QColor(tok("TEXT_MUTED_ALT", "#9a9a9a"))))
        return item

    @staticmethod
    def _rights_badge(rights: str) -> QWidget:
        if not rights:
            text, fg = "Не назначены", tok("TEXT_DANGER", "#e5534b")
        elif rights.lower() == "администратор":
            text, fg = rights, tok("ACCENT_PRIMARY", "#e0397f")
        elif rights.lower() == "пользователь":
            text, fg = rights, tok("TEXT_SUCCESS", "#3ec27a")
        else:
            text, fg = rights, tok("TEXT_MUTED_ALT", "#9a9a9a")

        wrap = QWidget()
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(8, 0, 8, 0)
        label = QLabel(text)
        color = QColor(fg)
        label.setStyleSheet(
            f"background-color: rgba({color.red()},{color.green()},{color.blue()},40);"
            f"color: {fg}; border-radius: 10px; padding: 2px 10px;"
            "font-size: 11px; font-weight: 600;"
        )
        lay.addWidget(label)
        lay.addStretch()
        return wrap

    # ---------- наведение на строку ----------

    def _set_hover_row(self, row: int) -> None:
        if row == self._hover_row:
            return
        self._paint_row(self._hover_row, False)
        self._hover_row = row if row not in self._group_rows else -1
        self._paint_row(self._hover_row, True)

    def _paint_row(self, row: int, hovered: bool) -> None:
        if row < 0 or row not in self._employees:
            return
        brush = QBrush(QColor(tok("BG_CARD_ELEVATED", "#282828"))) if hovered else QBrush()
        for col in range(len(COLUMNS)):
            item = self.item(row, col)
            if item is not None:
                item.setBackground(brush)
        actions = self._actions.get(row)
        if actions:
            actions.setVisible_actions(hovered)

    def leaveEvent(self, event):
        self._set_hover_row(-1)
        super().leaveEvent(event)

    def _on_double_click(self, row: int, _col: int) -> None:
        emp = self._employees.get(row)
        if emp:
            self.edit_clicked.emit(emp)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    t = EmployeeTable()
    t.resize(1100, 500)
    t.set_groups(
        [
            (
                None,
                [
                    {
                        "id": 1,
                        "full_name": "Григорьев Андрей Михайлович",
                        "position": "Преподаватель-методист",
                        "company": "БГУИР",
                        "department": "Отдел сопровождения образовательных программ",
                        "work_phone": "101",
                        "email": "i.ivanov@maz.by",
                        "rights": "Пользователь",
                    }
                ],
            ),
            (
                'ОАО "МАЗ"',
                [
                    {
                        "id": 2,
                        "full_name": "Апанас Ярослав Эдуардович",
                        "position": "Инженер-конструктор",
                        "company": 'ОАО "МАЗ"',
                        "department": "НТЦ",
                        "subdivision": "Мехатроники",
                        "work_phone": "101",
                        "email": "i.ivanov@maz.by",
                        "rights": "Пользователь",
                    },
                    {"id": 3, "full_name": "Анисимович Н. А.", "rights": ""},
                ],
            ),
        ]
    )
    t.edit_clicked.connect(lambda d: print("edit", d["full_name"]))
    t.delete_clicked.connect(lambda i: print("delete", i))
    t.show()
    sys.exit(app.exec())
