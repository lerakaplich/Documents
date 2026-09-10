# client/windows/profile/overtime/overtime_panel.py
from datetime import datetime

from PyQt6.QtWidgets import QMessageBox, QDialog
from PyQt6.QtCore import Qt, QDate

from client.core.filtering.hierarchical_department_filter import HierarchicalDepartmentFilter
from client.windows.period_dialog import PeriodDialog
from client.windows.profile.overtime.overtime_data_manager import OvertimeDataManager
from client.windows.profile.overtime.overtime_card_container import OvertimeCardContainer
from client.windows.profile.overtime.overtime_dialog import OvertimeDialog
from client.windows.profile.overtime.overtime_period_manager import OvertimePeriodManager
from client.services.overtime_service import OvertimeService


class OvertimePanel:
    """Управление отображением переработок: вкладки, карточки, фильтры."""

    def __init__(self, parent=None):
        self.parent = parent

        # Компоненты
        self.data_manager = OvertimeDataManager(self.parent)
        self.card_container = OvertimeCardContainer(self.parent)
        self.period_manager = OvertimePeriodManager(self.parent)

        # Сервис переработок (будет установлен позже)
        self.overtime_service = None

        # Виджеты
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
        self.current_employee_id = None
        self.btnImport = None

    def set_overtime_service(self, overtime_service: OvertimeService):
        """Устанавливает сервис переработок"""
        self.overtime_service = overtime_service
        self.data_manager.set_overtime_service(overtime_service)
        print("✅ OvertimeService установлен в OvertimePanel")

    def setup_ui_elements(self, tabWidget, btnSelectPeriod, btnSelectPeriodAll,
                      btnResetFilters, btnResetFiltersAll, btnAddOvertimeAll,
                      btnExport, labelTotalHoursMy, labelTotalHoursAll,
                      allOvertimeFiltersLayout, btnAddOvertime=None, btnImport=None):
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
        self.btnImport = btnImport
        # Инициализация
        self.remove_add_button_from_my_overtime()
        self.card_container.setup_card_containers()
        self.hide_reset_buttons()
        self.setup_hierarchical_filter()
        self._apply_initial_periods()

    def _apply_initial_periods(self):
        """Показывает текущий расчётный период на кнопках и делает reset видимым."""
        if self.period_manager.my_period and self.btnSelectPeriod:
            self.period_manager.update_period_button_text(
                self.btnSelectPeriod,
                self.period_manager.period_for_button(self.period_manager.my_period)
            )
            self.show_reset_button('my')
        if self.period_manager.all_period and self.btnSelectPeriodAll:
            self.period_manager.update_period_button_text(
                self.btnSelectPeriodAll,
                self.period_manager.period_for_button(self.period_manager.all_period)
            )
            self.show_reset_button('all')

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

        def on_department_filter_changed_id(self, department_id):
            print(f"Фильтр по отделу ID: {department_id}")
            self.data_manager.current_filter_department_id = department_id
            self.show_reset_button('all')
            self.load_overtime_data(filter_department_id=department_id, for_my=False)

    # ---------- Загрузка данных ----------
    def load_overtime_data(self, filter_department_id=None, for_my=False):
        """Загружает и отображает переработки. Даты берутся из period_manager для каждого таба."""
        try:
            if not self.card_container.myOvertimeContainer:
                self.card_container.setup_card_containers()
            if not self.card_container.allOvertimeContainer:
                self.card_container.setup_card_containers()

            # Периоды независимы для каждого таба
            my_period = self.period_manager.my_period
            all_period = self.period_manager.all_period

            if self.overtime_service:
                my_data, all_data = self.data_manager.load_overtime_from_api(
                    my_start=my_period['start'] if my_period else None,
                    my_end=my_period['end'] if my_period else None,
                    all_start=all_period['start'] if all_period else None,
                    all_end=all_period['end'] if all_period else None,
                )
            else:
                my_data, all_data = self.data_manager.get_test_data()

            # Только фильтр по отделу (клиентский)
            my_data, all_data = self.data_manager.filter_data(
                my_data, all_data, filter_department_id
            )

            if for_my:
                print(f"Обновление только 'Моих переработок' с {len(my_data)} записями")
                self.card_container.populate_card_container(
                    self.card_container.myOvertimeContainer, my_data,
                    self.on_overtime_edit_my, self.on_overtime_delete
                )
                self.card_container.update_total_hours(self.labelTotalHoursMy, my_data)
            else:
                print(f"Обновление 'Всех переработок' с {len(all_data)} записями")
                print(f"Обновление 'Моих переработок' с {len(my_data)} записями")
                self.card_container.populate_card_container(
                    self.card_container.allOvertimeContainer, all_data,
                    self.on_overtime_edit_all, self.on_overtime_delete
                )
                self.card_container.populate_card_container(
                    self.card_container.myOvertimeContainer, my_data,
                    self.on_overtime_edit_my, self.on_overtime_delete
                )
                self.card_container.update_total_hours(self.labelTotalHoursAll, all_data)
                self.card_container.update_total_hours(self.labelTotalHoursMy, my_data)

        except Exception as e:
            print(f"Ошибка в load_overtime_data: {e}")
            import traceback
            traceback.print_exc()
            if hasattr(self.parent, 'notification_manager'):
                self.parent.notification_manager.show_notification(
                    f"Ошибка загрузки данных: {str(e)}", duration=4000
                )

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

    def on_import_clicked(self):
        """Импорт переработок из Excel-файла (выгрузка СКУД)"""
        try:
            from PyQt6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getOpenFileName(
                self.parent,
                "Выберите файл выгрузки СКУД",
                "",
                "Excel files (*.xlsx *.xls)"
            )
            if not file_path:
                return

            if not self.overtime_service:
                if hasattr(self.parent, 'notification_manager'):
                    self.parent.notification_manager.show_notification(
                        "Сервис переработок недоступен", duration=3000
                    )
                return

            if hasattr(self.parent, 'notification_manager'):
                self.parent.notification_manager.show_notification(
                    "Импорт переработок... Пожалуйста, подождите", duration=3000
                )

            result = self.overtime_service.import_overtime(file_path)

            # Обновляем список
            self.load_overtime_data(
                filter_department_id=self.data_manager.current_filter_department_id,
                start_date_str=self.period_manager.all_period['start'] if self.period_manager.all_period else None,
                end_date_str=self.period_manager.all_period['end'] if self.period_manager.all_period else None
            )

            # Сообщение о результате — структура может отличаться, покажем всё, что пришло
            message = "Импорт завершён"
            if isinstance(result, dict):
                data = result.get("data")
                if isinstance(data, dict):
                    # пробуем вытащить типичные счётчики
                    for key in ("imported", "created", "updated", "total", "processed"):
                        if key in data:
                            message += f". {key}: {data[key]}"
                            break

            if hasattr(self.parent, 'notification_manager'):
                self.parent.notification_manager.show_notification(message, duration=5000)

        except Exception as e:
            print(f"❌ Ошибка импорта переработок: {e}")
            import traceback
            traceback.print_exc()
            if hasattr(self.parent, 'notification_manager'):
                self.parent.notification_manager.show_notification(
                    f"Ошибка импорта: {str(e)}", duration=5000
                )

    def _load_with_period(self, is_my, start_date, end_date):
        """Обновляет текст кнопки и перезагружает данные. Даты уже сохранены в period_manager."""
        if is_my:
            self.show_reset_button('my')
            self.period_manager.update_period_button_text(
                self.btnSelectPeriod,
                {'start_date_str': start_date, 'end_date_str': end_date} if start_date else None
            )
        else:
            self.show_reset_button('all')
            self.period_manager.update_period_button_text(
                self.btnSelectPeriodAll,
                {'start_date_str': start_date, 'end_date_str': end_date} if start_date else None
            )

        # Перезагружаем оба таба — каждый возьмёт свой период из period_manager
        self.load_overtime_data(
            filter_department_id=self.data_manager.current_filter_department_id,
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
        self.load_overtime_data(filter_department_id=self.data_manager.current_filter_department_id, for_my=False)

    def reset_my_filters(self):
        """Сбрасывает все фильтры для «Моих переработок»."""
        self.reset_my_period()
        if hasattr(self.parent, 'notification_manager'):
            self.parent.notification_manager.show_notification(
                "Фильтры для вкладки 'Мои переработки' сброшены",
                duration=2500
            )

    def reset_all_filters(self):
        """Сбрасывает все фильтры для «Всех переработок» (отдел + период)."""
        if self.department_filter:
            self.department_filter.clear_selection()
            self.department_filter.setVisible(True)

        self.data_manager.current_filter_department_id = None
        self.reset_all_period()
        if hasattr(self.parent, 'notification_manager'):
            self.parent.notification_manager.show_notification(
                "Фильтры для вкладки 'Все переработки' сброшены",
                duration=2500
            )

    def on_overtime_delete(self, overtime_id):
        if self.overtime_service:
            try:
                self.overtime_service.delete_overtime(overtime_id)
            except Exception as e:
                print(f"❌ Ошибка удаления переработки: {e}")
                if hasattr(self.parent, 'notification_manager'):
                    self.parent.notification_manager.show_notification(
                        f"Ошибка удаления: {str(e)}", duration=4000
                    )
                return

        if hasattr(self.parent, 'notification_manager'):
            self.parent.notification_manager.show_notification(
                f"Запись #{overtime_id} удалена", duration=3000
            )
        self.load_overtime_data(
            filter_department_id=self.data_manager.current_filter_department_id,
            for_my=False
        )

    def on_export_clicked(self):
        try:
            start_date = None
            end_date = None
            if self.period_manager.all_period:
                try:
                    start_date = QDate.fromString(self.period_manager.all_period['start'], "dd.MM.yyyy")
                    end_date = QDate.fromString(self.period_manager.all_period['end'], "dd.MM.yyyy")
                except:
                    pass

            if not start_date or not start_date.isValid():
                default = self.period_manager.get_default_overtime_period()
                start_date = QDate.fromString(default['start'], "dd.MM.yyyy")
                end_date = QDate.fromString(default['end'], "dd.MM.yyyy")

            dialog = PeriodDialog(self.parent, start_date=start_date, end_date=end_date)
            dialog.period_selected.connect(self.on_export_period_selected)
            dialog.exec()
        except Exception as e:
            if hasattr(self.parent, 'notification_manager'):
                self.parent.notification_manager.show_notification(
                    f"Ошибка открытия окна экспорта: {str(e)}",
                    duration=4000
                )

    def on_export_period_selected(self, period_data):
        """Обработчик выбора периода для экспорта."""
        try:
            start_date_str = period_data['start_date_str']
            end_date_str = period_data['end_date_str']
            print(f"Экспорт данных за период: {start_date_str} - {end_date_str}")

            if self.overtime_service:
                try:
                    # Парсим даты
                    start_date = datetime.strptime(start_date_str, "%d.%m.%Y").date()
                    end_date = datetime.strptime(end_date_str, "%d.%m.%Y").date()

                    # Выполняем экспорт
                    excel_data = self.overtime_service.export_overtime(
                        dept_id=self.data_manager.current_filter_department_id,
                        start_date=start_date,
                        end_date=end_date
                    )

                    # Сохраняем файл
                    from PyQt6.QtWidgets import QFileDialog
                    file_path, _ = QFileDialog.getSaveFileName(
                        self.parent,
                        "Сохранить отчет",
                        f"Отчет_по_переработкам_{start_date_str}_{end_date_str}.xlsx",
                        "Excel files (*.xlsx)"
                    )
                    if file_path:
                        with open(file_path, 'wb') as f:
                            f.write(excel_data)
                        if hasattr(self.parent, 'notification_manager'):
                            self.parent.notification_manager.show_notification(
                                f"Отчет сохранен: {file_path}",
                                duration=3000
                            )
                except Exception as e:
                    print(f"❌ Ошибка экспорта: {e}")
                    if hasattr(self.parent, 'notification_manager'):
                        self.parent.notification_manager.show_notification(
                            f"Ошибка экспорта: {str(e)}",
                            duration=4000
                        )
            else:
                # Заглушка для тестирования
                if hasattr(self.parent, 'notification_manager'):
                    self.parent.notification_manager.show_notification(
                        f"Экспорт данных за период {start_date_str} - {end_date_str} выполнен (заглушка)",
                        duration=3000
                    )
        except Exception as e:
            print(f"Ошибка в on_export_period_selected: {e}")
            import traceback
            traceback.print_exc()
            if hasattr(self.parent, 'notification_manager'):
                self.parent.notification_manager.show_notification(
                    f"Ошибка экспорта: {str(e)}",
                    duration=4000
                )

    def on_add_overtime_all_clicked(self):
        """Открывает диалог создания новой переработки."""
        dialog = OvertimeDialog(
            self.parent,
            readonly=False,
            overtime_service=self.overtime_service,
            current_employee_id=self.current_employee_id or 1
        )

        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data is not None:
            data = dialog.result_data
            employee_id = dialog.get_selected_employee_id()

            if not employee_id:
                if hasattr(self.parent, 'notification_manager'):
                    self.parent.notification_manager.show_notification(
                        "Не удалось определить сотрудника", duration=3000
                    )
                return

            if self.overtime_service:
                try:
                    date_obj = datetime.strptime(data['date'], "%d.%m.%Y")
                    formatted_date = date_obj.strftime("%Y-%m-%d")

                    create_data = {
                        "employee_id": employee_id,
                        "note_text": data['description'],
                        "overtime_date": formatted_date,
                        "overtime_start": data['start_time'],
                        "overtime_end": data['end_time']
                    }

                    self.overtime_service.create_overtime(create_data)
                    self.load_overtime_data(
                        filter_department_id=self.data_manager.current_filter_department_id,
                        for_my=False
                    )
                    if hasattr(self.parent, 'notification_manager'):
                        self.parent.notification_manager.show_notification(
                            "Переработка успешно добавлена", duration=3000
                        )
                except Exception as e:
                    print(f"❌ Ошибка создания переработки: {e}")
                    if hasattr(self.parent, 'notification_manager'):
                        self.parent.notification_manager.show_notification(
                            f"Ошибка создания: {str(e)}", duration=4000
                        )

    def on_overtime_edit_all(self, overtime_id):
        """Редактирование переработки (для вкладки 'Все переработки')"""
        data = self.data_manager.get_overtime_by_id(overtime_id)
        if not data:
            if hasattr(self.parent, 'notification_manager'):
                self.parent.notification_manager.show_notification("Запись не найдена", duration=3000)
            return

        dialog = OvertimeDialog(
            self.parent,
            readonly=False,
            overtime_service=self.overtime_service,
            current_employee_id=self.current_employee_id or 1
        )
        dialog.set_data(data)

        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data is not None:
            new_data = dialog.result_data

            # Обновляем переработку через сервис
            if self.overtime_service:
                try:
                    # Преобразуем дату из формата dd.MM.yyyy в YYYY-MM-DD
                    date_obj = datetime.strptime(new_data['date'], "%d.%m.%Y")
                    formatted_date = date_obj.strftime("%Y-%m-%d")

                    update_data = {
                        "note_text": new_data['description'],
                        "overtime_date": formatted_date,
                        "overtime_start": new_data['start_time'],
                        "overtime_end": new_data['end_time']
                    }

                    self.overtime_service.update_overtime(overtime_id, update_data)

                    self.load_overtime_data(
                        filter_department_id=self.data_manager.current_filter_department_id,
                        for_my=False
                    )

                    if hasattr(self.parent, 'notification_manager'):
                        self.parent.notification_manager.show_notification(
                            "Переработка обновлена",
                            duration=3000
                        )
                except Exception as e:
                    print(f"❌ Ошибка обновления переработки: {e}")
                    if hasattr(self.parent, 'notification_manager'):
                        self.parent.notification_manager.show_notification(
                            f"Ошибка обновления: {str(e)}",
                            duration=4000
                        )
            else:
                # Режим тестирования
                self.load_overtime_data(
                    filter_department_id=self.data_manager.current_filter_department_id,
                    start_date_str=self.period_manager.all_period['start'] if self.period_manager.all_period else None,
                    end_date_str=self.period_manager.all_period['end'] if self.period_manager.all_period else None
                )
                if hasattr(self.parent, 'notification_manager'):
                    self.parent.notification_manager.show_notification(
                        "Переработка обновлена (тестовый режим)",
                        duration=3000
                    )

    def on_overtime_edit_my(self, overtime_id):
        """Редактирование заметки переработки (для вкладки 'Мои переработки')"""
        data = self.data_manager.get_overtime_by_id(overtime_id)
        if not data:
            if hasattr(self.parent, 'notification_manager'):
                self.parent.notification_manager.show_notification("Запись не найдена", duration=3000)
            return

        # Для своих переработок только чтение описания
        dialog = OvertimeDialog(self.parent, readonly=True)
        dialog.set_data(data)

        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_data is not None:
            # Если пользователь нажал "Закрыть" (в режиме readonly)
            # и изменил описание, можно обновить
            new_note = dialog.result_data.get('description', '')
            if new_note != data.get('description', ''):
                if self.overtime_service:
                    try:
                        self.overtime_service.update_overtime_note(overtime_id, new_note)

                        self.load_overtime_data(filter_department_id=None, for_my=True)

                        if hasattr(self.parent, 'notification_manager'):
                            self.parent.notification_manager.show_notification(
                                "Описание обновлено",
                                duration=3000
                            )
                    except Exception as e:
                        print(f"❌ Ошибка обновления заметки: {e}")
                        if hasattr(self.parent, 'notification_manager'):
                            self.parent.notification_manager.show_notification(
                                f"Ошибка обновления: {str(e)}",
                                duration=4000
                            )