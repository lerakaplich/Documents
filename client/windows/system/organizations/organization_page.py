# client/windows/system/organizations/organization_page.py

import os
import sys
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QApplication,
    QSizePolicy, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.uic import loadUi

from client.windows.system.organizations.organization_card import OrganizationCard
from client.windows.system.organizations.organization_dialog import OrganizationDialog
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.animations.animated_notification import NotificationManager
from client.services.org_service import get_org_service
from client.core.http_client import HttpClient
from client.core.config import config
from client.core.state.app_state import AppState


class OrganizationsPage(QWidget):
    """Страница организаций с поиском, сортировкой и отображением в 2 колонки"""

    data_loaded = pyqtSignal()

    def __init__(self, parent=None, http_client: Optional[HttpClient] = None):
        super().__init__(parent)

        # Используем переданный HttpClient или создаем новый
        if http_client is None:
            app_state = AppState()
            if app_state.http_client:
                self.http_client = app_state.http_client
            else:
                self.http_client = HttpClient(config.base_url)
        else:
            self.http_client = http_client

        self.org_service = get_org_service(self.http_client)

        # Данные
        self.organizations: List[Dict[str, Any]] = []
        self.filtered_orgs: List[Dict[str, Any]] = []

        # Состояние
        self.current_sort = "А→Я"
        self.is_loading = False

        # Инициализация
        self.init_ui()
        self.setup_connections()

        # Создаем менеджер уведомлений
        self.notification_manager = NotificationManager(self, max_visible=3)

        # Загружаем данные
        QTimer.singleShot(100, self.load_organizations)

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
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'organizations', 'organization_page.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Настройка сигналов"""
        self.btnSort.clicked.connect(self.show_sort_menu)
        self.searchEdit.textChanged.connect(self.on_search_changed)
        self.btnResetFilters.clicked.connect(self.reset_all_filters)

    def show_success_notification(self, message: str):
        """Показать уведомление об успехе"""
        self.notification_manager.show_notification(f"✅ {message}", duration=2500)

    def show_error_notification(self, message: str):
        """Показать уведомление об ошибке"""
        self.notification_manager.show_notification(f"❌ {message}", duration=3000)

    def show_info_notification(self, message: str):
        """Показать информационное уведомление"""
        self.notification_manager.show_notification(f"ℹ️ {message}", duration=2500)

    # ==================== ЗАГРУЗКА ДАННЫХ ====================

    # client/windows/system/organizations/organization_page.py

    def load_organizations(self):
        """Загрузить организации из API"""
        if self.is_loading:
            return

        self.is_loading = True

        try:
            orgs = self.org_service.get_all_organizations(limit=200)

            # Преобразуем данные в нужный формат
            self.organizations = []
            for org in orgs:
                # Правильно обрабатываем телефон
                phone = org.get('phone_number')
                if phone is None:
                    phone = org.get('phone', '')
                if phone is None:
                    phone = ''

                self.organizations.append({
                    'id': org.get('id'),
                    'name': org.get('name', org.get('full_name', '')),
                    'full_name': org.get('full_name', ''),
                    'short_name': org.get('short_name', ''),
                    'unp': org.get('unp', ''),
                    'address': org.get('address', ''),
                    'phone': str(phone) if phone else '',
                    'phone_number': str(phone) if phone else '',
                    'email': org.get('email', ''),
                    'director': org.get('director', ''),
                    'smdo_code': org.get('smdo_code', ''),
                    'is_subscriber': org.get('is_subscriber', False)
                })

            self.is_loading = False
            self.update_display()
            self.data_loaded.emit()

            if self.organizations:
                self.show_success_notification(f"Загружено {len(self.organizations)} организаций")

        except Exception as e:
            self.is_loading = False
            import logging
            logging.error(f"Ошибка загрузки организаций: {e}")

            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось загрузить организации")

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
        return sorted(orgs, key=lambda x: x.get('name', '').lower())

    def sort_by_name_desc(self, orgs):
        return sorted(orgs, key=lambda x: x.get('name', '').lower(), reverse=True)

    def sort_by_unp_asc(self, orgs):
        return sorted(orgs, key=lambda x: x.get('unp', ''))

    def sort_by_unp_desc(self, orgs):
        return sorted(orgs, key=lambda x: x.get('unp', ''), reverse=True)

    def apply_sort(self, sort_func, sort_name):
        self.current_sort = sort_name
        short_name = sort_name.split('(')[0].strip() if '(' in sort_name else sort_name
        self.btnSort.setText(f"Сортировка ▼ ({short_name})")
        self.update_reset_button_visibility()
        self.update_display()
        self.show_info_notification(f"Сортировка: {short_name}")

    # ==================== ПОИСК И ФИЛЬТРЫ ====================

    def on_search_changed(self):
        self.update_reset_button_visibility()
        self.update_display()

    def has_active_filters(self):
        if self.searchEdit.text().strip():
            return True
        if self.current_sort != "А→Я":
            return True
        return False

    def update_reset_button_visibility(self):
        if self.has_active_filters():
            self.btnResetFilters.show()
        else:
            self.btnResetFilters.hide()

    def reset_all_filters(self):
        self.searchEdit.clear()
        self.current_sort = "А→Я"
        self.btnSort.setText("Сортировка ▼")
        self.btnResetFilters.hide()
        self.update_display()
        self.show_info_notification("Фильтры сброшены")

    def filter_and_sort_orgs(self):
        """Фильтрация и сортировка организаций"""
        filtered = self.organizations.copy()

        # Поиск
        search_text = self.searchEdit.text().strip().lower()
        if search_text:
            filtered = [
                org for org in filtered
                if search_text in org.get('name', '').lower() or
                   search_text in org.get('full_name', '').lower() or
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

    # ==================== ОТОБРАЖЕНИЕ ====================

    def _clear_layout_completely(self, layout):
        """Полностью очищает layout от всех виджетов и вложенных layout'ов"""
        if layout is None:
            return

        while layout.count() > 0:
            item = layout.takeAt(0)

            if item is None:
                continue

            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout():
                self._clear_layout_completely(item.layout())
                item.layout().setParent(None)

    def update_display(self):
        """Обновление отображения организаций в 2 колонки"""
        # Полностью очищаем layout
        self._clear_layout_completely(self.orgsLayout)

        # Получаем отфильтрованные и отсортированные организации
        self.filtered_orgs = self.filter_and_sort_orgs()

        # Если нет организаций, показываем сообщение
        if not self.filtered_orgs:
            empty_label = QLabel("Нет организаций")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #6c757d; font-size: 16px; padding: 40px;")
            self.orgsLayout.addWidget(empty_label)
            self.position_floating_button()
            return

        # Создаем контейнер для двух колонок
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setSpacing(10)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Создаем две колонки
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setAlignment(Qt.AlignmentFlag.AlignTop)

        right_column = QVBoxLayout()
        right_column.setSpacing(10)
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Распределяем карточки по колонкам
        for i, org in enumerate(self.filtered_orgs):
            org_card = OrganizationCard(org)
            org_card.edit_clicked.connect(self.on_edit_org)
            org_card.delete_clicked.connect(self.on_delete_org)
            org_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            if i % 2 == 0:
                left_column.addWidget(org_card)
            else:
                right_column.addWidget(org_card)

        # Добавляем колонки в контейнер
        container_layout.addLayout(left_column)
        container_layout.addLayout(right_column)

        # Добавляем контейнер в основной layout
        self.orgsLayout.addWidget(container)

        # Добавляем растяжку
        self.orgsLayout.addStretch()

        self.position_floating_button()

    # ==================== РАБОТА С ОРГАНИЗАЦИЯМИ (CRUD) ====================

    def on_add_org(self):
        """Обработчик нажатия на плавающую кнопку добавления организации"""
        dialog = OrganizationDialog(self, item={})

        if dialog.exec():
            new_org_data = dialog.get_data()
            self._create_organization(new_org_data)

    def _create_organization(self, org_data: Dict[str, Any]):
        """Создание организации"""
        try:
            # Получаем телефон
            phone = org_data.get('phone')
            if phone is None:
                phone = org_data.get('phone_number')
            if phone is None:
                phone = ''

            # Формируем данные для сервера
            server_data = {
                'name': org_data.get('full_name', org_data.get('name', '')),
                'full_name': org_data.get('full_name', ''),
                'short_name': org_data.get('short_name', ''),
                'unp': org_data.get('unp', ''),
                'address': org_data.get('address', ''),
                'phone_number': str(phone) if phone else None,  # Отправляем как phone_number
                'email': org_data.get('email', ''),
                'director': org_data.get('director', ''),
                'smdo_code': org_data.get('smdo_code', ''),
                'is_subscriber': org_data.get('is_subscriber', False)
            }

            print(f"[DEBUG] Создание организации: server_data={server_data}")

            result = self.org_service.create_organization(server_data)

            if result:
                print(f"[DEBUG] Результат создания: {result}")

                result_phone = result.get('phone_number')
                if result_phone is None:
                    result_phone = result.get('phone')
                if result_phone is None:
                    result_phone = ''

                self.organizations.append({
                    'id': result.get('id'),
                    'name': result.get('name', result.get('full_name', '')),
                    'full_name': result.get('full_name', ''),
                    'short_name': result.get('short_name', ''),
                    'unp': result.get('unp', ''),
                    'address': result.get('address', ''),
                    'phone': str(result_phone),
                    'phone_number': str(result_phone),
                    'email': result.get('email', ''),
                    'director': result.get('director', ''),
                    'smdo_code': result.get('smdo_code', ''),
                    'is_subscriber': result.get('is_subscriber', False)
                })

                self.update_display()
                self.show_success_notification(f"Организация «{result.get('name')}» создана")
            else:
                self.show_error_notification("Не удалось создать организацию")

        except Exception as e:
            import logging
            logging.error(f"Ошибка создания организации: {e}")
            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось создать организацию")

    def on_edit_org(self, org_data: Dict[str, Any]):
        """Обработка редактирования организации"""
        org_id = org_data.get('id')
        if not org_id:
            self.show_error_notification("ID организации не найден")
            return

        try:
            # Получаем актуальные данные с сервера
            server_org = self.org_service.get_organization(org_id)
            if not server_org:
                self.show_error_notification("Организация не найдена на сервере")
                return

            print(f"[DEBUG] Загружена организация с сервера: {server_org}")

            # Получаем телефон - обрабатываем None
            phone_value = server_org.get('phone_number')
            if phone_value is None:
                phone_value = server_org.get('phone')
            if phone_value is None:
                phone_value = ''

            # Получаем полное имя
            full_name = server_org.get('full_name')
            if full_name is None or not full_name:
                full_name = server_org.get('name', '')

            # Подготовка данных для диалога
            full_org_data = {
                'id': server_org.get('id'),
                'name': server_org.get('name', ''),
                'full_name': full_name,
                'short_name': server_org.get('short_name') or '',
                'unp': server_org.get('unp') or '',
                'address': server_org.get('address') or '',
                'phone': str(phone_value),  # Телефон в поле phone
                'phone_number': str(phone_value),  # И в phone_number
                'email': server_org.get('email') or '',
                'director': server_org.get('director') or '',
                'smdo_code': server_org.get('smdo_code') or '',
                'is_subscriber': server_org.get('is_subscriber', False)
            }

            print(f"[DEBUG] Подготовлены данные для диалога: {full_org_data}")

            dialog = OrganizationDialog(self, item=full_org_data)

            if dialog.exec():
                updated_data = dialog.get_data()
                print(f"[DEBUG] Данные из диалога: {updated_data}")
                self._update_organization(org_id, updated_data)

        except Exception as e:
            import logging
            import traceback
            logging.error(f"Ошибка загрузки организации для редактирования: {e}")
            traceback.print_exc()
            self.show_error_notification("Не удалось загрузить данные организации")

    def _update_organization(self, org_id: int, updated_data: Dict[str, Any]):
        """Обновление организации"""
        try:
            # Получаем телефон из данных
            phone = updated_data.get('phone')
            if phone is None:
                phone = updated_data.get('phone_number')
            if phone is None:
                phone = ''

            # Формируем данные для сервера - ВАЖНО: используем phone_number
            server_data = {
                'name': updated_data.get('full_name', updated_data.get('name', '')),
                'full_name': updated_data.get('full_name', ''),
                'short_name': updated_data.get('short_name', ''),
                'unp': updated_data.get('unp', ''),
                'address': updated_data.get('address', ''),
                'phone_number': str(phone) if phone else None,  # Отправляем как phone_number
                'email': updated_data.get('email', ''),
                'director': updated_data.get('director', ''),
                'smdo_code': updated_data.get('smdo_code', ''),
                'is_subscriber': updated_data.get('is_subscriber', False)
            }

            print(f"[DEBUG] Обновление организации {org_id}: server_data={server_data}")

            result = self.org_service.update_organization(org_id, server_data)

            if result:
                print(f"[DEBUG] Результат обновления: {result}")

                # Получаем телефон из результата
                result_phone = result.get('phone_number')
                if result_phone is None:
                    result_phone = result.get('phone')
                if result_phone is None:
                    result_phone = ''

                # Обновляем данные в памяти
                for i, org in enumerate(self.organizations):
                    if org.get('id') == org_id:
                        self.organizations[i].update({
                            'name': result.get('name', result.get('full_name', '')),
                            'full_name': result.get('full_name', ''),
                            'short_name': result.get('short_name', ''),
                            'unp': result.get('unp', ''),
                            'address': result.get('address', ''),
                            'phone': str(result_phone),
                            'phone_number': str(result_phone),
                            'email': result.get('email', ''),
                            'director': result.get('director', ''),
                            'smdo_code': result.get('smdo_code', ''),
                            'is_subscriber': result.get('is_subscriber', False)
                        })
                        break

                self.update_display()
                self.show_success_notification(f"Организация «{result.get('name')}» обновлена")
            else:
                self.show_error_notification("Не удалось обновить организацию")

        except Exception as e:
            import logging
            logging.error(f"Ошибка обновления организации: {e}")
            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось обновить организацию")

    def on_delete_org(self, org_id: int):
        """Обработка удаления организации"""
        org_name = "Неизвестная организация"
        for org in self.organizations:
            if org.get('id') == org_id:
                org_name = org.get('name', 'Неизвестная организация')
                break

        # Используем DeleteDialog
        from client.windows.system.delete_dialog import DeleteDialog
        if DeleteDialog.show_confirmation(self):
            self._delete_organization(org_id, org_name)

    def _delete_organization(self, org_id: int, org_name: str):
        """Удаление организации"""
        try:
            success = self.org_service.delete_organization(org_id)

            if success:
                self.organizations = [org for org in self.organizations if org.get('id') != org_id]
                self.update_display()
                self.show_success_notification(f"Организация «{org_name}» удалена")
            else:
                self.show_error_notification("Не удалось удалить организацию")

        except Exception as e:
            import logging
            logging.error(f"Ошибка удаления организации: {e}")
            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось удалить организацию")

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def position_floating_button(self):
        if hasattr(self, 'floating_btn'):
            margin = 20
            x = self.width() - self.floating_btn.width() - margin
            y = self.height() - self.floating_btn.height() - margin
            self.floating_btn.update_base_position(x, y)
            self.floating_btn.raise_()

    def on_scroll(self, value):
        if hasattr(self, 'floating_btn'):
            self.floating_btn.hide_with_animation()
            self.floating_btn.start_hide_timer()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_floating_button()

        if hasattr(self, 'notification_manager'):
            self.notification_manager.container.setGeometry(
                0, 0, self.width(), self.height()
            )

    def get_all_organizations(self):
        return self.organizations.copy()

    def get_filtered_organizations(self):
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