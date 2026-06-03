import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QApplication,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

from client.windows.system.organisations.organization_card import OrganizationCard
from client.windows.animations.floating_action_button import FloatingActionButton


class OrganizationsPage(QWidget):
    """Страница организаций с поиском, сортировкой и отображением в 1 колонку"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Данные
        self.organizations = []
        self.filtered_orgs = []

        # Состояние
        self.current_sort = "А→Я"

        # Инициализация
        self.init_ui()
        self.load_test_data()
        self.setup_connections()
        self.update_display()

    def init_ui(self):
        """Инициализация UI из файла"""
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)

        # Создаем плавающую кнопку
        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.on_add_org)

        # Подключаемся к скроллу
        self.scrollArea.verticalScrollBar().valueChanged.connect(self.on_scroll)

        # Скрываем кнопку сброса при старте
        self.btnResetFilters.hide()

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'organisations', 'organization_page.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Настройка сигналов"""
        self.btnSort.clicked.connect(self.show_sort_menu)
        self.searchEdit.textChanged.connect(self.on_search_changed)
        self.btnResetFilters.clicked.connect(self.reset_all_filters)

    def load_test_data(self):
        """Загрузка тестовых данных"""
        self.organizations = [
            {
                "id": 1,
                "name": "ОАО МАЗ",
                "unp": "100123456",
                "address": "г. Минск, ул. Социалистическая, 2",
                "phone": "+375 17 123-45-67",
                "email": "info@maz.by",
                "director": "Иванов Иван Иванович",
                "smdo_code": "MAZ_001",
                "is_subscriber": True
            },
            {
                "id": 2,
                "name": "ООО МАЗ-Кузовной",
                "unp": "200234567",
                "address": "г. Минск, ул. Промышленная, 15",
                "phone": "+375 17 234-56-78",
                "email": "info@maz-kuzov.by",
                "director": "Волков Сергей Николаевич",
                "smdo_code": "MAZ_KUZ_001",
                "is_subscriber": True
            },
            {
                "id": 3,
                "name": "СООО МАЗ-МАН",
                "unp": "300345678",
                "address": "г. Минск, ул. Инженерная, 8",
                "phone": "+375 17 345-67-89",
                "email": "info@maz-man.by",
                "director": "Новиков Александр Иванович",
                "smdo_code": "MAZ_MAN_001",
                "is_subscriber": True
            },
            {
                "id": 4,
                "name": "ОАО БЕЛАЗ",
                "unp": "400456789",
                "address": "г. Жодино, ул. 40 лет Октября, 4",
                "phone": "+375 1775 3-45-67",
                "email": "info@belaz.by",
                "director": "Петров Петр Петрович",
                "smdo_code": "BELAZ_001",
                "is_subscriber": True
            },
            {
                "id": 5,
                "name": "ОАО МТЗ",
                "unp": "500567890",
                "address": "г. Минск, ул. Долгобродская, 29",
                "phone": "+375 17 345-67-89",
                "email": "info@mtz.by",
                "director": "Сидоров Сидор Сидорович",
                "smdo_code": "MTZ_001",
                "is_subscriber": True
            },
            {
                "id": 6,
                "name": "ОАО Гомсельмаш",
                "unp": "600678901",
                "address": "г. Гомель, ул. Шоссейная, 41",
                "phone": "+375 232 3-45-67",
                "email": "info@gomselmash.by",
                "director": "Козлов Козел Козлович",
                "smdo_code": "GOMSEL_001",
                "is_subscriber": False
            },
            {
                "id": 7,
                "name": "ОАО БМЗ",
                "unp": "700789012",
                "address": "г. Жлобин, ул. Промышленная, 1",
                "phone": "+375 2334 5-67-89",
                "email": "info@bmz.by",
                "director": "Смирнов Алексей Алексеевич",
                "smdo_code": "BMZ_001",
                "is_subscriber": False
            },
            {
                "id": 8,
                "name": "ОАО Могилевлифтмаш",
                "unp": "800890123",
                "address": "г. Могилев, пр-т Мира, 42",
                "phone": "+375 222 3-45-67",
                "email": "info@liftmash.by",
                "director": "Кузнецов Дмитрий Дмитриевич",
                "smdo_code": "LIFT_001",
                "is_subscriber": False
            },
            {
                "id": 9,
                "name": "ОАО Интеграл",
                "unp": "900901234",
                "address": "г. Минск, ул. Казинца, 121А",
                "phone": "+375 17 345-67-89",
                "email": "info@integral.by",
                "director": "Федоров Федор Федорович",
                "smdo_code": "INTEG_001",
                "is_subscriber": True
            },
            {
                "id": 10,
                "name": "ОАО БАТЭ",
                "unp": "100012345",
                "address": "г. Борисов, ул. Чапаева, 51",
                "phone": "+375 177 7-89-01",
                "email": "info@bate.by",
                "director": "Морозов Михаил Михайлович",
                "smdo_code": "BATE_001",
                "is_subscriber": False
            },
        ]

    def show_sort_menu(self):
        """Показать меню сортировки"""
        menu = QMenu(self)

        menu.setStyleSheet("""
            QMenu { 
                background-color: white; 
                border: 1px solid #c0c0c0; 
                border-radius: 5px; 
                padding: 5px; 
                color: black;
            }
            QMenu::item { 
                padding: 8px 25px 8px 15px; 
                border-radius: 3px; 
                font-size: 14px; 
            }
            QMenu::item:selected { 
                background-color: #e3f2fd; 
            }
            QMenu::separator { 
                height: 1px; 
                background: #e0e0e0; 
                margin: 5px 10px; 
            }
        """)

        sort_options = {
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
            "По УНП (↑)": self.sort_by_unp_asc,
            "По УНП (↓)": self.sort_by_unp_desc,
        }

        for name, func in sort_options.items():
            action = menu.addAction(name)
            action.triggered.connect(lambda checked, f=func, n=name: self.apply_sort(f, n))

        menu.exec(self.btnSort.mapToGlobal(self.btnSort.rect().bottomLeft()))

    def sort_by_name_asc(self, orgs):
        """Сортировка по названию А→Я"""
        return sorted(orgs, key=lambda x: x.get('name', '').lower())

    def sort_by_name_desc(self, orgs):
        """Сортировка по названию Я→А"""
        return sorted(orgs, key=lambda x: x.get('name', '').lower(), reverse=True)

    def sort_by_unp_asc(self, orgs):
        """Сортировка по УНП (возрастание)"""
        return sorted(orgs, key=lambda x: x.get('unp', ''))

    def sort_by_unp_desc(self, orgs):
        """Сортировка по УНП (убывание)"""
        return sorted(orgs, key=lambda x: x.get('unp', ''), reverse=True)

    def apply_sort(self, sort_func, sort_name):
        """Применить сортировку"""
        self.current_sort = sort_name
        short_name = sort_name.split('(')[0].strip() if '(' in sort_name else sort_name
        self.btnSort.setText(f"Сортировка ▼ ({short_name})")
        self.update_reset_button_visibility()
        self.update_display()

    def on_search_changed(self):
        """Обработчик изменения текста поиска"""
        self.update_reset_button_visibility()
        self.update_display()

    def has_active_filters(self):
        """Проверяет, есть ли активные фильтры"""
        if self.searchEdit.text().strip():
            return True

        if self.current_sort != "А→Я":
            return True

        return False

    def update_reset_button_visibility(self):
        """Показать или скрыть кнопку сброса"""
        if self.has_active_filters():
            self.btnResetFilters.show()
        else:
            self.btnResetFilters.hide()

    def reset_all_filters(self):
        """Сброс всех фильтров и поиска"""
        self.searchEdit.clear()

        self.current_sort = "А→Я"
        self.btnSort.setText("Сортировка ▼")

        self.btnResetFilters.hide()
        self.update_display()

    def filter_and_sort_orgs(self):
        """Фильтрация и сортировка организаций"""
        filtered = self.organizations.copy()

        # Поиск
        search_text = self.searchEdit.text().strip().lower()
        if search_text:
            filtered = [
                org for org in filtered
                if search_text in org.get('name', '').lower() or
                   search_text in org.get('unp', '').lower() or
                   search_text in org.get('address', '').lower() or
                   search_text in org.get('director', '').lower() or
                   search_text in org.get('smdo_code', '').lower()
            ]

        # Сортировка
        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
            "По УНП (↑)": self.sort_by_unp_asc,
            "По УНП (↓)": self.sort_by_unp_desc,
        }

        sort_func = sort_methods.get(self.current_sort, self.sort_by_name_asc)
        return sort_func(filtered)

    def update_display(self):
        """Обновление отображения организаций в 1 колонку"""
        # Очищаем layout
        for i in reversed(range(self.orgsLayout.count())):
            widget = self.orgsLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Получаем отфильтрованные и отсортированные организации
        self.filtered_orgs = self.filter_and_sort_orgs()

        # Отображаем организации в 1 КОЛОНКУ
        for org in self.filtered_orgs:
            org_card = OrganizationCard(org)
            org_card.edit_clicked.connect(self.on_edit_org)
            org_card.delete_clicked.connect(self.on_delete_org)

            self.orgsLayout.addWidget(org_card)

        # Добавляем растяжку в конец
        self.orgsLayout.addStretch()

        # Обновляем позицию плавающей кнопки
        self.position_floating_button()

    def position_floating_button(self):
        """Позиционирование плавающей кнопки в правом нижнем углу"""
        if hasattr(self, 'floating_btn'):
            margin = 20
            x = self.width() - self.floating_btn.width() - margin
            y = self.height() - self.floating_btn.height() - margin
            self.floating_btn.update_base_position(x, y)
            self.floating_btn.raise_()

    def on_scroll(self, value):
        """Обработчик скролла"""
        if hasattr(self, 'floating_btn'):
            self.floating_btn.hide_with_animation()
            self.floating_btn.start_hide_timer()

    def resizeEvent(self, event):
        """Обработчик изменения размера для позиционирования кнопки"""
        super().resizeEvent(event)
        self.position_floating_button()

    def on_add_org(self):
        """Обработчик нажатия на плавающую кнопку добавления организации"""
        print("Добавление новой организации")
        QMessageBox.information(
            self,
            "Новая организация",
            "Создание новой организации\n\nЭта функция в разработке."
        )

    def on_edit_org(self, org_data):
        """Обработка редактирования организации"""
        print(f"Редактирование организации: {org_data.get('name')} (ID: {org_data.get('id')})")
        QMessageBox.information(
            self,
            "Редактирование организации",
            f"Редактирование: {org_data.get('name')}\n\nЭта функция в разработке."
        )

    def on_delete_org(self, org_id):
        """Обработка удаления организации"""
        org_name = "Неизвестная организация"
        for org in self.organizations:
            if org.get('id') == org_id:
                org_name = org.get('name', 'Неизвестная организация')
                break

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить организацию «{org_name}»?\n\n"
            f"Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            print(f"Удаление организации ID: {org_id}")
            self.organizations = [org for org in self.organizations if org.get('id') != org_id]
            self.update_display()
            QMessageBox.information(
                self,
                "Успешно",
                f"Организация «{org_name}» успешно удалена."
            )

    def add_org(self, org_data):
        """Добавление новой организации"""
        max_id = max([org.get('id', 0) for org in self.organizations], default=0)
        org_data['id'] = max_id + 1

        self.organizations.append(org_data)
        self.update_display()

    def update_org(self, org_id, new_data):
        """Обновление существующей организации"""
        for i, org in enumerate(self.organizations):
            if org.get('id') == org_id:
                self.organizations[i].update(new_data)
                break

        self.update_display()

    def get_all_organizations(self):
        """Возвращает список всех организаций"""
        return self.organizations.copy()

    def get_filtered_organizations(self):
        """Возвращает список отфильтрованных организаций"""
        return self.filtered_orgs.copy()


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = QWidget()
    window.setWindowTitle("Тест - Организации")
    window.setGeometry(100, 100, 1000, 700)

    orgs_page = OrganizationsPage()

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(orgs_page)

    window.show()
    sys.exit(app.exec())