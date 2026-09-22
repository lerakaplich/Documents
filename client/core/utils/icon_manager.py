"""
Менеджер для работы с иконками (с поддержкой перекраски под тему).
"""
import os

from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import QSize, Qt


class IconManager:
    """Менеджер иконок (singleton)."""

    _instance = None
    _icons = {}
    _images_dir = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._images_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            client_dir = os.path.dirname(os.path.dirname(current_dir))
            self._images_dir = os.path.join(client_dir, "icons")

    # ── публичное API ────────────────────────────────────────────────

    def get_icon(self, icon_name: str, size: QSize = None,
                 color: str = None) -> QIcon:
        """
        Получить иконку по имени.

        Если color не передан — берётся цвет из текущей темы
        (ICON_PIN_COLOR для 'pin', иначе ICON_COLOR).
        """
        if color is None:
            color = self._default_color_for(icon_name)

        cache_key = self._key(icon_name, size, color)
        if cache_key in self._icons:
            return self._icons[cache_key]

        path = self._resolve_path(icon_name, color)
        if not path:
            return QIcon()

        pixmap = QPixmap(path)
        if size:
            pixmap = pixmap.scaled(
                size.width(), size.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        ic = QIcon(pixmap)
        self._icons[cache_key] = ic
        return ic

    def get_pixmap(self, icon_name: str, size: QSize = None,
                   color: str = None) -> QPixmap:
        if color is None:
            color = self._default_color_for(icon_name)
        path = self._resolve_path(icon_name, color)
        if not path:
            return QPixmap()

        pixmap = QPixmap(path)
        if size:
            pixmap = pixmap.scaled(
                size.width(), size.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return pixmap

    @staticmethod
    def _default_color_for(icon_name: str) -> str:
        """Цвет по умолчанию из активной темы."""
        try:
            from client.core.themes import get_manager
            t = get_manager().current
            if icon_name == "pin":
                return t.ICON_PIN_COLOR
            return t.ICON_COLOR
        except Exception:
            return None

    def clear_cache(self):
        """Сбросить кэш — вызывать после set_theme()."""
        self._icons.clear()

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _key(icon_name: str, size: QSize, color: str) -> str:
        w = size.width() if size else "default"
        c = color or "orig"
        return f"{icon_name}_{w}_{c}"

    def _resolve_path(self, icon_name: str, color: str) -> str:
        """Возвращает путь к SVG: перекрашенный (если color) или оригинальный."""
        if color:
            try:
                from client.core.themes.icon_utils import _recolored_svg_path
                return _recolored_svg_path(icon_name, color)
            except Exception as e:
                print(f"[IconManager] перекраска не удалась: {e}")

        path = os.path.join(self._images_dir, f"{icon_name}.svg")
        if not os.path.exists(path):
            print(f"[IconManager] Иконка не найдена: {path}")
            return ""
        return path


# Глобальный экземпляр
icon_manager = IconManager()