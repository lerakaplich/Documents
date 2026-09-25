# client/windows/documents/table/create/document_dialog.py
"""
Универсальный диалог для создания и редактирования документа
"""
import os
import sys
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, Qt, QDate
from PyQt6.QtWidgets import QWidget, QMessageBox, QDateEdit, QFileDialog

from client.core.themes import apply_theme_to_widget, get_manager
from client.windows.date_edit import CustomCalendarDateEdit
from client.windows.documents.table.create.employee_selection_dialog import EmployeeSelectionDialog
from client.windows.documents.table.create.tag_selection_dialog import TagSelectionDialog

# Реальные направления документа (server: enum public.doc_direction).
# ВАЖНО: на сервере только 2 значения — 'internal' и 'external'.
# (в БД нет отдельных 'incoming'/'outgoing' — это старое, неверное
# предположение, которое было в UI раньше)
DIRECTIONS = [
    ("internal", "Внутренний документ"),
    ("external", "Внешний документ"),
]

# Кастомный календарь
try:
    _HAS_CUSTOM_DATE = True
except ImportError as _e:
    _HAS_CUSTOM_DATE = False
    print(f"[DocumentDialog] CustomDateEdit недоступен: {_e}")


class DocumentDialog(QWidget):
    """
    Универсальный диалог для создания и редактирования документа.
    Поддерживает два режима: 'create' и 'edit'.
    """

    document_created = pyqtSignal(dict)
    document_updated = pyqtSignal(dict)
    cancelled = pyqtSignal()

    def __init__(self, parent=None, mode: str = 'create',
                 document_data: Optional[Dict[str, Any]] = None,
                 current_user: Optional[Dict[str, Any]] = None,
                 organizations: List[Dict] = None,
                 departments: List[Dict] = None,
                 employees: List[Dict] = None,
                 tags: List[Dict] = None,
                 document_types: Optional[List[Dict[str, Any]]] = None,
                 http_client=None,
                 document_service=None,
                 doc_type_service=None):
        super().__init__(parent)

        self.mode = mode
        self.document_data = document_data or {}
        self.current_user = current_user or {}
        self.organizations = organizations or []
        self.departments = departments or []
        self.employees = employees or []
        self.available_tags = tags or []
        self.http_client = http_client or self._resolve_http_client()

        # Сервисы для сохранения на сервере
        self.document_service = document_service or self._resolve_document_service()
        self.doc_type_service = doc_type_service or self._resolve_doc_type_service()
        self.attachment_service = self._resolve_attachment_service()

        # Справочники (орг./отделы/сотрудники) нужны не только пикерам
        # выбора, но и самому диалогу — чтобы разложить выбранные
        # receiver_ids/executor_ids по типу узла при сборке payload
        # (иначе _orgs/_depts/_emps будут пустыми и получатели/исполнители
        # не найдутся, даже если реально были выбраны в пикере).
        if self.http_client and (not self.organizations or not self.departments or not self.employees):
            self._load_org_structure_if_needed()

        # Состояние формы
        self.selected_sender: Optional[Dict[str, Any]] = None
        self.selected_receivers: List = []
        self.selected_executors: List = []
        self.selected_tags: List = []
        self.selected_file_path: Optional[str] = None

        # Списки для комбобоксов
        self.directions = DIRECTIONS  # [(value, label), ...] — см. константу модуля
        self.create_methods = ["Создать новый", "Из шаблона", "Загрузить файл"]

        # Реальные типы документов с сервера (id, name, fields, auto_num, ...),
        # а не захардкоженный список названий — иначе type_id для POST /documents
        # взять неоткуда.
        self.document_types_data: List[Dict[str, Any]] = document_types or []
        if not self.document_types_data and self.doc_type_service:
            try:
                self.document_types_data = self.doc_type_service.get_all_types()
            except Exception as e:
                print(f"[DocumentDialog] Не удалось загрузить типы документов: {e}")

        # Настройка UI
        self._load_ui()
        self._replace_date_edits()      # ← заменяем календари на кастомные
        self._setup_widgets()

        # Если режим редактирования - загружаем данные
        if self.mode == 'edit' and self.document_data:
            self._load_document_data()

        # Устанавливаем заголовок и кнопки в зависимости от режима
        self._setup_mode_ui()

        self._connect_signals()
        self._set_default_dates()

    # ─────────────────── UI ───────────────────

    def _load_ui(self):
        """Загрузка UI из .ui файла"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            client_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
            ui_path = os.path.normpath(os.path.join(client_dir, 'ui', 'documents', 'create', 'document_create_dialog.ui'))

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
        from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit

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

        if hasattr(self, 'direction_box'):
            self.direction_box.clear()
            for value, label in self.directions:
                self.direction_box.addItem(label, value)
            self.direction_box.setCurrentIndex(-1)
            self.direction_box.setPlaceholderText("Выберите направление")

        if hasattr(self, 'select_box'):
            self.select_box.addItems(self.create_methods)
            self.select_box.setCurrentIndex(-1)
            self.select_box.setPlaceholderText("Выберите способ создания документа")

        # Настройка дат — если у нас ещё QDateEdit (не заменён)
        if hasattr(self, 'date_edit'):
            try:
                self.date_edit.setCalendarPopup(True)
            except AttributeError:
                pass
            try:
                self.date_edit.setDisplayFormat("dd.MM.yyyy")
            except AttributeError:
                pass

        if hasattr(self, 'date_deadline'):
            try:
                self.date_deadline.setCalendarPopup(True)
            except AttributeError:
                pass
            try:
                self.date_deadline.setDisplayFormat("dd.MM.yyyy")
            except AttributeError:
                pass

        self._setup_selection_buttons()

    def _populate_type_box(self):
        """
        Заполняет type_box реальными типами документов с сервера.
        userData каждого пункта = настоящий type_id (int), а не индекс —
        это то, что реально уходит в payload POST /documents.
        """
        if not hasattr(self, 'type_box'):
            return

        self.type_box.blockSignals(True)
        try:
            self.type_box.clear()
            if not self.document_types_data:
                self.type_box.setPlaceholderText("Нет доступных типов документов")
                return

            for doc_type in self.document_types_data:
                type_id = doc_type.get('id')
                name = doc_type.get('name') or f"Тип {type_id}"
                self.type_box.addItem(name, type_id)

            self.type_box.setCurrentIndex(-1)
            self.type_box.setPlaceholderText("Выберите тип документа")
        finally:
            self.type_box.blockSignals(False)

    def _setup_mode_ui(self):
        """Настройка UI в зависимости от режима"""
        if self.mode == 'create':
            self.setWindowTitle("Создание нового документа")
            if hasattr(self, 'btn_attach'):
                self.btn_attach.setText("Создать документ")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Создание нового документа")
        else:
            self.setWindowTitle("Редактирование документа")
            if hasattr(self, 'btn_attach'):
                self.btn_attach.setText("Сохранить изменения")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Редактирование документа")
            if hasattr(self, 'select_box'):
                self.select_box.setEnabled(False)

    def _setup_selection_buttons(self):
        """Настройка кнопок выбора. Стили — из .ui (плейсхолдеры {TOKEN})."""
        if hasattr(self, 'btn_sender'):
            self.btn_sender.clicked.connect(self._open_sender_selection)

        if hasattr(self, 'btn_receiver'):
            self.btn_receiver.clicked.connect(self._open_receiver_selection)

        if hasattr(self, 'btnExecutor'):
            self.btnExecutor.clicked.connect(self._open_executor_selection)

        if hasattr(self, 'btn_tag'):
            self.btn_tag.clicked.connect(self._open_tag_selection)

    def _connect_signals(self):
        """Связывание сигналов"""
        if hasattr(self, 'btn_attach'):
            self.btn_attach.clicked.connect(self.save_document)

        if hasattr(self, 'btnAddSender'):
            self.btnAddSender.clicked.connect(self.add_sender)

        if hasattr(self, 'direction_box'):
            self.direction_box.currentIndexChanged.connect(self._on_direction_changed)

        if hasattr(self, 'select_box'):
            self.select_box.currentIndexChanged.connect(self._on_create_method_changed)

    def _set_default_dates(self):
        """Установка дефолтных дат"""
        today = QDate.currentDate()
        if hasattr(self, 'date_edit') and self.mode == 'create':
            self.date_edit.setDate(today)
        if hasattr(self, 'date_deadline'):
            self.date_deadline.setDate(today.addDays(30))

    # ─────────────────── ЗАГРУЗКА ДАННЫХ (режим edit) ───────────────────

    def _load_document_data(self):
        """Загружает данные документа в поля (для режима редактирования)"""
        if not self.document_data:
            return

        data = self.document_data

        if hasattr(self, 'topic_edit'):
            self.topic_edit.setText(data.get('title', ''))

        if hasattr(self, 'type_box'):
            # Ищем по type_id (userData), а не по названию — название могло
            # измениться, id — нет.
            type_id = data.get('type_id')
            if type_id is not None:
                index = self.type_box.findData(type_id)
                if index >= 0:
                    self.type_box.setCurrentIndex(index)

        if hasattr(self, 'regarding_edit'):
            self.regarding_edit.setText(data.get('about', ''))

        if hasattr(self, 'number_edit'):
            self.number_edit.setText(data.get('reg_number', ''))

        if hasattr(self, 'date_edit'):
            created_at = data.get('created_at')
            if created_at:
                if isinstance(created_at, datetime):
                    self.date_edit.setDate(QDate(created_at.year, created_at.month, created_at.day))
                elif isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        self.date_edit.setDate(QDate(dt.year, dt.month, dt.day))
                    except Exception:
                        pass

        if hasattr(self, 'direction_box'):
            # direction в данных — реальное значение enum ('internal'/'external'),
            # ищем по userData, а не по русскому тексту.
            direction = data.get('direction', '')
            index = self.direction_box.findData(direction)
            if index >= 0:
                self.direction_box.setCurrentIndex(index)

        # Отправитель
        sender = data.get('sender')
        if sender and hasattr(self, 'btn_sender'):
            self.selected_sender = sender
            self._update_sender_button_text()

        # Получатели
        self.selected_receivers = data.get('receiver_ids', [])
        self._update_receiver_button_text()

        # Исполнители
        self.selected_executors = data.get('executor_ids', [])
        self._update_executor_button_text()

        # Теги
        tags_data = data.get('tags', [])
        if tags_data:
            if isinstance(tags_data[0], (int, str)):
                self.selected_tags = [
                    tag for tag in self.available_tags
                    if tag.get('id') in tags_data
                ]
            else:
                self.selected_tags = tags_data
            self._update_tag_button_text()

    # ─────────────────── ОТПРАВИТЕЛЬ ───────────────────

    def _open_sender_selection(self):
        """Открывает диалог выбора отправителя (single-select)."""
        print(f"[DEBUG] selected_sender = {self.selected_sender!r}")
        print(f"[DEBUG] type = {type(self.selected_sender)}")
        if self.selected_sender:
            print(
                f"[DEBUG] keys = {list(self.selected_sender.keys()) if isinstance(self.selected_sender, dict) else 'не dict'}")

        # Безопасно достаём id
        sender_id = None
        if isinstance(self.selected_sender, dict):
            sender_id = self.selected_sender.get("id")
        preselected = [sender_id] if sender_id else []

        dialog = EmployeeSelectionDialog(
            organizations=self.organizations,
            departments=self.departments,
            employees=self.employees,
            preselected_ids=preselected,
            parent=self,
            title="Выбор отправителя",
            instruction="Выберите отправителя документа:",
            http_client=self.http_client,
        )
        dialog.selection_confirmed.connect(self._on_sender_selected)
        dialog.exec()

    def _on_sender_selected(self, selected_ids):
        if not selected_ids:
            self.selected_sender = None
            self._update_sender_button_text()
            return

        if len(selected_ids) > 1:
            QMessageBox.warning(
                self, "Внимание",
                "Можно выбрать только одного отправителя. Будет использован первый."
            )

        emp_id = selected_ids[0]
        emp = next((e for e in self.employees if e.get('id') == emp_id), None)
        self.selected_sender = emp if emp else {'id': emp_id}
        self._update_sender_button_text()

    def _update_sender_button_text(self):
        if not hasattr(self, 'btn_sender'):
            return

        if not self.selected_sender:
            self.btn_sender.setText("Выберите отправителя")
            self.btn_sender.setToolTip("")
            return

        s = self.selected_sender
        name = (
            s.get('name')
            or s.get('full_name')
            or ' '.join(filter(None, [
                s.get('last_name', ''),
                s.get('first_name', ''),
                s.get('patronymic', ''),
            ])).strip()
        )
        if not name:
            name = f"ID: {s.get('id')}"

        self.btn_sender.setText(name)
        self.btn_sender.setToolTip(name)

    def add_sender(self):
        QMessageBox.information(self, "Поиск",
                                "Используйте кнопку «Выберите отправителя» для выбора.")

    # ─────────────────── ПОЛУЧАТЕЛИ ───────────────────
    @staticmethod
    def _resolve_http_client():
        try:
            from client.core.state.app_state import AppState
            return AppState().http_client
        except Exception:
            return None

    def _resolve_document_service(self):
        """Создаёт DocumentService на основе self.http_client, если он доступен."""
        if not self.http_client:
            return None
        try:
            from client.services.document_service import DocumentService
            return DocumentService(self.http_client)
        except Exception as e:
            print(f"[DocumentDialog] Не удалось создать DocumentService: {e}")
            return None

    def _resolve_doc_type_service(self):
        """Создаёт DocTypeService на основе self.http_client, если он доступен."""
        if not self.http_client:
            return None
        try:
            from client.services.doc_type_service import get_doc_type_service
            return get_doc_type_service(self.http_client)
        except Exception as e:
            print(f"[DocumentDialog] Не удалось создать DocTypeService: {e}")
            return None

    def _resolve_attachment_service(self):
        """Создаёт AttachmentService на основе self.http_client, если он доступен."""
        if not self.http_client:
            return None
        try:
            from client.services.attachment_service import get_attachment_service
            return get_attachment_service(self.http_client)
        except Exception as e:
            print(f"[DocumentDialog] Не удалось создать AttachmentService: {e}")
            return None

    def _load_org_structure_if_needed(self):
        """
        Подгружает организации/отделы/сотрудников тем же загрузчиком, что
        использует EmployeeSelectionDialog внутри себя. Без этого
        self.organizations/departments/employees остаются пустыми, если их
        не передали явно при создании DocumentDialog, и тогда получатели/
        исполнители, выбранные в пикере, нельзя сопоставить по типу узла
        (org/dept/emp) — при сборке payload все они уходят в
        "неизвестный получатель".
        """
        try:
            from client.core.org_structure.employee_selection_data_loader import EmployeeSelectionDataLoader
            loader = EmployeeSelectionDataLoader(self.http_client)
            if not self.organizations:
                self.organizations = loader.load_organizations()
            if not self.departments:
                self.departments = loader.load_departments_flat()
            if not self.employees:
                self.employees = loader.load_employees()
            print(
                f"[DocumentDialog] Справочники загружены: "
                f"орг={len(self.organizations)}, отд={len(self.departments)}, "
                f"сотр={len(self.employees)}"
            )
        except Exception as e:
            print(f"[DocumentDialog] Не удалось загрузить справочники орг.структуры: {e}")
            import traceback
            traceback.print_exc()

    def _open_receiver_selection(self):
        """Открывает диалог выбора получателей."""
        dialog = EmployeeSelectionDialog(
            organizations=self.organizations,
            departments=self.departments,
            employees=self.employees,
            preselected_ids=self.selected_receivers,
            parent=self,
            title="Выбор получателей",
            instruction="Выберите получателей документа:",
            http_client=self.http_client,
        )
        dialog.selection_confirmed.connect(self._on_receivers_selected)
        dialog.exec()

    def _on_receivers_selected(self, selected_ids):
        self.selected_receivers = selected_ids
        self._update_receiver_button_text()

    def _update_receiver_button_text(self):
        if not hasattr(self, 'btn_receiver'):
            return

        if not self.selected_receivers:
            self.btn_receiver.setText("Выберите получателя")
            self.btn_receiver.setToolTip("")
            return

        names = self._get_employee_names(self.selected_receivers)
        text = ', '.join(names[:3])
        if len(self.selected_receivers) > 3:
            text += f" +{len(self.selected_receivers) - 3}..."
        self.btn_receiver.setText(text)
        self.btn_receiver.setToolTip(', '.join(names))

    # ─────────────────── ИСПОЛНИТЕЛИ ───────────────────

    def _open_executor_selection(self):
        """Открывает диалог выбора исполнителей."""
        dialog = EmployeeSelectionDialog(
            organizations=self.organizations,
            departments=self.departments,
            employees=self.employees,
            preselected_ids=self.selected_executors,
            parent=self,
            title="Выбор исполнителей",
            instruction="Выберите исполнителей документа:",
            http_client=self.http_client,
        )
        dialog.selection_confirmed.connect(self._on_executors_selected)
        dialog.exec()

    def _on_executors_selected(self, selected_ids):
        self.selected_executors = selected_ids
        self._update_executor_button_text()

    def _update_executor_button_text(self):
        if not hasattr(self, 'btnExecutor'):
            return

        if not self.selected_executors:
            self.btnExecutor.setText("Выберите исполнителя")
            self.btnExecutor.setToolTip("")
            return

        names = self._get_employee_names(self.selected_executors)
        text = ', '.join(names[:3])
        if len(self.selected_executors) > 3:
            text += f" +{len(self.selected_executors) - 3}..."
        self.btnExecutor.setText(text)
        self.btnExecutor.setToolTip(', '.join(names))

    def _get_employee_names(self, node_ids: list) -> list:
        """
        Возвращает подписи для кнопок получателей/исполнителей.
        Узел может быть сотрудником, отделом или организацией (дерево выбора
        общее для всех трёх), поэтому ищем по всем трём справочникам, а не
        только по self.employees — иначе выбранные орг./отделы пропадали
        из текста кнопки молча.
        """
        names = []
        for node_id in node_ids:
            found_name = None
            for source in (self.employees, self.departments, self.organizations):
                for item in source:
                    if item.get('id') == node_id:
                        found_name = (
                            item.get('name')
                            or item.get('full_name')
                            or item.get('display_text')
                            or ' '.join(filter(None, [
                                item.get('last_name', ''),
                                item.get('first_name', ''),
                                item.get('patronymic', ''),
                            ])).strip()
                        )
                        break
                if found_name:
                    break
            names.append(found_name or f'ID:{node_id}')
        return names

    # ─────────────────── ТЕГИ ───────────────────

    def _open_tag_selection(self):
        """Открывает диалог выбора тегов."""
        dialog = TagSelectionDialog(
            tags_list=self.available_tags,
            parent=self,
            http_client=self.http_client,
        )

        if self.selected_tags:
            selected_ids = [tag.get('id') for tag in self.selected_tags]
            dialog.set_selected_tags(selected_ids)

        if hasattr(dialog, 'setupUi'):
            dialog.setupUi()

        dialog.tags_selected.connect(self._on_tags_selected)
        dialog.exec()

    def _on_tags_selected(self, selected_tags):
        self.selected_tags = selected_tags
        self._update_tag_button_text()

    def _update_tag_button_text(self):
        if not hasattr(self, 'btn_tag'):
            return

        if not self.selected_tags:
            self.btn_tag.setText("Выберите теги")
            self.btn_tag.setToolTip("")
            return

        names = [tag.get('name', '') for tag in self.selected_tags[:3]]
        text = ', '.join(names)
        if len(self.selected_tags) > 3:
            text += f" +{len(self.selected_tags) - 3}..."
        self.btn_tag.setText(text)
        self.btn_tag.setToolTip(', '.join(tag.get('name', '') for tag in self.selected_tags))

    # ─────────────────── ПРОЧИЕ ОБРАБОТЧИКИ ───────────────────

    def _on_direction_changed(self, index):
        if index >= 0 and hasattr(self, 'direction_box'):
            print(f"[UI] Выбрано направление: {self.direction_box.currentData()} "
                  f"({self.direction_box.currentText()})")

    def _on_create_method_changed(self, index):
        if index < 0:
            return
        method = self.create_methods[index]
        print(f"[UI] Выбран метод создания: {method}")

        if method == "Загрузить файл":
            self._open_file_dialog()

    def _open_file_dialog(self):
        """
        Открывает системный проводник для выбора файла документа.
        Раньше выбор пункта "Загрузить файл" только логировался в консоль
        и никакого диалога не открывал — отсюда жалоба "не открывается
        проводник".
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл документа",
            "",
            "Документы (*.pdf *.doc *.docx *.rtf *.odt *.png *.jpg *.jpeg *.tiff);;Все файлы (*.*)",
        )

        if not file_path:
            # Отмена выбора — возвращаем комбобокс в состояние "не выбрано",
            # чтобы не оставалось враньё, что файл прикреплён.
            self.selected_file_path = None
            if hasattr(self, 'select_box'):
                self.select_box.blockSignals(True)
                self.select_box.setCurrentIndex(-1)
                self.select_box.blockSignals(False)
            return

        self.selected_file_path = file_path
        print(f"[DocumentDialog] Выбран файл: {file_path}")

        # Показываем имя файла, если в .ui есть подходящий виджет;
        # в любом случае даём пользователю видимое подтверждение выбора.
        shown = False
        for attr_name in ("namedoc_browser", "file_name_label", "selectedFileLabel"):
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setText"):
                widget.setText(os.path.basename(file_path))
                shown = True
                break
        if not shown:
            QMessageBox.information(self, "Файл выбран", f"Выбран файл:\n{os.path.basename(file_path)}")

    # ─────────────────── СОХРАНЕНИЕ ───────────────────

    def save_document(self):
        print("🚨 save_document вызван!")
        print(f"   mode={self.mode}")
        print(f"   type_box currentIndex={getattr(self, 'type_box', None) and self.type_box.currentIndex()}")
        print(
            f"   direction_box currentIndex={getattr(self, 'direction_box', None) and self.direction_box.currentIndex()}")
        print(f"   topic='{getattr(self, 'topic_edit', None) and self.topic_edit.toPlainText()}'")
        print(f"   receivers={self.selected_receivers}")
        print(f"   document_service={self.document_service}")
        print(f"   http_client={self.http_client}")
        """
        Сбор данных формы и (в режиме 'create') реальная отправка на сервер
        через DocumentService.create_document → POST /documents.

        Ключи в doc_data соответствуют тому, что ожидает
        DocumentService._build_create_payload: type_id, direction,
        sender_id, global_msg_id, receiver_ids/executor_ids (+ справочники
        _orgs/_depts/_emps для разбора получателей по типу узла).
        """
        # ── Валидация на уровне формы ──
        if not hasattr(self, 'type_box') or self.type_box.currentIndex() < 0:
            QMessageBox.warning(self, "Внимание", "Выберите тип документа")
            return

        if not hasattr(self, 'direction_box') or self.direction_box.currentIndex() < 0:
            QMessageBox.warning(self, "Внимание", "Выберите направление документа")
            return

        if not hasattr(self, 'topic_edit') or not self.topic_edit.toPlainText().strip():
            QMessageBox.warning(self, "Внимание", "Введите тему документа")
            return

        if not self.selected_receivers:
            QMessageBox.warning(self, "Внимание", "Выберите получателей документа")
            return

        type_id = self.type_box.currentData()
        direction = self.direction_box.currentData()

        sender_id = self.selected_sender.get('id') if self.selected_sender else None

        # global_msg_id обязателен на сервере (NOT NULL, уникален) — при
        # создании генерируем UUID один раз; при редактировании переиспользуем
        # тот, что уже есть у документа.
        if self.mode == 'edit' and self.document_data.get('global_msg_id'):
            global_msg_id = self.document_data['global_msg_id']
        else:
            global_msg_id = str(uuid.uuid4())

        doc_data: Dict[str, Any] = {}

        if self.mode == 'edit' and self.document_data:
            doc_data['id'] = self.document_data.get('id')

        doc_data.update({
            'type_id': type_id,
            'direction': direction,
            'title': self.topic_edit.toPlainText().strip(),
            'about': self.regarding_edit.toPlainText().strip() if hasattr(self, 'regarding_edit') else '',
            'reg_number': self.number_edit.toPlainText().strip() if hasattr(self, 'number_edit') else '',
            'sender_id': sender_id,
            'receiver_ids': self.selected_receivers,
            'executor_ids': self.selected_executors,
            'tags': self.selected_tags,
            'global_msg_id': global_msg_id,
            'needs_response': bool(getattr(self, 'needs_response_check', None) and self.needs_response_check.isChecked()),
            'confident_flag': int(bool(getattr(self, 'confident_check', None) and self.confident_check.isChecked())),
            # Справочники — нужны DocumentService, чтобы разложить
            # receiver_ids/executor_ids по target_department_id /
            # target_organization_id / employee_id.
            '_orgs': self.organizations,
            '_depts': self.departments,
            '_emps': self.employees,
        })

        if hasattr(self, 'date_deadline'):
            doc_data['deadline'] = self.date_deadline.date().toString("yyyy-MM-dd")

        print(f"[DocumentDialog] {self.mode} документ: {doc_data}")

        if self.mode != 'create':
            # Обновление документа (PATCH /documents/{id}) в текущей версии
            # DocumentService не реализовано — эмитим как раньше, чтобы не
            # ломать существующий edit-флоу, если он где-то уже обработан.
            self.document_updated.emit(doc_data)
            self.close()
            return

        if not self.document_service:
            QMessageBox.critical(
                self, "Ошибка",
                "Не удалось подключиться к серверу (нет http_client/DocumentService)."
            )
            return

        if hasattr(self, 'btn_attach'):
            self.btn_attach.setEnabled(False)

        try:
            created = self.document_service.create_document(doc_data)
        except ValueError as e:
            # Клиентская валидация payload'а (validate_create_payload)
            QMessageBox.warning(self, "Внимание", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать документ:\n{e}")
            return
        finally:
            if hasattr(self, 'btn_attach'):
                self.btn_attach.setEnabled(True)

        if not created:
            QMessageBox.critical(self, "Ошибка", "Сервер не вернул созданный документ")
            return

        # Если пользователь выбрал файл через "Загрузить файл" — прикрепляем
        # его к только что созданному документу. Ошибка загрузки вложения
        # не откатывает уже созданный документ — просто предупреждаем.
        if self.selected_file_path:
            new_id = created.get('id') if isinstance(created, dict) else None
            if new_id and self.attachment_service:
                attachment = self.attachment_service.upload_attachment(new_id, self.selected_file_path)
                if not attachment:
                    QMessageBox.warning(
                        self, "Внимание",
                        "Документ создан, но не удалось загрузить прикреплённый файл.\n"
                        "Попробуйте прикрепить его повторно из карточки документа."
                    )
            elif not self.attachment_service:
                QMessageBox.warning(
                    self, "Внимание",
                    "Документ создан, но сервис загрузки вложений недоступен — "
                    "файл не прикреплён."
                )

        self.document_created.emit(created)
        self.close()

    # ─────────────────── ПУБЛИЧНЫЕ СЕТТЕРЫ ───────────────────

    def set_organizations_data(self, organizations: List[Dict]):
        self.organizations = organizations
        print(f"[UI] Загружено {len(organizations)} организаций")

    def set_departments_data(self, departments: List[Dict]):
        self.departments = departments
        print(f"[UI] Загружено {len(departments)} отделов")

    def set_employees_data(self, employees: List[Dict]):
        self.employees = employees
        print(f"[UI] Загружено {len(employees)} сотрудников")

    # ─────────────────── ТЕМА ───────────────────

    def reapply_theme(self):
        """Переприменить тему (в т.ч. кастомные календари)."""
        apply_theme_to_widget(self)
        if hasattr(self, 'date_edit') and hasattr(self.date_edit, 'reapply_theme'):
            self.date_edit.reapply_theme()
        if hasattr(self, 'date_deadline') and hasattr(self.date_deadline, 'reapply_theme'):
            self.date_deadline.reapply_theme()