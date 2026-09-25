import json
import os
import sys
import traceback
import requests
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox, QFormLayout, QLabel, QVBoxLayout, QHBoxLayout, \
    QPushButton, QTabWidget, QFrame
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.uic import loadUi

from client.core.state.app_state import AppState
from client.core.themes import apply_theme_to_widget, T, get_manager
from client.windows.profile.overtime.overtime_panel import OvertimePanel
from client.windows.profile.profile_info import ProfileInfo
from client.core.http_client import HttpClient
from client.services.employee_service import EmployeeService
from client.services.overtime_service import OvertimeService

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def global_exception_handler(exctype, value, tb):
    print("=" * 80)
    print("ГЛОБАЛЬНОЕ ИСКЛЮЧЕНИЕ:")
    print(f"Тип: {exctype}")
    print(f"Значение: {value}")
    print("Трассировка:")
    traceback.print_tb(tb)
    print("=" * 80)
    sys.__excepthook__(exctype, value, tb)


sys.excepthook = global_exception_handler


# ===== ProfileLoader - класс для загрузки данных в отдельном потоке =====
class ProfileLoader(QThread):
    """Загрузка профиля в отдельном потоке"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, http_client: HttpClient, use_current_user: bool = True):
        super().__init__()
        self.http_client = http_client
        self.use_current_user = use_current_user

    def run(self):
        try:
            service = EmployeeService(self.http_client)

            if self.use_current_user:
                print("📥 Загружаем профиль текущего пользователя (/me)")
                data = service.get_my_profile()
                print(f"✅ Данные получены: {data}")
            else:
                print("📥 Загружаем сотрудника с ID: 1")
                data = service.get_employee(1)

            self.finished.emit(data)

        except requests.exceptions.ConnectionError:
            self.error.emit("Не удалось подключиться к серверу. Проверьте, что сервер запущен.")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.error.emit(f"Ошибка авторизации. Токен истек или неверный.\n{e.response.text}")
            elif e.response.status_code == 404:
                self.error.emit("Профиль пользователя не найден.")
            else:
                self.error.emit(f"Ошибка сервера: {e.response.status_code}\n{e.response.text}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(f"Ошибка загрузки профиля: {str(e)}")


class ProfileForm(QWidget):
    """Главная форма профиля, объединяет ProfileInfo и OvertimePanel."""

    def __init__(self, parent=None, employee_id: int = None):
        super().__init__(parent)

        self.employee_id = employee_id
        self.use_current_user = employee_id is None


        if self.use_current_user:
            print("👤 Загружаем профиль текущего пользователя")
        else:
            print(f"👤 Загружаем профиль сотрудника с ID: {self.employee_id}")

        # ===== Получаем HTTP клиент из глобального состояния =====
        self.app_state = AppState()
        self.http_client = self.app_state.http_client
        if self.http_client:
            print(f"✅ Используем HTTP клиент из AppState: {self.http_client.base_url}")
        else:
            print("⚠️ HTTP клиент не найден в AppState, создаем новый")
            from client.core.config import config
            self.http_client = HttpClient(config.base_url)
            print(f"✅ Создан новый HTTP клиент: {self.http_client.base_url}")
        # ===== Конец инициализации HTTP клиента =====

        # ===== Загрузка UI =====
        ui_path = os.path.join(ROOT_DIR, "ui", "profile", "profile.ui")
        try:
            if os.path.exists(ui_path):
                loadUi(ui_path, self)
                apply_theme_to_widget(self)
                print("ProfileForm: UI загружен успешно")
            else:
                print(f"ProfileForm: UI файл не найден: {ui_path}")
                self.create_fallback_ui()
        except Exception as e:
            print(f"ProfileForm: ошибка загрузки UI - {e}")
            self.create_fallback_ui()
        # ===== Конец загрузки UI =====

        # ===== Создаём компоненты =====
        self.profile_info = ProfileInfo(self)
        self.overtime_panel = OvertimePanel(self)
        # ===== Конец создания компонентов =====

        # Создаем сервис переработок
        self.overtime_service = OvertimeService(self.http_client)

        # Передаем сервис в overtime_panel ДО настройки UI элементов
        self.overtime_panel.set_overtime_service(self.overtime_service)

        # ===== Передаём виджеты в компоненты =====
        self.profile_info.setup_ui_elements(
            infoFrame=self.infoFrame if hasattr(self, 'infoFrame') else None,
            labelTitle=self.labelTitle if hasattr(self, 'labelTitle') else None,
            label_position_value=self.label_position_value if hasattr(self, 'label_position_value') else None,
            label_phone_value=self.label_phone_value if hasattr(self, 'label_phone_value') else None,
            label_email_value=self.label_email_value if hasattr(self, 'label_email_value') else None,
            label_birth_date_value=self.label_birth_date_value if hasattr(self, 'label_birth_date_value') else None,
            mainLayout=self.mainLayout if hasattr(self, 'mainLayout') else None,
            )

        self.profile_info.set_http_client(self.http_client)
        # ===== Конец передачи виджетов =====

        # ===== Настройка overtime panel =====
        # Проверяем наличие виджетов перед передачей
        tabWidget = self.tabWidget if hasattr(self, 'tabWidget') else None
        btnSelectPeriod = self.btnSelectPeriod if hasattr(self, 'btnSelectPeriod') else None
        btnSelectPeriodAll = self.btnSelectPeriodAll if hasattr(self, 'btnSelectPeriodAll') else None
        btnResetFilters = self.btnResetFilters if hasattr(self, 'btnResetFilters') else None
        btnResetFiltersAll = self.btnResetFiltersAll if hasattr(self, 'btnResetFiltersAll') else None
        btnAddOvertimeAll = self.btnAddOvertimeAll if hasattr(self, 'btnAddOvertimeAll') else None
        btnExport = self.btnExport if hasattr(self, 'btnExport') else None
        labelTotalHoursMy = self.labelTotalHoursMy if hasattr(self, 'labelTotalHoursMy') else None
        labelTotalHoursAll = self.labelTotalHoursAll if hasattr(self, 'labelTotalHoursAll') else None
        allOvertimeFiltersLayout = self.allOvertimeFiltersLayout if hasattr(self, 'allOvertimeFiltersLayout') else None
        btnAddOvertime = self.btnAddOvertime if hasattr(self, 'btnAddOvertime') else None
        btnImport = self.btnImport if hasattr(self, 'btnImport') else None

        # Настраиваем UI элементы панели переработок
        self.overtime_panel.setup_ui_elements(
            tabWidget=tabWidget,
            btnSelectPeriod=btnSelectPeriod,
            btnSelectPeriodAll=btnSelectPeriodAll,
            btnResetFilters=btnResetFilters,
            btnResetFiltersAll=btnResetFiltersAll,
            btnAddOvertimeAll=btnAddOvertimeAll,
            btnExport=btnExport,
            labelTotalHoursMy=labelTotalHoursMy,
            labelTotalHoursAll=labelTotalHoursAll,
            allOvertimeFiltersLayout=allOvertimeFiltersLayout,
            btnAddOvertime=btnAddOvertime,
            btnImport=btnImport,
        )
        # ===== Конец настройки overtime panel =====

        # ===== Стилизация кнопок =====
        # ===== Конец стилизации =====

        # ===== Подключение сигналов =====
        self.setup_connections()
        # ===== Конец подключения сигналов =====

        # ===== Загрузка данных =====
        self.load_profile_from_api()
        # Загружаем переработки
        self.overtime_panel.load_overtime_data()
        # ===== Конец загрузки =====

    def load_profile_from_api(self):
        """Загрузка профиля через API в отдельном потоке"""
        if self.profile_info.labelTitle:
            self.profile_info.labelTitle.setText("⏳ Загрузка...")

        if not self.http_client._access_token:
            print("⚠️ Нет токена авторизации, пробуем загрузить тестовые данные")
            self.load_test_data()
            return

        self.loader = ProfileLoader(
            self.http_client,
            use_current_user=self.use_current_user
        )
        self.loader.finished.connect(self.on_profile_loaded)
        self.loader.error.connect(self.on_profile_error)
        self.loader.start()
        print("📥 Загрузка профиля начата...")

    def on_profile_loaded(self, data: dict):
        """Обработка успешной загрузки профиля"""
        try:
            print("=" * 60)
            print("✅ ДАННЫЕ ПРОФИЛЯ ПОЛУЧЕНЫ:")
            print("=" * 60)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("=" * 60)

            # ==== 1. ФИО ====
            last_name = data.get('last_name', '')
            first_name = data.get('first_name', '')
            patronymic = data.get('patronymic', '')

            full_name_parts = []
            if last_name:
                full_name_parts.append(last_name)
            if first_name:
                full_name_parts.append(first_name)
            if patronymic:
                full_name_parts.append(patronymic)

            full_name = ' '.join(full_name_parts) if full_name_parts else 'Не указано'
            print(f"📝 Собрано ФИО: {full_name}")

            # ==== 2. Должность и подразделения ====
            positions = data.get('positions', [])
            position_name = 'Не указана'
            department_chain = []

            if positions and len(positions) > 0:
                first_position = positions[0]
                position_name = first_position.get('position_name', 'Не указана')

                # Получаем цепочку подразделений
                dept_chain = first_position.get('department_chain', [])

                if dept_chain:
                    print(f"📋 Найдена цепочка подразделений: {dept_chain}")
                    for dept in dept_chain:
                        dept_type = dept.get('department_type_name', 'Подразделение')
                        dept_name = dept.get('name', '')
                        if dept_name:
                            department_chain.append((dept_type, dept_name))
                    print(f"🏢 Сформирована цепочка: {department_chain}")
                else:
                    dept_path = first_position.get('department_path', [])
                    if dept_path:
                        print(f"📋 Используем department_path: {dept_path}")
                        types = ['Организация', 'Управление', 'Отдел', 'Сектор']
                        for i, dept_name in enumerate(dept_path):
                            dept_type = types[i] if i < len(types) else 'Подразделение'
                            department_chain.append((dept_type, dept_name))
                    else:
                        dept_id = first_position.get('department_id')
                        if dept_id:
                            print(f"⚠️ Нет цепочки подразделений, только department_id: {dept_id}")
                            department_chain.append(("Подразделение", f"ID: {dept_id}"))

            print(f"📋 Должность: {position_name}")
            print(f"🏢 Итоговая цепочка подразделений: {department_chain}")

            # ==== 3. Телефон ====
            phone = data.get('phone_number', '')
            print(f"📞 Телефон: {phone}")

            # ==== 4. Email ====
            email = data.get('email', '')
            print(f"📧 Email: {email}")

            # ==== 5. Дата рождения ====
            birth_date = data.get('birth_date', 'Не указана')
            if birth_date and birth_date != 'Не указана':
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(birth_date.replace('Z', '+00:00'))
                    birth_date = dt.strftime('%d.%m.%Y')
                except:
                    pass
            print(f"🎂 Дата рождения: {birth_date}")

            # Обновляем профиль
            self.profile_info.update_profile(
                full_name=full_name,
                position=position_name,
                department_chain=department_chain,
                phone=phone,
                email=email,
                birth_date=birth_date
            )

            # Сохраняем данные для редактирования
            self.profile_info.current_phone_raw = phone
            self.profile_info.current_email_raw = email

            self.current_employee_id = data.get('id')
            if hasattr(self, 'overtime_panel'):
                self.overtime_panel.current_employee_id = self.current_employee_id
            print(f"👤 ID текущего сотрудника: {self.current_employee_id}")
            # ────────────────────────────────────────────────────────────────

            print("✅ Профиль успешно обновлен")

        except Exception as e:
            print(f"❌ Ошибка обработки данных: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Ошибка", f"Не удалось обработать данные профиля:\n{str(e)}")

    def on_profile_error(self, error_msg: str):
        """Обработка ошибки загрузки профиля"""
        print(f"❌ Ошибка загрузки профиля: {error_msg}")
        QMessageBox.warning(self, "Ошибка загрузки", error_msg)
        self.load_test_data()

    def setup_connections(self):
        """Подключает сигналы кнопок и фильтров."""
        if hasattr(self, 'btnSelectPeriod') and self.btnSelectPeriod:
            self.btnSelectPeriod.clicked.connect(self.overtime_panel.on_select_period_clicked)
        if hasattr(self, 'btnSelectPeriodAll') and self.btnSelectPeriodAll:
            self.btnSelectPeriodAll.clicked.connect(self.overtime_panel.on_select_period_all_clicked)

        if hasattr(self, 'btnResetFilters') and self.btnResetFilters:
            self.btnResetFilters.clicked.connect(self.overtime_panel.reset_my_filters)
        if hasattr(self, 'btnResetFiltersAll') and self.btnResetFiltersAll:
            self.btnResetFiltersAll.clicked.connect(self.overtime_panel.reset_all_filters)

        if hasattr(self, 'btnAddOvertimeAll') and self.btnAddOvertimeAll:
            self.btnAddOvertimeAll.clicked.connect(self.overtime_panel.on_add_overtime_all_clicked)

        if hasattr(self, 'btnExport') and self.btnExport:
            self.btnExport.clicked.connect(self.overtime_panel.on_export_clicked)

        if hasattr(self, 'btnImport') and self.btnImport:
            self.btnImport.clicked.connect(self.overtime_panel.on_import_clicked)

        # ─── НОВОЕ: сброс скролла при смене вкладки ───
        if hasattr(self, 'tabWidget') and self.tabWidget:
            self.tabWidget.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int):
        """Сброс скролла и пересчёт размеров при переключении вкладки."""
        if hasattr(self, 'scrollArea') and self.scrollArea:
            self.scrollArea.verticalScrollBar().setValue(0)

        if not hasattr(self, 'tabWidget') or not self.tabWidget:
            return

        current = self.tabWidget.currentWidget()
        if current and current.layout():
            current.layout().activate()

        self.tabWidget.updateGeometry()

        for container in (self.overtime_panel.card_container.myOvertimeContainer,
                          self.overtime_panel.card_container.allOvertimeContainer):
            if container:
                container.updateGeometry()
                if hasattr(container, 'main_layout'):
                    container.main_layout.activate()

        if hasattr(self, 'tabWidget'):
            current_tab = self.tabWidget.currentWidget()
            if current_tab and current_tab.layout():
                current_tab.layout().activate()

        # Подгоняем высоту под новую вкладку
        self._resize_tab_widget()

    # ==================== АДАПТИВНАЯ ВЫСОТА ВКЛАДОК ====================

    def _setup_adaptive_tabs(self):
        """Настраивает подгонку высоты QTabWidget под текущую вкладку."""
        if hasattr(self, 'scrollArea') and self.scrollArea:
            content = self.scrollArea.widget()
            if content and content.layout():
                layout = content.layout()
                has_stretch = False
                if layout.count() > 0:
                    last = layout.itemAt(layout.count() - 1)
                    if last is not None and last.spacerItem() is not None:
                        has_stretch = True
                if not has_stretch:
                    layout.addStretch(1)

        # 2. Подписываемся на переключение вкладок
        if hasattr(self, 'tabWidget') and self.tabWidget:
            self.tabWidget.currentChanged.connect(self._resize_tab_widget)
            # Первичная подгонка
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, self._resize_tab_widget)

        from PyQt6.QtWidgets import QSizePolicy

        if hasattr(self, 'infoFrame') and self.infoFrame:
            self.infoFrame.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Maximum  # вертикально — не больше sizeHint
            )

    def _resize_tab_widget(self, _index=None):
        """Фиксирует высоту QTabWidget по высоте текущей вкладки."""
        if not hasattr(self, 'tabWidget') or not self.tabWidget:
            return

        current = self.tabWidget.currentWidget()
        if current is None:
            return

        # Сначала снимаем ограничения
        self.tabWidget.setMinimumHeight(0)
        self.tabWidget.setMaximumHeight(16777215)

        # Форсируем пересчёт геометрии текущей страницы
        current.updateGeometry()
        if current.layout():
            current.layout().activate()
            current.layout().update()
        current.adjustSize()

        # Считаем высоту
        page_hint = current.sizeHint()
        tab_bar_h = self.tabWidget.tabBar().sizeHint().height()
        total_h = page_hint.height() + tab_bar_h + 4

        # Фиксируем высоту — максимум перебивает минимальный размер
        # внутреннего QStackedWidget (который = максимум по всем вкладкам)
        self.tabWidget.setMinimumHeight(total_h)
        self.tabWidget.setMaximumHeight(total_h)

        self.tabWidget.updateGeometry()
        if self.tabWidget.parentWidget() and self.tabWidget.parentWidget().layout():
            self.tabWidget.parentWidget().layout().activate()

    def load_test_data(self):
        """Загружает тестовые данные профиля (для отладки)."""
        print("load_test_data вызван (тестовые данные)")
        department_chain = [
            ("Организация", "ОАО 'Минский автомобильный завод'"),
            ("Управление", "Управление информационных технологий"),
            ("Отдел", "Отдел разработки ПО"),
            ("Сектор", "Сектор бэкенд-разработки")
        ]
        self.profile_info.update_profile(
            full_name="Иванов Иван Петрович",
            position="Ведущий разработчик",
            department_chain=department_chain,
            phone="375291234567",
            email="ivan.ivanov@company.by",
            birth_date="15.05.1985"
        )

    def create_fallback_ui(self):
        """Создаёт простой UI, если не удалось загрузить profile.ui."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Профиль сотрудника")
        t = get_manager().current
        title.setStyleSheet(
            f"font-size: 24px; font-weight: bold; color: {t.TEXT_PRIMARY};"
        )
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
        self.infoFrame.setStyleSheet(f"""
            background-color: {t.BG_CARD};
            border: 1px solid {t.BORDER_LIGHT};
            border-radius: 16px;
            padding: 20px;
        """)
        self.profile_info.setup_ui_elements(
            infoFrame=self.infoFrame,
            labelTitle=title,
            label_position_value=self.label_position_value,
            label_phone_value=self.label_phone_value,
            label_email_value=self.label_email_value,
            label_birth_date_value=self.label_birth_date_value,
            mainLayout=main_layout
        )

    def reapply_theme(self):
        """Переприменить стили к вложенным менеджерам (пагинация, инфо)."""
        if hasattr(self, 'overtime_panel') and self.overtime_panel:
            self.overtime_panel.reapply_theme()
        if hasattr(self, 'profile_info') and self.profile_info:
            self.profile_info.reapply_theme()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    employee_id = None
    if len(sys.argv) > 1:
        try:
            employee_id = int(sys.argv[1])
        except ValueError:
            pass

    window = ProfileForm(employee_id=employee_id)
    window.setWindowTitle("Профиль сотрудника")
    window.setGeometry(100, 100, 920, 820)
    window.show()
    sys.exit(app.exec())