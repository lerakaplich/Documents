# client/services/document_service.py

from typing import Optional, List, Dict, Any
from datetime import datetime
from client.core.http_client import HttpClient

# Поля, обязательные по контракту POST /documents (DocumentCreateForm).
# Ключ -> сообщение, которое покажем пользователю, если поле не заполнено.
REQUIRED_FIELDS_MESSAGES = {
    "type_id": "Выберите тип документа",
    "direction": "Выберите направление документа (внутренний/внешний)",
    "global_msg_id": "Не удалось сформировать идентификатор сообщения (global_msg_id)",
}
# Примечание: sender_id намеренно НЕ входит в обязательные — по конфигу
# типов документа (`types.fields.sender_id`) для части типов (например,
# "Приказы") поле отправителя не используется вовсе.


def validate_create_payload(payload: Dict[str, Any]) -> List[str]:
    """
    Локальная (клиентская) проверка payload'а перед отправкой на сервер,
    чтобы не ждать 422 от FastAPI и показать понятную ошибку сразу.
    """
    errors = []
    for field, message in REQUIRED_FIELDS_MESSAGES.items():
        if payload.get(field) in (None, ""):
            errors.append(message)
    return errors


class DocumentService:
    def __init__(self, http_client: HttpClient):
        self.client = http_client
        # ВАЖНО: 404 на POST /documents почти наверняка означает, что
        # реальный путь другой — по структуре сервера файл документов лежит
        # в server/app/api/doc/documents.py (в отличие от, например, типов —
        # server/app/api/types.py), значит роутер документов, скорее всего,
        # подключён в main.py с дополнительным префиксом (например,
        # "/doc/documents" или похожим). Проверьте include_router(...) для
        # documents в server/app/main.py и поправьте base_path здесь.
        self.base_path = "/documents/documents"

    # ─────────── ЧТЕНИЕ ───────────
    def get_all_documents(self) -> List[Dict[str, Any]]:
        try:
            r = self.client.get(self.base_path)
            return r.get("items", []) if isinstance(r, dict) else r
        except Exception as e:
            print(f"❌ get_all_documents: {e}")
            return []

    def get_document_by_id(self, document_id: int) -> Optional[Dict[str, Any]]:
        try:
            return self.client.get(f"{self.base_path}/{document_id}")
        except Exception as e:
            print(f"❌ get_document_by_id({document_id}): {e}")
            return None

    # ─────────── СОЗДАНИЕ ───────────
    def create_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._build_create_payload(data)
        errors = validate_create_payload(payload)
        if errors:
            raise ValueError("; ".join(errors))
        print(f"📤 POST /documents/ payload: {payload}")
        return self.client.post(f"{self.base_path}/", json=payload)  # ← добавили "/"

    def get_proposed_number(self, type_id: int, direction: str) -> Optional[str]:
        try:
            r = self.client.get(
                f"{self.base_path}/proposed-number",
                params={"type_id": type_id, "direction": direction},
            )
            return r.get("proposed_number") if isinstance(r, dict) else None
        except Exception as e:
            print(f"❌ get_proposed_number: {e}")
            return None

    def mark_as_read(self, document_ids: List[int]) -> Dict[str, Any]:
        try:
            return self.client.post(f"{self.base_path}/mark-read", json={"doc_ids": document_ids})
        except Exception as e:
            print(f"❌ mark_as_read: {e}")
            return {"marked_count": 0}

    # ─────────── МАППИНГ UI → СЕРВЕР ───────────

    @staticmethod
    def _build_create_payload(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Принимает плоский dict из DocumentDialog.save_document().
        Возвращает тело для POST /documents по контракту DocumentCreateForm.
        """

        def _iso(v):
            if not v:
                return None
            if hasattr(v, "toString"):                       # QDate
                return v.toString("yyyy-MM-dd")
            if isinstance(v, str) and len(v) >= 10 and v[4] == "-":
                return v
            try:
                return datetime.strptime(v, "%d.%m.%Y").date().isoformat()
            except Exception:
                return v

        # ── Получатели ──
        # UI отдаёт плоский список ID. Разделяем по типу через справочники,
        # которые прокидывает диалог: data["_orgs"], data["_depts"], data["_emps"].
        orgs   = {o["id"] for o in (data.get("_orgs")   or []) if "id" in o}
        depts  = {d["id"] for d in (data.get("_depts")  or []) if "id" in d}
        emps   = {e["id"] for e in (data.get("_emps")   or []) if "id" in e}

        receivers_payload: List[Dict[str, Any]] = []
        for node_id in (data.get("receiver_ids") or []):
            if node_id in depts:
                receivers_payload.append({
                    "target_department_id": node_id,
                    "target_organization_id": None,
                    "target_official_text": None,
                })
            elif node_id in orgs:
                receivers_payload.append({
                    "target_department_id": None,
                    "target_organization_id": node_id,
                    "target_official_text": None,
                })
            elif node_id in emps:
                # В `document_receivers` нет employee_id — по контракту
                # сотрудник как получатель не выражается. Скипаем.
                print(f"[DocumentService] ⚠️ сотрудник-получатель id={node_id} пропущен")
            else:
                print(f"[DocumentService] ⚠️ неизвестный получатель id={node_id}")

        # ── Исполнители ──
        # В employee_document.role исполнителем может быть только сотрудник,
        # поэтому если в executor_ids случайно попал id организации/отдела
        # (диалог выбора общий для орг/отделов/сотрудников) — отсекаем его,
        # а не отправляем на сервер как есть.
        raw_executors = list(data.get("executor_ids") or [])
        if emps:
            executors_payload = [eid for eid in raw_executors if eid in emps]
            skipped = [eid for eid in raw_executors if eid not in emps]
            if skipped:
                print(f"[DocumentService] ⚠️ исполнители пропущены (не сотрудники): {skipped}")
        else:
            # Справочник сотрудников не передан — доверяем списку как есть.
            executors_payload = raw_executors

        # ── Теги ──
        tags_raw = data.get("tags") or []
        if tags_raw and isinstance(tags_raw[0], dict):
            tag_ids = [t["id"] for t in tags_raw if t.get("id")]
        else:
            tag_ids = [int(x) for x in tags_raw if str(x).isdigit()]

        # ── Сборка ──
        payload: Dict[str, Any] = {
            "type_id": data.get("type_id"),
            "direction": data.get("direction"),
            "title": (data.get("title") or "").strip(),
            "about": (data.get("about") or "").strip() or None,
            "reg_number": (data.get("reg_number") or "").strip() or None,
            "sequence_number": data.get("sequence_number"),
            "deadline": _iso(data.get("deadline")),
            "incoming_number": (data.get("incoming_number") or "").strip() or None,
            "incoming_date": _iso(data.get("incoming_date")),
            "global_msg_id": data.get("global_msg_id"),
            "parent_document_id": data.get("parent_document_id"),
            "confident_flag": int(data.get("confident_flag", 0)),
            "clearance_id": data.get("clearance_id"),
            "source_employee_id": data.get("source_employee_id"),
            "source_organization_id": data.get("source_organization_id"),
            "source_official_text": (data.get("source_official_text") or "").strip() or None,
            "sender_id": data.get("sender_id"),
            "executors": executors_payload,
            "receivers": receivers_payload,
            "tag_ids": tag_ids,
            "needs_response": bool(data.get("needs_response", False)),
        }

        # Чистим None только для НЕобязательных
        optional_none_ok = {
            "about", "reg_number", "sequence_number", "deadline",
            "incoming_number", "incoming_date", "parent_document_id",
            "clearance_id", "source_employee_id", "source_organization_id",
            "source_official_text", "sender_id",
        }
        for k in list(payload.keys()):
            if payload[k] is None and k in optional_none_ok:
                payload.pop(k)

        return payload

    def get_unanswered_stats(self) -> List[Dict[str, Any]]:
        """GET /documents/documents/stats/unanswered."""
        try:
            r = self.client.get(f"{self.base_path}/stats/unanswered")
            if isinstance(r, list):
                return r
            return []
        except Exception as e:
            print(f"❌ get_unanswered_stats: {e}")
            return []