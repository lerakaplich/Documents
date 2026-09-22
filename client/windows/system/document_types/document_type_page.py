# client/windows/system/document_types/document_type_page.py

import os
import sys
from typing import List, Dict, Any, Optional, Union

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QApplication,
    QSizePolicy, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.uic import loadUi

from client.core.themes import T, get_menu_style, apply_theme_to_widget
from client.windows.system.document_types.document_type_card import DocumentTypeCard
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.document_types.document_type_dialog import DocumentTypeDialog
from client.windows.system.delete_dialog import DeleteDialog
from client.windows.animations.animated_notification import NotificationManager
from client.services.doc_type_service import get_doc_type_service
from client.core.http_client import HttpClient
from client.core.config import config
from client.core.state.app_state import AppState


class DocumentTypesPage(QWidget):
    """Страница типов документов с поиском, сортировкой и отображением в 1 колонку"""

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

        self.doc_type_service = get_doc_type_service(self.http_client)

        # Данные
        self.document_types: List[Dict[str, Any]] = []
        self.filtered_types: List[Dict[str, Any]] = []

        # Состояние
        self.current_sort = "А→Я"
        self.is_loading = False

        # Инициализация
        self.init_ui()
        self.setup_connections()

        # Создаем менеджер уведомлений
        self.notification_manager = NotificationManager(self, max_visible=3)

        # Загружаем данные
        QTimer.singleShot(100, self.load_types)

    def init_ui(self):
        """Инициализация UI из файла"""
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)
            apply_theme_to_widget(self)

        # Создаем плавающую кнопку
        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.on_add_type)

        # Подключаемся к скроллу
        self.scrollArea.verticalScrollBar().valueChanged.connect(self.on_scroll)

        # Скрываем кнопку сброса при старте
        self.btnResetFilters.hide()

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'document_types', 'document_type_page.ui')
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

    def _normalize_fields(self, fields: Union[Dict[str, bool], List[str], None]) -> Dict[str, bool]:
        """
        Нормализует поле fields в словарь {field_name: True/False}

        Args:
            fields: может быть словарем, списком или None

        Returns:
            Dict[str, bool]: нормализованный словарь
        """
        if fields is None:
            return {}

        # Если это список - конвертируем в словарь со значением True
        if isinstance(fields, list):
            return {item: True for item in fields}

        # Если это уже словарь - возвращаем как есть
        if isinstance(fields, dict):
            return fields

        # Если что-то другое - возвращаем пустой словарь
        return {}

    def _convert_fields_to_parameters(self, fields: Union[Dict[str, bool], List[str], None]) -> List[str]:
        """
        Конвертирует fields в список активных параметров

        Args:
            fields: словарь {field: bool} или список полей

        Returns:
            List[str]: список активных параметров
        """
        normalized = self._normalize_fields(fields)
        # Возвращаем только те поля, у которых значение True
        return [key for key, value in normalized.items() if value]

    def _convert_parameters_to_fields(self, parameters: List[str]) -> Dict[str, bool]:
        """
        Конвертирует список параметров в словарь fields

        Args:
            parameters: список параметров

        Returns:
            Dict[str, bool]: словарь {field: True}
        """
        if not parameters:
            return {}
        return {param: True for param in parameters}

    # ==================== ЗАГРУЗКА ДАННЫХ ====================

    def load_types(self):
        """Загрузить типы документов из API"""
        if self.is_loading:
            return

        self.is_loading = True

        try:
            types = self.doc_type_service.get_all_types()

            # Преобразуем данные в нужный формат
            self.document_types = []
            for doc_type in types:
                # Нормализуем fields
                fields = doc_type.get('fields', {})
                normalized_fields = self._normalize_fields(fields)
                parameters = self._convert_fields_to_parameters(fields)

                self.document_types.append({
                    'id': doc_type.get('id'),
                    'name': doc_type.get('name', ''),
                    'code': doc_type.get('smdo_code_type', ''),
                    'description': doc_type.get('description', ''),
                    'documents_count': doc_type.get('documents_count', 0),
                    'fields_count': len(parameters),
                    'auto_numbering': doc_type.get('auto_num', False),
                    'parameters': parameters,
                    'fields': normalized_fields,
                    'auto_num': doc_type.get('auto_num', False),
                    'smdo_code_type': doc_type.get('smdo_code_type', '')
                })

            self.is_loading = False
            self.update_display()
            self.data_loaded.emit()

            if self.document_types:
                self.show_success_notification(f"Загружено {len(self.document_types)} типов документов")

        except Exception as e:
            self.is_loading = False
            import logging
            logging.error(f"Ошибка загрузки типов документов: {e}")

            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось загрузить типы документов")

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
        }

        for name, func in sort_options.items():
            action = menu.addAction(name)
            action.triggered.connect(lambda checked, f=func, n=name: self.apply_sort(f, n))

        menu.exec(self.btnSort.mapToGlobal(self.btnSort.rect().bottomLeft()))

    def sort_by_name_asc(self, types):
        return sorted(types, key=lambda x: x.get('name', '').lower())

    def sort_by_name_desc(self, types):
        return sorted(types, key=lambda x: x.get('name', '').lower(), reverse=True)

    def sort_by_count_asc(self, types):
        return sorted(types, key=lambda x: x.get('documents_count', 0))

    def sort_by_count_desc(self, types):
        return sorted(types, key=lambda x: x.get('documents_count', 0), reverse=True)

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

    def filter_and_sort_types(self):
        """Фильтрация и сортировка типов документов"""
        filtered = self.document_types.copy()

        # Поиск
        search_text = self.searchEdit.text().strip().lower()
        if search_text:
            filtered = [
                dt for dt in filtered
                if search_text in dt.get('name', '').lower() or
                   search_text in dt.get('smdo_code_type', '').lower() or
                   search_text in dt.get('description', '').lower()
            ]

        # Сортировка
        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
            "По количеству документов (↑)": self.sort_by_count_asc,
            "По количеству документов (↓)": self.sort_by_count_desc,
        }

        sort_func = sort_methods.get(self.current_sort, self.sort_by_name_asc)
        return sort_func(filtered)

    # ==================== ОТОБРАЖЕНИЕ ====================

    # client/windows/system/document_types/document_type_page.py

    def update_display(self):
        """Обновление отображения типов документов в 2 колонки с выравниванием по верхнему краю"""
        # ⚠️ КРИТИЧНО: Полностью очищаем layout
        # Сначала удаляем все виджеты
        while self.typesLayout.count():
            item = self.typesLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Если это вложенный layout, очищаем его
                self._clear_layout(item.layout())

        # Получаем отфильтрованные и отсортированные типы
        self.filtered_types = self.filter_and_sort_types()

        # Если нет типов, показываем сообщение
        if not self.filtered_types:
            empty_label = QLabel("Нет типов документов")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(
                f"color: {T.TEXT_MUTED_ALT}; font-size: 16px; padding: 40px;"
            )
            self.typesLayout.addWidget(empty_label)
            self.position_floating_button()
            return

        # Создаем горизонтальный layout для двух колонок
        h_layout = QHBoxLayout()
        h_layout.setSpacing(10)
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Создаем две колонки
        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setAlignment(Qt.AlignmentFlag.AlignTop)

        right_column = QVBoxLayout()
        right_column.setSpacing(10)
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Распределяем карточки по двум колонкам
        for i, doc_type in enumerate(self.filtered_types):
            type_card = DocumentTypeCard(doc_type)
            type_card.edit_clicked.connect(self.on_edit_type)
            type_card.delete_clicked.connect(self.on_delete_type)
            type_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

            if i % 2 == 0:
                left_column.addWidget(type_card)
            else:
                right_column.addWidget(type_card)

        # Добавляем колонки в горизонтальный layout
        h_layout.addLayout(left_column)
        h_layout.addLayout(right_column)

        # Добавляем горизонтальный layout в основной вертикальный
        self.typesLayout.addLayout(h_layout)

        # Добавляем растяжку в конец, чтобы контент был сверху
        self.typesLayout.addStretch()

        self.position_floating_button()

    def _clear_layout(self, layout):
        """Рекурсивно очищает layout и все его дочерние элементы"""
        if layout is None:
            return

        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    # ==================== РАБОТА С ТИПАМИ (CRUD) ====================

    def on_add_type(self):
        """Обработчик нажатия на плавающую кнопку добавления типа"""
        dialog = DocumentTypeDialog(self, item={})

        if dialog.exec():
            new_type_data = dialog.get_data()
            self._create_type(new_type_data)

    # client/windows/system/document_types/document_type_page.py

    def _create_type(self, type_data: Dict[str, Any]):
        """Создание типа документа"""
        try:
            # Формируем данные для сервера
            server_data = {
                'name': type_data.get('name', ''),
                'fields': type_data.get('fields', {}),
                'auto_num': type_data.get('auto_num',
                                          type_data.get('auto_number', type_data.get('auto_numbering', False))),
                'smdo_code_type': type_data.get('smdo_code_type', '')
            }

            # Если fields пустой, берем из parameters (для обратной совместимости)
            if not server_data['fields'] and type_data.get('parameters'):
                server_data['fields'] = {param: True for param in type_data['parameters']}

            print(f"[DEBUG] Создание типа: server_data={server_data}")

            result = self.doc_type_service.create_type(server_data)

            if result:
                print(f"[DEBUG] Результат создания: {result}")

                # Нормализуем полученные fields
                result_fields = result.get('fields', {})
                normalized_fields = self._normalize_fields(result_fields)
                parameters_result = self._convert_fields_to_parameters(result_fields)

                # Получаем значение auto_num из результата
                auto_num = result.get('auto_num', False)
                print(f"[DEBUG] auto_num из результата: {auto_num}")

                self.document_types.append({
                    'id': result.get('id'),
                    'name': result.get('name', ''),
                    'code': result.get('smdo_code_type', ''),
                    'description': type_data.get('description', ''),
                    'documents_count': 0,
                    'fields_count': len(parameters_result),
                    'auto_numbering': auto_num,  # Для совместимости
                    'auto_num': auto_num,  # Для сервера
                    'auto_number': auto_num,  # Для UI
                    'parameters': parameters_result,
                    'fields': normalized_fields,
                    'smdo_code_type': result.get('smdo_code_type', '')
                })

                self.update_display()
                self.show_success_notification(f"Тип «{result.get('name')}» создан")
            else:
                self.show_error_notification("Не удалось создать тип")

        except Exception as e:
            import logging
            logging.error(f"Ошибка создания типа: {e}")
            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось создать тип")

    # client/windows/system/document_types/document_type_page.py

    def _update_type(self, type_id: int, updated_data: Dict[str, Any]):
        """Обновление типа документа"""
        try:
            # Формируем данные для сервера
            server_data = {
                'name': updated_data.get('name', ''),
                'fields': updated_data.get('fields', {}),
                'auto_num': updated_data.get('auto_num', updated_data.get('auto_number',
                                                                          updated_data.get('auto_numbering', False))),
                'smdo_code_type': updated_data.get('smdo_code_type', '')
            }

            # Если fields пустой, берем из parameters (для обратной совместимости)
            if not server_data['fields'] and updated_data.get('parameters'):
                server_data['fields'] = {param: True for param in updated_data['parameters']}

            print(f"[DEBUG] Обновление типа {type_id}: server_data={server_data}")

            result = self.doc_type_service.update_type(type_id, server_data)

            if result:
                print(f"[DEBUG] Результат обновления: {result}")

                # Нормализуем полученные fields
                result_fields = result.get('fields', {})
                normalized_fields = self._normalize_fields(result_fields)
                parameters_result = self._convert_fields_to_parameters(result_fields)

                # Получаем значение auto_num из результата
                auto_num = result.get('auto_num', False)
                print(f"[DEBUG] auto_num из результата: {auto_num}")

                for i, dt in enumerate(self.document_types):
                    if dt.get('id') == type_id:
                        self.document_types[i].update({
                            'name': result.get('name', ''),
                            'code': result.get('smdo_code_type', ''),
                            'fields_count': len(parameters_result),
                            'auto_numbering': auto_num,  # Для совместимости
                            'auto_num': auto_num,  # Для сервера
                            'auto_number': auto_num,  # Для UI
                            'parameters': parameters_result,
                            'fields': normalized_fields,
                            'smdo_code_type': result.get('smdo_code_type', '')
                        })
                        print(f"[DEBUG] Обновлен тип в памяти: {self.document_types[i]}")
                        break

                self.update_display()
                self.show_success_notification(f"Тип «{result.get('name')}» обновлен")
            else:
                self.show_error_notification("Не удалось обновить тип")

        except Exception as e:
            import logging
            logging.error(f"Ошибка обновления типа: {e}")
            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось обновить тип")

    # client/windows/system/document_types/document_type_page.py

    def on_edit_type(self, type_data: Dict[str, Any]):
        """Обработка редактирования типа документа"""
        type_id = type_data.get('id')
        if not type_id:
            self.show_error_notification("ID типа не найден")
            return

        try:
            # Получаем актуальные данные с сервера
            server_type = self.doc_type_service.get_type(type_id)
            if not server_type:
                self.show_error_notification("Тип не найден на сервере")
                return

            print(f"[DEBUG] Загружен тип с сервера: {server_type}")

            # Преобразуем данные в формат для диалога
            fields = server_type.get('fields', {})
            normalized_fields = self._normalize_fields(fields)
            parameters = self._convert_fields_to_parameters(fields)

            # Получаем auto_num
            auto_num = server_type.get('auto_num', False)

            full_type_data = {
                'id': server_type.get('id'),
                'name': server_type.get('name', ''),
                'code': server_type.get('smdo_code_type', ''),
                'description': server_type.get('description', ''),
                'documents_count': server_type.get('documents_count', 0),
                'fields_count': len(parameters),
                'auto_numbering': auto_num,
                'auto_num': auto_num,
                'auto_number': auto_num,
                'parameters': parameters,
                'fields': normalized_fields,
                'smdo_code_type': server_type.get('smdo_code_type', '')
            }

            print(f"[DEBUG] Подготовлены данные для диалога: {full_type_data}")

            # Открываем диалог
            dialog = DocumentTypeDialog(self, item=full_type_data)

            if dialog.exec():
                updated_data = dialog.get_data()
                print(f"[DEBUG] Получены данные из диалога: {updated_data}")
                self._update_type(type_id, updated_data)

        except Exception as e:
            import logging
            import traceback
            logging.error(f"Ошибка загрузки типа для редактирования: {e}")
            traceback.print_exc()
            self.show_error_notification("Не удалось загрузить данные типа")


    def on_delete_type(self, type_id: int):
        """Обработка удаления типа документа"""
        type_name = "Неизвестный тип"
        for dt in self.document_types:
            if dt.get('id') == type_id:
                type_name = dt.get('name', 'Неизвестный тип')
                break

        if DeleteDialog.show_confirmation(self):
            self._delete_type(type_id, type_name)

    def _delete_type(self, type_id: int, type_name: str):
        """Удаление типа документа"""
        try:
            success = self.doc_type_service.delete_type(type_id)

            if success:
                self.document_types = [dt for dt in self.document_types if dt.get('id') != type_id]
                self.update_display()
                self.show_success_notification(f"Тип «{type_name}» удален")
            else:
                self.show_error_notification("Не удалось удалить тип")

        except Exception as e:
            import logging
            logging.error(f"Ошибка удаления типа: {e}")
            if "401" in str(e) or "AuthError" in str(e):
                self.show_error_notification("Сессия истекла. Войдите заново.")
            else:
                self.show_error_notification("Не удалось удалить тип")

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

    def get_all_types(self):
        return self.document_types.copy()

    def get_filtered_types(self):
        return self.filtered_types.copy()


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = QWidget()
    window.setWindowTitle("Тест - Типы документов")
    window.setGeometry(100, 100, 1000, 700)

    types_page = DocumentTypesPage()

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(types_page)

    window.show()
    sys.exit(app.exec())