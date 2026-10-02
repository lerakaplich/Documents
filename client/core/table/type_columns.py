"""Какие столбцы таблицы выключены у типа документа (types.fields)."""

# Столбец → ключи в types.fields: серверные и из диалога типа («Система»)
TYPE_COLUMNS = {
    "Тема": ("title", "subject"),
    "Краткое содержание": ("about", "regarding"),
    "Отправители": ("sender_id", "from_who"),
    "Получатели": ("recipients", "to_who"),
    "Исполнители": ("executors", "executor"),
    "Хэштеги": ("tag_ids", "tag_id"),
    "Дата создания": ("sent_date", "send_date"),
    "Срок исполнения": ("deadline",),
    "Номер документа": ("reg_number", "number"),
    "Порядковый номер": ("sequence_number", "index_number"),
    "Статус": ("status_id",),
    "Вложение": ("attachment",),
    "Ответ": ("has_answer",),
    "Комментарии": ("comments",),
    "Направление": ("direction_name",),
}


def disabled_columns(fields) -> set[str]:
    """Столбцы, выключенные у типа.

    Конфиг типа бывает двух видов:
      • из диалога «Система» — хранит ТОЛЬКО включённые поля и всегда содержит
        обязательные attachment/redirect: отсутствие ключа = поле выключено;
      • серверный — ключи с явными true/false: столбцы, которых в нём нет,
        остаются видимыми.
    Пустой конфиг — всё включено."""
    if not isinstance(fields, dict) or not fields:
        return set()

    dialog_style = "attachment" in fields or "redirect" in fields
    disabled = set()
    for column, keys in TYPE_COLUMNS.items():
        if any(fields.get(k) for k in keys):
            continue
        if dialog_style or any(k in fields for k in keys):
            disabled.add(column)
    return disabled