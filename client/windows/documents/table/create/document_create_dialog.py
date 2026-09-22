# client/windows/documents/table/create/document_dialog.py
"""
Универсальный диалог для создания и редактирования документа
"""
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

from PyQt6 import uic
from PyQt6.QtCore import pyqtSignal, Qt, QDate
from PyQt6.QtWidgets import QWidget, QMessageBox

from client.core.data.sender_service import SenderService
from client.core.themes import apply_theme_to_widget, get_manager
from client.windows.documents.table.create.employee_selection_dialog import EmployeeSelectionDialog
from client.windows.documents.table.create.tag_selection_dialog import TagSelectionDialog


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
                 tags: List[Dict] = None):
        super().__init__(parent)

        self.mode = mode
        self.document_data = document_data or {}
        self.current_user = current_user or {}
        self.organizations = organizations or []
        self.departments = departments or []
        self.employees = employees or []
        self.available_tags = tags or []

        # Состояние формы
        self.selected_sender: Optional[Dict[str, Any]] = None
        self.selected_receivers: List = []
        self.selected_executors: List = []
        self.selected_tags: List = []

        # Списки для комбобоксов
        self.directions = ["Входящий", "Исходящий", "Внутренний"]
        self.create_methods = ["Создать новый", "Из шаблона", "Загрузить файл"]
        self.document_types = [
            "Приказ",
            "Распоряжение",
            "Письмо",
            "Служебная записка",
            "Заявление",
            "Договор",
            "Акт",
            "Протокол",
            "Уведомление",
        ]

        # Настройка UI
        self._load_ui()
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
        if hasattr(self, 'type_box'):
            self.type_box.addItems(self.document_types)
            self.type_box.setCurrentIndex(-1)
            self.type_box.setPlaceholderText("Выберите тип документа")

        if hasattr(self, 'direction_box'):
            self.direction_box.addItems(self.directions)
            self.direction_box.setCurrentIndex(-1)
            self.direction_box.setPlaceholderText("Выберите направление")

        if hasattr(self, 'select_box'):
            self.select_box.addItems(self.create_methods)
            self.select_box.setCurrentIndex(-1)
            self.select_box.setPlaceholderText("Выберите способ создания документа")

        if hasattr(self, 'date_edit'):
            self.date_edit.setCalendarPopup(True)
            self.date_edit.setDisplayFormat("dd.MM.yyyy")

        if hasattr(self, 'date_deadline'):
            self.date_deadline.setCalendarPopup(True)
            self.date_deadline.setDisplayFormat("dd.MM.yyyy")

        self._setup_selection_buttons()

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
            doc_type = data.get('doc_type', '')
            if doc_type:
                index = self.type_box.findText(doc_type)
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
            direction = data.get('direction', '')
            direction_map = {
                'incoming': 'Входящий',
                'outgoing': 'Исходящий',
                'internal': 'Внутренний',
            }
            dir_text = direction_map.get(direction, direction)
            index = self.direction_box.findText(dir_text)
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
        if not self.employees:
            QMessageBox.warning(self, "Нет данных", "Данные о сотрудниках не загружены.")
            return

        preselected = [self.selected_sender['id']] if self.selected_sender else []

        dialog = EmployeeSelectionDialog(
            organizations=self.organizations,
            departments=self.departments,
            employees=self.employees,
            preselected_ids=preselected,
            parent=self,
            title="Выбор отправителя",
            instruction="Выберите отправителя документа:",
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

    def _open_receiver_selection(self):
        if not self.employees:
            QMessageBox.warning(self, "Нет данных", "Данные о сотрудниках не загружены.")
            return

        dialog = EmployeeSelectionDialog(
            organizations=self.organizations,
            departments=self.departments,
            employees=self.employees,
            preselected_ids=self.selected_receivers,
            parent=self,
            title="Выбор получателей",
            instruction="Выберите получателей документа:",
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
        if not self.employees:
            QMessageBox.warning(self, "Нет данных", "Данные о сотрудниках не загружены.")
            return

        dialog = EmployeeSelectionDialog(
            organizations=self.organizations,
            departments=self.departments,
            employees=self.employees,
            preselected_ids=self.selected_executors,
            parent=self,
            title="Выбор исполнителей",
            instruction="Выберите исполнителей документа:",
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

    def _get_employee_names(self, employee_ids: list) -> list:
        names = []
        for emp_id in employee_ids:
            for emp in self.employees:
                if emp.get('id') == emp_id:
                    name = (
                        emp.get('name')
                        or emp.get('full_name')
                        or ' '.join(filter(None, [
                            emp.get('last_name', ''),
                            emp.get('first_name', ''),
                            emp.get('patronymic', ''),
                        ])).strip()
                        or f'ID:{emp_id}'
                    )
                    names.append(name)
                    break
        return names

    # ─────────────────── ТЕГИ ───────────────────

    def _open_tag_selection(self):
        if not self.available_tags:
            QMessageBox.warning(self, "Нет данных", "Список тегов не загружен.")
            return

        dialog = TagSelectionDialog(tags_list=self.available_tags, parent=self)

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
        if index >= 0:
            print(f"[UI] Выбрано направление: {self.directions[index]}")

    def _on_create_method_changed(self, index):
        if index >= 0:
            print(f"[UI] Выбран метод создания: {self.create_methods[index]}")

    # ─────────────────── СОХРАНЕНИЕ ───────────────────

    def save_document(self):
        """Сохранение документа - сбор всех данных"""
        if not self.selected_receivers:
            QMessageBox.warning(self, "Внимание", "Выберите получателей документа")
            return

        if not hasattr(self, 'topic_edit') or not self.topic_edit.toPlainText().strip():
            QMessageBox.warning(self, "Внимание", "Введите тему документа")
            return

        doc_data = {}

        if self.mode == 'edit' and self.document_data:
            doc_data['id'] = self.document_data.get('id')
            doc_data['updated_at'] = datetime.now().isoformat()

        doc_data.update({
            'direction': self.direction_box.currentText() if hasattr(self, 'direction_box') else None,
            'doc_type': self.type_box.currentText() if hasattr(self, 'type_box') else None,
            'number': self.number_edit.toPlainText().strip() if hasattr(self, 'number_edit') else None,
            'reg_number': self.number_edit.toPlainText().strip() if hasattr(self, 'number_edit') else None,
            'numcopy': self.copy_number_edit.toPlainText().strip() if hasattr(self, 'copy_number_edit') else None,
            'title': self.topic_edit.toPlainText().strip() if hasattr(self, 'topic_edit') else None,
            'about': self.regarding_edit.toPlainText().strip() if hasattr(self, 'regarding_edit') else None,
            'sender': self.selected_sender,
            'receiver_ids': self.selected_receivers,
            'executor_ids': self.selected_executors,
            'tags': self.selected_tags,
            'create_method': self.select_box.currentText() if hasattr(self, 'select_box') else None,
        })

        if hasattr(self, 'date_edit'):
            qdate = self.date_edit.date()
            doc_data['created_at'] = qdate.toString("yyyy-MM-dd")

        if hasattr(self, 'date_deadline'):
            qdate = self.date_deadline.date()
            doc_data['deadline'] = qdate.toString("yyyy-MM-dd")

        print(f"[DocumentDialog] {self.mode} документ: {doc_data}")

        if self.mode == 'create':
            self.document_created.emit(doc_data)
        else:
            self.document_updated.emit(doc_data)

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