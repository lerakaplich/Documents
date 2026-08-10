import os
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QSizePolicy, QSpacerItem, QMessageBox
from PyQt6.QtCore import Qt, QDate

from client.core.filtering.hierarchical_department_filter import HierarchicalDepartmentFilter
from client.windows.period_dialog import PeriodDialog
from client.windows.profile.overtime.overtime_card import OvertimeCard


class OvertimePanel:
    """Управление отображением переработок: вкладки, карточки, фильтры."""

    def __init__(self, parent=None):
        self.parent = parent

        # Периоды для каждой вкладки
        self.my_period = None       # {'start': 'dd.mm.yyyy', 'end': 'dd.mm.yyyy'}
        self.all_period = None

        # Флаги активности фильтров
        self.my_has_filter = False
        self.all_has_filter = False

        # ID выбранного отдела
        self.current_filter_department_id = None

        # Виджеты (будут переданы через setup_ui_elements)
        self.tabWidget = None
        self.myOvertimeContainer = None
        self.allOvertimeContainer = None
        self.btnSelectPeriod = None
        self.btnSelectPeriodAll = None
        self.btnResetFilters = None
        self.btnResetFiltersAll = None
        self.btnAddOvertimeAll = None
        self.btnExport = None
        self.labelTotalHoursMy = None
        self.labelTotalHoursAll = None
        self.allOvertimeFiltersLayout = None
        self.department_filter = None

        # Кнопка добавления (может отсутствовать)
        self.btnAddOvertime = None

    def setup_ui_elements(self, tabWidget, btnSelectPeriod, btnSelectPeriodAll, btnResetFilters,
                          btnResetFiltersAll, btnAddOvertimeAll, btnExport, labelTotalHoursMy,
                          labelTotalHoursAll, allOvertimeFiltersLayout, btnAddOvertime=None):
        """Передаёт ссылки на виджеты из главного окна."""
        self.tabWidget = tabWidget
        self.btnSelectPeriod = btnSelectPeriod
        self.btnSelectPeriodAll = btnSelectPeriodAll
        self.btnResetFilters = btnResetFilters
        self.btnResetFiltersAll = btnResetFiltersAll
        self.btnAddOvertimeAll = btnAddOvertimeAll
        self.btnExport = btnExport
        self.labelTotalHoursMy = labelTotalHoursMy
        self.labelTotalHoursAll = labelTotalHoursAll
        self.allOvertimeFiltersLayout = allOvertimeFiltersLayout
        self.btnAddOvertime = btnAddOvertime

        # Инициализация
        self.remove_add_button_from_my_overtime()
        self.setup_card_containers()
        self.hide_reset_buttons()
        self.setup_hierarchical_filter()

    # ---------- Вспомогательные методы для контейнеров карточек ----------
    def remove_add_button_from_my_overtime(self):
        """Удаляет кнопку «Добавить переработку» из вкладки «Мои переработки»."""
        if self.btnAddOvertime:
            parent = self.btnAddOvertime.parent()
            if parent and parent.objectName() == "tabMyOvertime":
                self.btnAddOvertime.deleteLater()
                self.btnAddOvertime = None
                print("Кнопка 'Добавить переработку' удалена из вкладки 'Мои переработки'")

    def setup_card_containers(self):
        """Создаёт контейнеры для карточек вместо таблиц."""
        # Удаляем старые таблицы, если они есть
        if hasattr(self.parent, 'myOvertimeTable'):
            self.parent.myOvertimeTable.deleteLater()
            self.parent.myOvertimeTable = None
        if hasattr(self.parent, 'allOvertimeTable'):
            self.parent.allOvertimeTable.deleteLater()
            self.parent.allOvertimeTable = None

        self.myOvertimeContainer = self._create_card_container()
        self.allOvertimeContainer = self._create_card_container()

        self._replace_widget_in_tab('tabMyOvertime', self.myOvertimeContainer)
        self._replace_widget_in_tab('tabAllOvertime', self.allOvertimeContainer)

    def _create_card_container(self):
        """Создаёт QWidget с QGridLayout для размещения карточек."""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        grid_layout.setColumnMinimumWidth(0, 450)
        grid_layout.setColumnMinimumWidth(1, 450)

        main_layout.addLayout(grid_layout)
        main_layout.addStretch()

        container.grid_layout = grid_layout
        container.main_layout = main_layout
        container.cards = []
        return container

    def _replace_widget_in_tab(self, tab_name, new_widget):
        """Заменяет старую таблицу на новый контейнер внутри вкладки."""
        tab = getattr(self.parent, tab_name, None)
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

    # ---------- Управление кнопками сброса ----------
    def hide_reset_buttons(self):
        if self.btnResetFilters:
            self.btnResetFilters.setVisible(False)
        if self.btnResetFiltersAll:
            self.btnResetFiltersAll.setVisible(False)

    def show_reset_button(self, tab_name):
        if tab_name == 'my' and self.btnResetFilters:
            self.btnResetFilters.setVisible(True)
        elif tab_name == 'all' and self.btnResetFiltersAll:
            self.btnResetFiltersAll.setVisible(True)

    def hide_reset_button(self, tab_name):
        if tab_name == 'my' and self.btnResetFilters:
            self.btnResetFilters.setVisible(False)
        elif tab_name == 'all' and self.btnResetFiltersAll:
            self.btnResetFiltersAll.setVisible(False)

    # ---------- Иерархический фильтр по отделам ----------
    def _get_children_departments(self, department_id):
        """Заглушка для получения дочерних отделов."""
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

    def setup_hierarchical_filter(self):
        """Создаёт и встраивает иерархический фильтр в панель фильтров."""
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

        # Заменяем старый comboDepartment на новый фильтр
        for i in range(layout.count()):
            widget = layout.itemAt(i).widget()
            if widget and widget.objectName() == "comboDepartment":
                layout.removeWidget(widget)
                widget.deleteLater()
                layout.insertWidget(i, self.department_filter)
                break
        else:
            layout.insertWidget(0, self.department_filter)

        self.department_filter.selectionChanged.connect(self.on_department_filter_changed_id)

    def on_department_filter_changed_id(self, department_id):
        """Обработчик изменения выбора отдела."""
        print(f"Фильтр по отделу ID: {department_id}")
        self.current_filter_department_id = department_id
        self.all_has_filter = True
        self.show_reset_button('all')
        self.load_overtime_data(
            filter_department_id=department_id,
            start_date_str=self.all_period['start'] if self.all_period else None,
            end_date_str=self.all_period['end'] if self.all_period else None
        )

    def _get_all_child_ids(self, dept_id):
        """Рекурсивно собирает все ID подразделений в поддереве."""
        ids = [dept_id]
        children = self._get_children_departments(dept_id)
        for child in children:
            ids.extend(self._get_all_child_ids(child["id"]))
        return ids

    # ---------- Загрузка и фильтрация данных ----------
    def load_overtime_data(self, filter_department_id=None, start_date_str=None, end_date_str=None, for_my=False):
        """Загружает и отображает переработки с учётом фильтров."""
        try:
            if not self.myOvertimeContainer:
                print("myOvertimeContainer не существует, создаем...")
                self.setup_card_containers()
            if not self.allOvertimeContainer:
                print("allOvertimeContainer не существует, создаем...")
                self.setup_card_containers()

            # Тестовые данные
            my_data = [
                {'employee_name': 'Иванов Иван', 'department_id': 1, 'created_at': '10.05.2026',
                 'description': 'Дедлайн проекта', 'date': '15.05.2026', 'start_time': '18:00',
                 'end_time': '20:30', 'duration': 2.5},
                {'employee_name': 'Иванов Иван', 'department_id': 5, 'created_at': '18.05.2026',
                 'description': 'Релиз версии', 'date': '22.05.2026', 'start_time': '17:00',
                 'end_time': '20:00', 'duration': 3.0}
            ]
            all_data = [
                {'employee_name': 'Иванов Иван', 'department_id': 1, 'created_at': '10.05.2026',
                 'description': 'Дедлайн проекта', 'date': '15.05.2026', 'start_time': '18:00',
                 'end_time': '20:30', 'duration': 2.5},
                {'employee_name': 'Петров Петр', 'department_id': 2, 'created_at': '12.05.2026',
                 'description': 'Консультация', 'date': '16.05.2026', 'start_time': '19:00',
                 'end_time': '20:00', 'duration': 1.0},
                {'employee_name': 'Сидорова Анна', 'department_id': 3, 'created_at': '15.05.2026',
                 'description': 'Внеплановые задачи', 'date': '20.05.2026', 'start_time': '18:00',
                 'end_time': '22:00', 'duration': 4.0},
                {'employee_name': 'Иванов Иван', 'department_id': 5, 'created_at': '18.05.2026',
                 'description': 'Релиз версии', 'date': '22.05.2026', 'start_time': '17:00',
                 'end_time': '20:00', 'duration': 3.0}
            ]

            # Фильтрация по отделам
            if filter_department_id is not None:
                print(f"Применяем фильтр по отделу ID: {filter_department_id}")
                all_ids = self._get_all_child_ids(filter_department_id)
                all_data = [item for item in all_data if item.get('department_id') in all_ids]
                my_data = [item for item in my_data if item.get('department_id') in all_ids]

            # Фильтрация по датам
            if start_date_str and end_date_str:
                try:
                    start_date = datetime.strptime(start_date_str, "%d.%m.%Y")
                    end_date = datetime.strptime(end_date_str, "%d.%m.%Y")
                    all_data = self._filter_by_date(all_data, start_date, end_date)
                    my_data = self._filter_by_date(my_data, start_date, end_date)
                    print(f"После фильтрации по датам: all_data={len(all_data)}, my_data={len(my_data)}")
                except ValueError as e:
                    print(f"Ошибка парсинга дат: {e}")

            # Обновление контейнеров
            if for_my:
                print(f"Обновление только 'Моих переработок' с {len(my_data)} записями")
                self._populate_card_container_safe(self.myOvertimeContainer, my_data)
                self._update_total_hours(self.labelTotalHoursMy, my_data)
            else:
                print(f"Обновление 'Всех переработок' с {len(all_data)} записями")
                print(f"Обновление 'Моих переработок' с {len(my_data)} записями")
                self._populate_card_container_safe(self.allOvertimeContainer, all_data)
                self._populate_card_container_safe(self.myOvertimeContainer, my_data)
                self._update_total_hours(self.labelTotalHoursAll, all_data)
                self._update_total_hours(self.labelTotalHoursMy, my_data)

        except Exception as e:
            print(f"Ошибка в load_overtime_data: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось загрузить данные: {str(e)}")

    def _populate_card_container_safe(self, container, data_list):
        """Безопасно заполняет контейнер карточками."""
        try:
            if not container:
                print("Контейнер не существует, пропускаем обновление")
                return

            if not hasattr(container, 'grid_layout'):
                print(f"У контейнера нет grid_layout, создаем...")
                grid_layout = QGridLayout()
                grid_layout.setSpacing(15)
                grid_layout.setContentsMargins(10, 10, 10, 10)
                grid_layout.setColumnMinimumWidth(0, 450)
                grid_layout.setColumnMinimumWidth(1, 450)
                container.grid_layout = grid_layout

                if not hasattr(container, 'main_layout'):
                    main_layout = QVBoxLayout(container)
                    main_layout.setSpacing(0)
                    main_layout.setContentsMargins(0, 0, 0, 0)
                    main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                    container.main_layout = main_layout

                container.main_layout.insertLayout(0, grid_layout)

            grid_layout = container.grid_layout

            # Очищаем
            while grid_layout.count():
                item = grid_layout.takeAt(0)
                if item and item.widget():
                    widget = item.widget()
                    widget.deleteLater()

            if not hasattr(container, 'cards'):
                container.cards = []
            else:
                container.cards.clear()

            # Добавляем карточки
            for i, data in enumerate(data_list):
                card = OvertimeCard(i + 1, data)
                card_id = i + 1
                card.edit_clicked.connect(lambda checked, oid=card_id: self.on_overtime_edit(oid))
                card.delete_clicked.connect(lambda checked, oid=card_id: self.on_overtime_delete(oid))
                card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

                row = i // 2
                col = i % 2
                grid_layout.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)
                container.cards.append(card)

            # Растяжка внизу
            if hasattr(container, 'main_layout'):
                for i in range(container.main_layout.count()):
                    item = container.main_layout.itemAt(i)
                    if item and isinstance(item, QSpacerItem):
                        container.main_layout.removeItem(item)
                        break

                spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
                container.main_layout.addItem(spacer)

        except Exception as e:
            print(f"Ошибка в _populate_card_container_safe: {e}")
            import traceback
            traceback.print_exc()

    def _filter_by_date(self, data_list, start_date, end_date):
        """Фильтрует список по диапазону дат."""
        filtered = []
        for item in data_list:
            try:
                item_date = datetime.strptime(item['date'], "%d.%m.%Y")
                if start_date <= item_date <= end_date:
                    filtered.append(item)
            except ValueError:
                continue
        return filtered

    def _update_total_hours(self, label, data_list):
        """Обновляет надпись с итоговым количеством часов."""
        total = sum(item.get('duration', 0) for item in data_list)
        if label:
            label.setText(f"Итого часов: {total:.1f}")

    # ---------- Работа с периодами ----------
    def update_period_button_text(self, button, period_data):
        """Обновляет текст на кнопке выбора периода."""
        if not button:
            return

        if period_data:
            start = period_data['start_date_str']
            end = period_data['end_date_str']
            start_short = start[:-2] + start[-2:]
            end_short = end[:-2] + end[-2:]
            button.setText(f"{start_short} - {end_short}")
            button.setStyleSheet("""
                QPushButton {
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    padding: 0px 16px;
                    color: #ccab6e;
                    font-size: 13px;
                    background-color: transparent;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
                QPushButton:pressed {
                    background-color: #e0e0e0;
                }
            """)
        else:
            button.setText("Выбрать период")
            button.setStyleSheet("""
                QPushButton {
                    border: none;
                    border-radius: 8px;
                    font-weight: bold;
                    padding: 0px 16px;
                    color: white;
                    background-color: #1B232A;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #D9D9D6;
                    color: black;
                }
                QPushButton:pressed {
                    background-color: #B8B8B5;
                }
            """)

    def on_select_period_clicked(self):
        """Открывает диалог выбора периода для «Моих переработок»."""
        try:
            start_date = None
            end_date = None
            if self.my_period:
                try:
                    start_date = QDate.fromString(self.my_period['start'], "dd.MM.yyyy")
                    end_date = QDate.fromString(self.my_period['end'], "dd.MM.yyyy")
                except:
                    pass

            dialog = PeriodDialog(self.parent, start_date=start_date, end_date=end_date)
            dialog.period_selected.connect(self.on_period_selected_for_my)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось открыть окно выбора периода\n{str(e)}")

    def on_select_period_all_clicked(self):
        """Открывает диалог выбора периода для «Всех переработок»."""
        try:
            start_date = None
            end_date = None
            if self.all_period:
                try:
                    start_date = QDate.fromString(self.all_period['start'], "dd.MM.yyyy")
                    end_date = QDate.fromString(self.all_period['end'], "dd.MM.yyyy")
                except:
                    pass

            dialog = PeriodDialog(self.parent, start_date=start_date, end_date=end_date)
            dialog.period_selected.connect(self.on_period_selected_for_all)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось открыть окно выбора периода\n{str(e)}")

    def on_period_selected_for_my(self, period_data):
        """Применяет выбранный период для «Моих переработок»."""
        try:
            start_date = period_data['start_date_str']
            end_date = period_data['end_date_str']
            print(f"Выбран период для 'Моих переработок': {start_date} - {end_date}")

            self.my_period = {'start': start_date, 'end': end_date}
            self.my_has_filter = True
            self.show_reset_button('my')
            self.update_period_button_text(self.btnSelectPeriod, period_data)

            self.load_overtime_data(
                filter_department_id=None,
                start_date_str=start_date,
                end_date_str=end_date,
                for_my=True
            )
        except Exception as e:
            print(f"Ошибка в on_period_selected_for_my: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось применить фильтр: {str(e)}")

    def on_period_selected_for_all(self, period_data):
        """Применяет выбранный период для «Всех переработок»."""
        try:
            start_date = period_data['start_date_str']
            end_date = period_data['end_date_str']
            print(f"Выбран период для 'Всех переработок': {start_date} - {end_date}")

            self.all_period = {'start': start_date, 'end': end_date}
            self.all_has_filter = True
            self.show_reset_button('all')
            self.update_period_button_text(self.btnSelectPeriodAll, period_data)

            self.load_overtime_data(
                filter_department_id=None,
                start_date_str=start_date,
                end_date_str=end_date,
                for_my=False
            )
        except Exception as e:
            print(f"Ошибка в on_period_selected_for_all: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось применить фильтр: {str(e)}")

    def reset_my_period(self):
        """Сбрасывает период для «Моих переработок»."""
        self.my_period = None
        self.my_has_filter = False
        self.hide_reset_button('my')
        self.update_period_button_text(self.btnSelectPeriod, None)
        self.load_overtime_data(filter_department_id=None, for_my=True)

    def reset_all_period(self):
        """Сбрасывает период для «Всех переработок»."""
        self.all_period = None
        self.all_has_filter = False
        self.hide_reset_button('all')
        self.update_period_button_text(self.btnSelectPeriodAll, None)
        self.load_overtime_data(filter_department_id=None, for_my=False)

    def reset_my_filters(self):
        """Сбрасывает все фильтры для «Моих переработок»."""
        self.reset_my_period()
        QMessageBox.information(self.parent, "Фильтры сброшены",
                                "Фильтры для вкладки 'Мои переработки' сброшены")

    def reset_all_filters(self):
        """Сбрасывает все фильтры для «Всех переработок» (отдел + период)."""
        if self.department_filter and hasattr(self.department_filter, 'reset'):
            self.department_filter.reset()
        self.current_filter_department_id = None
        self.reset_all_period()
        QMessageBox.information(self.parent, "Фильтры сброшены",
                                "Фильтры для вкладки 'Все переработки' сброшены")

    # ---------- Действия с карточками ----------
    def on_overtime_edit(self, overtime_id):
        QMessageBox.information(self.parent, "Редактирование", f"Редактирование записи #{overtime_id}")

    def on_overtime_delete(self, overtime_id):
        QMessageBox.information(self.parent, "Удаление", f"Запись #{overtime_id} удалена")
        self.load_overtime_data(
            filter_department_id=None,
            start_date_str=self.all_period['start'] if self.all_period else None,
            end_date_str=self.all_period['end'] if self.all_period else None
        )

    def on_add_overtime_all_clicked(self):
        QMessageBox.information(self.parent, "Добавление переработки", "Открыть форму создания карточки переработки")

    def on_export_clicked(self):
        QMessageBox.information(self.parent, "Экспорт", "Экспорт данных в Excel/PDF")