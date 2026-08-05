import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QApplication, QMessageBox, QFormLayout, QLabel,
    QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QFrame,
    QTableWidget, QTableWidgetItem, QComboBox, QScrollArea, QGridLayout,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

from client.core.filtering.hierarchical_department_filter import HierarchicalDepartmentFilter

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.windows.profile.user_data.email_edit_window import EmailEditWindow
from client.windows.profile.user_data.phone_edit_window import PhoneEditWindow
from client.windows.profile.overtime.overtime_card import OvertimeCard
# Импортируем иерархический фильтр (предполагаем, что он лежит в client.widgets)


class ProfileForm(QWidget):
    """Форма профиля сотрудника с динамическим отображением иерархии подразделений и карточками переработок"""

    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(ROOT_DIR, "ui", "profile", "profile.ui")
        try:
            if os.path.exists(ui_path):
                loadUi(ui_path, self)
                print("ProfileForm: UI загружен успешно")
            else:
                print(f"ProfileForm: UI файл не найден: {ui_path}")
                self.create_fallback_ui()
        except Exception as e:
            print(f"ProfileForm: ошибка загрузки UI - {e}")
            self.create_fallback_ui()

        self.remove_add_button_from_my_overtime()
        self.department_rows = []
        self.setup_card_containers()
        self.setup_connections()
        self.setup_edit_buttons()
        self.load_test_data()
        # Загружаем переработки без фильтра
        self.load_overtime_data()

    def remove_add_button_from_my_overtime(self):
        if hasattr(self, 'btnAddOvertime'):
            parent = self.btnAddOvertime.parent()
            if parent and parent.objectName() == "tabMyOvertime":
                self.btnAddOvertime.deleteLater()
                self.btnAddOvertime = None
                print("Кнопка 'Добавить переработку' удалена из вкладки 'Мои переработки'")

    def setup_card_containers(self):
        if hasattr(self, 'myOvertimeTable'):
            self.myOvertimeTable.deleteLater()
            self.myOvertimeTable = None
        if hasattr(self, 'allOvertimeTable'):
            self.allOvertimeTable.deleteLater()
            self.allOvertimeTable = None

        self.myOvertimeContainer = self._create_card_container()
        self.allOvertimeContainer = self._create_card_container()

        self._replace_widget_in_tab('tabMyOvertime', self.myOvertimeContainer)
        self._replace_widget_in_tab('tabAllOvertime', self.allOvertimeContainer)

    def _create_card_container(self):
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        grid_layout = QGridLayout(container)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        grid_layout.setColumnMinimumWidth(0, 450)
        grid_layout.setColumnMinimumWidth(1, 450)
        container.grid_layout = grid_layout
        container.cards = []
        return container

    def _replace_widget_in_tab(self, tab_name, new_widget):
        tab = getattr(self, tab_name, None)
        if not tab:
            return
        layout = tab.layout()
        if not layout:
            return
        old_table_name = "myOvertimeTable" if tab_name == "tabMyOvertime" else "allOvertimeTable"
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget and widget.objectName() == old_table_name:
                layout.replaceWidget(widget, new_widget)
                widget.deleteLater()
                break

    # ---------- НОВЫЙ МЕТОД ДЛЯ ПОЛУЧЕНИЯ ДОЧЕРНИХ ОТДЕЛОВ (ЗАГЛУШКА) ----------
    def _get_children_departments(self, department_id):
        print(f"_get_children_departments called with {department_id}")
        tree = {
            None: [{"id": 1, "name": "Телематика"}, {"id": 2, "name": "Бухгалтерия"}],
            1: [{"id": 3, "name": "НТЦ"}, {"id": 4, "name": "Отдел продаж"}],
            3: [{"id": 5, "name": "Разработки"}, {"id": 6, "name": "Тестирования"}],
            2: [{"id": 7, "name": "Расчётный отдел"}],
        }
        result = tree.get(department_id, [])
        print(f"Returning {result}")
        return result

    # ---------- НАСТРОЙКА ИЕРАРХИЧЕСКОГО ФИЛЬТРА ----------
    def setup_hierarchical_filter(self):
        print("setup_hierarchical_filter started")
        self.department_filter = HierarchicalDepartmentFilter()
        self.department_filter.set_children_func(self._get_children_departments)
        root = self._get_children_departments(None)
        print(f"Root departments: {root}")
        self.department_filter.set_root_items(root)

        layout = self.allOvertimeFiltersLayout
        print(f"Layout found: {layout}")
        if not layout:
            print("Layout not found, cannot add filter")
            return

        # ... остальной код

        # Ищем comboDepartment и заменяем его
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and widget.objectName() == "comboDepartment":
                layout.removeWidget(widget)
                widget.deleteLater()
                layout.insertWidget(i, self.department_filter)
                break
        else:
            # Если не нашли, добавляем в начало
            layout.insertWidget(0, self.department_filter)

        # Подключаем сигнал изменения выбора
        self.department_filter.selectionChanged.connect(self.on_department_filter_changed_id)

    # ---------- ОБРАБОТЧИК ИЗМЕНЕНИЯ ФИЛЬТРА ----------
    def on_department_filter_changed_id(self, department_id):
        """Вызывается при выборе отдела в иерархическом фильтре"""
        print(f"Фильтр по отделу ID: {department_id}")
        self.load_overtime_data(department_id)

    # ---------- ЗАГРУЗКА ДАННЫХ ПЕРЕРАБОТОК С ФИЛЬТРАЦИЕЙ ----------
    def load_overtime_data(self, filter_department_id=None):
        """
        Загружает данные переработок для вкладки «Все переработки».
        Если filter_department_id не None, применяет фильтрацию по отделу
        (включая все дочерние подразделения).
        """
        # Здесь должен быть реальный запрос к серверу.
        # Для примера используем тестовые данные с полем department_id.
        all_data = [
            {
                'employee_name': 'Иванов Иван',
                'department_id': 1,
                'created_at': '10.05.2026',
                'description': 'Дедлайн проекта',
                'date': '15.05.2026',
                'start_time': '18:00',
                'end_time': '20:30',
                'duration': 2.5
            },
            {
                'employee_name': 'Петров Петр',
                'department_id': 2,
                'created_at': '12.05.2026',
                'description': 'Консультация',
                'date': '16.05.2026',
                'start_time': '19:00',
                'end_time': '20:00',
                'duration': 1.0
            },
            {
                'employee_name': 'Сидорова Анна',
                'department_id': 3,
                'created_at': '15.05.2026',
                'description': 'Внеплановые задачи',
                'date': '20.05.2026',
                'start_time': '18:00',
                'end_time': '22:00',
                'duration': 4.0
            },
            {
                'employee_name': 'Иванов Иван',
                'department_id': 5,
                'created_at': '18.05.2026',
                'description': 'Релиз версии',
                'date': '22.05.2026',
                'start_time': '17:00',
                'end_time': '20:00',
                'duration': 3.0
            }
        ]

        if filter_department_id is not None:
            # Собираем все ID поддерева (включая дочерние)
            all_ids = self._get_all_child_ids(filter_department_id)
            filtered = [item for item in all_data if item.get('department_id') in all_ids]
        else:
            filtered = all_data

        self._populate_card_container(self.allOvertimeContainer, filtered)

    def _get_all_child_ids(self, dept_id):
        """Рекурсивно собирает все идентификаторы подразделений в поддереве"""
        ids = [dept_id]
        children = self._get_children_departments(dept_id)
        for child in children:
            ids.extend(self._get_all_child_ids(child["id"]))
        return ids

    # ---------- ОСТАЛЬНЫЕ МЕТОДЫ (БЕЗ ИЗМЕНЕНИЙ) ----------
    def load_test_overtime_data(self):
        """Старый метод загрузки тестовых данных (оставлен для совместимости)"""
        my_data = [
            {
                'employee_name': 'Иванов Иван',
                'created_at': '10.05.2026',
                'description': 'Дедлайн проекта',
                'date': '15.05.2026',
                'start_time': '18:00',
                'end_time': '20:30',
                'duration': 2.5
            },
            {
                'employee_name': 'Иванов Иван',
                'created_at': '15.05.2026',
                'description': 'Исправление багов',
                'date': '20.05.2026',
                'start_time': '19:00',
                'end_time': '20:30',
                'duration': 1.5
            },
            {
                'employee_name': 'Иванов Иван',
                'created_at': '18.05.2026',
                'description': 'Релиз версии',
                'date': '22.05.2026',
                'start_time': '17:00',
                'end_time': '20:00',
                'duration': 3.0
            }
        ]

        all_data = [
            {
                'employee_name': 'Иванов Иван',
                'created_at': '10.05.2026',
                'description': 'Дедлайн проекта',
                'date': '15.05.2026',
                'start_time': '18:00',
                'end_time': '20:30',
                'duration': 2.5
            },
            {
                'employee_name': 'Петров Петр',
                'created_at': '12.05.2026',
                'description': 'Консультация',
                'date': '16.05.2026',
                'start_time': '19:00',
                'end_time': '20:00',
                'duration': 1.0
            },
            {
                'employee_name': 'Сидорова Анна',
                'created_at': '15.05.2026',
                'description': 'Внеплановые задачи',
                'date': '20.05.2026',
                'start_time': '18:00',
                'end_time': '22:00',
                'duration': 4.0
            },
            {
                'employee_name': 'Иванов Иван',
                'created_at': '18.05.2026',
                'description': 'Релиз версии',
                'date': '22.05.2026',
                'start_time': '17:00',
                'end_time': '20:00',
                'duration': 3.0
            }
        ]

        self._populate_card_container(self.myOvertimeContainer, my_data)
        # Для all используем новый метод, но пока загружаем все данные
        self._populate_card_container(self.allOvertimeContainer, all_data)

    def _populate_card_container(self, container, data_list):
        grid_layout = container.grid_layout
        while grid_layout.count():
            item = grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        container.cards.clear()

        for i, data in enumerate(data_list):
            card = OvertimeCard(i + 1, data)
            card.edit_clicked.connect(lambda oid: self.on_overtime_edit(oid))
            card.delete_clicked.connect(lambda oid: self.on_overtime_delete(oid))

            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            row = i // 2
            col = i % 2
            grid_layout.addWidget(card, row, col)
            container.cards.append(card)

        if len(data_list) > 0 and len(data_list) % 2 != 0:
            spacer = QWidget()
            spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            grid_layout.addWidget(spacer, len(data_list) // 2, 1)

    def on_overtime_edit(self, overtime_id):
        QMessageBox.information(self, "Редактирование", f"Редактирование записи #{overtime_id}")

    def on_overtime_delete(self, overtime_id):
        QMessageBox.information(self, "Удаление", f"Запись #{overtime_id} удалена")
        # Перезагружаем данные
        self.load_overtime_data()

    def create_fallback_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Профиль сотрудника")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        self.infoFrame = QFrame()
        self.infoFrame.setFrameStyle(QFrame.Shape.Box)
        self.infoFrame.setLayout(QFormLayout())
        main_layout.addWidget(self.infoFrame)

        self.label_position_value = QLabel()
        self.label_phone_value = QLabel()
        self.label_email_value = QLabel()
        self.label_birth_date_value = QLabel()
        self.btnEditPhone = QPushButton("✏️")
        self.btnEditEmail = QPushButton("✏️")

        self.tabWidget = QTabWidget()
        main_layout.addWidget(self.tabWidget)

        self.load_test_data()
        self.load_overtime_data()

    def setup_edit_buttons(self):
        style = """
            QToolButton, QPushButton {
                background-color: transparent;
                color: #ccab6e;
                font-size: 20px;
                border: none;
                border-radius: 8px;
                padding: 5px;
            }
            QToolButton:hover, QPushButton:hover {
                color: #b8944a;
                background-color: rgba(204, 171, 110, 0.1);
            }
            QToolButton:pressed, QPushButton:pressed {
                color: #7a6a50;
                background-color: rgba(204, 171, 110, 0.2);
            }
        """
        if hasattr(self, 'btnEditPhone') and self.btnEditPhone:
            self.btnEditPhone.setStyleSheet(style)
            self.btnEditPhone.setText("✏️")
            self.btnEditPhone.setMinimumSize(30, 30)

        if hasattr(self, 'btnEditEmail') and self.btnEditEmail:
            self.btnEditEmail.setStyleSheet(style)
            self.btnEditEmail.setText("✏️")
            self.btnEditEmail.setMinimumSize(30, 30)

    def setup_connections(self):
        if hasattr(self, 'btnSelectPeriod') and self.btnSelectPeriod:
            self.btnSelectPeriod.clicked.connect(self.on_select_period_clicked)
        if hasattr(self, 'btnAddOvertimeAll') and self.btnAddOvertimeAll:
            self.btnAddOvertimeAll.clicked.connect(self.on_add_overtime_all_clicked)
        if hasattr(self, 'btnSelectPeriodAll') and self.btnSelectPeriodAll:
            self.btnSelectPeriodAll.clicked.connect(self.on_select_period_all_clicked)
        if hasattr(self, 'btnClearFilters') and self.btnClearFilters:
            self.btnClearFilters.clicked.connect(self.on_clear_filters_clicked)
        if hasattr(self, 'btnExport') and self.btnExport:
            self.btnExport.clicked.connect(self.on_export_clicked)
        # Убираем подключение старого comboDepartment, т.к. он будет заменён
        if hasattr(self, 'btnEditPhone') and self.btnEditPhone:
            self.btnEditPhone.clicked.connect(self.on_edit_phone_clicked)
        if hasattr(self, 'btnEditEmail') and self.btnEditEmail:
            self.btnEditEmail.clicked.connect(self.on_edit_email_clicked)

        # Настраиваем иерархический фильтр
        self.setup_hierarchical_filter()

    def update_profile(self, full_name, position, department_chain, phone, email, birth_date):
        print("update_profile вызван")
        if hasattr(self, 'labelTitle'):
            self.labelTitle.setText(full_name)
        else:
            print("labelTitle не найден")

        self.current_phone_raw = phone
        self.current_email_raw = email
        self.rebuild_info_layout(position, department_chain, phone, email, birth_date)

    def rebuild_info_layout(self, position, department_chain, phone, email, birth_date):
        print("rebuild_info_layout вызван")

        if not hasattr(self, 'infoFrame') or self.infoFrame is None:
            print("infoFrame не найден, создаём новый")
            self.infoFrame = QFrame(self)
            self.infoFrame.setObjectName("infoFrame")
            self.infoFrame.setStyleSheet(
                "padding: 20px; background-color: white; border-radius: 16px; border: 1px solid #E0E0E0;")
            if hasattr(self, 'mainLayout'):
                for i in range(self.mainLayout.count()):
                    item = self.mainLayout.itemAt(i)
                    if item.widget() and item.widget().objectName() == "infoFrame":
                        self.mainLayout.removeWidget(item.widget())
                        break
                self.mainLayout.insertWidget(1, self.infoFrame)
            else:
                layout = self.layout()
                if layout:
                    layout.insertWidget(1, self.infoFrame)

        layout = self.infoFrame.layout()
        if layout is None:
            layout = QFormLayout()
            layout.setSpacing(10)
            layout.setContentsMargins(0, 0, 0, 0)
            self.infoFrame.setLayout(layout)
        else:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                if item.layout():
                    item.layout().deleteLater()

        title_style = "font-size: 24px; color: black; background-color: transparent;"
        value_style = "font-size: 24px; color: black; background-color: transparent;"

        # Должность
        label_pos_title = QLabel("Должность:")
        label_pos_title.setStyleSheet(title_style)
        label_pos_value = QLabel(position if position else "Не указана")
        label_pos_value.setStyleSheet(value_style)
        layout.addRow(label_pos_title, label_pos_value)
        self.label_position_value = label_pos_value

        # Динамические подразделения
        self.department_rows = []
        for type_name, dept_name in department_chain:
            title = QLabel(f"{type_name}:")
            title.setStyleSheet(title_style)
            value = QLabel(dept_name if dept_name else "Не указано")
            value.setStyleSheet(value_style)
            layout.addRow(title, value)
            self.department_rows.append((title, value))

        # Телефон
        label_phone_title = QLabel("Номер телефона:")
        label_phone_title.setStyleSheet(title_style)
        label_phone_value = QLabel(self.format_phone_display(phone) if phone else "Не указан")
        label_phone_value.setStyleSheet(value_style)
        if not hasattr(self, 'btnEditPhone') or self.btnEditPhone is None:
            self.btnEditPhone = QPushButton("✏️")
            self.btnEditPhone.setStyleSheet(
                "background-color: transparent; color: #ccab6e; font-size: 20px; border: none;")
            self.btnEditPhone.setMinimumSize(30, 30)
            self.btnEditPhone.clicked.connect(self.on_edit_phone_clicked)
        phone_widget = QWidget()
        phone_widget.setStyleSheet("background-color: transparent;")
        phone_layout = QHBoxLayout(phone_widget)
        phone_layout.setContentsMargins(0, 0, 0, 0)
        phone_layout.setSpacing(5)
        phone_layout.addWidget(label_phone_value)
        phone_layout.addWidget(self.btnEditPhone)
        phone_layout.addStretch()
        layout.addRow(label_phone_title, phone_widget)
        self.label_phone_value = label_phone_value

        # Email
        label_email_title = QLabel("Электронная почта:")
        label_email_title.setStyleSheet(title_style)
        label_email_value = QLabel(email if email else "Не указан")
        label_email_value.setStyleSheet(value_style)
        if not hasattr(self, 'btnEditEmail') or self.btnEditEmail is None:
            self.btnEditEmail = QPushButton("✏️")
            self.btnEditEmail.setStyleSheet(
                "background-color: transparent; color: #ccab6e; font-size: 20px; border: none;")
            self.btnEditEmail.setMinimumSize(30, 30)
            self.btnEditEmail.clicked.connect(self.on_edit_email_clicked)
        email_widget = QWidget()
        email_widget.setStyleSheet("background-color: transparent;")
        email_layout = QHBoxLayout(email_widget)
        email_layout.setContentsMargins(0, 0, 0, 0)
        email_layout.setSpacing(5)
        email_layout.addWidget(label_email_value)
        email_layout.addWidget(self.btnEditEmail)
        email_layout.addStretch()
        layout.addRow(label_email_title, email_widget)
        self.label_email_value = label_email_value

        # Дата рождения
        label_birth_title = QLabel("Дата рождения:")
        label_birth_title.setStyleSheet(title_style)
        label_birth_value = QLabel(birth_date if birth_date else "Не указана")
        label_birth_value.setStyleSheet(value_style)
        layout.addRow(label_birth_title, label_birth_value)
        self.label_birth_date_value = label_birth_value

        print("rebuild_info_layout завершён")

    def load_test_data(self):
        print("load_test_data вызван")
        department_chain = [
            ("Отдел", "Телематика"),
            ("Подразделение", "НТЦ"),
            ("Сектор", "Разработки")
        ]
        self.update_profile(
            full_name="Иванов Иван Петрович",
            position="Ведущий разработчик",
            department_chain=department_chain,
            phone="375291234567",
            email="ivan.ivanov@company.by",
            birth_date="15.05.1985"
        )

    def format_phone_display(self, phone: str) -> str:
        if len(phone) == 12 and phone.isdigit():
            return f"+{phone[:3]} ({phone[3:5]}) {phone[5:8]}-{phone[8:10]}-{phone[10:12]}"
        return phone

    def on_edit_phone_clicked(self):
        try:
            dialog = PhoneEditWindow(self.current_phone_raw, parent=None)
            dialog.phone_updated.connect(self.on_phone_updated)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть окно редактирования телефона\n{str(e)}")

    def on_phone_updated(self, new_phone: str):
        self.current_phone_raw = new_phone
        if hasattr(self, 'label_phone_value'):
            self.label_phone_value.setText(self.format_phone_display(new_phone))
        QMessageBox.information(self, "Успешно", f"Номер телефона обновлён\n+{new_phone}")

    def on_edit_email_clicked(self):
        try:
            dialog = EmailEditWindow(self.current_email_raw, parent=None)
            dialog.email_updated.connect(self.on_email_updated)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть окно редактирования email\n{str(e)}")

    def on_email_updated(self, new_email: str):
        self.current_email_raw = new_email
        if hasattr(self, 'label_email_value'):
            self.label_email_value.setText(new_email if new_email else "Не указан")
        QMessageBox.information(self, "Успешно", "Email обновлён" if new_email else "Email удалён")

    def on_select_period_clicked(self):
        QMessageBox.information(self, "Выбор периода", "Открыть календарь для выбора периода")

    def on_add_overtime_all_clicked(self):
        QMessageBox.information(self, "Добавление переработки", "Открыть форму создания карточки переработки")

    def on_select_period_all_clicked(self):
        QMessageBox.information(self, "Выбор периода", "Открыть календарь для выбора периода")

    def on_clear_filters_clicked(self):
        # Сбрасываем иерархический фильтр
        if hasattr(self, 'department_filter'):
            self.department_filter.reset()
        else:
            # fallback, если фильтр не создан
            QMessageBox.information(self, "Фильтры", "Фильтры сброшены")

    def on_export_clicked(self):
        QMessageBox.information(self, "Экспорт", "Экспорт данных в Excel/PDF")

    # Удаляем старый обработчик on_department_filter_changed, он больше не нужен
    # def on_department_filter_changed(self, department: str):
    #     pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProfileForm()
    window.setWindowTitle("Профиль сотрудника")
    window.setGeometry(100, 100, 920, 820)
    window.show()
    sys.exit(app.exec())