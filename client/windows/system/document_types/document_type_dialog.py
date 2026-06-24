# client/windows/system/document_types/document_type_dialog.py

import os
from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QFileDialog


class DocumentTypeDialog(QtWidgets.QDialog):
    def __init__(self, parent_editor, item=None):
        super().__init__(parent_editor)

        # Загружаем UI
        ui_path = os.path.join(os.path.dirname(__file__), '../../../ui/system/document_types/document_type_dialog.ui')
        ui_path = os.path.normpath(ui_path)

        if os.path.exists(ui_path):
            uic.loadUi(ui_path, self)
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
            "direction_name": "Направление",  # Теперь можно выключать!
        }

        # СПИСОК ПАРАМЕТРОВ, КОТОРЫЕ НЕЛЬЗЯ ВЫКЛЮЧИТЬ
        self.mandatory_parameters = ['attachment', 'redirect']

        self.available_parameters = list(self.parameter_names.keys())
        self.toggle_buttons = {}  # Словарь для кнопок

        # --- ЖЕСТКАЯ ЛОГИКА ВЫБОРА ---
        self.selected_parameters = []

        # Получаем auto_number из item
        if item and 'auto_number' in item:
            self.auto_number = item.get('auto_number', True)
        else:
            self.auto_number = True

        print(f"[DEBUG] DocumentTypeDialog __init__: auto_number = {self.auto_number} (из item={item})")

        # 1. ПЕРВЫМ ДЕЛОМ смотрим в columns (строка из БД "send_date,subject")
        raw_columns = self.item.get('columns', "")

        if isinstance(raw_columns, str) and raw_columns.strip():
            self.selected_parameters = [f.strip() for f in raw_columns.split(',') if f.strip()]
            print(f"[DEBUG] Взяли данные из строки columns: {self.selected_parameters}")

        # 2. Если в columns пусто, но в parameters лежит список
        elif isinstance(self.item.get('parameters'), list):
            p_list = self.item.get('parameters', [])
            if len(p_list) < len(self.available_parameters) and len(p_list) > 0:
                self.selected_parameters = [str(p).strip() for p in p_list]
                print(f"[DEBUG] Взяли данные из специфичного списка parameters: {self.selected_parameters}")

        # 3. Если это НОВЫЙ документ (нет id), только тогда включаем всё
        if not self.item.get('id') and not self.selected_parameters:
            self.selected_parameters = self.available_parameters.copy()
            print("[DEBUG] Новый документ: включили всё по дефолту")

        # 4. УБЕДИМСЯ, ЧТО ОБЯЗАТЕЛЬНЫЕ ПАРАМЕТРЫ ВСЕГДА В СПИСКЕ
        for param in self.mandatory_parameters:
            if param not in self.selected_parameters:
                self.selected_parameters.append(param)
                print(f"[DEBUG] Добавлен обязательный параметр: {param}")

        print(f"[FINAL CHECK] Итоговый список для кнопок: {self.selected_parameters}")

        # Настройка окна
        is_edit = self.item.get('id') is not None
        self.setWindowTitle("Редактировать тип документа" if is_edit else "Добавить тип документа")

        # Устанавливаем заголовок в UI (если есть)
        if hasattr(self, 'title_label'):
            self.title_label.setText("Редактировать тип документа" if is_edit else "Новый тип документа")

        # Устанавливаем размер окна
        self.resize(600, 850)

        # Инициализация динамических параметров
        self.setup_parameters_ui()

        # Заполняем текстовое поле
        if hasattr(self, 'name_input'):
            self.name_input.setText(self.item.get('name', ''))
        else:
            print("[WARNING] name_input не найден в UI")

        # Устанавливаем чекбокс
        if hasattr(self, 'auto_number_checkbox'):
            self.auto_number_checkbox.setChecked(self.auto_number)
            print(f"[DEBUG] Чекбокс установлен в {self.auto_number}")
        else:
            print("[WARNING] auto_number_checkbox не найден в UI")

        # Настройка шаблона
        if hasattr(self, 'template_path_input'):
            # Загружаем сохраненный путь к шаблону
            template_path = self.item.get('template_path', '')
            self.template_path_input.setText(template_path)

            # Подключаем кнопки
            if hasattr(self, 'browse_template_btn'):
                self.browse_template_btn.clicked.connect(self.browse_template)
            if hasattr(self, 'clear_template_btn'):
                self.clear_template_btn.clicked.connect(self.clear_template)
            print(f"[DEBUG] Загружен шаблон: {template_path}")
        else:
            print("[WARNING] template_path_input не найден в UI")

        # Подключаем сигналы
        if hasattr(self, 'save_btn'):
            self.save_btn.clicked.connect(self.save_and_accept)
        else:
            print("[WARNING] save_btn не найден в UI")

    def setup_ui_fallback(self):
        """Создает UI программно, если файл .ui не найден"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        self.title_label = QtWidgets.QLabel("Новый тип документа")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: black;")
        main_layout.addWidget(self.title_label)

        name_label = QtWidgets.QLabel("Название типа*:")
        name_label.setStyleSheet("color: black;")
        main_layout.addWidget(name_label)

        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setStyleSheet("border-radius: 8px; border: 1px solid #ccab6e; padding: 8px; color: black;")
        main_layout.addWidget(self.name_input)

        auto_number_label = QtWidgets.QLabel("Настройки номера:")
        auto_number_label.setStyleSheet("color: black;")
        main_layout.addWidget(auto_number_label)

        self.auto_number_checkbox = QtWidgets.QCheckBox("Автоматически формировать номер документа")
        self.auto_number_checkbox.setStyleSheet("""
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
        main_layout.addWidget(self.auto_number_checkbox)

        # Поле для шаблона
        template_label = QtWidgets.QLabel("Шаблон документа:")
        template_label.setStyleSheet("color: black; font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(template_label)

        template_layout = QtWidgets.QHBoxLayout()
        self.template_path_input = QtWidgets.QLineEdit()
        self.template_path_input.setPlaceholderText("Путь к файлу шаблона...")
        self.template_path_input.setStyleSheet(
            "border-radius: 8px; border: 1px solid #ccab6e; padding: 8px; color: black; background: white;")
        self.template_path_input.setReadOnly(True)
        template_layout.addWidget(self.template_path_input)

        self.browse_template_btn = QtWidgets.QPushButton("Обзор...")
        self.browse_template_btn.setStyleSheet("""
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
        self.browse_template_btn.clicked.connect(self.browse_template)
        template_layout.addWidget(self.browse_template_btn)

        self.clear_template_btn = QtWidgets.QPushButton("Очистить")
        self.clear_template_btn.setStyleSheet("""
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
        self.clear_template_btn.clicked.connect(self.clear_template)
        template_layout.addWidget(self.clear_template_btn)
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

        self.save_btn = QtWidgets.QPushButton("Сохранить")
        self.save_btn.setStyleSheet("""
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
        main_layout.addWidget(self.save_btn)

    def setup_parameters_ui(self):
        """Создает интерфейс для выбора параметров"""
        # Проверяем, есть ли scroll_layout
        if not hasattr(self, 'scroll_layout'):
            print("[ERROR] scroll_layout не найден в UI, создаем программно")
            self.scroll_layout = QtWidgets.QVBoxLayout()
            self.scroll_content = QtWidgets.QWidget()
            self.scroll_content.setLayout(self.scroll_layout)
            self.scroll_area.setWidget(self.scroll_content)

        # Очищаем существующие параметры
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for param in self.available_parameters:
            frame = QtWidgets.QFrame()
            frame.setStyleSheet("border: 1px solid #E0E0E0; border-radius: 6px; background: white; margin: 2px;")
            flayout = QtWidgets.QHBoxLayout(frame)
            flayout.setContentsMargins(10, 5, 10, 5)

            lbl = QtWidgets.QLabel(self.parameter_names[param])
            lbl.setStyleSheet("font-weight: bold; border: none; color: black;")
            flayout.addWidget(lbl)
            flayout.addStretch()

            btn = QtWidgets.QPushButton()
            btn.setFixedSize(70, 26)

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

            # Правильный коннект
            btn.clicked.connect(lambda checked, p=param, b=btn: self.toggle_param(p, b))

            flayout.addWidget(btn)
            self.scroll_layout.addWidget(frame)

        self.scroll_layout.addStretch()

    def browse_template(self):
        """Открыть диалог выбора файла шаблона"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл шаблона документа",
            "",
            "Документы (*.docx *.doc *.odt);;Все файлы (*.*)"
        )

        if file_path:
            self.template_path_input.setText(file_path)
            print(f"[DEBUG] Выбран шаблон: {file_path}")

    def clear_template(self):
        """Очистить путь к шаблону"""
        self.template_path_input.clear()
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
        if hasattr(self, 'name_input'):
            name = self.name_input.text().strip()

        if not name:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Введите название!")
            return

        # Убедимся, что обязательные параметры в списке
        for param in self.mandatory_parameters:
            if param not in self.selected_parameters:
                self.selected_parameters.append(param)

        # Записываем и как список, и как строку
        self.item['name'] = name
        self.item['columns'] = ",".join(self.selected_parameters)
        self.item['parameters'] = self.selected_parameters

        # Получаем значение auto_number
        if hasattr(self, 'auto_number_checkbox'):
            self.item['auto_number'] = self.auto_number_checkbox.isChecked()
        else:
            self.item['auto_number'] = self.auto_number

        # Сохраняем путь к шаблону
        if hasattr(self, 'template_path_input'):
            template_path = self.template_path_input.text().strip()
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

        print(f"[DEBUG] Диалог закрыт. Подготовлено колонок: {self.item['columns']}")
        print(f"[DEBUG] Направление включено: {'direction_name' in self.selected_parameters}")
        print(f"[DEBUG] Выбрано направлений: {self.item.get('direction_ids')}")
        print(f"[DEBUG] auto_number: {self.item.get('auto_number')}")
        print(f"[DEBUG] template_path: {self.item.get('template_path')}")
        self.accept()

    def get_data(self):
        """Возвращает полный набор данных"""
        name = ""
        if hasattr(self, 'name_input'):
            name = self.name_input.text().strip()

        for param in self.mandatory_parameters:
            if param not in self.selected_parameters:
                self.selected_parameters.append(param)

        columns_str = ",".join(self.selected_parameters)

        result = {
            'name': name,
            'columns': columns_str,
            'parameters': self.selected_parameters,
            'parameter_names': {p: self.parameter_names[p] for p in self.selected_parameters}
        }

        if hasattr(self, 'auto_number_checkbox'):
            result['auto_number'] = self.auto_number_checkbox.isChecked()
        else:
            result['auto_number'] = self.auto_number

        # Добавляем шаблон в результат
        if hasattr(self, 'template_path_input'):
            template_path = self.template_path_input.text().strip()
            result['template_path'] = template_path if template_path else None

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
        if hasattr(self, 'name_input'):
            name = self.name_input.text().strip()

        if not name:
            errors.append("Название типа обязательно для заполнения")

        if not self.selected_parameters:
            errors.append("Должен быть выбран хотя бы один параметр")

        for param in self.mandatory_parameters:
            if param not in self.selected_parameters:
                errors.append(f"Параметр '{self.parameter_names[param]}' обязателен")

        return errors


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Быстрый тест нового документа
    dialog = DocumentTypeDialog(None)
    if dialog.exec():
        print("Результат:", dialog.get_data())

    sys.exit()