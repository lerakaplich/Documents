"""Иконки-стрелки для заголовков сортируемых столбцов (рисуются в цвет темы)."""

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap, QPolygonF

_SIZE = 16
_cache: dict[tuple[str, str], QIcon] = {}


def sort_icon(kind: str, color: str) -> QIcon:
    """kind: 'none' — приглушённое ⇅, 'asc' — ▲, 'desc' — ▼."""
    key = (kind, color)
    if key in _cache:
        return _cache[key]

    pm = QPixmap(_SIZE, _SIZE)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    c = QColor(color)

    if kind == "asc":
        p.setBrush(c)
        p.drawPolygon(QPolygonF([QPointF(4, 10.5), QPointF(12, 10.5), QPointF(8, 5)]))
    elif kind == "desc":
        p.setBrush(c)
        p.drawPolygon(QPolygonF([QPointF(4, 5.5), QPointF(12, 5.5), QPointF(8, 11)]))
    else:
        c.setAlphaF(0.4)
        p.setBrush(c)
        p.drawPolygon(QPolygonF([QPointF(4.5, 6.8), QPointF(11.5, 6.8), QPointF(8, 2.5)]))
        p.drawPolygon(QPolygonF([QPointF(4.5, 9.2), QPointF(11.5, 9.2), QPointF(8, 13.5)]))
    p.end()

    icon = QIcon(pm)
    _cache[key] = icon
    return icon