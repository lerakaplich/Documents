# client/windows/system/tags/tags_page.py

import os
import sys
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QApplication,
    QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.uic import loadUi

from client.core.themes import get_menu_style, T, apply_theme_to_widget
from client.windows.system.tags.tag_card import TagCard
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.tags.tag_dialog import TagDialog
from client.windows.animations.animated_notification import NotificationManager
from client.windows.system.delete_dialog import DeleteDialog
from client.services.tag_service import get_tag_service
from client.core.http_client import HttpClient
from client.core.config import config
from client.core.state.app_state import AppState


class TagsPage(QWidget):
    """Страница тегов с поиском, сортировкой и отображением в сетке (2 колонки)"""

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

        self.tag_service = get_tag_service(self.http_client)

        # Данные
        self.tags: List[Dict[str, Any]] = []
        self.filtered_tags: List[Dict[str, Any]] = []

        # Состояние
        self.current_sort = "По приоритету (важные сверху)"
        self.is_loading = False

        # Инициализация
        self.init_ui()
        self.setup_connections()

        # Создаем менеджер уведомлений
        self.notification_manager = NotificationManager(self, max_visible=3)

        # Загружаем данные
        QTimer.singleShot(100, self.load_tags)

    def init_ui(self):
        """Инициализация UI из файла"""
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)
            apply_theme_to_widget(self)

        # Создаем плавающую кнопку
        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.on_add_tag)

        # Подключаемся к скроллу
        self.scrollArea.verticalScrollBar().valueChanged.connect(self.on_scroll)

        # Скрываем кнопку сброса при старте
        self.btnResetFilters.hide()

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'tags', 'tag_page.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Настройка сигналов"""
        self.btnSort.clicked.connect(self.show_sort_menu)
        self.searchEdit.textChanged.connect(self.on_search_changed)
        self.btnResetFilters.clicked.connect(self.reset_all_filters)

    def show_success_notification(self, message: str):
        """Показать уведомление об успехе"""
        self.notification_manager.show_notification(
            f"✅ {message}",
            duration=2500
        )

    def show_error_notification(self, message: str):
        """Показать уведомление об ошибке"""
        self.notification_manager.show_notification(
            f"❌ {message}",
            duration=3000
        )

    def show_info_notification(self, message: str):
        """Показать информационное уведомление"""
        self.notification_manager.show_notification(
            f"ℹ️ {message}",
            duration=2500
        )

    # ==================== ЗАГРУЗКА ДАННЫХ ====================

    def load_tags(self):
        """Загрузить теги из API"""
        if self.is_loading:
            return

        self.is_loading = True

        try:
            tags = self.tag_service.get_all_tags()

            # Преобразуем данные в нужный формат
            self.tags = []
            for tag in tags:
                self.tags.append({
                    'id': tag.get('id'),
                    'name': tag.get('name', ''),
                    'color': tag.get('color', T.ACCENT_PRIMARY),
                    'documents_count': tag.get('documents_count', 0),
                    'priority': tag.get('priority', 'normal')
                })

            self.is_loading = False
            self.update_display()
            self.data_loaded.emit()


        except Exception as e:
            self.is_loading = False
            import logging
            logging.error(f"Ошибка загрузки тегов: {e}")

            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification(f"Не удалось загрузить теги")

    # ==================== СОРТИРОВКА ====================

    def show_sort_menu(self):
        """Показать меню сортировки"""
        menu = QMenu(self)
        menu.setStyleSheet(get_menu_style())

        sort_options = {
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
            "По количеству документов (↑)": self.sort_by_count_asc,
            "По количеству документов (↓)": self.sort_by_count_desc,
            "По приоритету (важные сверху)": self.sort_by_priority_desc,
            "По приоритету (обычные сверху)": self.sort_by_priority_asc,
        }

        for name, func in sort_options.items():
            action = menu.addAction(name)
            action.triggered.connect(lambda checked, f=func, n=name: self.apply_sort(f, n))

        menu.exec(self.btnSort.mapToGlobal(self.btnSort.rect().bottomLeft()))

    def sort_by_priority_desc(self, tags):
        """Срочные → Важные → Обычные, внутри — по названию."""
        order = {'urgent': 0, 'important': 1, 'normal': 2}
        return sorted(
            tags,
            key=lambda x: (order.get(x.get('priority', 'normal'), 3), x.get('name', '').lower())
        )

    def sort_by_priority_asc(self, tags):
        """Обычные → Важные → Срочные, внутри — по названию."""
        order = {'normal': 0, 'important': 1, 'urgent': 2}
        return sorted(
            tags,
            key=lambda x: (order.get(x.get('priority', 'normal'), 3), x.get('name', '').lower())
        )

    def sort_by_name_asc(self, tags):
        return sorted(tags, key=lambda x: x.get('name', '').lower())

    def sort_by_name_desc(self, tags):
        return sorted(tags, key=lambda x: x.get('name', '').lower(), reverse=True)

    def sort_by_count_asc(self, tags):
        return sorted(tags, key=lambda x: x.get('documents_count', 0))

    def sort_by_count_desc(self, tags):
        return sorted(tags, key=lambda x: x.get('documents_count', 0), reverse=True)

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
        if self.current_sort != "По приоритету (важные сверху)":
            return True
        return False

    def update_reset_button_visibility(self):
        if self.has_active_filters():
            self.btnResetFilters.show()
        else:
            self.btnResetFilters.hide()

    def reset_all_filters(self):
        self.searchEdit.clear()
        self.current_sort = "По приоритету (важные сверху)"
        self.btnSort.setText("Сортировка ▼")
        self.btnResetFilters.hide()
        self.update_display()
        self.show_info_notification("Фильтры сброшены")

    def filter_and_sort_tags(self):
        filtered = self.tags.copy()

        # Поиск
        search_text = self.searchEdit.text().strip().lower()
        if search_text:
            filtered = [
                tag for tag in filtered
                if search_text in tag.get('name', '').lower()
            ]

        # Сортировка
        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
            "По количеству документов (↑)": self.sort_by_count_asc,
            "По количеству документов (↓)": self.sort_by_count_desc,
            "По приоритету (важные сверху)": self.sort_by_priority_desc,
            "По приоритету (обычные сверху)": self.sort_by_priority_asc,
        }

        sort_func = sort_methods.get(self.current_sort, self.sort_by_name_asc)
        return sort_func(filtered)

    # ==================== ОТОБРАЖЕНИЕ ====================

    def update_display(self):
        """Обновление отображения тегов в сетке (2 колонки)"""
        # Очищаем сетку
        for i in reversed(range(self.tagsGridLayout.count())):
            widget = self.tagsGridLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Получаем отфильтрованные и отсортированные теги
        self.filtered_tags = self.filter_and_sort_tags()

        # Отображаем теги в сетке - 2 КОЛОНКИ
        row, col = 0, 0
        max_cols = 2

        for tag in self.filtered_tags:
            tag_card = TagCard(tag)
            tag_card.edit_clicked.connect(self.on_edit_tag)
            tag_card.delete_clicked.connect(self.on_delete_tag)
            tag_card.color_changed.connect(self.on_color_changed)

            tag_card.setMinimumWidth(350)

            self.tagsGridLayout.addWidget(tag_card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Добавляем растяжку
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.tagsGridLayout.addWidget(spacer, row + 1, 0, 1, max_cols)

        self.position_floating_button()

    # ==================== РАБОТА С ТЕГАМИ (CRUD) ====================

    def on_add_tag(self):
        """Обработчик нажатия на плавающую кнопку добавления тега"""
        dialog = TagDialog(self)

        if dialog.exec():
            tag_data = dialog.get_tag_data()
            self._create_tag(tag_data)

    def _create_tag(self, tag_data: Dict[str, Any]):
        """Создание тега"""
        try:
            tag_data.pop('id', None)
            result = self.tag_service.create_tag(tag_data)

            if result:
                self.tags.append({
                    'id': result.get('id'),
                    'name': result.get('name', ''),
                    'color': result.get('color', '#CCAB6E'),
                    'documents_count': result.get('documents_count', 0),
                    'priority': result.get('priority', 'normal')
                })

                self.update_display()
                self.show_success_notification(f"Тег «{result.get('name')}» создан")
            else:
                self.show_error_notification("Не удалось создать тег")

        except Exception as e:
            import logging
            logging.error(f"Ошибка создания тега: {e}")
            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось создать тег")

    def on_edit_tag(self, tag_data: Dict[str, Any]):
        """Обработка редактирования тега"""
        full_tag_data = None
        for tag in self.tags:
            if tag.get('id') == tag_data.get('id'):
                full_tag_data = tag.copy()
                break

        if not full_tag_data:
            self.show_error_notification("Тег не найден")
            return

        dialog = TagDialog(self, tag_id=tag_data.get('id'), tag_data=full_tag_data)

        if dialog.exec():
            updated_data = dialog.get_tag_data()
            self._update_tag(tag_data.get('id'), updated_data)

    def _update_tag(self, tag_id: int, updated_data: Dict[str, Any]):
        """Обновление тега"""
        try:
            result = self.tag_service.update_tag(tag_id, updated_data)

            if result:
                for i, tag in enumerate(self.tags):
                    if tag.get('id') == tag_id:
                        self.tags[i].update({
                            'name': result.get('name', ''),
                            'color': result.get('color', T.ACCENT_PRIMARY),
                            'priority': result.get('priority', 'normal'),
                            'documents_count': result.get('documents_count', 0)
                        })
                        break

                self.update_display()
                self.show_success_notification(f"Тег «{result.get('name')}» обновлен")
            else:
                self.show_error_notification("Не удалось обновить тег")

        except Exception as e:
            import logging
            logging.error(f"Ошибка обновления тега: {e}")
            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось обновить тег")

    def on_delete_tag(self, tag_id: int):
        """Обработка удаления тега"""
        tag_name = "Неизвестный тег"
        for tag in self.tags:
            if tag.get('id') == tag_id:
                tag_name = tag.get('name', 'Неизвестный тег')
                break

        # Используем красивый диалог удаления
        if DeleteDialog.show_confirmation(self):
            self._delete_tag(tag_id, tag_name)

    def _delete_tag(self, tag_id: int, tag_name: str):
        """Удаление тега"""
        try:
            success = self.tag_service.delete_tag(tag_id)

            if success:
                self.tags = [tag for tag in self.tags if tag.get('id') != tag_id]
                self.update_display()
                self.show_success_notification(f"Тег «{tag_name}» удален")
            else:
                self.show_error_notification("Не удалось удалить тег")

        except Exception as e:
            import logging
            logging.error(f"Ошибка удаления тега: {e}")
            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось удалить тег")

    def on_color_changed(self, tag_id: int, new_color: str):
        """Обработчик изменения цвета тега"""
        try:
            result = self.tag_service.update_tag(tag_id, {'color': new_color})
            if result:
                for tag in self.tags:
                    if tag.get('id') == tag_id:
                        tag['color'] = new_color
                        break
                # Показываем уведомление об изменении цвета
                tag_name = next((t.get('name') for t in self.tags if t.get('id') == tag_id), "Тег")
                self.show_info_notification(f"Цвет тега «{tag_name}» обновлен")
        except Exception as e:
            import logging
            logging.error(f"Ошибка обновления цвета тега {tag_id}: {e}")

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

        # Обновляем размер контейнера уведомлений
        if hasattr(self, 'notification_manager'):
            self.notification_manager.container.setGeometry(
                0, 0, self.width(), self.height()
            )

    def get_all_tags(self):
        return self.tags.copy()

    def get_filtered_tags(self):
        return self.filtered_tags.copy()


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = QWidget()
    window.setWindowTitle("Тест - Теги")
    window.setGeometry(100, 100, 1000, 700)

    tags_page = TagsPage()

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(tags_page)

    window.show()
    sys.exit(app.exec())