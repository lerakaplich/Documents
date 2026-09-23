"""
Панель документов - управление данными и UI
"""
import os
import sys
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.uic import loadUi

from client.core.data.document_data import DocumentDataConfig
from client.core.state.app_state import AppState           # ← НОВОЕ
from client.core.themes import apply_theme_to_widget, T
from client.windows.documents.history.history_dialog import HistoryDialog
from client.windows.documents.menus.column_menu import ColumnsMenu
from client.windows.documents.menus.filter_menu import FilterMenu
from client.windows.documents.menus.status_menu import StatusesMenu
from client.windows.documents.table.create.document_create_dialog import DocumentDialog
from client.windows.documents.table.documents_table import DocumentsTable
from client.core.table.documents_panel_controller import DocumentsPanelController

# Импортируем вашу плавающую кнопку
from client.windows.animations.floating_action_button import FloatingActionButton

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


class DocumentsPanel(QWidget):
    """
    Панель документов - контейнер с UI элементами.
    Отвечает исключительно за отображение данных и реакцию на действия пользователя.
    """

    # Сигналы
    filter_changed = pyqtSignal(dict)
    search_requested = pyqtSignal(str)
    document_selected = pyqtSignal(dict)
    document_action_triggered = pyqtSignal(str, dict)
    pin_status_changed = pyqtSignal(int, bool)

    data_loaded = pyqtSignal(int)
    type_changed = pyqtSignal(int)
    direction_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # HTTP-клиент — нужен для загрузки реальных данных в диалоге
        self.http_client = AppState().http_client          # ← НОВОЕ
        print(f"[DocumentsPanel] http_client = {self.http_client}")

        # Контроллер бизнес-логики
        self.controller = DocumentsPanelController()

        self._init_ui()
        self._init_table()
        self._connect_signals()
        self._init_floating_button()

        # Загружаем все документы по умолчанию
        self.load_all_documents()
        self.documents_table.document_action_triggered.connect(self._on_document_action)

    # ========== UI И КНОПКИ ==========
    def _init_ui(self):
        ui_path = os.path.join(ROOT_DIR, "client", "ui", "documents", "table", "documents_panel.ui")
        loadUi(ui_path, self)
        apply_theme_to_widget(self)
        self._setup_buttons()

    def _init_table(self):
        self.documents_table = DocumentsTable()
        if hasattr(self, 'contentFrame'):
            self.contentLayout.addWidget(self.documents_table)
        elif hasattr(self, 'horizontalLayoutHeader'):
            self.verticalLayout.addWidget(self.documents_table)
        elif hasattr(self, 'panelLayout'):
            self.panelLayout.addWidget(self.documents_table)
        else:
            self.layout().addWidget(self.documents_table)

    def _init_floating_button(self):
        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.on_add_document_clicked)
        if hasattr(self.documents_table, 'tableWidget'):
            scrollbar = self.documents_table.tableWidget.verticalScrollBar()
            scrollbar.valueChanged.connect(self.on_scroll)
        self.position_floating_button()

    def _setup_buttons(self):
        if hasattr(self, 'columnsBtn'):
            self.columns_menu = ColumnsMenu(parent=self)
            self.columnsBtn.clicked.connect(self._show_columns_menu)

        if hasattr(self, 'filterBtn'):
            self.filter_menu = FilterMenu(self)
            self.filterBtn.clicked.connect(self._show_filter_menu)

        if hasattr(self, 'statusesBtn'):
            self.statuses_menu = StatusesMenu(self)
            self.statusesBtn.clicked.connect(self._show_statuses_menu)
            self.statuses_menu.connect_clear_signal(self.statuses_menu.clear_selection)

        if hasattr(self, 'searchEdit'):
            self.searchEdit.textChanged.connect(self.on_search_changed)

    def _show_columns_menu(self):
        self.columns_menu.exec(
            self.columnsBtn.mapToGlobal(self.columnsBtn.rect().bottomLeft())
        )

    def _show_filter_menu(self):
        self.filter_menu.exec(
            self.filterBtn.mapToGlobal(self.filterBtn.rect().bottomLeft())
        )

    def _show_statuses_menu(self):
        self.statuses_menu.exec(
            self.statusesBtn.mapToGlobal(self.statusesBtn.rect().bottomLeft())
        )

    def _connect_signals(self):
        if hasattr(self, 'documents_table'):
            self.documents_table.document_action_triggered.connect(
                self.document_action_triggered.emit
            )
            self.documents_table.read_status_changed.connect(
                lambda doc_id, is_read: print(f"Document {doc_id} read: {is_read}")
            )
            self.documents_table.pin_status_changed.connect(
                self.pin_status_changed.emit
            )
            self.documents_table.data_loaded.connect(
                self.data_loaded.emit
            )

    # ========== ЛОГИКА ПЛАВАЮЩЕЙ КНОПКИ ==========
    def position_floating_button(self):
        if hasattr(self, 'floating_btn'):
            margin = 30
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

    # client/windows/documents/table/documents_panel.py

    # Измените импорт

    def on_add_document_clicked(self):
        """Обработка нажатия на плавающую кнопку '+'"""
        try:
            current_user = self.controller.get_current_user()
            organizations = self._get_organizations_data()
            departments = self._get_departments_data()
            employees = self._get_employees_data()
            tags = self._get_tags_data()

            # Создаем универсальный диалог в режиме 'create'
            self.document_dialog = DocumentDialog(
                parent=self,
                mode='create',
                current_user=current_user,
                organizations=organizations,
                departments=departments,
                employees=employees,
                tags=tags,
                http_client=self.http_client,         # ← НОВОЕ
            )

            self.document_dialog.document_created.connect(self._on_document_created_success)

            self.document_dialog.setWindowFlags(Qt.WindowType.Window)
            self.document_dialog.show()
            self.document_dialog.raise_()
            self.document_dialog.activateWindow()

        except Exception as e:
            print(f"[DocumentsPanel] Ошибка при открытии диалога: {e}")
            import traceback
            traceback.print_exc()

    def _get_tags_data(self) -> list:
        """Возвращает список тегов из контроллера, либо пустой список —
        тогда диалог сам подтянет данные с сервера."""
        try:
            if hasattr(self.controller, 'get_tags'):
                data = self.controller.get_tags()
                if data:
                    return data
            # Пробуем напрямую через TagService (если есть http_client)
            if self.http_client:
                from client.services.tag_service import get_tag_service
                service = get_tag_service(self.http_client)
                data = service.get_all_tags()
                if data:
                    return data
            print("[DocumentsPanel] Теги не получены — отдаём пустой список (диалог загрузит с сервера)")
            return []
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка получения тегов: {e}")
            return []

    def _handle_edit_document(self, document_data: dict):
        """Открывает диалог редактирования документа"""
        try:
            # Получаем полные данные документа
            full_document = self.controller.get_full_document_for_edit(document_data)

            if not full_document:
                QMessageBox.warning(self, "Ошибка", "Не удалось загрузить данные документа")
                return

            organizations = self._get_organizations_data()
            departments = self._get_departments_data()
            employees = self._get_employees_data()
            tags = self._get_tags_data()

            # Используем тот же диалог, но в режиме 'edit'
            self.document_dialog = DocumentDialog(
                parent=self,
                mode='edit',
                document_data=full_document,
                organizations=organizations,
                departments=departments,
                employees=employees,
                tags=tags,
                http_client=self.http_client,         # ← НОВОЕ
            )

            self.document_dialog.document_updated.connect(self._on_document_updated)

            self.document_dialog.setWindowFlags(Qt.WindowType.Window)
            self.document_dialog.show()
            self.document_dialog.raise_()
            self.document_dialog.activateWindow()

        except Exception as e:
            print(f"[DocumentsPanel] Ошибка при открытии диалога редактирования: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть редактор: {str(e)}")

    # client/windows/documents/table/documents_panel.py

    def _on_document_updated(self, updated_data: dict):
        """
        Обработка обновления документа

        Args:
            updated_data: обновленные данные документа
        """
        try:
            print(f"[DocumentsPanel] Обновление документа: {updated_data}")

            # Сохраняем через контроллер
            success = self.controller.update_document(updated_data)

            if success:
                QMessageBox.information(
                    self,
                    "Успешно",
                    "Документ успешно обновлен!"
                )
                # Обновляем таблицу
                self.refresh()
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось обновить документ"
                )
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка при обновлении документа: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Произошла ошибка при обновлении: {str(e)}"
            )

    def _get_organizations_data(self) -> list:
        """Получает список организаций из контроллера.
        Если контроллер не умеет — возвращаем пустой список,
        диалог сам подтянет данные с сервера через http_client."""
        try:
            if hasattr(self.controller, 'get_organizations'):
                data = self.controller.get_organizations()
                if data:
                    return data
            # Если метод отсутствует, пробуем получить через репозиторий
            elif hasattr(self.controller, 'organization_repo'):
                data = self.controller.organization_repo.get_all()
                if data:
                    return data
            print("[DocumentsPanel] Организации не получены — отдаём пустой список (диалог загрузит с сервера)")
            return []                                 # ← ИЗМЕНЕНО (было тестовые данные)
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка получения организаций: {e}")
            return []

    def _get_departments_data(self) -> list:
        """Получает список отделов из контроллера.
        Если контроллер не умеет — возвращаем пустой список."""
        try:
            if hasattr(self.controller, 'get_departments'):
                data = self.controller.get_departments()
                if data:
                    return data
            elif hasattr(self.controller, 'department_repo'):
                data = self.controller.department_repo.get_all()
                if data:
                    return data
            print("[DocumentsPanel] Отделы не получены — отдаём пустой список (диалог загрузит с сервера)")
            return []                                 # ← ИЗМЕНЕНО (было тестовые данные)
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка получения отделов: {e}")
            return []

    def _get_employees_data(self) -> list:
        """Получает список сотрудников из контроллера.
        Если контроллер не умеет — возвращаем пустой список."""
        try:
            if hasattr(self.controller, 'get_employees'):
                data = self.controller.get_employees()
                if data:
                    return data
            elif hasattr(self.controller, 'employee_repo'):
                data = self.controller.employee_repo.get_all()
                if data:
                    return data
            print("[DocumentsPanel] Сотрудники не получены — отдаём пустой список (диалог загрузит с сервера)")
            return []                                 # ← ИЗМЕНЕНО (было тестовые данные)
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка получения сотрудников: {e}")
            return []

    def _on_document_created_success(self, document_data: dict):
        """Слот, который вызывается, когда документ успешно сохранен в диалоге"""
        print(f"[DocumentsPanel] Документ успешно создан: {document_data}")
        # Обновляем таблицу, чтобы увидеть новый документ
        self.refresh()
        # Закрываем окно создания
        if hasattr(self, 'create_doc_window'):
            self.create_doc_window.close()

    def on_document_created(self, document_data: dict):
        """Обработка события создания нового документа"""
        try:
            # Через контроллер сохраняем документ
            success = self.controller.create_document(document_data)

            if success:
                QMessageBox.information(
                    self,
                    "Успешно",
                    "Документ успешно создан и добавлен в список!"
                )
                # Обновляем таблицу
                self.refresh()
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось сохранить документ."
                )
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка при создании документа: {e}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {str(e)}")

    # ========== ЗАГРУЗКА И ОТОБРАЖЕНИЕ ДАННЫХ ==========

    def load_all_documents(self):
        """Запросить данные у контроллера и отобразить их"""
        documents, title, view_mode, doc_type = self.controller.load_all_documents()
        self._update_table(documents, doc_type, title, view_mode)
        self.data_loaded.emit(len(documents))

    def load_documents_by_type(self, type_id: int):
        documents, title, view_mode, doc_type = self.controller.load_documents_by_type(type_id)
        self._update_table(documents, doc_type, title, view_mode)
        self.type_changed.emit(type_id)
        self.data_loaded.emit(len(documents))

    def load_documents_by_direction(self, direction: str, title: str = None):
        documents, title, view_mode, doc_type = self.controller.load_documents_by_direction(direction, title)
        self._update_table(documents, doc_type, title, view_mode)
        self.direction_changed.emit(direction)
        self.data_loaded.emit(len(documents))

    def _update_table(self, documents: list, doc_type: str = None, title: str = None, view_mode: str = None):
        """Обновить UI-компонент таблицы"""
        try:
            doc_type = doc_type or "default"
            view_mode = view_mode or self.controller.current_view_mode or "all"

            self.documents_table._controller.switch_doc_type(doc_type, documents, view_mode)

            if title and hasattr(self, 'labelTitle'):
                self.labelTitle.setText(title)

        except Exception as e:
            print(f"[DocumentsPanel] Error updating table: {e}")
            import traceback
            traceback.print_exc()

    def refresh(self):
        """Перезагрузить текущие данные через контроллер"""
        documents, title, view_mode, doc_type = self.controller.refresh()
        self._update_table(documents, doc_type, title, view_mode)

    # ========== ОБРАБОТЧИКИ СОБЫТИЙ ==========

    def on_search_changed(self, text):
        self.search_requested.emit(text)
        documents, title, view_mode, doc_type = self.controller.search_documents(text)
        self._update_table(documents, doc_type, title, view_mode)

    def update_title(self, title):
        if hasattr(self, 'labelTitle'):
            self.labelTitle.setText(title)
        self.controller.current_title = title

    def get_documents_table(self):
        return self.documents_table

    def _on_document_action(self, action_type: str, document_data: dict):
        """Обработка действий с документами"""
        if action_type == "redirect":
            self._handle_redirect_document(document_data)
        elif action_type == "comment":
            self._handle_comment_document(document_data)
        elif action_type == "history":
            self._handle_history_document(document_data)
        elif action_type == "edit":  # <-- ДОБАВИТЬ ЭТОТ БЛОК
            self._handle_edit_document(document_data)
        elif action_type == "delete":
            self._handle_delete_document(document_data)
        elif action_type == "attachment":
            self._handle_attachment_document(document_data)
        elif action_type == "reply_attachment":
            self._handle_reply_attachment_document(document_data)
        elif action_type == "read_status":
            is_read = document_data.get("is_read", False)
            self._handle_read_status_document(document_data, not is_read)
        elif action_type == "pin_toggle":
            self._handle_pin_toggle_document(document_data)
        else:
            print(f"[DocumentsPanel] Неизвестное действие: {action_type}")

    # client/windows/documents/table/documents_panel.py

    def _handle_delete_document(self, document_data: dict):
        """Обработка удаления документа"""
        doc_name = document_data.get('title', document_data.get('name', 'Документ'))
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы действительно хотите удалить документ '{doc_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if hasattr(self.controller, 'delete_document'):
                    success = self.controller.delete_document(document_data.get('id'))
                    if success:
                        self.refresh()
                        QMessageBox.information(self, "Успешно", "Документ удален")
                    else:
                        QMessageBox.warning(self, "Ошибка", "Не удалось удалить документ")
                else:
                    QMessageBox.warning(self, "Ошибка", "Функция удаления пока не реализована")
            except Exception as e:
                print(f"[DocumentsPanel] Ошибка при удалении: {e}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка удаления: {str(e)}")

    def _handle_attachment_document(self, document_data: dict):
        """Обработка прикрепления вложения"""
        QMessageBox.information(
            self,
            "Вложения",
            "Функция вложений будет добавлена в следующей версии"
        )

    def _handle_reply_attachment_document(self, document_data: dict):
        """Обработка ответного вложения"""
        QMessageBox.information(
            self,
            "Ответные вложения",
            "Функция ответных вложений будет добавлена в следующей версии"
        )

    def _handle_read_status_document(self, document_data: dict, is_read: bool):
        """Обработка изменения статуса прочтения"""
        doc_id = document_data.get('id')
        if hasattr(self.controller, 'change_read_status'):
            success = self.controller.change_read_status(doc_id, is_read)
            if success:
                self.refresh()
                status_text = "прочитанным" if is_read else "непрочитанным"
                QMessageBox.information(self, "Успешно", f"Документ отмечен как {status_text}")
        else:
            # Локальное обновление статуса
            self.documents_table.update_document_read_status(doc_id, is_read)
            QMessageBox.information(self, "Информация", "Статус прочтения обновлен локально")

    def _handle_pin_toggle_document(self, document_data: dict):
        """Обработка закрепления/открепления документа"""
        doc_id = document_data.get('id')
        if hasattr(self.controller, 'toggle_pin_status'):
            success = self.controller.toggle_pin_status(doc_id)
            if success:
                self.refresh()
                QMessageBox.information(self, "Успешно", "Статус закрепления обновлен")
        else:
            # Локальное обновление
            current_pin = document_data.get('is_pinned', False)
            new_pin = not current_pin
            self.documents_table._controller.toggle_pin(doc_id, new_pin)
            QMessageBox.information(self, "Информация", "Статус закрепления обновлен локально")

    def _handle_history_document(self, document_data: dict):
        """
        Отображение диалога истории документа

        Args:
            document_data: данные документа
        """
        try:
            # Получаем полные данные документа с историей
            full_document_data = self.controller.get_full_document_for_history(document_data)

            # Если контроллер не имеет метода, используем переданные данные
            if not full_document_data:
                # Добавляем историю из имеющихся данных
                full_document_data = self._enrich_document_with_history(document_data)

            # Получаем текущего пользователя
            current_user = self.controller.get_current_user() if hasattr(self.controller, 'get_current_user') else {}

            # Создаем и показываем диалог истории
            dialog = HistoryDialog(
                document_data=full_document_data,
                parent=self,
                current_user=current_user
            )
            dialog.exec()

        except Exception as e:
            print(f"[DocumentsPanel] Ошибка при открытии диалога истории: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось открыть историю документа: {str(e)}"
            )

    def _enrich_document_with_history(self, document_data: dict) -> dict:
        """
        Обогащает данные документа историей из базы данных

        Args:
            document_data: базовые данные документа

        Returns:
            dict: обогащенные данные документа с историей
        """
        enriched_data = document_data.copy()

        # Получаем историю из контроллера
        if hasattr(self.controller, 'get_document_history'):
            history = self.controller.get_document_history(document_data.get('id'))
            if history:
                enriched_data['history'] = history
                return enriched_data

        # Если истории нет - генерируем из имеющихся данных
        enriched_data['history'] = self._generate_history_from_document(document_data)

        return enriched_data

    def _generate_history_from_document(self, document_data: dict) -> list:
        """
        Генерирует историю из имеющихся данных документа

        Args:
            document_data: данные документа

        Returns:
            list: список событий истории
        """
        from datetime import datetime

        history = []

        # Событие создания
        created_at = document_data.get('created_at')
        if created_at:
            creator = document_data.get('creator', document_data.get('author', 'Неизвестный пользователь'))
            if isinstance(creator, dict):
                creator_name = creator.get('full_name', creator.get('name', 'Неизвестный пользователь'))
            else:
                creator_name = str(creator)

            history.append({
                'type': 'created',
                'user': creator_name,
                'created_at': created_at
            })

        # Комментарии
        comments = document_data.get('comments', [])
        for comment in comments:
            author = comment.get('author_name', comment.get('author', 'Неизвестный пользователь'))
            history.append({
                'type': 'comment',
                'user': author,
                'text': comment.get('text', ''),
                'created_at': comment.get('created_at', datetime.now())
            })

        # Перенаправления
        redirects = document_data.get('redirects', [])
        for redirect in redirects:
            from_user = redirect.get('from_user', 'Неизвестный пользователь')
            to_user = redirect.get('to_user', 'Неизвестный пользователь')
            history.append({
                'type': 'redirect',
                'from_user': from_user,
                'to_user': to_user,
                'created_at': redirect.get('redirected_at', datetime.now())
            })

        # Изменения статуса
        status_changes = document_data.get('status_changes', [])
        for change in status_changes:
            user = change.get('user', 'Неизвестный пользователь')
            history.append({
                'type': 'status_change',
                'user': user,
                'old_status': change.get('old_status', ''),
                'new_status': change.get('new_status', ''),
                'created_at': change.get('changed_at', datetime.now())
            })

        # Сортируем по дате
        history.sort(key=lambda x: x.get('created_at', datetime.min))

        return history

    def _handle_redirect_document(self, document_data: dict):
        """Отображение диалога перенаправления"""
        try:
            from client.windows.documents.redirect.redirect_dialog import RedirectDialog

            doc_id = document_data.get("id")
            current_recipients = document_data.get("delegates", [])

            all_employees = self.controller.get_employees_for_redirect()

            dialog = RedirectDialog(current_recipients, all_employees, parent=self)
            dialog.redirect_confirmed.connect(
                lambda ids, comment: self._confirm_redirect(doc_id, ids, comment)
            )
            dialog.exec()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _confirm_redirect(self, document_id: int, recipient_ids: list, comment: str):
        success = self.controller.redirect_document(document_id, recipient_ids, comment)
        if success:
            self.refresh()

    def _handle_comment_document(self, document_data: dict):
        """Отображение диалога комментариев"""
        try:
            from client.windows.documents.comments.comment_dialog import CommentDialog

            document_to_pass = self.controller.get_full_document_for_comment(document_data)
            current_user = self.controller.get_current_user()

            dialog = CommentDialog(
                document_data=document_to_pass,
                parent=self,
                current_user=current_user
            )
            dialog.comment_added.connect(
                lambda comment: self._on_comment_added(document_data.get("id"), comment)
            )
            dialog.exec()
        except Exception as e:
            import traceback
            print(f"[DocumentsPanel] Error opening comment dialog: {e}")
            traceback.print_exc()

    def _on_comment_added(self, document_id: int, new_comment: dict):
        success = self.controller.add_comment_to_document(document_id, new_comment)
        if success:
            self.refresh()
            print(f"[DocumentsPanel] Комментарий сохранен через контроллер для документа {document_id}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentsPanel()
    window.setWindowTitle("Documents Panel Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())