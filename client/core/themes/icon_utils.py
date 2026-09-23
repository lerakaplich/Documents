"""Перекраска SVG-иконок под цвет темы (с кэшем в %TEMP%)."""
import hashlib
import os
import re
import tempfile

import PyQt6.QtSvg  # noqa: F401
from PyQt6.QtGui import QIcon


_SHAPE_TAGS = ("path", "rect", "circle", "ellipse", "polygon", "polyline", "line")

_CACHE_DIR = os.path.join(tempfile.gettempdir(), "maz_icons")
os.makedirs(_CACHE_DIR, exist_ok=True)

_ICON_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "icons")
)


_FILL_RE   = re.compile(r'fill="[^"]*"')
_STROKE_RE = re.compile(r'stroke="[^"]*"')     # ← БЕЗ (?!none) — обрабатываем вручную


def _recolored_svg_path(name: str, color: str) -> str:
    fname = name if name.endswith(".svg") else f"{name}.svg"

    # Чекбоксы генерируем сами — не парсим исходники.
    if fname == "cb_checked.svg":
        data = _generate_checkbox_svg(checked=True, color=color)
    elif fname == "cb_unchecked.svg":
        data = _generate_checkbox_svg(checked=False, color=color)
    elif fname == "cb_partial.svg":
        data = _generate_checkbox_svg(checked=None, color=color)
    else:
        src = os.path.join(_ICON_DIR, fname)
        if not os.path.exists(src):
            return src.replace("\\", "/")
        with open(src, "r", encoding="utf-8") as f:
            data = f.read()
        data = _recolor_regular(data, color)

    key = hashlib.md5(f"{fname}_{color}_{data}".encode()).hexdigest()[:12]
    out = os.path.join(_CACHE_DIR, f"{os.path.splitext(fname)[0]}_{key}.svg")
    if not os.path.exists(out):
        with open(out, "w", encoding="utf-8") as f:
            f.write(data)
    return out.replace("\\", "/")

def _generate_checkbox_svg(checked, color: str) -> str:
    """
    checked=True   → залитый квадрат + белая галочка
    checked=False  → прозрачный квадрат + обводка цветом темы
    checked=None   → залитый квадрат + белый «минус»
    """
    if checked is False:
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 18 18" width="18" height="18">
  <rect x="1.5" y="1.5" width="15" height="15" rx="3.5" ry="3.5"
        fill="none" stroke="{color}" stroke-width="1.8"/>
</svg>'''

    if checked is None:
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 18 18" width="18" height="18">
  <rect x="1" y="1" width="16" height="16" rx="3.5" ry="3.5" fill="{color}"/>
  <path d="M5 9 H13" fill="none" stroke="#ffffff" stroke-width="2.2"
        stroke-linecap="round"/>
</svg>'''

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 18 18" width="18" height="18">
  <rect x="1" y="1" width="16" height="16" rx="3.5" ry="3.5" fill="{color}"/>
  <path d="M4.5 9 L7.5 12 L13.5 5.5" fill="none" stroke="#ffffff"
        stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''

def _recolor_regular(data: str, color: str) -> str:
    """Обычные иконки: все fill / stroke (кроме 'none') → color."""
    def _fill(m):
        return m.group(0) if 'none' in m.group(0) else f'fill="{color}"'
    def _stroke(m):
        return m.group(0) if 'none' in m.group(0) else f'stroke="{color}"'

    data = _FILL_RE.sub(_fill, data)
    data = _STROKE_RE.sub(_stroke, data)
    return data



def icon_path(name: str, color: str) -> str:
    """
    Путь к SVG для QSS: url(...).

    Возвращает путь В КАВЫЧКАХ — Qt QSS не парсит пути
    с ':' и '/' внутри url() без кавычек.
    """
    return f'"{_recolored_svg_path(name, color)}"'


def icon(name: str, color: str) -> QIcon:
    return QIcon(_recolored_svg_path(name, color))