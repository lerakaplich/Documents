# client/windows/system/document_types/document_type_dialog.py

import os
from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QFileDialog

from client.core.themes import apply_theme_to_widget


class DocumentTypeDialog(QtWidgets.QDialog):
    def __init__(self, parent_editor, item=None):
        super().__init__(parent_editor)

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), '../../../ui/system/document_types/document_type_dialog.ui')
        ui_path = os.path.normpath(ui_path)

        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
            apply_theme_to_widget(self)
            print(f"[DEBUG] UI файл успешно загружен: {ui_path}")
        else:
            print(f"[ERROR] UI файл не найден: {ui_path}")
            self.setup_ui_fallback()

        # 1. Сначала ВСЕГДА данные
        self.item = item if item is not None else {'name': '', 'columns': ''}
        self.editor = parent_editor
        self.document_directions = []  # Список всех направлений
        self.selected_direction_ids = []  # Выбранные ID направлений

        self.parameter_names = {
            "subject": "Тема",
            "regarding": "Касается",
            "from_who": "Отправитель",
            "to_who": "Получатель",
            "executor": "Исполнитель",
            "tag_id": "Тег",
            "send_date": "Дата отправки",
            "number": "Номер документа",
            "index_number": "Порядковый номер",
            "deadline": "Дедлайн",
            "status_id": "Статус",
            "attachment": "Вложение",
            "has_answer": "Ответ",
            "redirect": "Перенаправление",
            "comments": "Правки",
            "direction_name": "Направление",
        }

        # СПИСОК ПАРАМЕТРОВ, КОТОРЫЕ НЕЛЬЗЯ ВЫКЛЮЧИТЬ
        self.mandatory_parameters = ['attachment', 'redirect']

        self.available_parameters = list(self.parameter_names.keys())
        self.toggle_buttons = {}  # Словарь для кнопок

        # ⚠️ ВАЖНО: Инициализируем selected_parameters ДО того, как используем
        self.selected_parameters = []

        # --- ИСПРАВЛЕНИЕ: Получаем auto_number из item ---
        # Проверяем все возможные названия поля
        if item:
            # Проверяем в порядке приоритета
            if 'auto_number' in item:
                self.auto_number = item.get('auto_number', True)
            elif 'auto_num' in item:
                self.auto_number = item.get('auto_num', True)
            elif 'auto_numbering' in item:
                self.auto_number = item.get('auto_numbering', True)
            else:
                self.auto_number = True
        else:
            self.auto_number = True

        print(f"[DEBUG] DocumentTypeDialog __init__: auto_number = {self.auto_number} (из item={item})")

        # Теперь обрабатываем параметры
        # 1. Сначала пробуем взять из fields (новый формат)
        if isinstance(self.item.get('fields'), dict):
            fields_dict = self.item.get('fields', {})
            # Берем только те поля, у которых значение True
            self.selected_parameters = [key for key, value in fields_dict.items() if value]
            print(f"[DEBUG] Взяли данные из fields: {self.selected_parameters}")

        # 2. Если fields нет, смотрим в columns (строка из БД "send_date,subject")
        elif isinstance(self.item.get('columns'), str) and self.item.get('columns', '').strip():
            raw_columns = self.item.get('columns', '')
            self.selected_parameters = [f.strip() for f in raw_columns.split(',') if f.strip()]
            print(f"[DEBUG] Взяли данные из строки columns: {self.selected_parameters}")

        # 3. Если в columns пусто, но в parameters лежит список
        elif isinstance(self.item.get('parameters'), list):
            p_list = self.item.get('parameters', [])
            if len(p_list) > 0:
                self.selected_parameters = [str(p).strip() for p in p_list]
                print(f"[DEBUG] Взяли данные из списка parameters: {self.selected_parameters}")

        # 4. Если это НОВЫЙ документ (нет id) И selected_parameters пуст, включаем всё
        if not self.item.get('id') and not self.selected_parameters:
            self.selected_parameters = self.available_parameters.copy()
            print("[DEBUG] Новый документ: включили всё по дефолту")

        # 5. УБЕДИМСЯ, ЧТО ОБЯЗАТЕЛЬНЫЕ ПАРАМЕТРЫ ВСЕГДА В СПИСКЕ
        for param in self.mandatory_parameters:
            if param not in self.selected_parameters:
                self.selected_parameters.append(param)
                print(f"[DEBUG] Добавлен обязательный параметр: {param}")

        print(f"[FINAL CHECK] Итоговый список для кнопок: {self.selected_parameters}")

        # Настройка окна
        is_edit = self.item.get('id') is not None
        self.setWindowTitle("Редактировать тип документа" if is_edit else "Добавить тип документа")

        # Устанавливаем заголовок в UI (если есть)
        if hasattr(self, 'titleLabel'):
            self.titleLabel.setText("Редактировать тип документа" if is_edit else "Новый тип документа")

        # Устанавливаем размер окна
        self.resize(600, 850)

        # Инициализация динамических параметров
        self.setup_parameters_ui()

        # Заполняем текстовое поле
        if hasattr(self, 'nameInput'):
            self.nameInput.setText(self.item.get('name', ''))
        else:
            print("[WARNING] nameInput не найден в UI")

        # Устанавливаем чекбокс
        if hasattr(self, 'autoNumberCheckbox'):
            self.autoNumberCheckbox.setChecked(self.auto_number)
            print(f"[DEBUG] Чекбокс установлен в {self.auto_number}")
        else:
            print("[WARNING] autoNumberCheckbox не найден в UI")

        # Настройка шаблона
        if hasattr(self, 'templatePathInput'):
            # Загружаем сохраненный путь к шаблону
            template_path = self.item.get('template_path', '')
            self.templatePathInput.setText(template_path)

            # Подключаем кнопки
            if hasattr(self, 'browseBtn'):
                self.browseBtn.clicked.connect(self.browse_template)
            if hasattr(self, 'clearBtn'):
                self.clearBtn.clicked.connect(self.clear_template)
            print(f"[DEBUG] Загружен шаблон: {template_path}")
        else:
            print("[WARNING] templatePathInput не найден в UI")

        # Подключаем сигналы
        if hasattr(self, 'saveButton'):
            self.saveButton.clicked.connect(self.save_and_accept)
        else:
            print("[WARNING] saveButton не найден в UI")

    def set_auto_number_state(self, value: bool):
        """
        Устанавливает состояние чекбокса автоматической нумерации.
        Используется для синхронизации при загрузке данных.
        """
        if hasattr(self, 'autoNumberCheckbox'):
            self.autoNumberCheckbox.setChecked(value)
            self.auto_number = value
            print(f"[DEBUG] Установлен чекбокс autoNumberCheckbox = {value}")
        else:
            print("[WARNING] autoNumberCheckbox не найден, сохраняем значение в self.auto_number")
            self.auto_number = value

    def setup_ui_fallback(self):
        """Создает UI программно, если файл .ui не найден"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        self.titleLabel = QtWidgets.QLabel("Новый тип документа")
        self.titleLabel.setStyleSheet("font-size: 18px; font-weight: bold; color: black;")
        main_layout.addWidget(self.titleLabel)

        name_label = QtWidgets.QLabel("Название типа*:")
        name_label.setStyleSheet("color: black;")
        main_layout.addWidget(name_label)

        self.nameInput = QtWidgets.QLineEdit()
        self.nameInput.setStyleSheet("border-radius: 8px; border: 1px solid #ccab6e; padding: 8px; color: black;")
        main_layout.addWidget(self.nameInput)

        auto_number_label = QtWidgets.QLabel("Настройки номера:")
        auto_number_label.setStyleSheet("color: black;")
        main_layout.addWidget(auto_number_label)

        self.autoNumberCheckbox = QtWidgets.QCheckBox("Автоматически формировать номер документа")
        self.autoNumberCheckbox.setStyleSheet("""
            QCheckBox {
                spacing: 10px;
                font-size: 14px;
                padding: 8px;
                border: 1px solid #ccab6e;
                border-radius: 6px;
                background: white;
                color: black;
            }
        """)
        main_layout.addWidget(self.autoNumberCheckbox)

        # Поле для шаблона
        template_label = QtWidgets.QLabel("Шаблон документа:")
        template_label.setStyleSheet("color: black; font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(template_label)

        template_layout = QtWidgets.QHBoxLayout()
        self.templatePathInput = QtWidgets.QLineEdit()
        self.templatePathInput.setPlaceholderText("Путь к файлу шаблона...")
        self.templatePathInput.setStyleSheet(
            "border-radius: 8px; border: 1px solid #ccab6e; padding: 8px; color: black; background: white;")
        self.templatePathInput.setReadOnly(True)
        template_layout.addWidget(self.templatePathInput)

        self.browseBtn = QtWidgets.QPushButton("Обзор...")
        self.browseBtn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #ccab6e;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.browseBtn.clicked.connect(self.browse_template)
        template_layout.addWidget(self.browseBtn)

        self.clearBtn = QtWidgets.QPushButton("Очистить")
        self.clearBtn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #ccab6e;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.clearBtn.clicked.connect(self.clear_template)
        template_layout.addWidget(self.clearBtn)
        main_layout.addLayout(template_layout)

        main_layout.addSpacing(10)

        params_label = QtWidgets.QLabel("Выберите активные параметры:")
        params_label.setStyleSheet("color: black;")
        main_layout.addWidget(params_label)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")

        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QVBoxLayout(self.scroll_content)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        self.saveButton = QtWidgets.QPushButton("Сохранить")
        self.saveButton.setStyleSheet("""
            QPushButton {
                background-color: #ccab6e;
                color: white;
                border-radius: 8px;
                font-weight: bold;
                font-size: 18px;
                border: none;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #998664;
            }
        """)
        main_layout.addWidget(self.saveButton)

    def setup_parameters_ui(self):
        """Создает интерфейс для выбора параметров"""
        # Ищем правильный контейнер для параметров
        if hasattr(self, 'paramsScrollLayout'):
            # Используем существующий layout из UI
            layout = self.paramsScrollLayout
            print("[DEBUG] Найден paramsScrollLayout из UI")
        elif hasattr(self, 'scroll_layout'):
            # Если есть scroll_layout (для fallback)
            layout = self.scroll_layout
            print("[DEBUG] Используем scroll_layout (fallback)")
        else:
            # Создаем новый layout
            print("[ERROR] Не найден layout для параметров, создаем новый")
            layout = QtWidgets.QVBoxLayout()

            # Проверяем наличие scroll_content
            if hasattr(self, 'scroll_content'):
                self.scroll_content.setLayout(layout)
            elif hasattr(self, 'paramsScrollContent'):
                self.paramsScrollContent.setLayout(layout)
            else:
                # Создаем контейнер
                container = QtWidgets.QWidget()
                container.setLayout(layout)
                if hasattr(self, 'paramsScrollArea'):
                    self.paramsScrollArea.setWidget(container)
                elif hasattr(self, 'scrollArea'):
                    self.scrollArea.setWidget(container)

        # Очищаем существующие параметры
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for param in self.available_parameters:
            frame = QtWidgets.QFrame()
            frame.setObjectName(f"paramFrame_{param}")
            from client.core.themes import get_manager
            _t = get_manager().current
            frame.setStyleSheet(f"""
                QFrame {{
                    border: 1px solid {_t.BORDER_FRAME_SOFT};
                    border-radius: 6px;
                    background: {_t.BG_CARD};
                    margin: 2px;
                }}
                QFrame:hover {{
                    border-color: {_t.ACCENT_PRIMARY};
                    background-color: {_t.BG_HOVER_ACCENT_SOFT};
                }}
            """)
            flayout = QtWidgets.QHBoxLayout(frame)
            flayout.setContentsMargins(10, 5, 10, 5)

            lbl = QtWidgets.QLabel(self.parameter_names[param])
            lbl.setStyleSheet(f"""font-weight: bold; border: none; background-color: transparent; color: {_t.TEXT_MUTED_ALT};""")
            flayout.addWidget(lbl)
            flayout.addStretch()

            btn = QtWidgets.QPushButton()
            btn.setFixedSize(70, 26)
            btn.setObjectName(f"toggleBtn_{param}")
            btn.setProperty("toggle_btn", True)  # Для стилей

            # Проверяем наличие параметра в загруженном списке
            is_active = param in self.selected_parameters
            btn.setProperty("is_on", is_active)
            self.toggle_buttons[param] = btn

            # Принудительно вызываем покраску сразу
            self.update_toggle_style(btn)

            # Если параметр обязательный, отключаем кнопку
            if param in self.mandatory_parameters:
                btn.setEnabled(False)
                btn.setToolTip("Этот параметр обязателен и не может быть отключен")

            # Правильный коннект с сохранением параметров
            btn.clicked.connect(lambda checked, p=param, b=btn: self.toggle_param(p, b))

            flayout.addWidget(btn)
            layout.addWidget(frame)

        layout.addStretch()

    def browse_template(self):
        """Открыть диалог выбора файла шаблона"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл шаблона документа",
            "",
            "Документы (*.docx *.doc *.odt);;Все файлы (*.*)"
        )

        if file_path:
            self.templatePathInput.setText(file_path)
            print(f"[DEBUG] Выбран шаблон: {file_path}")

    def clear_template(self):
        """Очистить путь к шаблону"""
        self.templatePathInput.clear()
        print("[DEBUG] Шаблон очищен")

    def toggle_param(self, param, btn):
        """Меняем состояние при клике"""
        if param in self.mandatory_parameters:
            return

        is_on = not btn.property("is_on")
        btn.setProperty("is_on", is_on)

        if is_on:
            if param not in self.selected_parameters:
                self.selected_parameters.append(param)
        else:
            if param in self.selected_parameters:
                while param in self.selected_parameters:
                    self.selected_parameters.remove(param)

        self.update_toggle_style(btn)
        print(f"[DEBUG] Текущий выбор: {self.selected_parameters}")

    def save_and_accept(self):
        """Сохранение с приведением к единому стандарту"""
        name = ""
        if hasattr(self, 'nameInput'):
            name = self.nameInput.text().strip()

        if not name:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите название!")
            return

        # Убедимся, что обязательные параметры в списке
        for param in self.mandatory_parameters:
            if param not in self.selected_parameters:
                self.selected_parameters.append(param)

        # --- ИЗМЕНЕНИЕ: Формируем данные для сервера ---
        # 1. Преобразуем параметры в словарь fields (как ожидает сервер)
        fields_dict = {param: True for param in self.selected_parameters}

        # 2. Получаем auto_num
        auto_num = False
        if hasattr(self, 'autoNumberCheckbox'):
            auto_num = self.autoNumberCheckbox.isChecked()
        else:
            auto_num = self.auto_number

        # 3. Формируем данные для сервера
        self.item['name'] = name
        self.item['fields'] = fields_dict
        self.item['auto_num'] = auto_num

        # 4. Сохраняем также в старом формате для совместимости с UI
        self.item['columns'] = ",".join(self.selected_parameters)
        self.item['parameters'] = self.selected_parameters
        self.item['auto_numbering'] = auto_num

        # Сохраняем путь к шаблону
        if hasattr(self, 'templatePathInput'):
            template_path = self.templatePathInput.text().strip()
            self.item['template_path'] = template_path if template_path else None
            print(f"[DEBUG] Сохранен шаблон: {self.item.get('template_path')}")

        # Сохраняем выбранные направления только если параметр direction_name активен
        if 'direction_name' in self.selected_parameters:
            if hasattr(self, 'direction_btn'):
                selected_ids = self.direction_btn.property("selected_ids") or []
                if selected_ids:
                    self.item['direction_ids'] = selected_ids
                    self.item['direction_id'] = ",".join(str(id) for id in selected_ids)
                else:
                    self.item['direction_ids'] = []
                    self.item['direction_id'] = None
        else:
            self.item['direction_ids'] = []
            self.item['direction_id'] = None

        print(
            f"[DEBUG] Диалог закрыт. Данные для сервера: fields={self.item['fields']}, auto_num={self.item['auto_num']}")
        print(f"[DEBUG] Направление включено: {'direction_name' in self.selected_parameters}")
        print(f"[DEBUG] Выбрано направлений: {self.item.get('direction_ids')}")
        self.accept()

    def get_data(self):
        """Возвращает полный набор данных в формате для сервера"""
        name = ""
        if hasattr(self, 'nameInput'):
            name = self.nameInput.text().strip()

        # Убедимся, что обязательные параметры в списке
        for param in self.mandatory_parameters:
            if param not in self.selected_parameters:
                self.selected_parameters.append(param)

        # Преобразуем параметры в словарь fields
        fields_dict = {param: True for param in self.selected_parameters}

        # Получаем auto_num
        auto_num = False
        if hasattr(self, 'autoNumberCheckbox'):
            auto_num = self.autoNumberCheckbox.isChecked()
        else:
            auto_num = self.auto_number

        # Формируем результат
        result = {
            'name': name,
            'fields': fields_dict,
            'auto_num': auto_num,
            # Сохраняем также старые поля для совместимости
            'columns': ",".join(self.selected_parameters),
            'parameters': self.selected_parameters,
            'parameter_names': {p: self.parameter_names[p] for p in self.selected_parameters}
        }

        # Добавляем шаблон
        if hasattr(self, 'templatePathInput'):
            template_path = self.templatePathInput.text().strip()
            result['template_path'] = template_path if template_path else None

        # Добавляем направления
        if 'direction_name' in self.selected_parameters:
            if hasattr(self, 'direction_btn'):
                selected_ids = self.direction_btn.property("selected_ids") or []
                if selected_ids:
                    result['direction_ids'] = selected_ids
                    result['direction_id'] = ",".join(str(id) for id in selected_ids)
                else:
                    result['direction_ids'] = []
                    result['direction_id'] = None
        else:
            result['direction_ids'] = []
            result['direction_id'] = None

        return result

    def update_toggle_style(self, toggle_btn):
        """Обновляет стиль Toggle Switch в зависимости от состояния"""
        is_on = toggle_btn.property("is_on")

        if not toggle_btn.isEnabled():
            if is_on:
                toggle_btn.setText("ON")
                toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #81C784;
                        color: white;
                        border-radius: 13px;
                        border: 2px solid #4CAF50;
                        font-size: 12px;
                        font-weight: bold;
                        padding-left: 2px;
                        padding-right: 8px;
                        text-align: right;
                        margin: 0;
                        opacity: 0.8;
                    }
                """)
            else:
                toggle_btn.setText("OFF")
                toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E57373;
                        color: white;
                        border-radius: 13px;
                        border: 2px solid #E53935;
                        font-size: 12px;
                        font-weight: bold;
                        padding-left: 8px;
                        padding-right: 2px;
                        text-align: left;
                        margin: 0;
                        opacity: 0.8;
                    }
                """)
        else:
            if is_on:
                toggle_btn.setText("ON")
                toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #81C784;
                        color: white;
                        border-radius: 13px;
                        border: 1px solid #66BB6A;
                        font-size: 12px;
                        font-weight: bold;
                        padding-left: 2px;
                        padding-right: 8px;
                        text-align: right;
                        margin: 0;
                    }
                    QPushButton:hover {
                        background-color: #66BB6A;
                        border: 1px solid #4CAF50;
                    }
                """)
            else:
                toggle_btn.setText("OFF")
                toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E57373;
                        color: white;
                        border-radius: 13px;
                        border: 1px solid #EF5350;
                        font-size: 12px;
                        font-weight: bold;
                        padding-left: 8px;
                        padding-right: 2px;
                        text-align: left;
                        margin: 0;
                    }
                    QPushButton:hover {
                        background-color: #EF5350;
                        border: 1px solid #E53935;
                    }
                """)

    def validate(self):
        """Валидация данных"""
        errors = []

        name = ""
        if hasattr(self, 'nameInput'):
            name = self.nameInput.text().strip()

        if not name:
            errors.append("Название типа обязательно для заполнения")

        if not self.selected_parameters:
            errors.append("Должен быть выбран хотя бы один параметр")

        for param in self.mandatory_parameters:
            if param not in self.selected_parameters:
                errors.append(f"Параметр '{self.parameter_names[param]}' обязателен")

        return errors

    def reapply_theme(self):
        from client.core.themes import get_manager
        _t = get_manager().current
        for param, btn in getattr(self, 'toggle_buttons', {}).items():
            self.update_toggle_style(btn)


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Быстрый тест нового документа
    dialog = DocumentTypeDialog(None)
    if dialog.exec():
        print("Результат:", dialog.get_data())

    sys.exit()