# client/windows/system/departments/department_node.py

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.uic import loadUi

from client.windows.system.departments.department_card import DepartmentCard


class DepartmentNode(QWidget):
    """
    Раскрывающийся виджет для отдела с анимацией.
    Заголовок стилизован как на странице сотрудников (CollapsibleGroup).
    """
    edit_clicked = pyqtSignal(dict)
    delete_clicked = pyqtSignal(int)

    def __init__(self, department_data: dict, parent=None, is_root=False):
        super().__init__(parent)
        self.department_data = department_data
        self.is_root = is_root
        self.children_nodes = []
        self.card = None

        self._expanded = False
        self._setup_ui()
        self._fill_data()
        self._connect_signals()
        self._setup_animation()

        # Изначально содержимое скрыто (высота 0)
        self.contentWidget.setVisible(True)
        self.contentWidget.setMaximumHeight(0)

    def _setup_ui(self):
        ui_path = self._get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)
            self._setup_expand_button()
            self._apply_header_style()
        else:
            self._setup_placeholder()

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum
        )

        if hasattr(self, 'contentLayout'):
            self.contentLayout.setContentsMargins(30, 4, 0, 0)

    def _get_ui_path(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'departments', 'department_node.ui')
        return os.path.normpath(ui_path)

    def _setup_placeholder(self):
        from PyQt6.QtWidgets import QLabel, QVBoxLayout
        layout = QVBoxLayout(self)
        label = QLabel("DepartmentNode (UI not found)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        self.contentWidget = QWidget()
        self.contentLayout = QVBoxLayout(self.contentWidget)
        layout.addWidget(self.contentWidget)

    def _setup_expand_button(self):
        if not hasattr(self, 'expandBtn'):
            return

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        icons_dir = os.path.join(base_dir, 'icons')
        down_path = os.path.join(icons_dir, 'down_arrow.svg')
        up_path = os.path.join(icons_dir, 'up_arrow.svg')

        self.down_icon = QIcon(down_path) if os.path.exists(down_path) else QIcon()
        self.up_icon = QIcon(up_path) if os.path.exists(up_path) else QIcon()

        self.expandBtn.setIcon(self.down_icon)
        self.expandBtn.setIconSize(QSize(16, 16))
        self.expandBtn.setText("")
        self.expandBtn.setArrowType(Qt.ArrowType.NoArrow)

    def _apply_header_style(self):
        if hasattr(self, 'headerFrame'):
            self.headerFrame.setStyleSheet("""
                QFrame#headerFrame {
                    background-color: #F8F9FA;
                    border: 1px solid #DEE2E6;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QFrame#headerFrame:hover {
                    background-color: #FDFBF7;
                    border: 1px solid #CCAB6E;
                }
            """)
        if hasattr(self, 'nameLabel'):
            self.nameLabel.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 15px;
                    color: #212529;
                    background: transparent;
                    border: none;
                }
            """)
        if hasattr(self, 'typeLabel'):
            self.typeLabel.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #6C757D;
                    background: transparent;
                    border: none;
                }
            """)
        if hasattr(self, 'codeLabel'):
            self.codeLabel.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #7A6A50;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                }
            """)

    def _setup_animation(self):
        self.animation = QPropertyAnimation(self.contentWidget, b"maximumHeight")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.finished.connect(self._on_animation_finished)

    def _fill_data(self):
        data = self.department_data
        if hasattr(self, 'nameLabel'):
            self.nameLabel.setText(data.get('name', 'Без названия'))
        if hasattr(self, 'typeLabel'):
            dept_type = data.get('type_display', data.get('department_type', ''))
            self.typeLabel.setText(dept_type if dept_type else '')
        if hasattr(self, 'codeLabel'):
            code = data.get('code', data.get('id', ''))
            self.codeLabel.setText(f"Код: {code}" if code else '')

    def _connect_signals(self):
        if hasattr(self, 'expandBtn'):
            self.expandBtn.clicked.connect(self.toggle_expand)
            if hasattr(self, 'headerFrame'):
                self.headerFrame.mousePressEvent = self._on_header_click

    def _on_header_click(self, event):
        self.toggle_expand()

    def toggle_expand(self):
        self._expanded = not self._expanded

        if hasattr(self, 'expandBtn'):
            self.expandBtn.setIcon(self.up_icon if self._expanded else self.down_icon)

        self.animation.stop()

        if self._expanded:
            # Разворачиваем: делаем виджет видимым и вычисляем целевую высоту
            self.contentWidget.setVisible(True)
            # Принудительно активируем layout, чтобы пересчитать размеры
            if self.contentWidget.layout():
                self.contentWidget.layout().activate()
            self.contentWidget.updateGeometry()
            self.contentWidget.adjustSize()
            target_height = self.contentWidget.sizeHint().height()
            if target_height <= 0:
                target_height = self.contentWidget.minimumHeight()
                if target_height <= 0:
                    target_height = 100
            # Начинаем анимацию с 0 до target_height
            self.contentWidget.setMaximumHeight(0)
            self.animation.setStartValue(0)
            self.animation.setEndValue(target_height)
        else:
            # Сворачиваем: анимируем от текущей высоты до 0
            current_height = self.contentWidget.height()
            if current_height <= 0:
                current_height = self.contentWidget.sizeHint().height()
                if current_height <= 0:
                    current_height = 100
            self.animation.setStartValue(current_height)
            self.animation.setEndValue(0)

        self.animation.start()

    def _on_animation_finished(self):
        if not self._expanded:
            self.contentWidget.setVisible(False)
            self.contentWidget.setMaximumHeight(0)
        else:
            # Снимаем ограничение, чтобы содержимое могло расти дальше
            self.contentWidget.setMaximumHeight(16777215)
            self.contentWidget.setVisible(True)
        self.updateGeometry()
        if self.parent():
            self.parent().updateGeometry()

    def add_child(self, child_node):
        self.children_nodes.append(child_node)
        if hasattr(self, 'contentLayout'):
            self.contentLayout.addWidget(child_node)
            # Обновляем геометрию родителя, чтобы учесть новый дочерний узел
            self.update_content_geometry()

    def set_card_data(self, card_data: dict):
        if self.is_root:
            return

        self.card = DepartmentCard(card_data)
        self.card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        self.card.edit_clicked.connect(self.edit_clicked.emit)
        self.card.delete_clicked.connect(self.delete_clicked.emit)

        if hasattr(self, 'contentLayout'):
            self.contentLayout.insertWidget(0, self.card)

    def update_data(self, new_data: dict):
        self.department_data.update(new_data)
        self._fill_data()
        if self.card:
            self.card.update_data(new_data)

    def set_expanded(self, expanded: bool):
        if self._expanded != expanded:
            self.toggle_expand()

    def is_expanded(self) -> bool:
        return self._expanded

    def add_content_widget(self, widget):
        """
        Добавляет произвольный виджет (например, карточку сотрудника) в содержимое узла.
        Вставляет сразу после карточки отдела (если она есть), но перед дочерними узлами.
        """
        if hasattr(self, 'contentLayout'):
            index = 1 if self.card is not None else 0
            self.contentLayout.insertWidget(index, widget)
            # Принудительно обновляем layout и геометрию
            self.contentLayout.update()
            self.contentWidget.updateGeometry()
            self.contentWidget.adjustSize()
            # Отложенное обновление, чтобы sizeHint пересчитался после добавления
            QTimer.singleShot(0, self._delayed_update)
        else:
            print("Warning: contentLayout not found")

    def _delayed_update(self):
        """Отложенное обновление геометрии после добавления виджетов"""
        if self.contentWidget.layout():
            self.contentWidget.layout().activate()
        self.contentWidget.updateGeometry()
        self.contentWidget.adjustSize()

    def update_content_geometry(self):
        """Обновляет геометрию contentWidget для пересчета sizeHint после добавления дочерних виджетов"""
        if self.contentWidget.layout():
            self.contentWidget.layout().activate()
        self.contentWidget.updateGeometry()
        self.contentWidget.adjustSize()
        # Также отложим, чтобы гарантировать пересчет
        QTimer.singleShot(0, self._delayed_update)