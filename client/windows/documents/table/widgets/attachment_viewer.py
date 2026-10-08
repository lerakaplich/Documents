# client/windows/documents/table/widgets/attachment_viewer.py
"""
Постраничный просмотрщик вложений (TIFF / PDF).

Каждое вложение открывается в своём окне — можно держать открытыми несколько
документов одновременно и сравнивать их. Повторное открытие того же вложения
не плодит окно, а выводит уже открытое на передний план.

Страницы приходят с сервера готовыми JPEG (GET /documents/attachments/{id}/page/{n},
нумерация с 1) и грузятся в фоне: окно открывается сразу, следующая страница
подгружается заранее, последние страницы кэшируются.

Управление: ◀ ▶ / PgUp / PgDn / стрелки влево-вправо — страницы; Home / End — первая
и последняя; Ctrl + колесо, «+» / «−» — масштаб; Ctrl+0 — по ширине; Ctrl+1 — 100 %;
Ctrl+R — повернуть; левая кнопка мыши — перетаскивание увеличенной страницы.
"""

import itertools
import logging
import math
from collections import OrderedDict

from PyQt6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QKeySequence, QPixmap, QShortcut, QTransform
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from client.core.themes import get_manager

logger = logging.getLogger(__name__)

VIEWABLE_EXTENSIONS = {"tif", "tiff", "pdf"}
CACHE_PAGES = 4  # сколько декодированных страниц держим в памяти на окно
MIN_SCALE, MAX_SCALE = 0.1, 6.0
ZOOM_STEP = 1.25
MAX_PIXELS = 40_000_000  # потолок размера отрисовываемой страницы (защита памяти при большом зуме)

_pool = QThreadPool()
_pool.setMaxThreadCount(3)  # общий пул на все окна просмотра

_open_windows: dict = {}
_anon_ids = itertools.count(1)


def is_viewable(file_name: str | None) -> bool:
    """Умеет ли просмотрщик открыть файл с таким именем."""
    if not file_name or "." not in file_name:
        return False
    return file_name.lower().rsplit(".", 1)[-1] in VIEWABLE_EXTENSIONS


# ───────────────────────── фоновые задачи ─────────────────────────


class _ViewerSignals(QObject):
    counted = pyqtSignal(int)  # число страниц
    page_loaded = pyqtSignal(int, object)  # номер страницы, QImage
    failed = pyqtSignal(int, str)  # номер страницы (0 — не удалось получить число страниц), текст


class _CountTask(QRunnable):
    def __init__(self, service, attachment_id, signals):
        super().__init__()
        self._service = service
        self._attachment_id = attachment_id
        self._signals = signals

    def run(self):
        try:
            total = self._service.get_page_count(self._attachment_id)
            if not total:
                raise ValueError("Не удалось определить число страниц вложения")
            self._signals.counted.emit(int(total))
        except Exception as e:  # noqa: BLE001
            self._signals.failed.emit(0, str(e))


class _PageTask(QRunnable):
    def __init__(self, service, attachment_id, page, signals):
        super().__init__()
        self._service = service
        self._attachment_id = attachment_id
        self._page = page
        self._signals = signals

    def run(self):
        from PyQt6.QtGui import QImage  # QImage безопасен для декодирования вне GUI-потока

        try:
            data = self._service.get_page_image(self._attachment_id, self._page)
            image = QImage.fromData(data)
            if image.isNull():
                raise ValueError("Сервер вернул не изображение")
            self._signals.page_loaded.emit(self._page, image)
        except Exception as e:  # noqa: BLE001
            self._signals.failed.emit(self._page, str(e))


# ───────────────────────── область страницы ─────────────────────────


class _PageView(QScrollArea):
    """QScrollArea с Ctrl+колесо (масштаб) и перетаскиванием мышью."""

    zoom_step = pyqtSignal(int)  # +1 / -1

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QFrame.Shape.NoFrame)
        # Вертикальная полоса всегда на месте: «по ширине» не прыгает при её появлении
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_step.emit(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            pos = event.position().toPoint()
            delta = pos - self._drag_pos
            self._drag_pos = pos
            h, v = self.horizontalScrollBar(), self.verticalScrollBar()
            h.setValue(h.value() - delta.x())
            v.setValue(v.value() - delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


# ───────────────────────── окно просмотра ─────────────────────────


class AttachmentViewerWindow(QWidget):
    _cascade = 0

    def __init__(self, service, document: dict, attachment: dict):
        super().__init__(None)  # без родителя — самостоятельное окно
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self._service = service
        self._attachment_id = attachment.get("id")
        self._total: int | None = None
        self._current = 1
        self._cache: OrderedDict[int, QPixmap] = OrderedDict()
        self._inflight: set[int] = set()
        self._rotation = 0
        self._mode = "width"  # "width" | "page" | "manual"
        self._zoom = 1.0  # для режима "manual"
        self._scale = 1.0  # фактический масштаб последней отрисовки
        self._rotated = None  # (page, rotation, pixmap)

        name = attachment.get("file_name") or attachment.get("name") or "Вложение"
        ref = document.get("reg_number") or document.get("title") or document.get("id")
        self.setWindowTitle(f"{name} — {ref}" if ref else name)

        self._signals = _ViewerSignals()
        self._signals.counted.connect(self._on_counted)
        self._signals.page_loaded.connect(self._on_page_loaded)
        self._signals.failed.connect(self._on_failed)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(60)
        self._resize_timer.timeout.connect(self._rerender_if_fit)

        self._build_ui()
        self._apply_style()
        self._setup_shortcuts()
        self._place_window()

        self._show_message("Загрузка…")
        self._start_count()

    # ---------- построение окна ----------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._bar = QFrame()
        self._bar.setObjectName("viewerBar")
        bar = QHBoxLayout(self._bar)
        bar.setContentsMargins(10, 6, 10, 6)
        bar.setSpacing(6)

        def button(text, tip, slot, width=34):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setFixedHeight(30)
            b.setMinimumWidth(width)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(slot)
            return b

        self._btn_prev = button("◀", "Предыдущая страница (←, PgUp)", lambda: self._go(-1))
        self._spin = QSpinBox()
        self._spin.setRange(1, 1)
        self._spin.setFixedWidth(64)
        self._spin.setFixedHeight(30)
        self._spin.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._spin.setEnabled(False)
        self._spin.valueChanged.connect(self._show_page)
        self._lbl_total = QLabel("из …")
        self._btn_next = button("▶", "Следующая страница (→, PgDn)", lambda: self._go(1))

        self._btn_zoom_out = button("−", "Уменьшить (−, Ctrl+колесо)", lambda: self._zoom_by(1 / ZOOM_STEP))
        self._lbl_zoom = QLabel("100%")
        self._lbl_zoom.setMinimumWidth(48)
        self._lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_zoom_in = button("+", "Увеличить (+, Ctrl+колесо)", lambda: self._zoom_by(ZOOM_STEP))
        self._btn_fit_width = button("По ширине", "По ширине окна (Ctrl+0)", lambda: self._set_mode("width"), 84)
        self._btn_fit_page = button("По странице", "Страница целиком", lambda: self._set_mode("page"), 92)
        self._btn_100 = button("100%", "Реальный размер (Ctrl+1)", self._zoom_100, 52)
        self._btn_rot_l = button("⟲", "Повернуть влево", lambda: self._rotate(-90))
        self._btn_rot_r = button("⟳", "Повернуть вправо (Ctrl+R)", lambda: self._rotate(90))
        self._btn_retry = button("Повторить", "Повторить загрузку", self._retry, 84)
        self._btn_retry.hide()

        for w in (self._btn_prev, self._spin, self._lbl_total, self._btn_next):
            bar.addWidget(w)
        bar.addSpacing(12)
        for w in (self._btn_zoom_out, self._lbl_zoom, self._btn_zoom_in, self._btn_fit_width, self._btn_fit_page, self._btn_100):
            bar.addWidget(w)
        bar.addSpacing(12)
        bar.addWidget(self._btn_rot_l)
        bar.addWidget(self._btn_rot_r)
        bar.addStretch(1)
        bar.addWidget(self._btn_retry)

        self._view = _PageView()
        self._view.zoom_step.connect(lambda s: self._zoom_by(ZOOM_STEP if s > 0 else 1 / ZOOM_STEP))
        self._page_label = QLabel()
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._view.setWidget(self._page_label)

        root.addWidget(self._bar)
        root.addWidget(self._view, 1)
        self._sync_controls()

    def _apply_style(self):
        t = get_manager().current

        def tok(name, default):
            return getattr(t, name, default)

        bg = tok("BG_DIALOG", "#ffffff")
        text = tok("TEXT_PRIMARY", "#222222")
        accent = tok("ACCENT_PRIMARY", "#2a7de1")
        accent_hover = tok("ACCENT_HOVER", accent)
        on_accent = tok("TEXT_ON_ACCENT", "#ffffff")
        border = tok("BORDER_DEFAULT", "#c8c8c8")
        field = tok("BG_INPUT", "#ffffff")

        self.setStyleSheet(
            f"""
            QWidget {{ background-color: {bg}; color: {text}; }}
            QFrame#viewerBar {{ border-bottom: 1px solid {border}; }}
            QPushButton {{
                border: 1px solid {border}; border-radius: 6px; padding: 0 8px;
                background-color: {field}; color: {text}; font-size: 13px;
            }}
            QPushButton:hover {{ border-color: {accent}; }}
            QPushButton:pressed {{ background-color: {accent}; color: {on_accent}; }}
            QPushButton:disabled {{ color: {border}; }}
            QSpinBox {{
                border: 1px solid {border}; border-radius: 6px; padding: 0 6px;
                background-color: {field}; color: {text};
            }}
            QSpinBox:focus {{ border: 2px solid {accent_hover}; }}
            """
        )
        # Полотно просмотра — тёмное в любой теме, как в обычных просмотрщиках сканов
        self._view.setStyleSheet("QScrollArea { background-color: #2b2b2b; border: none; }")
        self._page_label.setStyleSheet("background-color: transparent; color: #dddddd; font-size: 14px;")

    def reapply_theme(self):
        self._apply_style()

    def _setup_shortcuts(self):
        bindings = {
            "PgDown": lambda: self._go(1),
            "Right": lambda: self._go(1),
            "PgUp": lambda: self._go(-1),
            "Left": lambda: self._go(-1),
            "Home": lambda: self._show_page(1),
            "End": lambda: self._show_page(self._total or 1),
            "+": lambda: self._zoom_by(ZOOM_STEP),
            "=": lambda: self._zoom_by(ZOOM_STEP),
            "-": lambda: self._zoom_by(1 / ZOOM_STEP),
            "Ctrl+0": lambda: self._set_mode("width"),
            "Ctrl+1": self._zoom_100,
            "Ctrl+R": lambda: self._rotate(90),
        }
        for seq, fn in bindings.items():
            shortcut = QShortcut(QKeySequence(seq), self)
            shortcut.activated.connect(fn)

    def _place_window(self):
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        width, height = 900, 1000
        if avail is not None:
            width = min(width, int(avail.width() * 0.8))
            height = min(height, int(avail.height() * 0.9))
        self.resize(width, height)
        if avail is not None:
            offset = 28 * (AttachmentViewerWindow._cascade % 8)  # окна каскадом, не одно поверх другого
            self.move(avail.x() + 60 + offset, avail.y() + 40 + offset)
        AttachmentViewerWindow._cascade += 1

    # ---------- загрузка ----------

    def _start_count(self):
        _pool.start(_CountTask(self._service, self._attachment_id, self._signals))

    def _request(self, page: int):
        if page in self._cache or page in self._inflight:
            return
        self._inflight.add(page)
        _pool.start(_PageTask(self._service, self._attachment_id, page, self._signals))

    @pyqtSlot(int)
    def _on_counted(self, total: int):
        self._total = total
        self._spin.setEnabled(True)
        self._spin.blockSignals(True)
        self._spin.setRange(1, total)
        self._spin.blockSignals(False)
        self._lbl_total.setText(f"из {total}")
        self._show_page(1)

    @pyqtSlot(int, object)
    def _on_page_loaded(self, page: int, image):
        self._inflight.discard(page)
        self._cache[page] = QPixmap.fromImage(image)
        self._cache.move_to_end(page)
        while len(self._cache) > CACHE_PAGES:
            for key in self._cache:
                if key != self._current:
                    del self._cache[key]
                    break
            else:
                break
        if page == self._current:
            self._render(reset_scroll=True)

    @pyqtSlot(int, str)
    def _on_failed(self, page: int, message: str):
        if page == 0:
            self._show_message(f"Не удалось открыть вложение:\n{message}")
            self._btn_retry.show()
            return
        self._inflight.discard(page)
        if page == self._current:  # ошибки заранее подгружаемых страниц не показываем
            self._show_message(f"Не удалось загрузить страницу {page}:\n{message}")
            self._btn_retry.show()

    def _retry(self):
        self._btn_retry.hide()
        if self._total is None:
            self._show_message("Загрузка…")
            self._start_count()
        else:
            self._inflight.discard(self._current)
            self._show_page(self._current)

    # ---------- страницы ----------

    def _go(self, delta: int):
        if self._total:
            self._show_page(self._current + delta)

    def _show_page(self, page: int):
        if not self._total:
            return
        page = max(1, min(self._total, int(page)))
        changed = page != self._current
        self._current = page
        self._btn_retry.hide()
        self._sync_controls()

        if page in self._cache:
            self._render(reset_scroll=changed)
        else:
            self._show_message(f"Загрузка страницы {page}…")
            self._request(page)

        for neighbour in (page + 1, page - 1):  # соседние страницы — заранее
            if 1 <= neighbour <= self._total and neighbour not in self._cache:
                self._request(neighbour)

    def _sync_controls(self):
        total = self._total or 1
        self._spin.blockSignals(True)
        self._spin.setValue(self._current)
        self._spin.blockSignals(False)
        self._btn_prev.setEnabled(self._current > 1)
        self._btn_next.setEnabled(self._current < total)

    # ---------- отрисовка и масштаб ----------

    def _show_message(self, text: str):
        self._page_label.setPixmap(QPixmap())
        self._page_label.setText(text)
        self._page_label.setMinimumSize(0, 0)
        self._page_label.adjustSize()

    def _source_pixmap(self):
        pixmap = self._cache.get(self._current)
        if pixmap is None:
            return None
        if not self._rotation:
            return pixmap
        cached = self._rotated
        if cached and cached[0] == self._current and cached[1] == self._rotation:
            return cached[2]
        rotated = pixmap.transformed(QTransform().rotate(self._rotation), Qt.TransformationMode.FastTransformation)
        self._rotated = (self._current, self._rotation, rotated)
        return rotated

    def _render(self, reset_scroll: bool = False):
        src = self._source_pixmap()
        if src is None or src.isNull():
            return
        self._cache.move_to_end(self._current)

        sw, sh = src.width(), src.height()
        viewport = self._view.viewport().size()
        if self._mode == "width":
            scale = viewport.width() / sw
        elif self._mode == "page":
            scale = min(viewport.width() / sw, viewport.height() / sh)
        else:
            scale = self._zoom
        scale = max(MIN_SCALE, min(MAX_SCALE, scale))
        if sw * sh * scale * scale > MAX_PIXELS:
            scale = math.sqrt(MAX_PIXELS / (sw * sh))
        self._scale = scale

        if abs(scale - 1.0) < 0.001:
            shown = src
        else:
            target = QSize(max(1, round(sw * scale)), max(1, round(sh * scale)))
            shown = src.scaled(target, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

        self._page_label.setText("")
        self._page_label.setPixmap(shown)
        self._page_label.resize(shown.size())
        self._lbl_zoom.setText(f"{round(scale * 100)}%")
        if reset_scroll:
            self._view.verticalScrollBar().setValue(0)
            self._view.horizontalScrollBar().setValue(0)

    def _rerender_if_fit(self):
        if self._mode in ("width", "page") and self._current in self._cache:
            self._render()

    def _set_mode(self, mode: str):
        self._mode = mode
        self._render(reset_scroll=True)

    def _zoom_by(self, factor: float):
        if self._current not in self._cache:
            return
        self._zoom = max(MIN_SCALE, min(MAX_SCALE, self._scale * factor))
        self._mode = "manual"
        self._render()

    def _zoom_100(self):
        self._zoom = 1.0
        self._mode = "manual"
        self._render(reset_scroll=True)

    def _rotate(self, degrees: int):
        self._rotation = (self._rotation + degrees) % 360
        self._rotated = None
        if self._current in self._cache:
            self._render(reset_scroll=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start()  # пересчёт «по ширине / по странице» после паузы в изменении размера

    def closeEvent(self, event):
        self._cache.clear()
        self._rotated = None
        super().closeEvent(event)


# ───────────────────────── точка входа ─────────────────────────


def open_attachment_viewer(service, document: dict, attachment: dict) -> AttachmentViewerWindow:
    """Открывает вложение в отдельном окне (или выводит уже открытое на передний план)."""
    key = attachment.get("id")
    if key is not None:
        existing = _open_windows.get(key)
        if existing is not None:
            try:
                existing.setWindowState(
                    (existing.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive
                )
                existing.show()
                existing.raise_()
                existing.activateWindow()
                return existing
            except RuntimeError:  # окно уже уничтожено
                _open_windows.pop(key, None)
    else:
        key = ("anonymous", next(_anon_ids))

    window = AttachmentViewerWindow(service, document, attachment)
    _open_windows[key] = window  # сильная ссылка: окно без родителя иначе удалит сборщик мусора
    window.destroyed.connect(lambda *_args, k=key: _open_windows.pop(k, None))
    window.show()
    window.raise_()
    window.activateWindow()
    return window