# client/core/data/document_mapper.py
"""
Адаптер между ответом сервера GET /documents/documents/ (DocumentListItem)
и форматом словаря, который ожидают RowRenderer и билдеры ячеек таблицы
(client/windows/documents/table/builders/row_renderer.py, cell_builders.py).

Он существует только потому, что таблица исторически писалась под тестовые
данные (client/core/data/document_data.py: TEST_DATA) с другими именами
полей. Как только реестр окончательно перейдёт на реальный API, часть этого
маппинга можно будет убрать, переименовав ключи прямо в RowRenderer.

ЧТО ТОЧНО СОВПАДАЕТ И НЕ ТРЕБУЕТ ПРЕОБРАЗОВАНИЯ:
    id, is_read, is_pinned, is_archived, has_attachments, reply_id,
    title, about, reg_number, status, direction, deadline, type_name,
    last_comment_text, tags (ключи name/color внутри тегов уже совпадают
    с тем, что ждёт TagsCellBuilder).

ЧТО ПЕРЕИМЕНОВЫВАЕТСЯ:
    sent_date      -> created_at   (колонка "Дата создания")
    sender (dict)  -> senders (list[dict])   (колонка "Отправители")
    recipients     -> receivers              (колонка "Получатели")

ЧТО ПОКА НЕ РЕШЕНО (см. TODO ниже) — не гадаем, оставляем пусто/False,
чтобы не показать пользователю неверные данные:
    executors  — фильтруется по role == "executor", это ДОГАДКА (не
        подтверждена в DocumentRole). delegates используют role == "delegate",
        это подтверждено докстрингом на сервере (см. document_mapper.py).
    attachments, reply_file — реестр отдаёт только флаги has_attachments
        и reply_id, полного списка файлов тут нет. Реальный список теперь
        подгружается лениво по клику через AttachmentService.get_attachments()
        (см. cell_builders.AttachmentCellBuilder) — не через этот маппер,
        т.к. дёргать вложения для каждой строки сразу при рендере таблицы
        значит по одному HTTP-запросу на строку. reply_file по-прежнему
        не решён: сервер отдаёт только reply_id (число), а не объект ответа.
    comments — список комментариев реестр не отдаёт, только
        last_comment_text. Оставляем [] — этого достаточно, т.к.
        CommentsCellBuilder показывает last_comment_text напрямую
        (см. правку в cell_builders.py).
"""
from typing import Any, Dict, List, Optional

# TODO(бэкенд): значение "delegate" подтверждено докстрингом
# UnansweredDocumentStat.assignees на сервере ("ФИО Получателей (recipient)
# и Делегатов (delegate)"). Значение "executor" НЕ подтверждено — сам enum
# DocumentRole (server/app/database/document_models.py) не проверялся.
EXECUTOR_ROLES = {"executor"}  # ⚠ догадка, сверить с DocumentRole
DELEGATE_ROLES = {"delegate"}  # подтверждено докстрингом на сервере


def map_document_list_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Приводит один DocumentListItem к формату, ожидаемому таблицей."""
    sender = item.get("sender")
    senders: List[Dict[str, Any]] = [sender] if sender else []

    participants = item.get("participants") or []
    executors = [p for p in participants if p.get("role") in EXECUTOR_ROLES]
    delegates = [p for p in participants if p.get("role") in DELEGATE_ROLES]

    mapped = dict(item)  # копия — не мутируем то, что вернул http_client
    mapped["created_at"] = item.get("sent_date")
    mapped["senders"] = senders
    mapped["receivers"] = item.get("recipients", [])
    mapped["executors"] = executors
    mapped["delegates"] = delegates
    mapped["comments"] = []
    mapped["attachments"] = []
    mapped["reply_file"] = None
    return mapped


def map_documents_response(response: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Разворачивает {"total", "limit", "offset", "items": [...]} в список строк таблицы."""
    if not response:
        return []
    items = response.get("items", []) if isinstance(response, dict) else response
    return [map_document_list_item(item) for item in (items or [])]