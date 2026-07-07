"""
Модуль с тестовыми данными и конфигурацией таблицы документов
"""
from PyQt6.QtGui import QColor
from datetime import datetime, timedelta
from typing import List, Dict, Any


class DocumentDataConfig:
    """Конфигурация и тестовые данные для таблицы документов"""

    # ============ ТИПЫ ДОКУМЕНТОВ ============
    DOCUMENT_TYPES = [
        {
            "id": 1,
            "name": "Служебная записка",
            "fields": [
                {"name": "basis", "type": "text", "label": "Основание"}
            ],
            "auto_num": True,
            "smdo_code_type": None
        },
        {
            "id": 2,
            "name": "Приказ генерального директора",
            "fields": [
                {"name": "control_date", "type": "date", "label": "Срок контроля"}
            ],
            "auto_num": True,
            "smdo_code_type": None
        },
        {
            "id": 3,
            "name": "Официальное письмо",
            "fields": [],
            "auto_num": False,
            "smdo_code_type": "1.1.2.5"
        },
        {
            "id": 4,
            "name": "Циркулярное письмо",
            "fields": [],
            "auto_num": True,
            "smdo_code_type": "1.1.2.1"
        }
    ]

    # ============ НАПРАВЛЕНИЯ (DIRECTIONS) ============
    # Маппинг направлений из БД в человекочитаемый вид
    DIRECTION_MAPPING = {
        "internal": "Внутренние документы",
        "external": "Внешние документы"
    }

    # Группировка типов документов по направлениям
    # Определяем, какие типы относятся к каким направлениям
    TYPE_DIRECTION_MAPPING = {
        "internal": [1, 2],  # Служебная записка, Приказ генерального директора
        "external": [3, 4]   # Официальное письмо (Входящее СМДО), Циркулярное письмо (Исходящее СМДО)
    }

    # ============ СТАТУСЫ ============
    STATUS_MAPPING = {
        "under_review": "На рассмотрении",
        "partially_approved": "Частично утвержден",
        "approved": "Утвержден",
        "rejected": "Отклонен"
    }

    # ============ КОНФИГУРАЦИЯ КОЛОНОК ============
    COLUMNS_CONFIG = {
        0: "ID",
        1: "Прочитано",
        2: "Номер документа",
        3: "Тема",
        4: "Тип",
        5: "Дата создания",
        6: "Статус",
        7: "Направление",
        8: "Отправители",
        9: "Получатели",
        10: "Исполнители",
        11: "Делегаты",
        12: "Хэштеги",
        13: "Комментарии",
        14: "Вложение",
        15: "Ответ",
        16: "Краткое содержание",
        17: "Срок исполнения"
    }

    # ============ ЦВЕТА ============
    EVEN_ROW_COLOR = QColor("#FFFFFF")
    ODD_ROW_COLOR = QColor("#F5F5F5")
    TEXT_COLOR = QColor("#1B232A")
    SELECTED_COLOR = QColor("#E3F2FD")

    # ============ ФОРМАТЫ ФАЙЛОВ ============
    SUPPORTED_FORMATS = (
        "Документы (*.pdf *.docx *.doc *.txt *.tif);;"
        "PDF (*.pdf);;"
        "Word (*.docx *.doc);;"
        "Текст (*.txt);;"
        "TIFF (*.tif)"
    )

    # ============ ТЕСТОВЫЕ ДАННЫЕ ============
    TEST_DATA = [
        {
            "id": 1,
            "type_id": 2,
            "type_name": "Приказ генерального директора",
            "direction": "internal",
            "status": "under_review",
            "title": "О внесении изменений в план работы",
            "about": "Внесение корректировок в план работы на 2-е полугодие",
            "reg_number": "01-15/123",
            "sequence_number": 123,
            "sent_date": "2026-06-10",
            "deadline": "2026-07-10",
            "incoming_number": None,
            "incoming_date": None,
            "global_msg_id": "uuid-123-456-789",
            "parent_document_id": None,
            "confident_flag": 0,
            "clearance_id": None,
            "clearance_name": None,
            "numcopy": "01",
            "senders": ["Иванов И.И.", "Петров А.А."],
            "senders_ids": [1, 2],
            "receivers": ["Отдел кадров", "Бухгалтерия"],
            "receivers_ids": [3, 4],
            "executors": ["Сидоров С.С.", "Морозов М.М."],
            "executors_ids": [5, 6],
            "delegates": ["Козлов К.К."],
            "delegates_ids": [7],
            "tags": [
                {"id": 1, "name": "Срочно", "color": "#D22730", "priority": "urgent"},
                {"id": 2, "name": "Кадры", "color": "#4A90E2", "priority": "normal"}
            ],
            "comments": [
                {"id": 1, "employee_id": 1, "text": "Прошу рассмотреть в кратчайшие сроки", "created_at": "2026-06-10T10:00:00Z"},
                {"id": 2, "employee_id": 2, "text": "Согласовано", "created_at": "2026-06-11T11:30:00Z"},
                {"id": 3, "employee_id": 5, "text": "Требуется доработка раздела 3", "created_at": "2026-06-11T14:20:00Z"}
            ],
            "last_comment_text": "Требуется доработка раздела 3",
            "attachments": [
                {"id": 1, "file_name": "Приказ_№123.pdf", "file_size": 245760, "storage_path": "/attachments/order_123.pdf"},
                {"id": 2, "file_name": "Приложение_1.docx", "file_size": 102400, "storage_path": "/attachments/appendix_1.docx"}
            ],
            "reply_file": {"id": 1, "file_name": "Ответ_на_приказ.pdf", "file_size": 156672, "storage_path": "/replies/reply_123.pdf"},
            "has_reply": True,
            "is_read": False,
            "is_completed": False,
            "created_at": "2026-06-10T08:00:00Z",
            "source_employee_id": 1,
            "source_organization_id": 1,
            "source_official_text": "Генеральный директор Иванов И.И."
        },
        {
            "id": 2,
            "type_id": 1,
            "type_name": "Служебная записка",
            "direction": "internal",
            "status": "approved",
            "title": "Служебная записка о закупке оборудования",
            "about": "Закупка нового оборудования для отдела разработки",
            "reg_number": "01-15/124",
            "sequence_number": 124,
            "sent_date": "2026-06-09",
            "deadline": "2026-06-30",
            "incoming_number": None,
            "incoming_date": None,
            "global_msg_id": "uuid-123-456-790",
            "parent_document_id": None,
            "confident_flag": 0,
            "clearance_id": None,
            "clearance_name": None,
            "numcopy": "02",
            "senders": ["Петров П.П."],
            "senders_ids": [8],
            "receivers": ["Отдел закупок"],
            "receivers_ids": [9],
            "executors": ["Морозов М.М.", "Сидоров С.С."],
            "executors_ids": [6, 5],
            "delegates": [],
            "delegates_ids": [],
            "tags": [
                {"id": 3, "name": "Закупки", "color": "#50C878", "priority": "normal"},
                {"id": 4, "name": "Важно", "color": "#FF8C00", "priority": "important"}
            ],
            "comments": [
                {"id": 4, "employee_id": 6, "text": "Оборудование заказано", "created_at": "2026-06-10T09:00:00Z"}
            ],
            "last_comment_text": "Оборудование заказано",
            "attachments": [],
            "reply_file": None,
            "has_reply": False,
            "is_read": True,
            "is_completed": True,
            "created_at": "2026-06-09T15:30:00Z",
            "source_employee_id": 8,
            "source_organization_id": 1,
            "source_official_text": "Начальник отдела Петров П.П."
        },
        {
            "id": 3,
            "type_id": 3,
            "type_name": "Официальное письмо (Входящее СМДО)",
            "direction": "external",
            "status": "partially_approved",
            "title": "Письмо о сотрудничестве от ООО Партнер",
            "about": "Предложение о долгосрочном сотрудничестве",
            "reg_number": "01-15/125",
            "sequence_number": 125,
            "sent_date": "2026-06-08",
            "deadline": "2026-07-15",
            "incoming_number": "ИН-2026-456",
            "incoming_date": "2026-06-08",
            "global_msg_id": "uuid-123-456-791",
            "parent_document_id": None,
            "confident_flag": 0,
            "clearance_id": None,
            "clearance_name": None,
            "numcopy": "03",
            "senders": ["ООО Партнер"],
            "senders_ids": [10],
            "receivers": ["Юридический отдел", "Отдел продаж"],
            "receivers_ids": [11, 12],
            "executors": ["Петров А.А."],
            "executors_ids": [2],
            "delegates": ["Козлов К.К.", "Морозов М.М."],
            "delegates_ids": [7, 6],
            "tags": [
                {"id": 5, "name": "Партнеры", "color": "#9B59B6", "priority": "normal"}
            ],
            "comments": [
                {"id": 5, "employee_id": 5, "text": "Необходимо согласовать условия", "created_at": "2026-06-08T10:00:00Z"},
                {"id": 6, "employee_id": 2, "text": "Отправил на согласование юристам", "created_at": "2026-06-09T11:30:00Z"}
            ],
            "last_comment_text": "Отправил на согласование юристам",
            "attachments": [
                {"id": 3, "file_name": "Договор_проект.pdf", "file_size": 512000, "storage_path": "/attachments/contract_draft.pdf"}
            ],
            "reply_file": None,
            "has_reply": False,
            "is_read": False,
            "is_completed": False,
            "created_at": "2026-06-08T09:45:00Z",
            "source_employee_id": None,
            "source_organization_id": 2,
            "source_official_text": "ООО Партнер, директор Смирнов С.С."
        },
        {
            "id": 4,
            "type_id": 4,
            "type_name": "Циркулярное письмо (Исходящее СМДО)",
            "direction": "external",
            "status": "approved",
            "title": "Циркулярное письмо о внедрении новой системы",
            "about": "Уведомление о внедрении новой системы документооборота",
            "reg_number": "01-15/126",
            "sequence_number": 126,
            "sent_date": "2026-06-07",
            "deadline": "2026-08-01",
            "incoming_number": None,
            "incoming_date": None,
            "global_msg_id": "uuid-123-456-792",
            "parent_document_id": None,
            "confident_flag": 1,
            "clearance_id": 1,
            "clearance_name": "Для служебного пользования",
            "numcopy": "04",
            "senders": ["Руководство МАЗ"],
            "senders_ids": [1],
            "receivers": ["Все структурные подразделения"],
            "receivers_ids": [],
            "executors": ["Козлов К.К.", "Морозов М.М."],
            "executors_ids": [7, 6],
            "delegates": [],
            "delegates_ids": [],
            "tags": [
                {"id": 6, "name": "Системные", "color": "#3498DB", "priority": "urgent"}
            ],
            "comments": [
                {"id": 7, "employee_id": 7, "text": "Письмо отправлено всем подразделениям", "created_at": "2026-06-07T16:00:00Z"},
                {"id": 8, "employee_id": 1, "text": "Утверждено", "created_at": "2026-06-08T09:00:00Z"}
            ],
            "last_comment_text": "Утверждено",
            "attachments": [
                {"id": 4, "file_name": "Циркуляр.pdf", "file_size": 1024000, "storage_path": "/attachments/circular.pdf"},
                {"id": 5, "file_name": "Приложение_А.xlsx", "file_size": 256000, "storage_path": "/attachments/appendix_a.xlsx"}
            ],
            "reply_file": None,
            "has_reply": False,
            "is_read": True,
            "is_completed": True,
            "created_at": "2026-06-07T14:20:00Z",
            "source_employee_id": 1,
            "source_organization_id": 1,
            "source_official_text": "Генеральный директор Иванов И.И."
        },
        {
            "id": 5,
            "type_id": 1,
            "type_name": "Служебная записка",
            "direction": "internal",
            "status": "rejected",
            "title": "Заявка на командировку",
            "about": "Командировка в Минск для участия в конференции",
            "reg_number": "01-15/127",
            "sequence_number": 127,
            "sent_date": "2026-06-06",
            "deadline": "2026-06-20",
            "incoming_number": None,
            "incoming_date": None,
            "global_msg_id": "uuid-123-456-793",
            "parent_document_id": 2,
            "confident_flag": 0,
            "clearance_id": None,
            "clearance_name": None,
            "numcopy": "05",
            "senders": ["Морозов М.М.", "Петров А.А."],
            "senders_ids": [6, 2],
            "receivers": ["Отдел кадров", "Бухгалтерия", "Руководство"],
            "receivers_ids": [3, 4, 1],
            "executors": ["Иванов И.И.", "Сидоров С.С."],
            "executors_ids": [1, 5],
            "delegates": ["Петров А.А.", "Козлов К.К."],
            "delegates_ids": [2, 7],
            "tags": [
                {"id": 7, "name": "Командировки", "color": "#E67E22", "priority": "normal"},
                {"id": 1, "name": "Срочно", "color": "#D22730", "priority": "urgent"}
            ],
            "comments": [
                {"id": 9, "employee_id": 6, "text": "Прошу согласовать командировку", "created_at": "2026-06-06T08:00:00Z"},
                {"id": 10, "employee_id": 1, "text": "Отклонено", "created_at": "2026-06-07T10:00:00Z"}
            ],
            "last_comment_text": "Отклонено",
            "attachments": [
                {"id": 6, "file_name": "Заявка_командировка.docx", "file_size": 45600, "storage_path": "/attachments/business_trip.docx"}
            ],
            "reply_file": None,
            "has_reply": False,
            "is_read": False,
            "is_completed": True,
            "created_at": "2026-06-06T07:30:00Z",
            "source_employee_id": 6,
            "source_organization_id": 1,
            "source_official_text": "Ведущий специалист Морозов М.М."
        }
    ]

    # ============ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ============

    @classmethod
    def get_status_text(cls, status: str) -> str:
        """Получить человекочитаемый статус"""
        return cls.STATUS_MAPPING.get(status, status)

    @classmethod
    def get_direction_text(cls, direction: str) -> str:
        """Получить человекочитаемое направление"""
        return cls.DIRECTION_MAPPING.get(direction, direction)

    @classmethod
    def get_document_by_id(cls, doc_id: int) -> dict:
        """Получить документ по ID"""
        for doc in cls.TEST_DATA:
            if doc.get("id") == doc_id:
                return doc
        return None

    @classmethod
    def get_document_types(cls) -> list:
        """Получить типы документов"""
        return cls.DOCUMENT_TYPES

    @classmethod
    def get_document_type_by_id(cls, type_id: int) -> dict:
        """Получить тип документа по ID"""
        for doc_type in cls.DOCUMENT_TYPES:
            if doc_type.get("id") == type_id:
                return doc_type
        return None

    @classmethod
    def get_documents_by_type(cls, type_id: int) -> list:
        """Получить документы по типу"""
        return [doc for doc in cls.TEST_DATA if doc.get("type_id") == type_id]

    @classmethod
    def get_documents_by_direction(cls, direction: str) -> list:
        """Получить документы по направлению"""
        return [doc for doc in cls.TEST_DATA if doc.get("direction") == direction]

    @classmethod
    def get_types_by_direction(cls, direction: str) -> list:
        """Получить типы документов по направлению"""
        type_ids = cls.TYPE_DIRECTION_MAPPING.get(direction, [])
        return [t for t in cls.DOCUMENT_TYPES if t.get("id") in type_ids]

    @classmethod
    def get_directions_data(cls) -> list:
        """
        Получить данные для левой панели на основе типов документов.
        Группировка: внутренние и внешние документы.
        """
        directions_data = []

        for direction_key, direction_label in cls.DIRECTION_MAPPING.items():
            types = cls.get_types_by_direction(direction_key)
            direction_data = {
                "group": direction_label,
                "direction": direction_key,
                "directions": [
                    {
                        "name": doc_type["name"],
                        "type_id": doc_type["id"],
                        "fields": doc_type.get("fields", []),
                        "auto_num": doc_type.get("auto_num", False),
                        "smdo_code_type": doc_type.get("smdo_code_type")
                    }
                    for doc_type in types
                ]
            }
            directions_data.append(direction_data)

        return directions_data

    @classmethod
    def get_documents_with_type_info(cls) -> list:
        """
        Получить документы с полной информацией о типе.
        """
        docs_with_types = []
        for doc in cls.TEST_DATA:
            doc_copy = doc.copy()
            type_info = cls.get_document_type_by_id(doc.get("type_id"))
            if type_info:
                doc_copy["type_fields"] = type_info.get("fields", [])
                doc_copy["type_auto_num"] = type_info.get("auto_num", False)
                doc_copy["type_smdo_code"] = type_info.get("smdo_code_type")
            docs_with_types.append(doc_copy)
        return docs_with_types

    @classmethod
    def get_columns_for_type(cls, type_id: int) -> dict:
        """
        Получить конфигурацию колонок для конкретного типа документа.
        Базовые колонки всегда есть, дополнительные добавляются из fields.
        """
        # Базовые колонки для всех типов
        base_columns = {
            0: "ID",
            1: "Прочитано",
            2: "Номер документа",
            5: "Дата создания",
            13: "Комментарии",
            14: "Вложение",
        }

        # Если есть дополнительные поля - добавляем их
        type_info = cls.get_document_type_by_id(type_id)
        if type_info and type_info.get("fields"):
            fields = type_info["fields"]
            for idx, field in enumerate(fields, start=20):
                field_name = field.get("label", field.get("name", f"Поле_{idx}"))
                base_columns[idx] = field_name

        return base_columns

    @classmethod
    def get_documents_response(cls, type_id: int = None, direction: str = None) -> dict:
        """
        Получить ответ в формате API с пагинацией.
        """
        items = cls.TEST_DATA.copy()

        if type_id is not None:
            items = [doc for doc in items if doc.get("type_id") == type_id]

        if direction is not None:
            items = [doc for doc in items if doc.get("direction") == direction]

        return {
            "total": len(items),
            "limit": 20,
            "offset": 0,
            "items": items
        }

    # client/core/data/document_data.py - добавляем метод

    @classmethod
    def get_columns_for_type(cls, type_id: int) -> dict:
        """
        Получить конфигурацию колонок для конкретного типа документа.
        Базовые колонки всегда есть, дополнительные добавляются из fields.
        """
        # Базовые колонки для всех типов
        base_columns = {
            0: "ID",
            1: "Прочитано",
            2: "Номер документа",
            3: "Тема",
            5: "Дата создания",
            6: "Статус",
            13: "Комментарии",
            14: "Вложение",
            17: "Срок исполнения"
        }

        # Если есть дополнительные поля - добавляем их
        type_info = cls.get_document_type_by_id(type_id)
        if type_info and type_info.get("fields"):
            fields = type_info["fields"]
            # Добавляем поля начиная с индекса 20
            for idx, field in enumerate(fields, start=20):
                field_name = field.get("label", field.get("name", f"Поле_{idx}"))
                base_columns[idx] = field_name

        return base_columns