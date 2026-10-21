# client/windows/documents/table/create/document_create_dialog.py
"""
Универсальный диалог для создания и редактирования документа.

Класс собран из миксинов (каждый в своём файле):
  document_dialog_constants.py    — константы (DIRECTIONS, поля, алиасы)
  document_dialog_ui.py           — загрузка .ui, виджеты, сигналы, тема
  document_dialog_type_fields.py  — поля по конфигу типа (types.fields)
  document_dialog_selectors.py    — отправитель, получатели, исполнители, теги
  document_dialog_nodes.py        — узлы (type, id), подписи, фоновый резолвер имён
  document_dialog_services.py     — http_client, сервисы, справочники
  document_dialog_load.py         — заполнение формы в режиме edit, set_*_data
  document_dialog_save.py         — выбор файла и сохранение
"""

from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget

from client.windows.documents.table.create.document_dialog_constants import DIRECTIONS
from client.windows.documents.table.create.document_dialog_load import LoadMixin
from client.windows.documents.table.create.document_dialog_nodes import NodesMixin
from client.windows.documents.table.create.document_dialog_save import SaveMixin
from client.windows.documents.table.create.document_dialog_selectors import SelectorsMixin
from client.windows.documents.table.create.document_dialog_services import ServicesMixin
from client.windows.documents.table.create.document_dialog_type_fields import TypeFieldsMixin
from client.windows.documents.table.create.document_dialog_ui import UiMixin

__all__ = ["DIRECTIONS", "DocumentDialog"]


class DocumentDialog(
    UiMixin,
    TypeFieldsMixin,
    SelectorsMixin,
    NodesMixin,
    ServicesMixin,
    LoadMixin,
    SaveMixin,
    QWidget,  # QWidget — последним в списке баз
):
    """
    Универсальный диалог для создания и редактирования документа.
    Поддерживает два режима: 'create' и 'edit'.
    """

    document_created = pyqtSignal(dict)
    document_updated = pyqtSignal(dict)
    cancelled = pyqtSignal()

    def __init__(
        self,
        parent=None,
        mode: str = "create",
        document_data: dict[str, Any] | None = None,
        current_user: dict[str, Any] | None = None,
        organizations: list[dict] | None = None,
        departments: list[dict] | None = None,
        employees: list[dict] | None = None,
        tags: list[dict] | None = None,
        document_types: list[dict[str, Any]] | None = None,
        initial_type_id: int | None = None,
        initial_direction: str | None = None,
        http_client=None,
        document_service=None,
        doc_type_service=None,
        reply_to: dict[str, Any] | None = None,
    ):
        super().__init__(parent)

        self.mode = mode
        # Ответ на документ: при сохранении в документ пишется parent_document_id = id исходного
        self.reply_to = reply_to
        self.parent_document_id = reply_to.get("id") if reply_to else None
        self.document_data = document_data or {}
        self.current_user = current_user or {}
        self.organizations = organizations or []
        self.departments = departments or []
        self.employees = employees or []
        self.available_tags = tags or []
        self.http_client = http_client or self._resolve_http_client()

        # Сервисы для сохранения на сервере
        self.document_service = document_service or self._resolve_document_service()
        self.doc_type_service = doc_type_service or self._resolve_doc_type_service()
        self.attachment_service = self._resolve_attachment_service()

        # Состояние формы
        self.selected_sender: dict[str, Any] | None = None
        self.selected_receivers: list = []
        self.selected_executors: list = []
        self.selected_tags: list = []
        self.selected_file_path: str | None = None

        # Списки для комбобоксов
        self.directions = DIRECTIONS  # [(value, label), ...] — см. константу модуля
        self.create_methods = ["Создать новый", "Из шаблона", "Загрузить файл"]

        # Реальные типы документов с сервера (id, name, fields, auto_num, ...),
        # а не захардкоженный список названий — иначе type_id для POST /documents
        # взять неоткуда.
        self.document_types_data: list[dict[str, Any]] = document_types or []
        if not self.document_types_data and self.doc_type_service:
            try:
                self.document_types_data = self.doc_type_service.get_all_types()
            except Exception as e:
                print(f"[DocumentDialog] Не удалось загрузить типы документов: {e}")

        self._active_fields: dict[str, Any] = {}
        self._base_height: int | None = None
        self._full_min_height = 0
        self._type_pinned = False  # тип задан вкладкой → type_box скрыт
        self._direction_pinned = False  # направление задано группой → direction_box скрыт

        # Настройка UI
        self._load_ui()
        self._replace_date_edits()  # ← заменяем календари на кастомные
        self._setup_widgets()

        # Тип и направление с активной вкладки: предвыбираем и прячем поля.
        # Если значения нет в списке, поле остаётся видимым для ручного выбора.
        if self.mode == "create" and initial_type_id is not None and hasattr(self, "type_box"):
            idx = self.type_box.findData(initial_type_id)
            if idx >= 0:
                self.type_box.setCurrentIndex(idx)
                self._type_pinned = True

        if self.mode == "create" and initial_direction and hasattr(self, "direction_box"):
            idx = self.direction_box.findData(initial_direction)
            if idx >= 0:
                self.direction_box.setCurrentIndex(idx)
                self._direction_pinned = True

        # Справочники целиком не грузим ни в create, ни в edit: пикеры подгружают их лениво,
        # а подписи кнопок в edit — точечно (_resolve_names_async), по запросу на узел документа.

        # Устанавливаем заголовок и кнопки в зависимости от режима
        self._setup_mode_ui()
        if self.mode == "edit":
            self._resolve_names_async()

        self._connect_signals()
        self._set_default_dates()
        self._apply_type_fields()