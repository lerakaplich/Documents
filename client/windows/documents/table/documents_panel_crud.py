"""
Создание/редактирование документа (DocumentDialog) + справочники для него
(организации, отделы, сотрудники, теги). Вынесено из DocumentsPanel.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from client.windows.documents.table.create.document_create_dialog import DocumentDialog


class DocumentsCrudController:
    def __init__(self, panel):
        self.panel = panel

    # ---------- справочники (пустой список = диалог сам подтянет с сервера) ----------

    def _tags(self) -> list:
        panel, controller = self.panel, self.panel.controller
        try:
            if hasattr(controller, "get_tags"):
                data = controller.get_tags()
                if data:
                    return data
            if panel.http_client:
                from client.services.tag_service import get_tag_service

                data = get_tag_service(panel.http_client).get_all_tags()
                if data:
                    return data
            print("[DocumentsPanel] Теги не получены — отдаём пустой список (диалог загрузит с сервера)")
            return []
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка получения тегов: {e}")
            return []

    def _organizations(self) -> list:
        controller = self.panel.controller
        try:
            if hasattr(controller, "get_organizations"):
                data = controller.get_organizations()
                if data:
                    return data
            elif hasattr(controller, "organization_repo"):
                data = controller.organization_repo.get_all()
                if data:
                    return data
            print("[DocumentsPanel] Организации не получены — отдаём пустой список (диалог загрузит с сервера)")
            return []
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка получения организаций: {e}")
            return []

    def _departments(self) -> list:
        controller = self.panel.controller
        try:
            if hasattr(controller, "get_departments"):
                data = controller.get_departments()
                if data:
                    return data
            elif hasattr(controller, "department_repo"):
                data = controller.department_repo.get_all()
                if data:
                    return data
            print("[DocumentsPanel] Отделы не получены — отдаём пустой список (диалог загрузит с сервера)")
            return []
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка получения отделов: {e}")
            return []

    def _employees(self) -> list:
        controller = self.panel.controller
        try:
            if hasattr(controller, "get_employees"):
                data = controller.get_employees()
                if data:
                    return data
            elif hasattr(controller, "employee_repo"):
                data = controller.employee_repo.get_all()
                if data:
                    return data
            print("[DocumentsPanel] Сотрудники не получены — отдаём пустой список (диалог загрузит с сервера)")
            return []
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка получения сотрудников: {e}")
            return []

    # ---------- создание ----------

    def open_create_dialog(self):
        panel = self.panel
        try:
            dialog = DocumentDialog(
                parent=panel,
                mode="create",
                current_user=panel.controller.get_current_user(),
                organizations=self._organizations(),
                departments=self._departments(),
                employees=self._employees(),
                tags=self._tags(),
                http_client=panel.http_client,
            )
            dialog.document_created.connect(self._on_created)

            panel.document_dialog = dialog
            dialog.setWindowFlags(Qt.WindowType.Window)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка при открытии диалога: {e}")
            import traceback

            traceback.print_exc()

    def _on_created(self, document_data: dict):
        print(f"[DocumentsPanel] Документ успешно создан: {document_data}")
        self.panel.refresh()
        if hasattr(self.panel, "create_doc_window"):
            self.panel.create_doc_window.close()

    def create_document(self, document_data: dict):
        """Путь через DocumentsPanelController.create_document — оставлен для
        обратной совместимости; сам диалог сохраняет документ через
        http_client и шлёт document_created, приходящий в _on_created выше."""
        panel = self.panel
        try:
            success = panel.controller.create_document(document_data)
            if success:
                QMessageBox.information(panel, "Успешно", "Документ успешно создан и добавлен в список!")
                panel.refresh()
            else:
                QMessageBox.warning(panel, "Ошибка", "Не удалось сохранить документ.")
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка при создании документа: {e}")
            QMessageBox.critical(panel, "Ошибка", f"Произошла ошибка: {e!s}")

    # ---------- редактирование ----------

    def open_edit_dialog(self, document_data: dict):
        panel = self.panel
        try:
            full_document = panel.controller.get_full_document_for_edit(document_data)
            if not full_document:
                QMessageBox.warning(panel, "Ошибка", "Не удалось загрузить данные документа")
                return

            dialog = DocumentDialog(
                parent=panel,
                mode="edit",
                document_data=full_document,
                organizations=self._organizations(),
                departments=self._departments(),
                employees=self._employees(),
                tags=self._tags(),
                http_client=panel.http_client,
            )
            dialog.document_updated.connect(self._on_updated)

            panel.document_dialog = dialog
            dialog.setWindowFlags(Qt.WindowType.Window)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка при открытии диалога редактирования: {e}")
            import traceback

            traceback.print_exc()
            QMessageBox.critical(panel, "Ошибка", f"Не удалось открыть редактор: {e!s}")

    def _on_updated(self, updated_data: dict):
        panel = self.panel
        try:
            print(f"[DocumentsPanel] Обновление документа: {updated_data}")
            success = panel.controller.update_document(updated_data)
            if success:
                QMessageBox.information(panel, "Успешно", "Документ успешно обновлен!")
                panel.refresh()
            else:
                QMessageBox.warning(panel, "Ошибка", "Не удалось обновить документ")
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка при обновлении документа: {e}")
            import traceback

            traceback.print_exc()
            QMessageBox.critical(panel, "Ошибка", f"Произошла ошибка при обновлении: {e!s}")
