# client/windows/system/common.py
"""Общие хелперы вкладок «Система»: склонения, бейджи, hover-кнопки, нормализация сотрудника."""

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel

from client.core.themes import T


def plural_ru(n: int, forms: tuple[str, str, str]) -> str:
    """plural_ru(5, ("документ", "документа", "документов")) -> "документов"."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]


def count_text(n: int, forms: tuple[str, str, str]) -> str:
    return f"{n} {plural_ru(n, forms)}"


def badge_style(kind: str = "neutral") -> str:
    """QSS бейджа-«таблетки». kind: ok | bad | neutral."""
    if kind == "ok":
        fg, bg, border = T.TEXT_SUCCESS, "transparent", T.TEXT_SUCCESS
    elif kind == "bad":
        fg, bg, border = T.TEXT_DANGER, "transparent", T.TEXT_DANGER
    else:
        fg, bg, border = T.CHIP_TEXT, T.CHIP_BG, T.CHIP_BG
    return (
        f"color: {fg}; background-color: {bg}; border: 1px solid {border};"
        "border-radius: 10px; padding: 1px 9px; font-size: 11px; font-weight: 600;"
    )


def initials(full_name: str) -> str:
    parts = [p for p in (full_name or "").replace(".", " ").split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def make_avatar(full_name: str, size: int = 28) -> QLabel:
    lbl = QLabel(initials(full_name))
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(
        f"background-color: {T.BG_HOVER_ACCENT_SOFT}; color: {T.ACCENT_PRIMARY};"
        f"border: none; border-radius: {size // 2}px; font-size: 11px; font-weight: bold;"
    )
    return lbl


class HoverActionsMixin:
    """Кнопки действий карточки проявляются при наведении (layout не «прыгает»).

    class MyCard(HoverActionsMixin, QFrame): ...
    self.init_hover_actions(self.editBtn, self.deleteBtn)
    """

    def init_hover_actions(self, *widgets):
        self._hover_effects = []
        for w in widgets:
            effect = QGraphicsOpacityEffect(w)
            effect.setOpacity(0.0)
            w.setGraphicsEffect(effect)
            self._hover_effects.append(effect)

    def _set_actions_opacity(self, value: float):
        for effect in getattr(self, "_hover_effects", []):
            effect.setOpacity(value)

    def enterEvent(self, event):
        self._set_actions_opacity(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_actions_opacity(0.0)
        super().leaveEvent(event)


# ---------------------------------------------------------------------------
# Нормализация сотрудника из API.
# ВАЖНО: точная форма ответа /employees/all и /org/{id}/employees мне неизвестна,
# поэтому ключи перебираются «с запасом». Когда пришлёте один реальный объект
# (его печатает [DEBUG] sample employee в EmployeeService) — оставлю только нужные.
# ---------------------------------------------------------------------------


def _name_of(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("name") or value.get("short_name") or value.get("full_name") or ""
    return value or ""


def _id_of(value: Any, fallback: Any = None):
    return value.get("id") if isinstance(value, dict) else fallback


def normalize_employee(raw: dict[str, Any]) -> dict[str, Any]:
    full_name = raw.get("full_name") or raw.get("fio") or " ".join(
        p
        for p in (
            raw.get("last_name") or raw.get("surname"),
            raw.get("first_name") or raw.get("name"),
            raw.get("middle_name") or raw.get("patronymic"),
        )
        if p
    )

    positions = []
    for p in raw.get("positions") or []:
        if not isinstance(p, dict):
            continue
        dep = p.get("department")
        org = p.get("organization")
        positions.append(
            {
                "position": _name_of(p.get("position") or p.get("position_name") or p.get("title") or p.get("name")),
                "department": _name_of(dep) or p.get("department_name") or "",
                "department_id": _id_of(dep, p.get("department_id")),
                "organization": _name_of(org) or p.get("organization_name") or "",
                "organization_id": _id_of(org, p.get("organization_id")),
            }
        )
    if not positions and (raw.get("position") or raw.get("department") or raw.get("department_name")):
        dep = raw.get("department")
        org = raw.get("organization")
        positions.append(
            {
                "position": _name_of(raw.get("position") or raw.get("position_name")),
                "department": _name_of(dep) or raw.get("department_name") or "",
                "department_id": _id_of(dep, raw.get("department_id")),
                "organization": _name_of(org) or raw.get("organization_name") or "",
                "organization_id": _id_of(org, raw.get("organization_id")),
            }
        )

    first = positions[0] if positions else {}
    return {
        "id": raw.get("id"),
        "full_name": full_name or "—",
        "phone": raw.get("phone_number") or raw.get("phone") or raw.get("internal_phone") or "",
        "email": raw.get("email") or "",
        "role": _name_of(raw.get("role")) or "",
        "positions": positions,
        "position": first.get("position", ""),
        "department": first.get("department", ""),
        "organization": first.get("organization", "") or _name_of(raw.get("organization")),
        "raw": raw,
    }
