from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt, QDate

from client.core.filtering.hierarchical_department_filter import HierarchicalDepartmentFilter
from client.windows.period_dialog import PeriodDialog
from client.windows.profile.overtime.overtime_data_manager import OvertimeDataManager
from client.windows.profile.overtime.overtime_card_container import OvertimeCardContainer
from client.windows.profile.overtime.overtime_period_manager import OvertimePeriodManager


class OvertimePanel:
    """Управление отображением переработок: вкладки, карточки, фильтры."""

    def __init__(self, parent=None):
        self.parent = parent  # ProfileForm

        # Компоненты - передаём parent как QWidget
        self.data_manager = OvertimeDataManager(self.parent)
        self.card_container = OvertimeCardContainer(self.parent)
        self.period_manager = OvertimePeriodManager(self.parent)

        # Виджеты (будут переданы через setup_ui_elements)
        self.tabWidget = None
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
        self.card_container.setup_card_containers()
        self.hide_reset_buttons()
        self.setup_hierarchical_filter()

    def remove_add_button_from_my_overtime(self):
        """Удаляет кнопку «Добавить переработку» из вкладки «Мои переработки»."""
        if self.btnAddOvertime:
            parent = self.btnAddOvertime.parent()
            if parent and parent.objectName() == "tabMyOvertime":
                self.btnAddOvertime.deleteLater()
                self.btnAddOvertime = None
                print("Кнопка 'Добавить переработку' удалена из вкладки 'Мои переработки'")

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
    def setup_hierarchical_filter(self):
        """Создаёт и встраивает иерархический фильтр в панель фильтров."""
        print("setup_hierarchical_filter started")
        self.department_filter = HierarchicalDepartmentFilter()
        self.department_filter.set_children_func(self.data_manager.get_children_departments)
        root = self.data_manager.get_children_departments(None)
        print(f"Root departments: {root}")
        self.department_filter.set_root_items(root)

        layout = self.allOvertimeFiltersLayout
        print(f"Layout found: {layout}")
        if not layout:
            print("Layout not found, cannot add filter")
            return

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
        self.data_manager.current_filter_department_id = department_id
        self.show_reset_button('all')
        self.load_overtime_data(
            filter_department_id=department_id,
            start_date_str=self.period_manager.all_period['start'] if self.period_manager.all_period else None,
            end_date_str=self.period_manager.all_period['end'] if self.period_manager.all_period else None
        )

    # ---------- Загрузка данных ----------
    def load_overtime_data(self, filter_department_id=None, start_date_str=None, end_date_str=None, for_my=False):
        """Загружает и отображает переработки с учётом фильтров."""
        try:
            if not self.card_container.myOvertimeContainer:
                print("myOvertimeContainer не существует, создаем...")
                self.card_container.setup_card_containers()
            if not self.card_container.allOvertimeContainer:
                print("allOvertimeContainer не существует, создаем...")
                self.card_container.setup_card_containers()

            # Получаем и фильтруем данные
            my_data, all_data = self.data_manager.get_test_data()
            my_data, all_data = self.data_manager.filter_data(
                my_data, all_data, filter_department_id, start_date_str, end_date_str
            )

            # Обновление контейнеров
            if for_my:
                print(f"Обновление только 'Моих переработок' с {len(my_data)} записями")
                self.card_container.populate_card_container(
                    self.card_container.myOvertimeContainer, my_data,
                    self.on_overtime_edit, self.on_overtime_delete
                )
                self.card_container.update_total_hours(self.labelTotalHoursMy, my_data)
            else:
                print(f"Обновление 'Всех переработок' с {len(all_data)} записями")
                print(f"Обновление 'Моих переработок' с {len(my_data)} записями")
                self.card_container.populate_card_container(
                    self.card_container.allOvertimeContainer, all_data,
                    self.on_overtime_edit, self.on_overtime_delete
                )
                self.card_container.populate_card_container(
                    self.card_container.myOvertimeContainer, my_data,
                    self.on_overtime_edit, self.on_overtime_delete
                )
                self.card_container.update_total_hours(self.labelTotalHoursAll, all_data)
                self.card_container.update_total_hours(self.labelTotalHoursMy, my_data)

        except Exception as e:
            print(f"Ошибка в load_overtime_data: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось загрузить данные: {str(e)}")

    # ---------- Работа с периодами ----------
    def on_select_period_clicked(self):
        """Открывает диалог выбора периода для «Моих переработок»."""
        self.period_manager.show_period_dialog(
            self.period_manager.my_period,
            lambda data: self.period_manager.on_period_selected(data, True, self._load_with_period)
        )

    def on_select_period_all_clicked(self):
        """Открывает диалог выбора периода для «Всех переработок»."""
        self.period_manager.show_period_dialog(
            self.period_manager.all_period,
            lambda data: self.period_manager.on_period_selected(data, False, self._load_with_period)
        )

    def _load_with_period(self, is_my, start_date, end_date):
        """Загружает данные с применением периода."""
        if is_my:
            self.show_reset_button('my')
            self.period_manager.update_period_button_text(self.btnSelectPeriod,
                {'start_date_str': start_date, 'end_date_str': end_date} if start_date else None)
            self.load_overtime_data(
                filter_department_id=None,
                start_date_str=start_date,
                end_date_str=end_date,
                for_my=True
            )
        else:
            self.show_reset_button('all')
            self.period_manager.update_period_button_text(self.btnSelectPeriodAll,
                {'start_date_str': start_date, 'end_date_str': end_date} if start_date else None)
            self.load_overtime_data(
                filter_department_id=None,
                start_date_str=start_date,
                end_date_str=end_date,
                for_my=False
            )

    def reset_my_period(self):
        """Сбрасывает период для «Моих переработок»."""
        self.period_manager.reset_period(True)
        self.hide_reset_button('my')
        self.period_manager.update_period_button_text(self.btnSelectPeriod, None)
        self.load_overtime_data(filter_department_id=None, for_my=True)

    def reset_all_period(self):
        """Сбрасывает период для «Всех переработок»."""
        self.period_manager.reset_period(False)
        self.hide_reset_button('all')
        self.period_manager.update_period_button_text(self.btnSelectPeriodAll, None)
        self.load_overtime_data(filter_department_id=None, for_my=False)

    def reset_my_filters(self):
        """Сбрасывает все фильтры для «Моих переработок»."""
        self.reset_my_period()
        QMessageBox.information(self.parent, "Фильтры сброшены",
                                "Фильтры для вкладки 'Мои переработки' сброшены")

    def reset_all_filters(self):
        """Сбрасывает все фильтры для «Всех переработок» (отдел + период)."""
        if self.department_filter:
            self.department_filter.clear_selection()
            self.department_filter.setVisible(True)

        self.data_manager.current_filter_department_id = None
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
            start_date_str=self.period_manager.all_period['start'] if self.period_manager.all_period else None,
            end_date_str=self.period_manager.all_period['end'] if self.period_manager.all_period else None
        )

    def on_add_overtime_all_clicked(self):
        QMessageBox.information(self.parent, "Добавление переработки", "Открыть форму создания карточки переработки")

    def on_export_clicked(self):
        """Открывает диалог выбора периода для экспорта."""
        try:
            start_date = None
            end_date = None
            if self.period_manager.all_period:
                try:
                    start_date = QDate.fromString(self.period_manager.all_period['start'], "dd.MM.yyyy")
                    end_date = QDate.fromString(self.period_manager.all_period['end'], "dd.MM.yyyy")
                except:
                    pass

            dialog = PeriodDialog(self.parent, start_date=start_date, end_date=end_date)
            dialog.period_selected.connect(self.on_export_period_selected)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось открыть окно выбора периода для экспорта\n{str(e)}")

    def on_export_period_selected(self, period_data):
        """Обработчик выбора периода для экспорта."""
        try:
            start_date = period_data['start_date_str']
            end_date = period_data['end_date_str']
            print(f"Экспорт данных за период: {start_date} - {end_date}")
            QMessageBox.information(self.parent, "Экспорт",
                                    f"Экспорт данных за период {start_date} - {end_date} в Excel/PDF")
        except Exception as e:
            print(f"Ошибка в on_export_period_selected: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось выполнить экспорт: {str(e)}")