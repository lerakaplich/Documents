# client/core/utils/window_size.py
"""
Запоминание размера окон/диалогов между запусками (SettingsManager, ключ "window_sizes").

Использование в диалоге:
    restore_window_size(self, "employee_dialog", default=(675, 820))   # в __init__
    save_window_size(self, "employee_dialog")                          # в done()/closeEvent()
"""

from client.core.settings.settings_manager import SettingsManager

SETTINGS_KEY = "window_sizes"
SCREEN_MARGIN = 40  # запас от краёв экрана, чтобы окно не уезжало за видимую область


def restore_window_size(window, name: str, default: tuple[int, int] = (800, 600)) -> None:
    """Ставит сохранённый размер (или default), не выходя за экран и не меньше minimumSize."""
    saved = (SettingsManager().get(SETTINGS_KEY, {}) or {}).get(name) or {}
    try:
        width = int(saved.get("w", default[0]))
        height = int(saved.get("h", default[1]))
    except (TypeError, ValueError):
        width, height = default

    screen = window.screen()
    if screen is not None:
        avail = screen.availableGeometry()
        width = min(width, avail.width() - SCREEN_MARGIN)
        height = min(height, avail.height() - SCREEN_MARGIN)

    width = max(width, window.minimumWidth())
    height = max(height, window.minimumHeight())
    window.resize(width, height)


def save_window_size(window, name: str) -> None:
    """Сохраняет текущий размер (развёрнутое/полноэкранное окно не запоминаем)."""
    if window.isMaximized() or window.isFullScreen():
        return
    sizes = dict(SettingsManager().get(SETTINGS_KEY, {}) or {})
    sizes[name] = {"w": window.width(), "h": window.height()}
    SettingsManager().set(SETTINGS_KEY, sizes)
