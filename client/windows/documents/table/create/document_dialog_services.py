# client/windows/documents/table/create/document_dialog_services.py
"""
Получение http_client, сервисов и справочников для диалога документа
"""


class ServicesMixin:
    @staticmethod
    def _resolve_http_client():
        try:
            from client.core.state.app_state import AppState

            return AppState().http_client
        except Exception:
            return None

    def _resolve_document_service(self):
        """Создаёт DocumentService на основе self.http_client, если он доступен."""
        if not self.http_client:
            return None
        try:
            from client.services.document_service import DocumentService

            return DocumentService(self.http_client)
        except Exception as e:
            print(f"[DocumentDialog] Не удалось создать DocumentService: {e}")
            return None

    def _resolve_doc_type_service(self):
        """Создаёт DocTypeService на основе self.http_client, если он доступен."""
        if not self.http_client:
            return None
        try:
            from client.services.doc_type_service import get_doc_type_service

            return get_doc_type_service(self.http_client)
        except Exception as e:
            print(f"[DocumentDialog] Не удалось создать DocTypeService: {e}")
            return None

    def _resolve_attachment_service(self):
        """Создаёт AttachmentService на основе self.http_client, если он доступен."""
        if not self.http_client:
            return None
        try:
            from client.services.attachment_service import get_attachment_service

            return get_attachment_service(self.http_client)
        except Exception as e:
            print(f"[DocumentDialog] Не удалось создать AttachmentService: {e}")
            return None

    def _fetch_tags(self) -> list:
        try:
            if self.http_client:
                from client.services.tag_service import get_tag_service

                return get_tag_service(self.http_client).get_all_tags() or []
        except Exception as e:
            print(f"[DocumentDialog] Не удалось загрузить теги: {e}")
        return []

    def _load_org_structure_if_needed(self):
        """
        Подгружает организации/отделы/сотрудников тем же загрузчиком, что
        использует EmployeeSelectionDialog внутри себя. Без этого
        self.organizations/departments/employees остаются пустыми, если их
        не передали явно при создании DocumentDialog, и тогда получатели/
        исполнители, выбранные в пикере, нельзя сопоставить по типу узла
        (org/dept/emp) — при сборке payload все они уходят в
        "неизвестный получатель".
        """
        try:
            from client.core.org_structure.employee_selection_data_loader import (
                EmployeeSelectionDataLoader,
            )

            loader = EmployeeSelectionDataLoader(self.http_client)
            if not self.organizations:
                self.organizations = loader.load_organizations()
            if not self.departments:
                self.departments = loader.load_departments_flat()
            if not self.employees:
                self.employees = loader.load_employees()
            print(
                f"[DocumentDialog] Справочники загружены: "
                f"орг={len(self.organizations)}, отд={len(self.departments)}, "
                f"сотр={len(self.employees)}"
            )
        except Exception as e:
            print(f"[DocumentDialog] Не удалось загрузить справочники орг.структуры: {e}")
            import traceback

            traceback.print_exc()
