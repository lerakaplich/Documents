# client/windows/profile/overtime/overtime_panel.py
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, pyqtSignal, pyqtSlot

from client.core.filtering.hierarchical_department_filter import (
    HierarchicalDepartmentFilter,
)
from client.services.overtime_service import OvertimeService
from client.windows.profile.overtime.overtime_card_container import (
    OvertimeCardContainer,
)
from client.windows.profile.overtime.overtime_crud_manager import OvertimeCrudManager
from client.windows.profile.overtime.overtime_data_manager import OvertimeDataManager
from client.windows.profile.overtime.overtime_import_export_manager import (
    OvertimeImportExportManager,
)
from client.windows.profile.overtime.overtime_pagination_manager import (
    OvertimePaginationManager,
)
from client.windows.profile.overtime.overtime_period_manager import (
    OvertimePeriodManager,
)


class _OvertimeLoadSignals(QObject):
    """Доставляет результат фоновой загрузки в поток интерфейса."""

    done = pyqtSignal(int, object)  # request_id, (my_data, all_data)
    failed = pyqtSignal(int, str)

    def __init__(self, on_done, on_failed):
        super().__init__()
        self._on_done = on_done
        self._on_failed = on_failed
        self.done.connect(self._handle_done)
        self.failed.connect(self._handle_failed)

    @pyqtSlot(int, object)
    def _handle_done(self, request_id, result):
        self._on_done(request_id, result)

    @pyqtSlot(int, str)
    def _handle_failed(self, request_id, message):
        self._on_failed(request_id, message)


class _OvertimeLoadTask(QRunnable):
    def __init__(self, request_id, fn, signals):
        super().__init__()
        self._request_id = request_id
        self._fn = fn
        self._signals = signals

    def run(self):
        try:
            result = self._fn()
        except Exception as e:  # noqa: BLE001
            self._signals.failed.emit(self._request_id, str(e))
            return
        self._signals.done.emit(self._request_id, result)


class OvertimePanel:
    """Оркестратор панели переработок. Делегирует работу специализированным менеджерам."""

    def __init__(self, parent=None):
        self.parent = parent

        # Базовые компоненты
        self.data_manager = OvertimeDataManager(self.parent)
        self.card_container = OvertimeCardContainer(self.parent)
        self.period_manager = OvertimePeriodManager(self.parent)

        # Специализированные менеджеры
        self.pagination = OvertimePaginationManager(self.parent)
        self.crud = OvertimeCrudManager(self)
        self.io_manager = OvertimeImportExportManager(self)

        # Сервис
        self.overtime_service = None
        self.current_employee_id = None

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
        self.btnImport = None

        # Фоновая загрузка: один поток (кэши менеджера данных не гоняются), устаревшие
        # ответы по каждой вкладке отбрасываются по номеру запроса
        self._load_signals = _OvertimeLoadSignals(self._on_loaded, self._on_load_failed)
        self._load_pool = QThreadPool()
        self._load_pool.setMaxThreadCount(1)
        self._request_seq = 0
        self._side_tokens = {"my": 0, "all": 0}
        self._requests = {}
        self._pending_loads = 0

    # ==================== ИНИЦИАЛИЗАЦИЯ ====================

    def set_overtime_service(self, overtime_service: OvertimeService):
        self.overtime_service = overtime_service
        self.data_manager.set_overtime_service(overtime_service)
        print("✅ OvertimeService установлен в OvertimePanel")

    def setup_ui_elements(
        self,
        tabWidget,
        btnSelectPeriod,
        btnSelectPeriodAll,
        btnResetFilters,
        btnResetFiltersAll,
        btnAddOvertimeAll,
        btnExport,
        labelTotalHoursMy,
        labelTotalHoursAll,
        allOvertimeFiltersLayout,
        btnAddOvertime=None,
        btnImport=None,
    ):
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

        self.remove_add_button_from_my_overtime()
        self.card_container.setup_card_containers()
        self.hide_reset_buttons()
        self.setup_hierarchical_filter()
        self._apply_initial_periods()
        self.pagination.setup_bars(
            self.card_container.myOvertimeContainer,
            self.card_container.allOvertimeContainer,
            self._change_page,
        )
        self._update_pagination_labels()

    # ==================== ПАГИНАЦИЯ ====================

    def _change_page(self, tab: str, delta: int):
        p = self.data_manager.get_my_pagination() if tab == "my" else self.data_manager.get_all_pagination()

        new_page = self.pagination.current_page(tab) + delta
        if 1 <= new_page <= p["pages"]:
            self.pagination.set_page(tab, new_page)
            self.load_overtime_data(
                filter_department_id=self.data_manager.current_filter_department_id if tab == "all" else None,
                scope=tab,
            )

    def _update_pagination_labels(self):
        self.pagination.update_labels(
            self.data_manager.get_my_pagination(),
            self.data_manager.get_all_pagination(),
        )

    # ==================== ЗАГРУЗКА ДАННЫХ ====================

    def load_overtime_data(self, filter_department_id=None, for_my=False, scope=None):
        """Загружает данные В ФОНЕ и перерисовывает карточки, когда ответ пришёл.

        scope: "my" | "all" | "both" — какие вкладки запросить и перерисовать.
        По умолчанию как раньше: for_my=True → только «Мои», иначе обе."""
        if scope is None:
            scope = "my" if for_my else "both"
        try:
            if not self.card_container.myOvertimeContainer or not self.card_container.allOvertimeContainer:
                self.card_container.setup_card_containers()

            my_period = self.period_manager.my_period
            all_period = self.period_manager.all_period
            args = {
                "my_start": my_period["start"] if my_period else None,
                "my_end": my_period["end"] if my_period else None,
                "all_start": all_period["start"] if all_period else None,
                "all_end": all_period["end"] if all_period else None,
                "my_page": self.pagination.my_current_page,
                "all_page": self.pagination.all_current_page,
                "page_size": self.pagination.page_size,
                "scope": scope,
            }

            sides = ("my", "all") if scope == "both" else (scope,)
            self._request_seq += 1
            request_id = self._request_seq
            for side in sides:
                self._side_tokens[side] = request_id
            self._requests[request_id] = sides
            self._set_busy(1)

            self._load_pool.start(
                _OvertimeLoadTask(
                    request_id,
                    lambda: self._fetch(args, filter_department_id),
                    self._load_signals,
                )
            )
        except Exception as e:
            print(f"Ошибка в load_overtime_data: {e}")
            import traceback

            traceback.print_exc()
            self._notify(f"Ошибка загрузки данных: {e!s}", duration=4000)

    def _fetch(self, args, filter_department_id):
        """Блокирующая часть (HTTP + форматирование + фильтр по отделу) — в фоновом потоке."""
        if self.overtime_service:
            my_data, all_data = self.data_manager.load_overtime_from_api(**args)
        else:
            my_data, all_data = self.data_manager.get_test_data()
        return self.data_manager.filter_data(my_data, all_data, filter_department_id)

    def _set_busy(self, delta):
        self._pending_loads = max(0, self._pending_loads + delta)
        widget = self.parent
        if widget is not None and hasattr(widget, "setCursor"):
            if self._pending_loads:
                widget.setCursor(Qt.CursorShape.BusyCursor)
            else:
                widget.unsetCursor()

    def _on_load_failed(self, request_id, message):
        self._set_busy(-1)
        self._requests.pop(request_id, None)
        print(f"Ошибка загрузки переработок: {message}")
        self._notify(f"Ошибка загрузки данных: {message}", duration=4000)

    def _on_loaded(self, request_id, result):
        """В потоке интерфейса: рисуем только те вкладки, чей запрос ещё актуален."""
        self._set_busy(-1)
        sides = self._requests.pop(request_id, ("my", "all"))
        my_data, all_data = result
        try:
            applied = False
            if "all" in sides and self._side_tokens["all"] == request_id:
                self.card_container.populate_card_container(
                    self.card_container.allOvertimeContainer,
                    all_data,
                    self.crud.edit_overtime_all,
                    self.crud.delete_overtime,
                )
                self.card_container.update_total_hours(self.labelTotalHoursAll, all_data)
                applied = True
            if "my" in sides and self._side_tokens["my"] == request_id:
                self.card_container.populate_card_container(
                    self.card_container.myOvertimeContainer,
                    my_data,
                    self.crud.edit_overtime_my,
                    self.crud.delete_overtime,
                )
                self.card_container.update_total_hours(self.labelTotalHoursMy, my_data)
                applied = True

            if not applied:
                return  # пришёл устаревший ответ

            self._update_pagination_labels()
            # Форсируем пересчёт размеров вкладки и QTabWidget
            if self.tabWidget:
                current = self.tabWidget.currentWidget()
                if current:
                    current.updateGeometry()
                    if current.layout():
                        current.layout().activate()
                self.tabWidget.updateGeometry()

            # Пересчитываем высоту вкладки после подгрузки карточек
            if self.parent and hasattr(self.parent, "_resize_tab_widget"):
                QTimer.singleShot(0, self.parent._resize_tab_widget)

        except Exception as e:
            print(f"Ошибка в _on_loaded: {e}")
            import traceback

            traceback.print_exc()
            self._notify(f"Ошибка загрузки данных: {e!s}", duration=4000)

    # ==================== ПЕРИОДЫ ====================

    def on_select_period_clicked(self):
        self.period_manager.show_period_dialog(
            self.period_manager.my_period,
            lambda data: self.period_manager.on_period_selected(data, True, self._load_with_period),
        )

    def on_select_period_all_clicked(self):
        self.period_manager.show_period_dialog(
            self.period_manager.all_period,
            lambda data: self.period_manager.on_period_selected(data, False, self._load_with_period),
        )

    def _load_with_period(self, is_my, start_date, end_date):
        """Обновляет текст кнопки периода, показывает кнопку сброса и перезагружает данные."""
        if is_my:
            self.show_reset_button("my")
            self.period_manager.update_period_button_text(
                self.btnSelectPeriod,
                {"start_date_str": start_date, "end_date_str": end_date} if start_date else None,
            )
        else:
            self.show_reset_button("all")
            self.period_manager.update_period_button_text(
                self.btnSelectPeriodAll,
                {"start_date_str": start_date, "end_date_str": end_date} if start_date else None,
            )

        self.pagination.reset("my" if is_my else "all")
        # Период меняется только у одной вкладки — запрашиваем и рисуем только её
        self.load_overtime_data(
            filter_department_id=None if is_my else self.data_manager.current_filter_department_id,
            scope="my" if is_my else "all",
        )

    def _apply_initial_periods(self):
        if self.period_manager.my_period and self.btnSelectPeriod:
            self.period_manager.update_period_button_text(
                self.btnSelectPeriod,
                self.period_manager.period_for_button(self.period_manager.my_period),
            )
            self.show_reset_button("my")
        if self.period_manager.all_period and self.btnSelectPeriodAll:
            self.period_manager.update_period_button_text(
                self.btnSelectPeriodAll,
                self.period_manager.period_for_button(self.period_manager.all_period),
            )
            self.show_reset_button("all")

    # ==================== ФИЛЬТР ПО ОТДЕЛАМ ====================

    def setup_hierarchical_filter(self):
        print("setup_hierarchical_filter started")
        self.department_filter = HierarchicalDepartmentFilter()
        self.department_filter.set_children_func(self.data_manager.get_children_departments)
        root = self.data_manager.get_children_departments(None)
        print(f"Root departments: {root}")
        self.department_filter.set_root_items(root)

        layout = self.allOvertimeFiltersLayout
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
        """Только для вкладки «Все переработки»."""
        self.pagination.reset("all")
        print(f"Фильтр по отделу ID: {department_id}")
        self.data_manager.current_filter_department_id = department_id
        self.show_reset_button("all")
        self.load_overtime_data(filter_department_id=department_id, scope="all")

    # ==================== КНОПКИ СБРОСА ====================

    def hide_reset_buttons(self):
        if self.btnResetFilters:
            self.btnResetFilters.setVisible(False)
        if self.btnResetFiltersAll:
            self.btnResetFiltersAll.setVisible(False)

    def show_reset_button(self, tab_name):
        if tab_name == "my" and self.btnResetFilters:
            self.btnResetFilters.setVisible(True)
        elif tab_name == "all" and self.btnResetFiltersAll:
            self.btnResetFiltersAll.setVisible(True)

    def hide_reset_button(self, tab_name):
        if tab_name == "my" and self.btnResetFilters:
            self.btnResetFilters.setVisible(False)
        elif tab_name == "all" and self.btnResetFiltersAll:
            self.btnResetFiltersAll.setVisible(False)

    def remove_add_button_from_my_overtime(self):
        if self.btnAddOvertime:
            parent = self.btnAddOvertime.parent()
            if parent and parent.objectName() == "tabMyOvertime":
                self.btnAddOvertime.deleteLater()
                self.btnAddOvertime = None
                print("Кнопка 'Добавить переработку' удалена из вкладки 'Мои переработки'")

    # ==================== СБРОС ФИЛЬТРОВ ====================

    def reset_my_period(self):
        self.pagination.reset("my")
        self.period_manager.reset_period(True)
        self.hide_reset_button("my")
        self.period_manager.update_period_button_text(self.btnSelectPeriod, None)
        self.load_overtime_data(filter_department_id=None, for_my=True)

    def reset_all_period(self):
        self.pagination.reset("all")
        self.period_manager.reset_period(False)
        self.hide_reset_button("all")
        self.period_manager.update_period_button_text(self.btnSelectPeriodAll, None)
        self.load_overtime_data(
            filter_department_id=self.data_manager.current_filter_department_id,
            scope="all",
        )

    def reset_my_filters(self):
        self.reset_my_period()
        self._notify("Фильтры для вкладки 'Мои переработки' сброшены", duration=2500)

    def reset_all_filters(self):
        if self.department_filter:
            self.department_filter.clear_selection()
            self.department_filter.setVisible(True)
        self.data_manager.current_filter_department_id = None
        self.reset_all_period()
        self._notify("Фильтры для вкладки 'Все переработки' сброшены", duration=2500)

    # ==================== ДЕЛЕГИРУЮЩИЕ МЕТОДЫ ====================
    # (эти имена вызываются из profile_window.py — сохраняем интерфейс)

    def on_import_clicked(self):
        self.io_manager.on_import_clicked()

    def on_export_clicked(self):
        self.io_manager.on_export_clicked()

    def on_add_overtime_all_clicked(self):
        self.crud.add_overtime()

    # ==================== ВСПОМОГАТЕЛЬНОЕ ====================

    def _notify(self, message, duration=3000):
        if hasattr(self.parent, "notification_manager"):
            self.parent.notification_manager.show_notification(message, duration=duration)

    def reapply_theme(self):
        if self.pagination:
            self.pagination.reapply_theme()