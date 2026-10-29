"""
Локальный счётчик «самых частых» отправителей / получателей / исполнителей.

Хранится в settings.json под ключом "frequent_picks", отдельно для каждого
пользователя приложения:

    {"<user_id>": {"sender":   {"employee:12": {...}, "department:3001": {...}},
                   "receiver": {...},
                   "executor": {...}}}

Запись элемента: {"kind": "employee", "id": 12, "name": "Иванов И.И.",
                  "count": 5, "last": "2026-10-29T10:15:00"}
"""

from datetime import datetime
from typing import Any

from client.core.settings.settings_manager import SettingsManager

FREQUENT_KEY = "frequent_picks"

# Роли (соответствуют окнам выбора)
ROLE_SENDER = "sender"
ROLE_RECEIVER = "receiver"
ROLE_EXECUTOR = "executor"
ROLES = (ROLE_SENDER, ROLE_RECEIVER, ROLE_EXECUTOR)

# Виды элементов: сотрудник, отдел, любой другой структурный элемент
KIND_EMPLOYEE = "employee"
KIND_DEPARTMENT = "department"
KIND_ORGANIZATION = "organization"

MAX_PER_ROLE = 50   # сколько записей храним на роль (лишние с малым счётчиком отбрасываются)


class FrequentManager:
    """Подсчёт и выдача топа часто выбираемых сотрудников/отделов."""

    def __init__(self, user_id: int | None = None, settings=None):
        self._settings = settings or SettingsManager()
        if user_id is None:
            from client.core.state.app_state import AppState

            user = AppState().current_user or {}
            user_id = user.get("id", 0)
        self._uid = str(user_id)

    # ───────── внутреннее ─────────

    @staticmethod
    def _key(kind: str, entity_id: Any) -> str:
        return f"{kind}:{entity_id}"

    def _load(self) -> dict:
        return dict(self._settings.get(FREQUENT_KEY, {}) or {})

    def _role_data(self, all_data: dict, role: str) -> dict:
        return all_data.setdefault(self._uid, {}).setdefault(role, {})

    # ───────── запись ─────────

    def record(self, role: str, items: list[dict]) -> None:
        """
        Учесть выбор. Вызывать ОДИН раз, когда документ реально сохранён/отправлен
        (а не при открытии/отмене диалога).

        items: [{"kind": "employee", "id": 12, "name": "Иванов И.И."}, ...]
        Один и тот же элемент в одном вызове считается один раз.
        """
        if role not in ROLES or not items:
            return

        all_data = self._load()
        bucket = self._role_data(all_data, role)
        now = datetime.now().isoformat(timespec="seconds")

        seen = set()
        for it in items:
            kind, eid = it.get("kind"), it.get("id")
            if not kind or eid is None:
                continue
            key = self._key(kind, eid)
            if key in seen:
                continue
            seen.add(key)

            rec = bucket.get(key) or {"kind": kind, "id": eid, "count": 0}
            rec["count"] += 1
            rec["last"] = now
            if it.get("name"):
                rec["name"] = it["name"]          # обновляем имя на актуальное
            if it.get("org_id") is not None:
                rec["org_id"] = it["org_id"]      # организация элемента (для ленивой подгрузки)
            bucket[key] = rec

        # ограничение размера: оставляем самые частые/свежие
        if len(bucket) > MAX_PER_ROLE:
            keep = sorted(bucket.items(), key=lambda kv: (kv[1]["count"], kv[1]["last"]), reverse=True)
            all_data[self._uid][role] = dict(keep[:MAX_PER_ROLE])

        self._settings.set(FREQUENT_KEY, all_data)

    # ───────── чтение ─────────

    def top(self, role: str, limit: int = 5, kinds: set[str] | None = None) -> list[dict]:
        """Топ часто выбираемых для роли: по убыванию счётчика, при равенстве — свежие выше.
        kinds — ограничить видами (например {"employee"}), None — все."""
        bucket = (self._load().get(self._uid, {}) or {}).get(role, {}) or {}
        recs = [r for r in bucket.values() if not kinds or r.get("kind") in kinds]
        recs.sort(key=lambda r: (r.get("count", 0), r.get("last", "")), reverse=True)
        return recs[:limit]

    # ───────── обслуживание ─────────

    def forget(self, kind: str, entity_id: Any, role: str | None = None) -> None:
        """Убрать элемент из счётчиков (например, сотрудник удалён/уволен)."""
        all_data = self._load()
        user_data = all_data.get(self._uid, {})
        for r in ([role] if role else list(user_data)):
            user_data.get(r, {}).pop(self._key(kind, entity_id), None)
        self._settings.set(FREQUENT_KEY, all_data)

    def clear(self, role: str | None = None) -> None:
        all_data = self._load()
        if role:
            all_data.get(self._uid, {}).pop(role, None)
        else:
            all_data.pop(self._uid, None)
        self._settings.set(FREQUENT_KEY, all_data)
