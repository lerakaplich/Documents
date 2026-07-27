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
from PyQt6.QtWidgets import QWidget, QMessageBox, QComboBox, QCompleter
from PyQt6.QtGui import QStandardItemModel, QStandardItem

from client.core.data.sender_service import SenderService
from client.windows.documents.table.create.employee_selection_dialog import EmployeeSelectionDialog


class DocumentDialog(QWidget):
    """
    Универсальный диалог для создания и редактирования документа
    Поддерживает два режима: 'create' и 'edit'
    """

    # Сигнал для создания документа
    document_created = pyqtSignal(dict)

    # Сигнал для обновления документа
    document_updated = pyqtSignal(dict)

    cancelled = pyqtSignal()

    def __init__(self, parent=None, mode: str = 'create',
                 document_data: Optional[Dict[str, Any]] = None,
                 current_user: Optional[Dict[str, Any]] = None,
                 organizations: List[Dict] = None,
                 departments: List[Dict] = None,
                 employees: List[Dict] = None):
        """
        Args:
            mode: 'create' или 'edit'
            document_data: данные документа для режима 'edit'
            current_user: текущий пользователь
            organizations: список организаций
            departments: список отделов
            employees: список сотрудников
        """
        super().__init__(parent)

        self.mode = mode
        self.document_data = document_data or {}
        self.current_user = current_user or {}
        self.organizations = organizations or []
        self.departments = departments or []
        self.employees = employees or []

        # Состояние формы
        self.selected_sender: Optional[Dict[str, Any]] = None
        self.selected_receivers = []
        self.selected_executors = []
        self.selected_tags = []

        # Сервисы
        self.sender_service = SenderService()

        # Списки для комбобоксов
        self.directions = ["Входящий", "Исходящий", "Внутренний"]
        self.create_methods = ["Создать новый", "Из шаблона", "Загрузить файл"]

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

    def _load_ui(self):
        """Загрузка UI из .ui файла"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Поднимаемся на 4 уровня вверх до client
            client_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
            ui_path = os.path.normpath(os.path.join(client_dir, 'ui', 'documents', 'create', 'document_create_dialog.ui'))

            if os.path.exists(ui_path):
                uic.loadUi(ui_path, self)
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
        from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QDateEdit, QComboBox, QLineEdit

        self.setWindowTitle("Документ")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("Документ")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title_label)

        # Тема
        layout.addWidget(QLabel("Тема:"))
        self.topic_edit = QTextEdit()
        self.topic_edit.setPlaceholderText("Введите тему документа...")
        layout.addWidget(self.topic_edit)

        # Содержание
        layout.addWidget(QLabel("Содержание:"))
        self.regarding_edit = QTextEdit()
        self.regarding_edit.setPlaceholderText("Введите содержание...")
        layout.addWidget(self.regarding_edit)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setStyleSheet("background-color: #CCAB6E; color: white; padding: 10px; border-radius: 8px;")
        self.save_btn.clicked.connect(self.save_document)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.close)

        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def _setup_widgets(self):
        """Настройка виджетов"""
        # Настройка комбобоксов
        if hasattr(self, 'direction_box'):
            self.direction_box.addItems(self.directions)
            self.direction_box.setCurrentIndex(-1)
            self.direction_box.setPlaceholderText("Выберите направление")

        if hasattr(self, 'select_box'):
            self.select_box.addItems(self.create_methods)
            self.select_box.setCurrentIndex(-1)
            self.select_box.setPlaceholderText("Выберите способ создания документа")

        # Настройка дат
        if hasattr(self, 'date_edit'):
            self.date_edit.setCalendarPopup(True)
            self.date_edit.setDisplayFormat("dd.MM.yyyy")

        if hasattr(self, 'date_deadline'):
            self.date_deadline.setCalendarPopup(True)
            self.date_deadline.setDisplayFormat("dd.MM.yyyy")

        # Настройка кнопок выбора
        self._setup_selection_buttons()
        self._setup_sender_autocomplete()

    def _setup_mode_ui(self):
        """Настройка UI в зависимости от режима"""
        if self.mode == 'create':
            self.setWindowTitle("Создание нового документа")
            if hasattr(self, 'btn_attach'):
                self.btn_attach.setText("Создать документ")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Создание нового документа")
        else:  # edit
            self.setWindowTitle("Редактирование документа")
            if hasattr(self, 'btn_attach'):
                self.btn_attach.setText("Сохранить изменения")
            if hasattr(self, 'titleLabel'):
                self.titleLabel.setText("Редактирование документа")

            # Отключаем поля, которые не должны меняться при редактировании
            if hasattr(self, 'select_box'):
                self.select_box.setEnabled(False)

    def _setup_selection_buttons(self):
        """Настройка кнопок выбора получателей и исполнителей"""
        button_style = """
            QPushButton {
                border-radius: 10px;
                border: 1px solid #CCAB6E;
                padding: 5px;
                text-align: left;
                background-color: white;
                color: #1B232A;
            }
            QPushButton:hover {
                border: 1px solid #998664;
                background-color: #FDFBF7;
            }
            QPushButton:focus {
                border: 2px solid #CCAB6E;
            }
        """

        if hasattr(self, 'btn_receiver'):
            self.btn_receiver.clicked.connect(self._open_receiver_selection)
            self.btn_receiver.setStyleSheet(button_style)

        if hasattr(self, 'btnExecutor'):
            self.btnExecutor.clicked.connect(self._open_executor_selection)
            self.btnExecutor.setStyleSheet(button_style)

        if hasattr(self, 'btn_tag'):
            self.btn_tag.clicked.connect(self._open_tag_selection)

    def _setup_sender_autocomplete(self):
        """Настройка автодополнения для поля отправителя"""
        if not hasattr(self, 'sender_box'):
            return

        self.sender_box.setEditable(True)
        line_edit = self.sender_box.lineEdit()
        if line_edit:
            line_edit.setPlaceholderText("Введите для поиска отправителя...")

        # Модель для QCompleter
        self.sender_model = QStandardItemModel()
        for sender in self.sender_service.test_senders:
            item = QStandardItem(sender['display_text'])
            item.setData(sender, Qt.ItemDataRole.UserRole)
            self.sender_model.appendRow(item)
            self.sender_box.addItem(sender['display_text'], sender)

        # Конфигурация QCompleter
        completer = QCompleter(self.sender_model, self.sender_box)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        completer.popup().setStyleSheet("""
            QListView { 
                border: 1px solid #CCAB6E; 
                border-radius: 6px; 
                background-color: white; 
                padding: 4px; 
            }
            QListView::item { 
                padding: 8px; 
                color: #1B232A; 
            }
            QListView::item:hover, 
            QListView::item:selected { 
                background-color: #e3f2fd; 
            }
        """)

        self.sender_box.setCompleter(completer)
        completer.activated.connect(self._on_sender_completer_activated)

    def _load_document_data(self):
        """Загружает данные документа в поля (для режима редактирования)"""
        if not self.document_data:
            return

        data = self.document_data

        # Тема
        if hasattr(self, 'topic_edit'):
            self.topic_edit.setText(data.get('title', ''))

        # Содержание
        if hasattr(self, 'regarding_edit'):
            self.regarding_edit.setText(data.get('about', ''))

        # Номер
        if hasattr(self, 'number_edit'):
            self.number_edit.setText(data.get('reg_number', ''))

        # Номер экземпляра
        if hasattr(self, 'copy_number_edit'):
            self.copy_number_edit.setText(data.get('numcopy', ''))

        # Дата
        if hasattr(self, 'date_edit'):
            created_at = data.get('created_at')
            if created_at:
                if isinstance(created_at, datetime):
                    self.date_edit.setDate(QDate(created_at.year, created_at.month, created_at.day))
                elif isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        self.date_edit.setDate(QDate(dt.year, dt.month, dt.day))
                    except:
                        pass

        # Направление
        if hasattr(self, 'direction_box'):
            direction = data.get('direction', '')
            direction_map = {
                'incoming': 'Входящий',
                'outgoing': 'Исходящий',
                'internal': 'Внутренний'
            }
            dir_text = direction_map.get(direction, direction)
            index = self.direction_box.findText(dir_text)
            if index >= 0:
                self.direction_box.setCurrentIndex(index)

        # Отправитель
        sender = data.get('sender')
        if sender and hasattr(self, 'sender_box'):
            self._set_sender(sender)

        # Получатели
        self.selected_receivers = data.get('receiver_ids', [])
        self._update_receiver_button_text()

        # Исполнители
        self.selected_executors = data.get('executor_ids', [])
        self._update_executor_button_text()

    def _set_default_dates(self):
        """Установка дефолтных дат"""
        today = QDate.currentDate()
        if hasattr(self, 'date_edit') and self.mode == 'create':
            self.date_edit.setDate(today)
        if hasattr(self, 'date_deadline'):
            self.date_deadline.setDate(today.addDays(30))

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

        if hasattr(self, 'sender_box'):
            self.sender_box.currentIndexChanged.connect(self._on_sender_changed)
            line_edit = self.sender_box.lineEdit()
            if line_edit:
                line_edit.textChanged.connect(self._on_sender_text_changed)

    # ========== ВЫБОР ПОЛУЧАТЕЛЕЙ И ИСПОЛНИТЕЛЕЙ ==========

    def _open_receiver_selection(self):
        """Открывает диалог выбора получателей"""
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
            instruction="Выберите получателей документа:"
        )
        dialog.selection_confirmed.connect(self._on_receivers_selected)
        dialog.exec()

    def _on_receivers_selected(self, selected_ids):
        self.selected_receivers = selected_ids
        self._update_receiver_button_text()

    def _open_executor_selection(self):
        """Открывает диалог выбора исполнителей"""
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
            instruction="Выберите исполнителей документа:"
        )
        dialog.selection_confirmed.connect(self._on_executors_selected)
        dialog.exec()

    def _on_executors_selected(self, selected_ids):
        self.selected_executors = selected_ids
        self._update_executor_button_text()

    def _open_tag_selection(self):
        """Открывает диалог выбора тегов"""
        QMessageBox.information(self, "Выбор тегов", "Функция выбора тегов будет добавлена в следующей версии.")

    def _update_receiver_button_text(self):
        """Обновляет текст кнопки получателей"""
        if hasattr(self, 'btn_receiver'):
            if not self.selected_receivers:
                self.btn_receiver.setText("Выберите получателя")
            else:
                names = self._get_employee_names(self.selected_receivers)
                text = ', '.join(names[:3])
                if len(self.selected_receivers) > 3:
                    text += f" +{len(self.selected_receivers) - 3}..."
                self.btn_receiver.setText(text)

    def _update_executor_button_text(self):
        """Обновляет текст кнопки исполнителей"""
        if hasattr(self, 'btnExecutor'):
            if not self.selected_executors:
                self.btnExecutor.setText("Выберите исполнителя")
            else:
                names = self._get_employee_names(self.selected_executors)
                text = ', '.join(names[:3])
                if len(self.selected_executors) > 3:
                    text += f" +{len(self.selected_executors) - 3}..."
                self.btnExecutor.setText(text)

    def _get_employee_names(self, employee_ids: list) -> list:
        """Получает имена сотрудников по ID"""
        names = []
        for emp_id in employee_ids:
            for emp in self.employees:
                if emp.get('id') == emp_id:
                    names.append(emp.get('name', f'ID:{emp_id}'))
                    break
        return names

    # ========== СЛОТЫ И ОБРАБОТЧИКИ ==========

    def _on_sender_completer_activated(self, index):
        if index.isValid():
            item = self.sender_model.itemFromIndex(index)
            if item:
                self._set_sender(item.data(Qt.ItemDataRole.UserRole))

    def _on_sender_changed(self, index):
        if index >= 0:
            sender_data = self.sender_box.itemData(index, Qt.ItemDataRole.UserRole)
            if sender_data:
                self._set_sender(sender_data)

    def _on_sender_text_changed(self, text):
        if not text.strip():
            self.selected_sender = None

    def _set_sender(self, sender_data: Dict[str, Any]):
        if not sender_data:
            return
        self.selected_sender = sender_data
        display_text = self.sender_service.get_sender_display_text(sender_data)

        line_edit = self.sender_box.lineEdit()
        if line_edit:
            line_edit.setText(display_text)

    def _on_direction_changed(self, index):
        if index >= 0:
            print(f"[UI] Выбрано направление: {self.directions[index]}")

    def _on_create_method_changed(self, index):
        if index >= 0:
            print(f"[UI] Выбран метод создания: {self.create_methods[index]}")

    def add_sender(self):
        QMessageBox.information(self, "Поиск", "Используйте встроенное поле ввода для быстрого поиска.")

    def save_document(self):
        """Сохранение документа - сбор всех данных"""
        # Проверяем обязательные поля
        if not self.selected_receivers:
            QMessageBox.warning(self, "Внимание", "Выберите получателей документа")
            return

        if not hasattr(self, 'topic_edit') or not self.topic_edit.toPlainText().strip():
            QMessageBox.warning(self, "Внимание", "Введите тему документа")
            return

        # Собираем данные документа
        doc_data = {}

        # Если режим редактирования - берем ID из существующих данных
        if self.mode == 'edit' and self.document_data:
            doc_data['id'] = self.document_data.get('id')
            doc_data['updated_at'] = datetime.now().isoformat()

        # Общие поля
        doc_data.update({
            'direction': self.direction_box.currentText() if hasattr(self, 'direction_box') else None,
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

        # Дата
        if hasattr(self, 'date_edit'):
            qdate = self.date_edit.date()
            doc_data['created_at'] = qdate.toString("yyyy-MM-dd")

        # Дедлайн
        if hasattr(self, 'date_deadline'):
            qdate = self.date_deadline.date()
            doc_data['deadline'] = qdate.toString("yyyy-MM-dd")

        print(f"[DocumentDialog] {self.mode} документ: {doc_data}")

        # Отправляем сигнал в зависимости от режима
        if self.mode == 'create':
            self.document_created.emit(doc_data)
        else:
            self.document_updated.emit(doc_data)

        self.close()

    def set_organizations_data(self, organizations: List[Dict]):
        self.organizations = organizations
        print(f"[UI] Загружено {len(organizations)} организаций")

    def set_departments_data(self, departments: List[Dict]):
        self.departments = departments
        print(f"[UI] Загружено {len(departments)} отделов")

    def set_employees_data(self, employees: List[Dict]):
        self.employees = employees
        print(f"[UI] Загружено {len(employees)} сотрудников")