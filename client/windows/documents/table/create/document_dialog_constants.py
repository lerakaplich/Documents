# client/windows/documents/table/create/document_dialog_constants.py
"""
Константы диалога создания/редактирования документа
"""

# Реальные направления документа (server: enum public.doc_direction).
# ВАЖНО: на сервере только 2 значения — 'internal' и 'external'.
# (в БД нет отдельных 'incoming'/'outgoing' — это старое, неверное
# предположение, которое было в UI раньше)
DIRECTIONS = [
    ("internal", "Внутренний документ"),
    ("external", "Внешний документ"),
]

# ключ поля из types.fields → виджеты, которые он включает/выключает
SIMPLE_FIELDS = {
    "title": ("topic_edit",),
    "about": ("regarding_edit",),
    "sender_id": ("btn_sender", "btnAddSender"),
    "recipients": ("btn_receiver", "btnAddReceiver"),
    "executors": ("btnExecutor", "btnAddExecutor"),
    "tag_ids": ("btn_tag", "btnAddTag"),
    "needs_response": ("needs_response_check",),
}

# Две строки по две «ячейки»: (ключ поля, layout ячейки, её виджеты).
# Имена layout'ов в .ui обманчивы: в verticalLayoutDate_2 лежит порядковый номер,
# в verticalLayoutDeadline_2 — номер документа.
CELL_ROWS = (
    (
        ("sequence_number", "verticalLayoutDate_2", ("labelIndexNumber", "index_number_edit")),
        ("reg_number", "verticalLayoutDeadline_2", ("labelNumber", "number_edit")),
    ),
    (
        ("sent_date", "verticalLayoutDate", ("labelDate", "date_edit")),
        ("deadline", "verticalLayoutDeadline", ("labelDeadline", "date_deadline")),
    ),
)
ROW_LAYOUTS = ("horizontalLayoutDates_2", "horizontalLayoutDates")

# Заголовок блока виден, только если виден хотя бы один его пункт
HEADER_BLOCKS = {
    "labelContent": ("about", "title"),
    "labelParticipants": ("sender_id", "recipients", "executors"),
    "labelTags": ("tag_ids",),
}

# Обязательные поля: показываются всегда, независимо от types.fields
ALWAYS_VISIBLE = frozenset({"sequence_number", "reg_number", "needs_response"})

# Ключ поля в диалоге документа → ключи в types.fields (серверные и из диалога типа)
FIELD_ALIASES = {
    "title": ("title", "subject"),
    "about": ("about", "regarding"),
    "sender_id": ("sender_id", "from_who"),
    "recipients": ("recipients", "to_who"),
    "executors": ("executors", "executor"),
    "tag_ids": ("tag_ids", "tag_id"),
    "sent_date": ("sent_date", "send_date"),
    "deadline": ("deadline",),
    "reg_number": ("reg_number", "number"),
    "sequence_number": ("sequence_number", "index_number"),
    "needs_response": ("needs_response",),
}