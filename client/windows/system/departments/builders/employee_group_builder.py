# client/windows/system/departments/builders/employee_group_builder.py
import os
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon


def build_employee_group(title: str, is_expanded: bool = True) -> QWidget:
    """Создаёт сворачиваемую группу сотрудников (используется внутри DepartmentNode)."""
    from client.core.themes import get_manager
    from client.core.themes.icon_utils import icon

    _t = get_manager().current
    down_icon = icon("down_arrow", _t.ICON_COLOR)
    up_icon   = icon("up_arrow",   _t.ICON_COLOR)

    group_widget = QWidget()
    group_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    header = QFrame()
    header.setStyleSheet(f"""
        QFrame {{
            border: 1px solid {_t.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 4px 8px;
        }}
        QFrame:hover {{
            background-color: {_t.BG_HOVER_ACCENT_SOFT};
            border: 1px solid {_t.ACCENT_PRIMARY};
        }}
    """)
    hl = QHBoxLayout(header)
    hl.setContentsMargins(8, 4, 8, 4)

    btn = QPushButton()
    btn.setFixedSize(24, 24)
    btn.setFlat(True)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet("QPushButton { border: none; background: transparent; }")
    btn.setIcon(up_icon if is_expanded else down_icon)
    btn.setIconSize(QSize(16, 16))

    lbl = QLabel(title)
    lbl.setStyleSheet(
        f"font-weight: bold; font-size: 14px; color: {_t.TEXT_BLACK}; "
        f"background: transparent; border: none;"
    )

    hl.addWidget(btn)
    hl.addWidget(lbl)
    hl.addStretch()

    content = QWidget()
    cl = QVBoxLayout(content)
    cl.setContentsMargins(30, 4, 0, 8)
    cl.setSpacing(8)

    main = QVBoxLayout(group_widget)
    main.setContentsMargins(0, 0, 0, 0)
    main.setSpacing(2)
    main.addWidget(header)
    main.addWidget(content)

    anim = QPropertyAnimation(content, b"maximumHeight")
    anim.setDuration(250)
    anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    state = {'expanded': is_expanded}

    def toggle():
        state['expanded'] = not state['expanded']
        btn.setIcon(up_icon if state['expanded'] else down_icon)
        anim.stop()
        if state['expanded']:
            content.setVisible(True)
            content.updateGeometry()
            content.adjustSize()
            target = max(content.sizeHint().height(), 100)
            content.setMaximumHeight(0)
            anim.setStartValue(0)
            anim.setEndValue(target)
        else:
            current = max(content.height(), 100)
            anim.setStartValue(current)
            anim.setEndValue(0)
        anim.start()

    def on_finished():
        if state['expanded']:
            content.setMaximumHeight(16777215)
        else:
            content.setVisible(False)
            content.setMaximumHeight(0)

    anim.finished.connect(on_finished)
    header.mousePressEvent = lambda _e: toggle()
    btn.clicked.connect(toggle)

    if is_expanded:
        content.setVisible(True)
        content.setMaximumHeight(16777215)
    else:
        content.setVisible(False)
        content.setMaximumHeight(0)

    group_widget.add_card = lambda w: cl.addWidget(w)
    return group_widget