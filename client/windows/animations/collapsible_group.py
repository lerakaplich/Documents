# collapsible_group.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QEasingCurve, QPropertyAnimation, QTimer

from client.windows.system.employees.employee_card import EmployeeCard


class CollapsibleGroup(QWidget):
    """Виджет с возможностью сворачивания/разворачивания с анимацией"""

    def __init__(self, title, is_expanded=False, parent=None):
        super().__init__(parent)

        self.is_expanded = is_expanded
        self.content_widgets = []
        self._content_height = 0
        self._updating_height = False

        # Главный layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        self.header = QPushButton()
        self.header.setStyleSheet("""
            QPushButton {
                text-align: left;
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 14px;
                font-weight: bold;
                color: #333;
            }
            QPushButton:hover {
                background-color: #E9ECEF;
            }
        """)
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(self.toggle)

        # Контент
        self.content_area = QWidget()
        self.content_area.setStyleSheet("background-color: transparent;")
        self.content_area_layout = QVBoxLayout(self.content_area)
        self.content_area_layout.setSpacing(10)
        self.content_area_layout.setContentsMargins(15, 10, 15, 10)
        self.content_area_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Добавляем в основной layout
        self.main_layout.addWidget(self.header)
        self.main_layout.addWidget(self.content_area)

        # Анимация для высоты контента
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.finished.connect(self._on_animation_finished)

        # Настройка начального состояния
        self.set_title(title)

        # Отложенная инициализация состояния
        if is_expanded:
            # Если нужно развернутое состояние, но контент еще не добавлен
            self.is_expanded = False  # Временно устанавливаем False
            self.set_expanded(True, animated=False)
        else:
            self.set_expanded(False, animated=False)

    def set_title(self, title):
        self.header_text = title
        self.update_arrow()

    def update_arrow(self):
        if self.is_expanded:
            self.header.setText(f"  ▼ {self.header_text}")
        else:
            self.header.setText(f"  ▶ {self.header_text}")

    def calculate_content_height(self):
        """Вычисляет необходимую высоту для контента"""
        if not self.content_widgets:
            return 0

        # Временно делаем контент видимым для расчета
        was_visible = self.content_area.isVisible()
        was_max_height = self.content_area.maximumHeight()

        if not was_visible:
            self.content_area.setVisible(True)

        # Временно убираем ограничение по высоте
        self.content_area.setMaximumHeight(16777215)

        # Принудительно обновляем layout
        self.content_area_layout.activate()
        self.content_area.adjustSize()

        # Получаем оптимальную высоту
        height = self.content_area.sizeHint().height()

        # Восстанавливаем состояние
        self.content_area.setMaximumHeight(was_max_height)
        if not was_visible:
            self.content_area.setVisible(False)

        return max(height, 10)  # Минимум 10px

    def update_content_height(self):
        """Обновляет сохраненную высоту контента"""
        if self.content_widgets:
            self._content_height = self.calculate_content_height()
        else:
            self._content_height = 0
        return self._content_height

    def toggle(self):
        """Переключает состояние"""
        self.set_expanded(not self.is_expanded, animated=True)

    def set_expanded(self, expanded, animated=True):
        """Устанавливает состояние развернутости"""
        if self.is_expanded == expanded and self._content_height > 0:
            return

        old_state = self.is_expanded
        self.is_expanded = expanded
        self.update_arrow()

        # Обновляем высоту контента перед разворачиванием
        if expanded:
            new_height = self.update_content_height()
            # Если нет контента, просто меняем состояние без анимации
            if new_height <= 0:
                self.content_area.setVisible(False)
                return
        else:
            new_height = 0

        if animated and self.content_widgets:
            self.animation.stop()

            if expanded:
                # Разворачиваем: от текущей высоты до полной
                start_height = self.content_area.maximumHeight()
                if start_height <= 0:
                    start_height = 0
                self.content_area.setVisible(True)
                self.animation.setStartValue(start_height)
                self.animation.setEndValue(self._content_height)
            else:
                # Сворачиваем: от текущей высоты до 0
                current_height = self.content_area.maximumHeight()
                if current_height <= 0:
                    current_height = self._content_height if self._content_height > 0 else 100
                self.animation.setStartValue(current_height)
                self.animation.setEndValue(0)

            self.animation.start()
        else:
            # Без анимации
            if expanded:
                if self._content_height > 0:
                    self.content_area.setVisible(True)
                    self.content_area.setMaximumHeight(self._content_height)
                else:
                    self.content_area.setVisible(False)
            else:
                self.content_area.setMaximumHeight(0)
                self.content_area.setVisible(False)

    def _on_animation_finished(self):
        """Обработчик завершения анимации"""
        if not self.is_expanded:
            self.content_area.setMaximumHeight(0)
            self.content_area.setVisible(False)

    def add_widget(self, widget):
        """Добавляет виджет в контент"""
        self.content_area_layout.addWidget(widget)
        self.content_widgets.append(widget)

        # Если группа развернута, обновляем высоту
        if self.is_expanded:
            # Используем QTimer для отложенного обновления
            QTimer.singleShot(10, self._delayed_height_update)

    def _delayed_height_update(self):
        """Отложенное обновление высоты после добавления виджетов"""
        if self.is_expanded and self.content_widgets:
            new_height = self.update_content_height()
            if new_height > 0:
                self.content_area.setVisible(True)
                self.content_area.setMaximumHeight(new_height)

    def remove_widget(self, widget):
        """Удаляет виджет из контента"""
        if widget in self.content_widgets:
            self.content_widgets.remove(widget)
            self.content_area_layout.removeWidget(widget)
            widget.deleteLater()

            # Обновляем высоту
            if self.is_expanded:
                QTimer.singleShot(10, self._delayed_height_update)

    def clear_content(self):
        """Очищает весь контент"""
        for widget in self.content_widgets:
            widget.deleteLater()
        self.content_widgets.clear()

        if self.is_expanded:
            self._content_height = 0
            self.content_area.setMaximumHeight(0)
            self.content_area.setVisible(False)

    # А также небольшое исправление в EmployeesPage.update_display()
    # Добавьте этот метод в класс EmployeesPage:

    def update_display(self):
        """Обновление отображения сотрудников"""
        # Очищаем scroll area
        for i in reversed(range(self.scrollAreaLayout.count())):
            widget = self.scrollAreaLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        filtered = self.filter_employees()
        groups = self.group_by_organization(filtered)

        if self.current_org_id and self.current_org_id in self.organizations:
            org_name = self.organizations[self.current_org_id]["name"]
            if org_name in groups:
                groups = {org_name: groups[org_name]}

        org_order = list(groups.keys())
        org_order.sort(key=lambda x: (x != "ОАО МАЗ", x))

        for i, org_name in enumerate(org_order):
            employees = groups[org_name]
            if not employees:
                continue

            # Определяем, должна ли группа быть развернутой
            if self.current_org_id:
                selected_org_name = self.organizations[self.current_org_id]["name"]
                is_expanded = (org_name == selected_org_name)
            else:
                is_expanded = (i == 0)

            # Создаем группу
            group = CollapsibleGroup(org_name, is_expanded)

            # Добавляем сотрудников
            for emp in employees:
                full_name = f"{emp.get('last_name', '')} {emp.get('first_name', '')} {emp.get('patronymic', '')}".strip()

                card_data = {
                    "id": emp.get("id"),
                    "number": emp.get("service_number", ""),
                    "full_name": full_name,
                    "position": emp.get("position_name", ""),
                    "company": org_name,
                    "department": emp.get("department_name", ""),
                    "subdivision": emp.get("department_path", ""),
                    "phone": emp.get("phone_number", ""),
                    "work_phone": emp.get("work_number", ""),
                    "rights": "Администратор" if emp.get("is_leader") else "Пользователь"
                }

                employee_card = EmployeeCard(card_data)
                employee_card.edit_clicked.connect(
                    lambda data: QMessageBox.information(self, "Информация", "В разработке")
                )
                employee_card.delete_clicked.connect(
                    lambda emp_id: QMessageBox.information(self, "Информация", "В разработке")
                )

                group.add_widget(employee_card)

            # Принудительно обновляем состояние после добавления всех виджетов
            if is_expanded and employees:
                # Небольшая задержка для корректного отображения
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, lambda g=group: g._delayed_height_update() if hasattr(g,
                                                                                            '_delayed_height_update') else None)

            self.scrollAreaLayout.addWidget(group)

        self.scrollAreaLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.position_floating_button()