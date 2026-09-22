"""
Модуль с тестовыми данными и конфигурацией таблицы документов
"""
from PyQt6.QtGui import QColor
from datetime import datetime, timedelta
from typing import List, Dict, Any
import copy


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
            # Какие поля с пользователями доступны для этого типа
            "user_fields": ["senders", "receivers", "executors", "delegates"],
            "auto_num": True,
            "smdo_code_type": None
        },
        {
            "id": 2,
            "name": "Приказ генерального директора",
            "fields": [
                {"name": "control_date", "type": "date", "label": "Срок контроля"}
            ],
            "user_fields": ["senders", "receivers", "executors"],
            "auto_num": True,
            "smdo_code_type": None
        },
        {
            "id": 3,
            "name": "Официальное письмо",
            "fields": [],
            "user_fields": ["senders", "receivers"],
            "auto_num": False,
            "smdo_code_type": "1.1.2.5"
        },
        {
            "id": 4,
            "name": "Циркулярное письмо",
            "fields": [],
            "user_fields": ["senders", "receivers", "executors", "delegates"],
            "auto_num": True,
            "smdo_code_type": "1.1.2.1"
        }
    ]

    # ============ НАПРАВЛЕНИЯ (DIRECTIONS) ============
    DIRECTION_MAPPING = {
        "internal": "Внутренние документы",
        "external": "Внешние документы"
    }

    TYPE_DIRECTION_MAPPING = {
        "internal": [1, 2],
        "external": [3, 4]
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
    # ============ ЦВЕТА (динамические, из текущей темы) ============

    @classmethod
    def get_row_color(cls, is_even: bool) -> QColor:
        """Фон чётной/нечётной строки таблицы."""
        from client.core.themes import get_manager
        t = get_manager().current
        return QColor(t.TABLE_BG if is_even else t.TABLE_ROW_ALT)

    @classmethod
    def get_even_row_color(cls) -> QColor:
        return cls.get_row_color(is_even=True)

    @classmethod
    def get_odd_row_color(cls) -> QColor:
        return cls.get_row_color(is_even=False)

    @classmethod
    def get_text_color(cls) -> QColor:
        """Основной цвет текста в таблице."""
        from client.core.themes import get_manager
        return QColor(get_manager().current.TEXT_PRIMARY)

    @classmethod
    def get_selected_color(cls) -> QColor:
        """Фон выделенной строки."""
        from client.core.themes import get_manager
        return QColor(get_manager().current.TABLE_SELECTION_BG)

    # ============ ФОРМАТЫ ФАЙЛОВ ============
    SUPPORTED_FORMATS = (
        "Документы (*.pdf *.docx *.doc *.txt *.tif);;"
        "PDF (*.pdf);;"
        "Word (*.docx *.doc);;"
        "Текст (*.txt);;"
        "TIFF (*.tif)"
    )

    # ============ ТЕСТОВЫЕ ДАННЫЕ (БАЗОВЫЕ ШАБЛОНЫ) ============
    # Базовые данные для каждого типа документа
    _BASE_DOCUMENTS = {
        1: {  # Служебная записка
            "type_name": "Служебная записка",
            "direction": "internal",
            "titles": [
                "Служебная записка о закупке оборудования",
                "Заявка на командировку",
                "Служебная записка о премировании",
                "Запрос на согласование бюджета"
            ],
            "abouts": [
                "Закупка нового оборудования для отдела разработки",
                "Командировка в Минск для участия в конференции",
                "Премирование сотрудников по итогам квартала",
                "Согласование бюджета на следующий квартал"
            ],
            "senders": [["Петров П.П."], ["Морозов М.М.", "Петров А.А."], ["Сидоров С.С."], ["Иванов И.И."]],
            "senders_ids": [[8], [6, 2], [5], [1]],
            "receivers": [["Отдел закупок"], ["Отдел кадров", "Бухгалтерия", "Руководство"], ["Финансовый отдел"], ["Плановый отдел"]],
            "receivers_ids": [[9], [3, 4, 1], [13], [14]],
            "executors": [["Морозов М.М.", "Сидоров С.С."], ["Иванов И.И.", "Сидоров С.С."], ["Петров А.А."], ["Козлов К.К."]],
            "executors_ids": [[6, 5], [1, 5], [2], [7]],
            "delegates": [[], ["Петров А.А.", "Козлов К.К."], ["Морозов М.М."], []],
            "delegates_ids": [[], [2, 7], [6], []],
            "extra_fields": {
                "basis": ["Для закупки оборудования", "Для командировки", "Для премирования", "Для бюджета"]
            }
        },
        2: {  # Приказ генерального директора
            "type_name": "Приказ генерального директора",
            "direction": "internal",
            "titles": [
                "О внесении изменений в план работы",
                "О назначении ответственных лиц",
                "Об утверждении новой структуры",
                "О проведении инвентаризации"
            ],
            "abouts": [
                "Внесение корректировок в план работы на 2-е полугодие",
                "Назначение ответственных за реализацию проекта",
                "Утверждение новой организационной структуры",
                "Проведение ежегодной инвентаризации"
            ],
            "senders": [["Иванов И.И.", "Петров А.А."], ["Иванов И.И."], ["Петров А.А."], ["Иванов И.И.", "Сидоров С.С."]],
            "senders_ids": [[1, 2], [1], [2], [1, 5]],
            "receivers": [["Отдел кадров", "Бухгалтерия"], ["Все подразделения"], ["Отдел кадров"], ["Бухгалтерия", "Склад"]],
            "receivers_ids": [[3, 4], [15], [3], [4, 16]],
            "executors": [["Сидоров С.С.", "Морозов М.М."], ["Козлов К.К."], ["Морозов М.М."], ["Сидоров С.С."]],
            "executors_ids": [[5, 6], [7], [6], [5]],
            "delegates": [],  # У приказов нет делегатов в этом примере
            "delegates_ids": [],
            "extra_fields": {
                "control_date": ["2026-07-10", "2026-06-30", "2026-08-15", "2026-07-20"]
            }
        },
        3: {  # Официальное письмо
            "type_name": "Официальное письмо (Входящее СМДО)",
            "direction": "external",
            "titles": [
                "Письмо о сотрудничестве от ООО Партнер",
                "Запрос от АО Технологии",
                "Предложение от ИП Смирнов",
                "Уведомление от ООО СтройИнвест"
            ],
            "abouts": [
                "Предложение о долгосрочном сотрудничестве",
                "Запрос на участие в тендере",
                "Коммерческое предложение",
                "Уведомление о проведении аудита"
            ],
            "senders": [["ООО Партнер"], ["АО Технологии"], ["ИП Смирнов"], ["ООО СтройИнвест"]],
            "senders_ids": [[10], [17], [18], [19]],
            "receivers": [["Юридический отдел", "Отдел продаж"], ["Отдел закупок"], ["Отдел развития"], ["Бухгалтерия"]],
            "receivers_ids": [[11, 12], [9], [20], [4]],
            "executors": [],  # У официальных писем нет исполнителей
            "executors_ids": [],
            "delegates": [],  # У официальных писем нет делегатов
            "delegates_ids": [],
            "extra_fields": {}
        },
        4: {  # Циркулярное письмо
            "type_name": "Циркулярное письмо (Исходящее СМДО)",
            "direction": "external",
            "titles": [
                "Циркулярное письмо о внедрении новой системы",
                "Циркуляр о новых правилах документооборота",
                "Циркуляр о изменении графика работы",
                "Циркуляр о проведении обучения"
            ],
            "abouts": [
                "Уведомление о внедрении новой системы документооборота",
                "Информирование о новых правилах работы с документами",
                "Изменение графика работы в праздничные дни",
                "Проведение обязательного обучения персонала"
            ],
            "senders": [["Руководство МАЗ"], ["Департамент управления"], ["Руководство МАЗ"], ["Отдел кадров"]],
            "senders_ids": [[1], [21], [1], [3]],
            "receivers": [["Все структурные подразделения"], ["Все отделы"], ["Все сотрудники"], ["Все подразделения"]],
            "receivers_ids": [[], [], [], []],
            "executors": [["Козлов К.К.", "Морозов М.М."], ["Сидоров С.С."], ["Петров А.А."], ["Морозов М.М."]],
            "executors_ids": [[7, 6], [5], [2], [6]],
            "delegates": [[], ["Козлов К.К."], [], ["Петров А.А."]],
            "delegates_ids": [[], [7], [], [2]],
            "extra_fields": {}
        }
    }

    TAGS_DATA = [
        {'id': 1, 'name': 'Срочно', 'priority': 'urgent', 'color': '#FF0000'},
        {'id': 2, 'name': 'Важно', 'priority': 'important', 'color': '#FFA500'},
        {'id': 3, 'name': 'Обычный', 'priority': 'normal', 'color': '#808080'},
        {'id': 4, 'name': 'Финансы', 'priority': 'important', 'color': '#008000'},
        {'id': 5, 'name': 'Кадры', 'priority': 'normal', 'color': '#0000FF'},
        {'id': 6, 'name': 'Юридический', 'priority': 'normal', 'color': '#800080'},
        {'id': 7, 'name': 'Договор', 'priority': 'urgent', 'color': '#FF4500'},
        {'id': 8, 'name': 'Отчет', 'priority': 'important', 'color': '#2E8B57'},
        {'id': 9, 'name': 'Технический', 'priority': 'normal', 'color': '#4169E1'},
        {'id': 10, 'name': 'Маркетинг', 'priority': 'normal', 'color': '#FF1493'},
    ]

    @classmethod
    def get_tags_data(cls) -> list:
        """Получить все теги"""
        return cls.TAGS_DATA.copy()

    @classmethod
    def get_tag_by_id(cls, tag_id: int) -> dict:
        """Получить тег по ID"""
        for tag in cls.TAGS_DATA:
            if tag.get('id') == tag_id:
                return tag.copy()
        return None

    # ============ ГЕНЕРАЦИЯ ТЕСТОВЫХ ДАННЫХ ============
    @classmethod
    def _generate_document(cls, type_id: int, index: int, status: str, is_read: bool, is_completed: bool,
                          reg_number: str, sequence_number: int, sent_date: str, deadline: str,
                          incoming_number: str = None, incoming_date: str = None,
                          parent_document_id: int = None, confident_flag: int = 0,
                          clearance_id: int = None, clearance_name: str = None,
                          attachments: list = None, reply_file: dict = None,
                          has_reply: bool = False, source_employee_id: int = None,
                          source_organization_id: int = 1, source_official_text: str = "",
                          extra_values: dict = None) -> dict:
        """Генерирует документ на основе шаблона типа"""

        base = cls._BASE_DOCUMENTS.get(type_id, cls._BASE_DOCUMENTS[1])
        extra_values = extra_values or {}

        # Базовые поля
        doc = {
            "id": index,
            "type_id": type_id,
            "type_name": base["type_name"],
            "direction": base["direction"],
            "status": status,
            "title": base["titles"][index % len(base["titles"])],
            "about": base["abouts"][index % len(base["abouts"])],
            "reg_number": reg_number,
            "sequence_number": sequence_number,
            "sent_date": sent_date,
            "deadline": deadline,
            "incoming_number": incoming_number,
            "incoming_date": incoming_date,
            "global_msg_id": f"uuid-{index}-{type_id}-{sequence_number}",
            "parent_document_id": parent_document_id,
            "confident_flag": confident_flag,
            "clearance_id": clearance_id,
            "clearance_name": clearance_name,
            "numcopy": f"{index:02d}",
            "is_read": is_read,
            "is_completed": is_completed,
            "created_at": f"{sent_date}T{'08:00:00Z' if index % 2 == 0 else '14:30:00Z'}",
            "source_employee_id": source_employee_id,
            "source_organization_id": source_organization_id,
            "source_official_text": source_official_text,
        }

        # Добавляем поля пользователей только если они есть в типе
        user_fields = cls.get_document_type_by_id(type_id).get("user_fields", [])

        if "senders" in user_fields:
            senders_list = base["senders"][index % len(base["senders"])]
            doc["senders"] = senders_list
            doc["senders_ids"] = base["senders_ids"][index % len(base["senders_ids"])]
        else:
            doc["senders"] = []
            doc["senders_ids"] = []

        if "receivers" in user_fields:
            receivers_list = base["receivers"][index % len(base["receivers"])]
            doc["receivers"] = receivers_list
            doc["receivers_ids"] = base["receivers_ids"][index % len(base["receivers_ids"])]
        else:
            doc["receivers"] = []
            doc["receivers_ids"] = []

        if "executors" in user_fields:
            executors_list = base["executors"][index % len(base["executors"])] if base["executors"] else []
            doc["executors"] = executors_list
            doc["executors_ids"] = base["executors_ids"][index % len(base["executors_ids"])] if base["executors_ids"] else []
        else:
            doc["executors"] = []
            doc["executors_ids"] = []

        if "delegates" in user_fields:
            delegates_list = base["delegates"][index % len(base["delegates"])] if base["delegates"] else []
            doc["delegates"] = delegates_list
            doc["delegates_ids"] = base["delegates_ids"][index % len(base["delegates_ids"])] if base["delegates_ids"] else []
        else:
            doc["delegates"] = []
            doc["delegates_ids"] = []

        # Добавляем теги
        doc["tags"] = cls._generate_tags(index)

        # Добавляем комментарии
        doc["comments"] = cls._generate_comments(index, status)
        doc["last_comment_text"] = doc["comments"][-1]["text"] if doc["comments"] else ""

        # Добавляем вложения
        doc["attachments"] = attachments or cls._generate_attachments(index, type_id)

        # Добавляем ответ
        doc["reply_file"] = reply_file
        doc["has_reply"] = has_reply

        # Добавляем дополнительные поля из типа
        type_info = cls.get_document_type_by_id(type_id)
        if type_info and type_info.get("fields"):
            for field in type_info["fields"]:
                field_name = field["name"]
                if field_name in base.get("extra_fields", {}):
                    values = base["extra_fields"][field_name]
                    doc[field_name] = values[index % len(values)] if values else None
                elif field_name in extra_values:
                    doc[field_name] = extra_values[field_name]
                else:
                    doc[field_name] = None

        return doc

    @classmethod
    def _generate_tags(cls, index: int) -> list:
        """Генерирует теги для документа"""
        tags_map = {
            0: [
                {"id": 1, "name": "Срочно", "color": "#D22730", "priority": "urgent"},
                {"id": 2, "name": "Кадры", "color": "#4A90E2", "priority": "normal"}
            ],
            1: [
                {"id": 3, "name": "Закупки", "color": "#50C878", "priority": "normal"},
                {"id": 4, "name": "Важно", "color": "#FF8C00", "priority": "important"}
            ],
            2: [
                {"id": 5, "name": "Партнеры", "color": "#9B59B6", "priority": "normal"}
            ],
            3: [
                {"id": 6, "name": "Системные", "color": "#3498DB", "priority": "urgent"}
            ],
            4: [
                {"id": 7, "name": "Командировки", "color": "#E67E22", "priority": "normal"},
                {"id": 1, "name": "Срочно", "color": "#D22730", "priority": "urgent"}
            ]
        }
        return tags_map.get(index % 5, [])

    @classmethod
    def _generate_comments(cls, index: int, status: str) -> list:
        """Генерирует комментарии для документа в правильном формате"""
        base_comments = {
            0: [
                {"id": 1, "author_fio": "Иванов И.И.", "text": "Прошу рассмотреть в кратчайшие сроки",
                 "created_at": "2026-06-10T10:00:00Z"},
                {"id": 2, "author_fio": "Петров П.П.", "text": "Согласовано", "created_at": "2026-06-11T11:30:00Z"},
                {"id": 3, "author_fio": "Сидоров С.С.", "text": "Требуется доработка раздела 3",
                 "created_at": "2026-06-11T14:20:00Z"}
            ],
            1: [
                {"id": 4, "author_fio": "Морозов М.М.", "text": "Оборудование заказано",
                 "created_at": "2026-06-10T09:00:00Z"}
            ],
            3: [  # ← Документ 3
                {"id": 7, "author_fio": "Неизвестный", "text": "Письмо отправлено всем подразделениям",
                 "created_at": "2026-06-07T16:00:00Z"},
                {"id": 8, "author_fio": "Неизвестный", "text": "Утверждено", "created_at": "2026-06-08T09:00:00Z"}
            ],
            4: [
                {"id": 9, "author_fio": "Козлов К.К.", "text": "Прошу согласовать командировку",
                 "created_at": "2026-06-06T08:00:00Z"},
                {"id": 10, "author_fio": "Иванов И.И.", "text": "Отклонено", "created_at": "2026-06-07T10:00:00Z"}
            ]
        }

        # Для всех остальных документов добавляем хотя бы один комментарий
        if index not in base_comments:
            return [
                {
                    "id": 100 + index,
                    "author_fio": "Сидоров С.С.",
                    "text": f"Тестовый комментарий к документу #{index}",
                    "created_at": "2026-06-01T12:00:00Z"
                }
            ]

        return base_comments.get(index, [])

    @classmethod
    def _generate_attachments(cls, index: int, type_id: int) -> list:
        """Генерирует вложения для документа"""
        attachments_map = {
            0: [
                {"id": 1, "file_name": "Приказ_№123.pdf", "file_size": 245760, "storage_path": "/attachments/order_123.pdf"},
                {"id": 2, "file_name": "Приложение_1.docx", "file_size": 102400, "storage_path": "/attachments/appendix_1.docx"}
            ],
            1: [],
            2: [
                {"id": 3, "file_name": "Договор_проект.pdf", "file_size": 512000, "storage_path": "/attachments/contract_draft.pdf"}
            ],
            3: [
                {"id": 4, "file_name": "Циркуляр.pdf", "file_size": 1024000, "storage_path": "/attachments/circular.pdf"},
                {"id": 5, "file_name": "Приложение_А.xlsx", "file_size": 256000, "storage_path": "/attachments/appendix_a.xlsx"}
            ],
            4: [
                {"id": 6, "file_name": "Заявка_командировка.docx", "file_size": 45600, "storage_path": "/attachments/business_trip.docx"}
            ]
        }
        return attachments_map.get(index % 5, [])

    # ============ ИНИЦИАЛИЗАЦИЯ ТЕСТОВЫХ ДАННЫХ ============
    TEST_DATA = []

    @classmethod
    def _initialize_test_data(cls):
        """Инициализирует тестовые данные на основе конфигурации типов"""
        if cls.TEST_DATA:
            return cls.TEST_DATA

        # Параметры для генерации документов
        doc_configs = [
            # (type_id, status, is_read, is_completed, reg_number, seq_num, sent_date, deadline, extra)
            {
                "type_id": 2,
                "status": "under_review",
                "is_read": False,
                "is_completed": False,
                "reg_number": "01-15/123",
                "seq_num": 123,
                "sent_date": "2026-06-10",
                "deadline": "2026-07-10",
                "incoming_number": None,
                "incoming_date": None,
                "parent_document_id": None,
                "confident_flag": 0,
                "clearance_id": None,
                "clearance_name": None,
                "attachments": None,
                "reply_file": {"id": 1, "file_name": "Ответ_на_приказ.pdf", "file_size": 156672, "storage_path": "/replies/reply_123.pdf"},
                "has_reply": True,
                "source_employee_id": 1,
                "source_official_text": "Генеральный директор Иванов И.И."
            },
            {
                "type_id": 1,
                "status": "approved",
                "is_read": True,
                "is_completed": True,
                "reg_number": "01-15/124",
                "seq_num": 124,
                "sent_date": "2026-06-09",
                "deadline": "2026-06-30",
                "incoming_number": None,
                "incoming_date": None,
                "parent_document_id": None,
                "confident_flag": 0,
                "clearance_id": None,
                "clearance_name": None,
                "attachments": [],
                "reply_file": None,
                "has_reply": False,
                "source_employee_id": 8,
                "source_official_text": "Начальник отдела Петров П.П."
            },
            {
                "type_id": 3,
                "status": "partially_approved",
                "is_read": False,
                "is_completed": False,
                "reg_number": "01-15/125",
                "seq_num": 125,
                "sent_date": "2026-06-08",
                "deadline": "2026-07-15",
                "incoming_number": "ИН-2026-456",
                "incoming_date": "2026-06-08",
                "parent_document_id": None,
                "confident_flag": 0,
                "clearance_id": None,
                "clearance_name": None,
                "attachments": None,
                "reply_file": None,
                "has_reply": False,
                "source_employee_id": None,
                "source_organization_id": 2,
                "source_official_text": "ООО Партнер, директор Смирнов С.С."
            },
            {
                "type_id": 4,
                "status": "approved",
                "is_read": True,
                "is_completed": True,
                "reg_number": "01-15/126",
                "seq_num": 126,
                "sent_date": "2026-06-07",
                "deadline": "2026-08-01",
                "incoming_number": None,
                "incoming_date": None,
                "parent_document_id": None,
                "confident_flag": 1,
                "clearance_id": 1,
                "clearance_name": "Для служебного пользования",
                "attachments": None,
                "reply_file": None,
                "has_reply": False,
                "source_employee_id": 1,
                "source_official_text": "Генеральный директор Иванов И.И."
            },
            {
                "type_id": 1,
                "status": "rejected",
                "is_read": False,
                "is_completed": True,
                "reg_number": "01-15/127",
                "seq_num": 127,
                "sent_date": "2026-06-06",
                "deadline": "2026-06-20",
                "incoming_number": None,
                "incoming_date": None,
                "parent_document_id": 2,
                "confident_flag": 0,
                "clearance_id": None,
                "clearance_name": None,
                "attachments": None,
                "reply_file": None,
                "has_reply": False,
                "source_employee_id": 6,
                "source_official_text": "Ведущий специалист Морозов М.М."
            }
        ]

        for idx, config in enumerate(doc_configs, start=1):
            doc = cls._generate_document(
                type_id=config["type_id"],
                index=idx,
                status=config["status"],
                is_read=config["is_read"],
                is_completed=config["is_completed"],
                reg_number=config["reg_number"],
                sequence_number=config["seq_num"],
                sent_date=config["sent_date"],
                deadline=config["deadline"],
                incoming_number=config.get("incoming_number"),
                incoming_date=config.get("incoming_date"),
                parent_document_id=config.get("parent_document_id"),
                confident_flag=config.get("confident_flag", 0),
                clearance_id=config.get("clearance_id"),
                clearance_name=config.get("clearance_name"),
                attachments=config.get("attachments"),
                reply_file=config.get("reply_file"),
                has_reply=config.get("has_reply", False),
                source_employee_id=config.get("source_employee_id"),
                source_organization_id=config.get("source_organization_id", 1),
                source_official_text=config.get("source_official_text", "")
            )
            cls.TEST_DATA.append(doc)

        return cls.TEST_DATA

    # ============ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ============

    def _get_tags_data(self) -> list:
        """Получает список доступных тегов из контроллера"""
        try:
            if hasattr(self.controller, 'get_tags'):
                return self.controller.get_tags()
            else:
                # Возвращаем те самые тестовые данные, которые были в DocumentDialog
                return [
                    {'id': 1, 'name': 'Срочно', 'priority': 'urgent', 'color': '#FF0000'},
                    {'id': 2, 'name': 'Важно', 'priority': 'important', 'color': '#FFA500'},
                    {'id': 3, 'name': 'Обычный', 'priority': 'normal', 'color': '#808080'},
                    {'id': 4, 'name': 'Финансы', 'priority': 'important', 'color': '#008000'},
                    {'id': 5, 'name': 'Кадры', 'priority': 'normal', 'color': '#0000FF'},
                    {'id': 6, 'name': 'Юридический', 'priority': 'normal', 'color': '#800080'},
                    {'id': 7, 'name': 'Договор', 'priority': 'urgent', 'color': '#FF4500'},
                    {'id': 8, 'name': 'Отчет', 'priority': 'important', 'color': '#2E8B57'},
                    {'id': 9, 'name': 'Технический', 'priority': 'normal', 'color': '#4169E1'},
                    {'id': 10, 'name': 'Маркетинг', 'priority': 'normal', 'color': '#FF1493'},
                ]
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка получения тегов: {e}")
            return []

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
        cls._initialize_test_data()
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
        cls._initialize_test_data()
        return [doc for doc in cls.TEST_DATA if doc.get("type_id") == type_id]

    @classmethod
    def get_documents_by_direction(cls, direction: str) -> list:
        """Получить документы по направлению"""
        cls._initialize_test_data()
        return [doc for doc in cls.TEST_DATA if doc.get("direction") == direction]

    @classmethod
    def get_types_by_direction(cls, direction: str) -> list:
        """Получить типы документов по направлению"""
        type_ids = cls.TYPE_DIRECTION_MAPPING.get(direction, [])
        return [t for t in cls.DOCUMENT_TYPES if t.get("id") in type_ids]

    @classmethod
    def get_directions_data(cls) -> list:
        """Получить данные для левой панели на основе типов документов."""
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
                        "user_fields": doc_type.get("user_fields", []),
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
        """Получить документы с полной информацией о типе."""
        cls._initialize_test_data()
        docs_with_types = []
        for doc in cls.TEST_DATA:
            doc_copy = doc.copy()
            type_info = cls.get_document_type_by_id(doc.get("type_id"))
            if type_info:
                doc_copy["type_fields"] = type_info.get("fields", [])
                doc_copy["type_user_fields"] = type_info.get("user_fields", [])
                doc_copy["type_auto_num"] = type_info.get("auto_num", False)
                doc_copy["type_smdo_code"] = type_info.get("smdo_code_type")
            docs_with_types.append(doc_copy)
        return docs_with_types

    @classmethod
    def get_columns_for_type(cls, type_id: int) -> dict:
        """
        Получить конфигурацию колонок для конкретного типа документа.
        Базовые колонки всегда есть, пользовательские и дополнительные добавляются из конфигурации.
        """
        # Базовые колонки для всех типов
        base_columns = {
            0: "ID",
            1: "Прочитано",
            2: "Номер документа",
            3: "Тема",
            4: "Тип",
            5: "Дата создания",
            6: "Статус",
            7: "Направление",
            12: "Хэштеги",
            13: "Комментарии",
            14: "Вложение",
            15: "Ответ",
            16: "Краткое содержание",
            17: "Срок исполнения"
        }

        # Добавляем пользовательские поля в зависимости от типа
        type_info = cls.get_document_type_by_id(type_id)
        if type_info:
            user_fields = type_info.get("user_fields", [])

            # Маппинг имен полей на индексы колонок
            user_field_mapping = {
                "senders": 8,
                "receivers": 9,
                "executors": 10,
                "delegates": 11
            }

            for field_name in user_fields:
                if field_name in user_field_mapping:
                    col_index = user_field_mapping[field_name]
                    col_label = cls.COLUMNS_CONFIG.get(col_index, field_name)
                    base_columns[col_index] = col_label

            # Добавляем дополнительные поля из fields
            if type_info.get("fields"):
                fields = type_info["fields"]
                for idx, field in enumerate(fields, start=20):
                    field_name = field.get("label", field.get("name", f"Поле_{idx}"))
                    base_columns[idx] = field_name

        # Сортируем колонки по индексу
        return dict(sorted(base_columns.items()))

    @classmethod
    def get_documents_response(cls, type_id: int = None, direction: str = None) -> dict:
        """Получить ответ в формате API с пагинацией."""
        cls._initialize_test_data()
        items = cls.TEST_DATA.copy()

        if type_id is not None:
            items = [doc for doc in items if doc.get("type_id") == type_id]

        if direction is not None:
            items = [doc for doc in items if doc.get("direction") == direction]

        # Фильтруем поля для каждого документа в соответствии с типом
        filtered_items = []
        for doc in items:
            type_info = cls.get_document_type_by_id(doc.get("type_id"))
            if type_info:
                user_fields = type_info.get("user_fields", [])
                # Создаем копию документа с только нужными полями
                filtered_doc = {k: v for k, v in doc.items()
                               if k not in ["senders", "senders_ids", "receivers", "receivers_ids",
                                          "executors", "executors_ids", "delegates", "delegates_ids"]}
                # Добавляем только разрешенные пользовательские поля
                for field in user_fields:
                    if field in doc:
                        filtered_doc[field] = doc[field]
                        # Добавляем ID если есть
                        id_field = f"{field}_ids"
                        if id_field in doc:
                            filtered_doc[id_field] = doc[id_field]
                filtered_items.append(filtered_doc)
            else:
                filtered_items.append(doc)

        return {
            "total": len(filtered_items),
            "limit": 20,
            "offset": 0,
            "items": filtered_items
        }

    @classmethod
    def get_document_schema(cls, type_id: int) -> dict:
        """
        Получить схему документа для конкретного типа.
        Возвращает структуру с описанием всех полей.
        """
        type_info = cls.get_document_type_by_id(type_id)
        if not type_info:
            return {}

        schema = {
            "id": {"type": "integer", "required": True},
            "type_id": {"type": "integer", "required": True},
            "type_name": {"type": "string", "required": True},
            "direction": {"type": "string", "required": True},
            "status": {"type": "string", "required": True},
            "title": {"type": "string", "required": True},
            "about": {"type": "string", "required": False},
            "reg_number": {"type": "string", "required": False},
            "sequence_number": {"type": "integer", "required": False},
            "sent_date": {"type": "date", "required": False},
            "deadline": {"type": "date", "required": False},
            "incoming_number": {"type": "string", "required": False},
            "incoming_date": {"type": "date", "required": False},
            "global_msg_id": {"type": "string", "required": False},
            "parent_document_id": {"type": "integer", "required": False},
            "confident_flag": {"type": "integer", "required": False},
            "clearance_id": {"type": "integer", "required": False},
            "clearance_name": {"type": "string", "required": False},
            "numcopy": {"type": "string", "required": False},
            "is_read": {"type": "boolean", "required": True},
            "is_completed": {"type": "boolean", "required": True},
            "created_at": {"type": "datetime", "required": True},
            "source_employee_id": {"type": "integer", "required": False},
            "source_organization_id": {"type": "integer", "required": False},
            "source_official_text": {"type": "string", "required": False},
        }

        # Добавляем пользовательские поля
        user_fields = type_info.get("user_fields", [])
        user_field_schema = {
            "senders": {"type": "array", "items": "string", "required": False},
            "senders_ids": {"type": "array", "items": "integer", "required": False},
            "receivers": {"type": "array", "items": "string", "required": False},
            "receivers_ids": {"type": "array", "items": "integer", "required": False},
            "executors": {"type": "array", "items": "string", "required": False},
            "executors_ids": {"type": "array", "items": "integer", "required": False},
            "delegates": {"type": "array", "items": "string", "required": False},
            "delegates_ids": {"type": "array", "items": "integer", "required": False},
        }

        for field in user_fields:
            if field in user_field_schema:
                schema[field] = user_field_schema[field]
                # Добавляем соответствующие ID поля
                id_field = f"{field}_ids"
                if id_field in user_field_schema:
                    schema[id_field] = user_field_schema[id_field]

        # Добавляем дополнительные поля
        for field in type_info.get("fields", []):
            field_name = field["name"]
            field_type = field.get("type", "string")
            schema[field_name] = {
                "type": field_type,
                "label": field.get("label", field_name),
                "required": False
            }

        return schema


# Инициализируем тестовые данные при загрузке модуля
DocumentDataConfig._initialize_test_data()