# client/windows/documents/table/create/document_dialog_ui.py
"""
Построение интерфейса диалога документа: загрузка .ui, виджеты, сигналы, тема
"""

import contextlib
import os

from PyQt6 import uic
from PyQt6.QtCore import QDate

from client.core.themes import apply_theme_to_widget

# Кастомный календарь
try:
    from client.windows.date_edit import CustomCalendarDateEdit

    _HAS_CUSTOM_DATE = True
except ImportError as _e:
    CustomCalendarDateEdit = None
    _HAS_CUSTOM_DATE = False
    print(f"[DocumentDialog] CustomDateEdit недоступен: {_e}")


class UiMixin:
    def _load_ui(self):
        """Загрузка UI из .ui файла"""
        try:
            # Файл лежит в той же папке, что и document_create_dialog.py,
            # поэтому глубина пути до client/ не меняется.
            current_dir = os.path.dirname(os.path.abspath(__file__))
            client_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
            ui_path = os.path.normpath(
                os.path.join(client_dir, "ui", "documents", "create", "document_create_dialog.ui")
            )

            if os.path.exists(ui_path):
                uic.loadUi(ui_path, self)
                apply_theme_to_widget(self)
                print(f"[DocumentDialog] UI загружен: {ui_path}")
            else:
                print(f"[Warning] UI файл не найден: {ui_path}")
                self._setup_fallback_ui()
        except Exception as e:
            print(f"[Error] Ошибка загрузки UI: {e}")
            import traceback

            traceback.print_exc()
            self._setup_fallback_ui()

    def _replace_date_edits(self):
        """
        Программно заменяет QDateEdit (date_edit, date_deadline) на
        CustomCalendarDateEdit — тот же QDateEdit, но с нашим попапом.
        """
        if not _HAS_CUSTOM_DATE:
            print("[DocumentDialog] Пропускаем замену календарей — CustomCalendarDateEdit нет")
            return

        replacements = [
            ("date_edit", "verticalLayoutDate"),
            ("date_deadline", "verticalLayoutDeadline"),
        ]

        for attr_name, layout_name in replacements:
            old_widget = getattr(self, attr_name, None)
            layout = getattr(self, layout_name, None)

            if old_widget is None or layout is None:
                print(f"[DocumentDialog] {attr_name}: не найден widget или layout {layout_name}")
                continue

            new_widget = CustomCalendarDateEdit(parent=self)

            # ── переносим размеры/поведение из .ui ──
            new_widget.setMinimumSize(old_widget.minimumSize())
            new_widget.setMaximumSize(old_widget.maximumSize())
            new_widget.setSizePolicy(old_widget.sizePolicy())

            # ── переносим формат и значение ──
            try:
                new_widget.setDisplayFormat(old_widget.displayFormat())
            except Exception:
                new_widget.setDisplayFormat("dd.MM.yyyy")

            try:
                new_widget.setDate(old_widget.date())
            except Exception:
                new_widget.setDate(QDate.currentDate())

            # ── заменяем в layout ──
            layout.replaceWidget(old_widget, new_widget)
            old_widget.setParent(None)
            old_widget.deleteLater()

            setattr(self, attr_name, new_widget)
            print(f"[DocumentDialog] {attr_name} → CustomCalendarDateEdit")

    def _setup_fallback_ui(self):
        """Создает простой UI если файл не найден"""
        from PyQt6.QtWidgets import (
            QHBoxLayout,
            QLabel,
            QPushButton,
            QTextEdit,
            QVBoxLayout,
        )

        self.setWindowTitle("Документ")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        title_label = QLabel("Документ")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title_label)

        layout.addWidget(QLabel("Тема:"))
        self.topic_edit = QTextEdit()
        self.topic_edit.setPlaceholderText("Введите тему документа...")
        layout.addWidget(self.topic_edit)

        layout.addWidget(QLabel("Содержание:"))
        self.regarding_edit = QTextEdit()
        self.regarding_edit.setPlaceholderText("Введите содержание...")
        layout.addWidget(self.regarding_edit)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_document)
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.close)

        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def _setup_widgets(self):
        """Настройка виджетов"""
        self._populate_type_box()

        if hasattr(self, "direction_box"):
            self.direction_box.clear()
            for value, label in self.directions:
                self.direction_box.addItem(label, value)
            self.direction_box.setCurrentIndex(-1)
            self.direction_box.setPlaceholderText("Выберите направление")

        if hasattr(self, "select_box"):
            self.select_box.addItems(self.create_methods)
            self.select_box.setCurrentIndex(-1)
            self.select_box.setPlaceholderText("Выберите способ создания документа")

        # Настройка дат — если у нас ещё QDateEdit (не заменён)
        if hasattr(self, "date_edit"):
            with contextlib.suppress(AttributeError):
                self.date_edit.setCalendarPopup(True)
            with contextlib.suppress(AttributeError):
                self.date_edit.setDisplayFormat("dd.MM.yyyy")

        if hasattr(self, "date_deadline"):
            with contextlib.suppress(AttributeError):
                self.date_deadline.setCalendarPopup(True)
            with contextlib.suppress(AttributeError):
                self.date_deadline.setDisplayFormat("dd.MM.yyyy")

        self._setup_selection_buttons()

    def _populate_type_box(self):
        """
        Заполняет type_box реальными типами документов с сервера.
        userData каждого пункта = настоящий type_id (int), а не индекс —
        это то, что реально уходит в payload POST /documents.
        """
        if not hasattr(self, "type_box"):
            return

        self.type_box.blockSignals(True)
        try:
            self.type_box.clear()
            if not self.document_types_data:
                self.type_box.setPlaceholderText("Нет доступных типов документов")
                return

            for doc_type in self.document_types_data:
                type_id = doc_type.get("id")
                name = doc_type.get("name") or f"Тип {type_id}"
                self.type_box.addItem(name, type_id)

            self.type_box.setCurrentIndex(-1)
            self.type_box.setPlaceholderText("Выберите тип документа")
        finally:
            self.type_box.blockSignals(False)

    def _setup_mode_ui(self):
        """Настройка UI в зависимости от режима"""
        if self.mode == "create":
            if self.parent_document_id is not None:
                ref = (self.reply_to or {}).get("reg_number") or f"#{self.parent_document_id}"
                title = f"Ответ на документ №{ref}" if (self.reply_to or {}).get("reg_number") else f"Ответ на документ {ref}"
                self.setWindowTitle(title)
                if hasattr(self, "btn_attach"):
                    self.btn_attach.setText("Отправить ответ")
                if hasattr(self, "titleLabel"):
                    self.titleLabel.setText(title)
            else:
                self.setWindowTitle("Создание нового документа")
                if hasattr(self, "btn_attach"):
                    self.btn_attach.setText("Создать документ")
                if hasattr(self, "titleLabel"):
                    self.titleLabel.setText("Создание нового документа")
        else:
            self.setWindowTitle("Редактирование документа")
            if hasattr(self, "btn_attach"):
                self.btn_attach.setText("Сохранить изменения")
            if hasattr(self, "titleLabel"):
                self.titleLabel.setText("Редактирование документа")
            if hasattr(self, "select_box"):
                self.select_box.setEnabled(False)

    def _setup_selection_buttons(self):
        """Настройка кнопок выбора. Стили — из .ui (плейсхолдеры {TOKEN})."""
        if hasattr(self, "btn_sender"):
            self.btn_sender.clicked.connect(self._open_sender_selection)

        if hasattr(self, "btn_receiver"):
            self.btn_receiver.clicked.connect(self._open_receiver_selection)

        if hasattr(self, "btnExecutor"):
            self.btnExecutor.clicked.connect(self._open_executor_selection)

        if hasattr(self, "btn_tag"):
            self.btn_tag.clicked.connect(self._open_tag_selection)

    def _connect_signals(self):
        """Связывание сигналов"""
        if hasattr(self, "btn_attach"):
            self.btn_attach.clicked.connect(self.save_document)

        # «+» у отправителя / получателей / исполнителей — меню «Сотрудник / Организация / Отдел»
        # и соответствующий диалог создания; «+» у тегов — диалог тега
        from client.windows.documents.table.create.quick_add import QuickAddController

        self._quick_add = QuickAddController(self)
        for button_name, role in (
            ("btnAddSender", "sender"),
            ("btnAddReceiver", "receiver"),
            ("btnAddExecutor", "executor"),
        ):
            button = getattr(self, button_name, None)
            if button is not None:
                button.clicked.connect(lambda checked=False, b=button, r=role: self._quick_add.show_menu(b, r))

        if hasattr(self, "btnAddTag"):
            self.btnAddTag.clicked.connect(lambda checked=False: self._quick_add.create_tag())

        if hasattr(self, "direction_box"):
            self.direction_box.currentIndexChanged.connect(self._on_direction_changed)

        if hasattr(self, "select_box"):
            self.select_box.currentIndexChanged.connect(self._on_create_method_changed)

        if hasattr(self, "type_box"):
            self.type_box.currentIndexChanged.connect(self._apply_type_fields)

    def _set_default_dates(self):
        """Установка дефолтных дат"""
        today = QDate.currentDate()
        if hasattr(self, "date_edit") and self.mode == "create":
            self.date_edit.setDate(today)
        if hasattr(self, "date_deadline"):
            self.date_deadline.setDate(today.addDays(30))

    def _collect_extra_payload(self) -> dict:
        """Доп. поля формы для payload (create и edit): сейчас только needs_response."""
        check = getattr(self, "needs_response_check", None)
        if check is None:
            return {}
        return {"needs_response": check.isChecked()}

    def reapply_theme(self):
        """Переприменить тему (в т.ч. кастомные календари)."""
        apply_theme_to_widget(self)
        if hasattr(self, "date_edit") and hasattr(self.date_edit, "reapply_theme"):
            self.date_edit.reapply_theme()
        if hasattr(self, "date_deadline") and hasattr(self.date_deadline, "reapply_theme"):
            self.date_deadline.reapply_theme()