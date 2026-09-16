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

from client.core.state.data_events import get_data_events
from client.windows.system.departments.api_task import ApiTask, TaskKeeper
from client.windows.system.organizations.organization_card import OrganizationCard
from client.windows.system.organizations.organization_dialog import OrganizationDialog
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.animations.animated_notification import NotificationManager
from client.services.org_service import get_org_service
from client.core.http_client import HttpClient, logger
from client.core.config import config
from client.core.state.app_state import AppState


class OrganizationsPage(QWidget):
    """Страница организаций с поиском, сортировкой и отображением в 2 колонки"""

    data_loaded = pyqtSignal()

    def __init__(self, parent=None, http_client: Optional[HttpClient] = None):
        super().__init__(parent)

        if http_client is None:
            app_state = AppState()
            if app_state.http_client:
                self.http_client = app_state.http_client
            else:
                self.http_client = HttpClient(config.base_url)
        else:
            self.http_client = http_client

        self.data_events = get_data_events()
        self.data_events.departments_changed.connect(self._on_external_change)
        self.data_events.employees_changed.connect(self._on_external_change)
        self.data_events.organizations_changed.connect(self._on_external_change)
        # защита от собственных эмиссий
        self._self_change_in_progress = False

        self.org_service = get_org_service(self.http_client)

        # Данные
        self.organizations: List[Dict[str, Any]] = []
        self.filtered_orgs: List[Dict[str, Any]] = []
        self._tasks = TaskKeeper()

        # Состояние
        self.current_sort = "А→Я"
        self.is_loading = False

        # Инициализация
        self.init_ui()
        self.setup_connections()

        self.notification_manager = NotificationManager(self, max_visible=3)

        QTimer.singleShot(100, self.load_organizations)

    # ==================== UI ====================

    def init_ui(self):
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)

        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.on_add_org)

        self.scrollArea.verticalScrollBar().valueChanged.connect(self.on_scroll)

        self.btnResetFilters.hide()

    def get_ui_path(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'organizations', 'organization_page.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        self.btnSort.clicked.connect(self.show_sort_menu)
        self.searchEdit.textChanged.connect(self.on_search_changed)
        self.btnResetFilters.clicked.connect(self.reset_all_filters)

    # ==================== Уведомления ====================

    def show_success_notification(self, message: str):
        self.notification_manager.show_notification(f"✅ {message}", duration=2500)

    def show_error_notification(self, message: str):
        self.notification_manager.show_notification(f"❌ {message}", duration=3000)

    def show_info_notification(self, message: str):
        self.notification_manager.show_notification(f"ℹ️ {message}", duration=2500)

    # ==================== ШИНА СОБЫТИЙ ====================

    def _on_external_change(self, org_id: int = 0):
        """Что-то поменялось в другой вкладке — обновляем список организаций.

        Если известен id — точечно перезапрашиваем только его.
        Иначе — полный refetch.
        """
        if self._self_change_in_progress:
            return
        if self.is_loading:
            return

        if org_id:
            if self._refresh_one(org_id):
                return
        # fallback — если id=0 или не нашли в локальном списке
        self.load_organizations()

    def _refresh_one(self, org_id: int) -> bool:
        """Перезапрашивает ОДНУ организацию и обновляет её карточку. Без полного GET /org."""
        try:
            server_org = self.org_service.get_organization(org_id)
        except Exception as e:
            print(f"[WARN] GET /org/{org_id}: {e}")
            return False
        if not server_org:
            return False
        for i, o in enumerate(self.organizations):
            if o.get('id') == org_id:
                self.organizations[i] = self._normalize_org(server_org)
                self.update_display()
                return True
        return False

    def get_department_staff(self, dept_id: int) -> list:
        """Сотрудники подразделения — для комбобокса «Руководитель»."""
        try:
            response = self.http.get(f"{self.base_path}/{dept_id}/staff")
            return response if isinstance(response, list) else []
        except Exception as e:
            logger.error(f"Ошибка получения сотрудников отдела {dept_id}: {e}")
            return []

    # ==================== ЗАГРУЗКА ДАННЫХ ====================

    def load_organizations(self):
        """Полный refetch списка организаций."""
        if self.is_loading:
            return

        self.is_loading = True
        try:
            orgs = self.org_service.get_all_organizations(limit=200)
            self.organizations = [self._normalize_org(org) for org in (orgs or [])]

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

    def _normalize_org(self, raw: dict) -> dict:
        """Приводит сырой ответ сервера к формату, который ждут карточки."""
        phone = raw.get('phone_number')
        if phone is None:
            phone = raw.get('phone', '')
        if phone is None:
            phone = ''
        return {
            'id': raw.get('id'),
            'name': raw.get('name', raw.get('full_name', '')),
            'full_name': raw.get('full_name', ''),
            'short_name': raw.get('short_name', ''),
            'unp': raw.get('unp', ''),
            'address': raw.get('address', ''),
            'phone': str(phone) if phone else '',
            'phone_number': str(phone) if phone else '',
            'email': raw.get('email', ''),
            'director': raw.get('director', ''),
            'smdo_code': raw.get('smdo_code', ''),
            'is_subscriber': raw.get('is_subscriber', False),
        }

    # ==================== СОРТИРОВКА ====================

    def show_sort_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { 
                background-color: white; 
                border: 1px solid #c0c0c0; 
                border-radius: 5px; 
                padding: 5px; 
                color: black;
            }
            QMenu::item { padding: 8px 25px 8px 15px; border-radius: 3px; font-size: 14px; }
            QMenu::item:selected { background-color: #e3f2fd; }
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
        filtered = self.organizations.copy()

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
        if layout is None:
            return
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
                continue
            sub = item.layout()
            if sub is not None:
                self._clear_layout_completely(sub)
                sub.deleteLater()

    def update_display(self):
        self._clear_layout_completely(self.orgsLayout)
        self.filtered_orgs = self.filter_and_sort_orgs()

        if not self.filtered_orgs:
            empty_label = QLabel("Нет организаций")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #6c757d; font-size: 16px; padding: 40px;")
            self.orgsLayout.addWidget(empty_label)
            self.position_floating_button()
            return

        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setSpacing(10)
        container_layout.setContentsMargins(0, 0, 0, 0)

        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setAlignment(Qt.AlignmentFlag.AlignTop)

        right_column = QVBoxLayout()
        right_column.setSpacing(10)
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setAlignment(Qt.AlignmentFlag.AlignTop)

        # всегда создаём новые карточки — старые уже уничтожены
        for i, org in enumerate(self.filtered_orgs):
            card = OrganizationCard(org)
            card.edit_clicked.connect(self.on_edit_org)
            card.delete_clicked.connect(self.on_delete_org)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            if i % 2 == 0:
                left_column.addWidget(card)
            else:
                right_column.addWidget(card)

        container_layout.addLayout(left_column)
        container_layout.addLayout(right_column)
        self.orgsLayout.addWidget(container)
        self.orgsLayout.addStretch()

        self.position_floating_button()

    # ==================== CRUD ====================

    def on_add_org(self):
        dialog = OrganizationDialog(self, item={})
        if dialog.exec():
            new_org_data = dialog.get_data()
            self._create_organization(new_org_data)

    def _create_organization(self, org_data: Dict[str, Any]):
        try:
            phone = org_data.get('phone')
            if phone is None:
                phone = org_data.get('phone_number')
            if phone is None:
                phone = ''

            server_data = {
                'name': org_data.get('full_name', org_data.get('name', '')),
                'full_name': org_data.get('full_name', ''),
                'short_name': org_data.get('short_name', ''),
                'unp': org_data.get('unp', ''),
                'address': org_data.get('address', ''),
                'phone_number': str(phone) if phone else None,
                'email': org_data.get('email', ''),
                'director': org_data.get('director', ''),
                'smdo_code': org_data.get('smdo_code', ''),
                'is_subscriber': org_data.get('is_subscriber', False)
            }

            print(f"[DEBUG] Создание организации: server_data={server_data}")

            result = self.org_service.create_organization(server_data)

            if result:
                new_id = result.get('id')
                self.organizations.append(self._normalize_org(result))
                self.update_display()  # без refetch
                self.show_success_notification(f"Организация «{result.get('name')}» создана")
                self._emit_self_change(new_id)
            else:
                self.show_error_notification("Не удалось создать организацию")

        except Exception as e:
            import logging
            logging.error(f"Ошибка создания организации: {e}")
            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось создать организацию")

    def on_edit_org(self, org_data):
        org_id = org_data.get('id')
        if not org_id:
            self.show_error_notification("ID организации не найден")
            return

        local = next((o for o in self.organizations if o.get('id') == org_id), {}) or {}
        self._open_edit_dialog(org_id, dict(local))

    def _open_edit_dialog(self, org_id, data):
        phone = data.get('phone_number') or data.get('phone') or ''
        full_name = data.get('full_name') or data.get('name', '')

        payload = {
            'id': data.get('id'),
            'name': data.get('name', ''),
            'full_name': full_name,
            'short_name': data.get('short_name') or '',
            'unp': data.get('unp') or '',
            'address': data.get('address') or '',
            'phone': str(phone),
            'phone_number': str(phone),
            'email': data.get('email') or '',
            'director': data.get('director') or '',
            'smdo_code': data.get('smdo_code') or '',
            'is_subscriber': data.get('is_subscriber', False),
        }

        dialog = OrganizationDialog(self, item=payload)
        if dialog.exec():
            updated = dialog.get_data()
            self._update_organization(org_id, updated)

    def _update_organization(self, org_id: int, updated_data: Dict[str, Any]):
        try:
            phone = updated_data.get('phone')
            if phone is None:
                phone = updated_data.get('phone_number')
            if phone is None:
                phone = ''

            server_data = {
                'name': updated_data.get('full_name', updated_data.get('name', '')),
                'full_name': updated_data.get('full_name', ''),
                'short_name': updated_data.get('short_name', ''),
                'unp': updated_data.get('unp', ''),
                'address': updated_data.get('address', ''),
                'phone_number': str(phone) if phone else None,
                'email': updated_data.get('email', ''),
                'director': updated_data.get('director', ''),
                'smdo_code': updated_data.get('smdo_code', ''),
                'is_subscriber': updated_data.get('is_subscriber', False)
            }

            print(f"[DEBUG] Обновление организации {org_id}: server_data={server_data}")

            result = self.org_service.update_organization(org_id, server_data)

            if result:
                # точечно обновляем локальный список из ответа PATCH
                for i, org in enumerate(self.organizations):
                    if org.get('id') == org_id:
                        self.organizations[i] = self._normalize_org(result)
                        break

                self.update_display()   # без GET /org
                self.show_success_notification(f"Организация «{result.get('name')}» обновлена")
                self._emit_self_change(org_id)
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
        org_name = "Неизвестная организация"
        for org in self.organizations:
            if org.get('id') == org_id:
                org_name = org.get('name', 'Неизвестная организация')
                break

        from client.windows.system.delete_dialog import DeleteDialog
        if DeleteDialog.show_confirmation(self):
            self._delete_organization(org_id, org_name)

    def _delete_organization(self, org_id: int, org_name: str):
        try:
            self.org_service.delete_organization(org_id)
        except Exception as e:
            msg = str(e).lower()
            if "404" in msg or "не найдена" in msg:
                print(f"[INFO] DELETE org {org_id}: уже не существует на сервере")
            else:
                print(f"[ERROR] DELETE org {org_id}: {e}")
                self.show_error_notification(f"Не удалось удалить: {e}")
                return

        self.organizations = [o for o in self.organizations if o.get('id') != org_id]
        self.update_display()
        self.show_success_notification(f"Организация «{org_name}» удалена")
        self._emit_self_change(org_id)

    # ==================== ВСПОМОГАТЕЛЬНЫЕ ====================

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