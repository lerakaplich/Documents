"""
Менеджер для работы с иконками
"""
import os
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import QSize, Qt


class IconManager:
    """Менеджер иконок"""

    _instance = None
    _icons = {}
    _images_dir = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._images_dir is None:
            # Определяем путь к папке с изображениями
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Поднимаемся на уровень выше: core -> client
            client_dir = os.path.dirname(os.path.dirname(current_dir))
            self._images_dir = os.path.join(client_dir, 'icons')

    def get_icon(self, icon_name: str, size: QSize = None) -> QIcon:
        """
        Получить иконку по имени

        Args:
            icon_name: имя иконки (например, 'pin')
            size: размер иконки

        Returns:
            QIcon: иконка
        """
        cache_key = f"{icon_name}_{size.width() if size else 'default'}"

        if cache_key in self._icons:
            return self._icons[cache_key]

        icon_path = os.path.join(self._images_dir, f"{icon_name}.png")

        if not os.path.exists(icon_path):
            print(f"[IconManager] Иконка не найдена: {icon_path}")
            return QIcon()

        pixmap = QPixmap(icon_path)

        if size:
            pixmap = pixmap.scaled(
                size.width(),
                size.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        icon = QIcon(pixmap)
        self._icons[cache_key] = icon
        return icon

    def get_pixmap(self, icon_name: str, size: QSize = None) -> QPixmap:
        """
        Получить QPixmap иконки

        Args:
            icon_name: имя иконки
            size: размер

        Returns:
            QPixmap: пиксельная карта
        """
        icon_path = os.path.join(self._images_dir, f"{icon_name}.png")

        if not os.path.exists(icon_path):
            print(f"[IconManager] Иконка не найдена: {icon_path}")
            return QPixmap()

        pixmap = QPixmap(icon_path)

        if size:
            pixmap = pixmap.scaled(
                size.width(),
                size.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        return pixmap


# Создаем глобальный экземпляр
icon_manager = IconManager()