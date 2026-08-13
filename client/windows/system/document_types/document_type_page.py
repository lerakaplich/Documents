# client/windows/system/document_types/document_types_page.py

import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QApplication,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

from client.windows.system.document_types.document_type_card import DocumentTypeCard
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.document_types.document_type_dialog import DocumentTypeDialog  # Добавлен импорт


class DocumentTypesPage(QWidget):
    """Страница типов документов с поиском, сортировкой и отображением в 1 колонку"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Данные
        self.document_types = []
        self.filtered_types = []

        # Состояние
        self.current_sort = "А→Я"

        # Инициализация
        self.init_ui()
        self.load_test_data()
        self.setup_connections()
        self.update_display()

    def init_ui(self):
        """Инициализация UI из файла"""
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)

        # Создаем плавающую кнопку
        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.on_add_type)

        # Подключаемся к скроллу
        self.scrollArea.verticalScrollBar().valueChanged.connect(self.on_scroll)

        # Скрываем кнопку сброса при старте
        self.btnResetFilters.hide()

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'document_types', 'document_type_page.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Настройка сигналов"""
        self.btnSort.clicked.connect(self.show_sort_menu)
        self.searchEdit.textChanged.connect(self.on_search_changed)
        self.btnResetFilters.clicked.connect(self.reset_all_filters)

    def load_test_data(self):
        """Загрузка тестовых данных"""
        self.document_types = [
            {"id": 1, "name": "Приказ", "code": "PR", "description": "Приказы по основной деятельности",
             "documents_count": 45},
            {"id": 2, "name": "Распоряжение", "code": "RP", "description": "Распоряжения руководства",
             "documents_count": 32},
            {"id": 3, "name": "Договор", "code": "DG", "description": "Договоры с контрагентами",
             "documents_count": 78},
            {"id": 4, "name": "Акт", "code": "AK", "description": "Акты выполненных работ", "documents_count": 56},
            {"id": 5, "name": "Счет-фактура", "code": "SF", "description": "Счета-фактуры", "documents_count": 120},
            {"id": 6, "name": "Накладная", "code": "NK", "description": "Товарные накладные", "documents_count": 93},
            {"id": 7, "name": "Протокол", "code": "PRT", "description": "Протоколы совещаний", "documents_count": 28},
            {"id": 8, "name": "Служебная записка", "code": "SZ", "description": "Внутренние служебные записки",
             "documents_count": 67},
            {"id": 9, "name": "Заявление", "code": "ZV", "description": "Заявления сотрудников", "documents_count": 34},
            {"id": 10, "name": "Отчет", "code": "OT", "description": "Отчеты о проделанной работе",
             "documents_count": 41},
            {"id": 11, "name": "План работ", "code": "PL", "description": "Планы работ подразделений",
             "documents_count": 15},
            {"id": 12, "name": "График", "code": "GR", "description": "Графики и расписания", "documents_count": 22},
            {"id": 13, "name": "Смета", "code": "SM", "description": "Сметы расходов", "documents_count": 19},
            {"id": 14, "name": "Проект", "code": "PJ", "description": "Проектная документация", "documents_count": 37},
            {"id": 15, "name": "Спецификация", "code": "SP", "description": "Технические спецификации",
             "documents_count": 25},
            {"id": 16, "name": "Инструкция", "code": "IN", "description": "Инструкции и руководства",
             "documents_count": 53},
            {"id": 17, "name": "Регламент", "code": "RG", "description": "Регламенты процессов", "documents_count": 18},
            {"id": 18, "name": "Положение", "code": "PL", "description": "Положения о подразделениях",
             "documents_count": 12},
            {"id": 19, "name": "Устав", "code": "US", "description": "Устав организации", "documents_count": 1},
            {"id": 20, "name": "Сертификат", "code": "SR", "description": "Сертификаты соответствия",
             "documents_count": 8},
            {"id": 21, "name": "Лицензия", "code": "LC", "description": "Лицензии и разрешения", "documents_count": 3},
            {"id": 22, "name": "Паспорт изделия", "code": "PS", "description": "Паспорта на изделия",
             "documents_count": 44},
            {"id": 23, "name": "Технические условия", "code": "TU", "description": "Технические условия",
             "documents_count": 16},
            {"id": 24, "name": "Доверенность", "code": "DV", "description": "Доверенности", "documents_count": 29},
            {"id": 25, "name": "Журнал", "code": "JR", "description": "Журналы учета", "documents_count": 38},
            {"id": 26, "name": "Объяснительная записка", "code": "OZ", "description": "Объяснительные записки",
             "documents_count": 11},
            {"id": 27, "name": "Представление", "code": "PR", "description": "Представления к наградам",
             "documents_count": 7},
            {"id": 28, "name": "Ходатайство", "code": "HD", "description": "Ходатайства", "documents_count": 9},
            {"id": 29, "name": "Заключение", "code": "ZK", "description": "Экспертные заключения",
             "documents_count": 14},
            {"id": 30, "name": "Решение", "code": "RS", "description": "Решения коллегиальных органов",
             "documents_count": 21},
            {"id": 31, "name": "Постановление", "code": "PS", "description": "Постановления", "documents_count": 6},
            {"id": 32, "name": "Уведомление", "code": "UV", "description": "Уведомления и извещения",
             "documents_count": 48},
            {"id": 33, "name": "Извещение", "code": "IZ", "description": "Извещения об изменениях",
             "documents_count": 33},
            {"id": 34, "name": "Заявка", "code": "ZV", "description": "Заявки на закупку", "documents_count": 52},
            {"id": 35, "name": "Счет", "code": "SC", "description": "Счета на оплату", "documents_count": 87},
            {"id": 36, "name": "Акт приема-передачи", "code": "AP", "description": "Акты приема-передачи",
             "documents_count": 31},
            {"id": 37, "name": "Дефектный акт", "code": "DA", "description": "Дефектные акты", "documents_count": 13},
            {"id": 38, "name": "Справка", "code": "SP", "description": "Справки", "documents_count": 42},
            {"id": 39, "name": "Выписка", "code": "VP", "description": "Выписки из документов", "documents_count": 26},
            {"id": 40, "name": "Сводка", "code": "SV", "description": "Сводки и обобщения", "documents_count": 17},
            {"id": 41, "name": "Письмо", "code": "PM", "description": "Деловые письма", "documents_count": 95},
            {"id": 42, "name": "Телеграмма", "code": "TL", "description": "Телеграммы", "documents_count": 2},
            {"id": 43, "name": "Факс", "code": "FX", "description": "Факсимильные сообщения", "documents_count": 5},
            {"id": 44, "name": "Меморандум", "code": "MM", "description": "Меморандумы", "documents_count": 10},
            {"id": 45, "name": "Презентация", "code": "PR", "description": "Презентационные материалы",
             "documents_count": 23},
            {"id": 46, "name": "Бизнес-план", "code": "BP", "description": "Бизнес-планы", "documents_count": 4},
            {"id": 47, "name": "Техническое задание", "code": "TZ", "description": "Технические задания",
             "documents_count": 36},
            {"id": 48, "name": "Реестр", "code": "RR", "description": "Реестры и перечни", "documents_count": 20},
            {"id": 49, "name": "Номенклатура", "code": "NM", "description": "Номенклатура дел", "documents_count": 8},
            {"id": 50, "name": "Штатное расписание", "code": "SR", "description": "Штатное расписание",
             "documents_count": 3},
        ]

    def show_sort_menu(self):
        """Показать меню сортировки"""
        menu = QMenu(self)

        menu.setStyleSheet("""
            QMenu { 
                background-color: white; 
                border: 1px solid #c0c0c0; 
                border-radius: 5px; 
                padding: 5px; 
                color: black;
            }
            QMenu::item { 
                padding: 8px 25px 8px 15px; 
                border-radius: 3px; 
                font-size: 14px; 
            }
            QMenu::item:selected { 
                background-color: #e3f2fd; 
            }
            QMenu::separator { 
                height: 1px; 
                background: #e0e0e0; 
                margin: 5px 10px; 
            }
        """)

        sort_options = {
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
            "По количеству документов (↑)": self.sort_by_count_asc,
            "По количеству документов (↓)": self.sort_by_count_desc,
        }

        for name, func in sort_options.items():
            action = menu.addAction(name)
            action.triggered.connect(lambda checked, f=func, n=name: self.apply_sort(f, n))

        menu.exec(self.btnSort.mapToGlobal(self.btnSort.rect().bottomLeft()))

    def sort_by_name_asc(self, types):
        """Сортировка по названию А→Я"""
        return sorted(types, key=lambda x: x.get('name', '').lower())

    def sort_by_name_desc(self, types):
        """Сортировка по названию Я→А"""
        return sorted(types, key=lambda x: x.get('name', '').lower(), reverse=True)

    def sort_by_count_asc(self, types):
        """Сортировка по количеству документов (возрастание)"""
        return sorted(types, key=lambda x: x.get('documents_count', 0))

    def sort_by_count_desc(self, types):
        """Сортировка по количеству документов (убывание)"""
        return sorted(types, key=lambda x: x.get('documents_count', 0), reverse=True)

    def sort_by_code_asc(self, types):
        """Сортировка по коду А→Я"""
        return sorted(types, key=lambda x: x.get('code', '').lower())

    def sort_by_code_desc(self, types):
        """Сортировка по коду Я→А"""
        return sorted(types, key=lambda x: x.get('code', '').lower(), reverse=True)

    def apply_sort(self, sort_func, sort_name):
        """Применить сортировку"""
        self.current_sort = sort_name
        short_name = sort_name.split('(')[0].strip() if '(' in sort_name else sort_name
        self.btnSort.setText(f"Сортировка ▼ ({short_name})")
        self.update_reset_button_visibility()
        self.update_display()

    def on_search_changed(self):
        """Обработчик изменения текста поиска"""
        self.update_reset_button_visibility()
        self.update_display()

    def has_active_filters(self):
        """Проверяет, есть ли активные фильтры"""
        if self.searchEdit.text().strip():
            return True

        if self.current_sort != "А→Я":
            return True

        return False

    def update_reset_button_visibility(self):
        """Показать или скрыть кнопку сброса"""
        if self.has_active_filters():
            self.btnResetFilters.show()
        else:
            self.btnResetFilters.hide()

    def reset_all_filters(self):
        """Сброс всех фильтров и поиска"""
        self.searchEdit.clear()

        self.current_sort = "А→Я"
        self.btnSort.setText("Сортировка ▼")

        self.btnResetFilters.hide()
        self.update_display()

    def filter_and_sort_types(self):
        """Фильтрация и сортировка типов документов"""
        filtered = self.document_types.copy()

        # Поиск
        search_text = self.searchEdit.text().strip().lower()
        if search_text:
            filtered = [
                dt for dt in filtered
                if search_text in dt.get('name', '').lower() or
                   search_text in dt.get('code', '').lower() or
                   search_text in dt.get('description', '').lower()
            ]

        # Сортировка
        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
            "По количеству документов (↑)": self.sort_by_count_asc,
            "По количеству документов (↓)": self.sort_by_count_desc,
        }

        sort_func = sort_methods.get(self.current_sort, self.sort_by_name_asc)
        return sort_func(filtered)

    def update_display(self):
        """Обновление отображения типов документов в 2 колонки"""
        # Очищаем layout
        for i in reversed(range(self.typesLayout.count())):
            widget = self.typesLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Получаем отфильтрованные и отсортированные типы
        self.filtered_types = self.filter_and_sort_types()

        # Создаем горизонтальный layout для двух колонок
        h_layout = QHBoxLayout()
        h_layout.setSpacing(10)  # Расстояние между колонками
        h_layout.setContentsMargins(0, 0, 0, 0)

        # Создаем две колонки
        left_column = QVBoxLayout()
        left_column.setSpacing(10)  # Расстояние между карточками в колонке
        left_column.setContentsMargins(0, 0, 0, 0)

        right_column = QVBoxLayout()
        right_column.setSpacing(10)
        right_column.setContentsMargins(0, 0, 0, 0)

        # Распределяем карточки по двум колонкам (поочередно)
        for i, doc_type in enumerate(self.filtered_types):
            type_card = DocumentTypeCard(doc_type)
            type_card.edit_clicked.connect(self.on_edit_type)
            type_card.delete_clicked.connect(self.on_delete_type)

            if i % 2 == 0:
                left_column.addWidget(type_card)
            else:
                right_column.addWidget(type_card)

        # Добавляем колонки в горизонтальный layout
        h_layout.addLayout(left_column)
        h_layout.addLayout(right_column)

        # Добавляем горизонтальный layout в основной вертикальный
        self.typesLayout.addLayout(h_layout)

        # Добавляем растяжку в конец
        self.typesLayout.addStretch()

        # Обновляем позицию плавающей кнопки
        self.position_floating_button()

    def position_floating_button(self):
        """Позиционирование плавающей кнопки в правом нижнем углу"""
        if hasattr(self, 'floating_btn'):
            margin = 20
            x = self.width() - self.floating_btn.width() - margin
            y = self.height() - self.floating_btn.height() - margin
            self.floating_btn.update_base_position(x, y)
            self.floating_btn.raise_()

    def on_scroll(self, value):
        """Обработчик скролла"""
        if hasattr(self, 'floating_btn'):
            self.floating_btn.hide_with_animation()
            self.floating_btn.start_hide_timer()

    def resizeEvent(self, event):
        """Обработчик изменения размера для позиционирования кнопки"""
        super().resizeEvent(event)
        self.position_floating_button()

    def on_add_type(self):
        """Обработчик нажатия на плавающую кнопку добавления типа"""
        # Создаем диалог для нового типа
        dialog = DocumentTypeDialog(self, item={})

        if dialog.exec():
            # Получаем данные из диалога
            new_type_data = dialog.get_data()

            # Добавляем ID
            max_id = max([dt.get('id', 0) for dt in self.document_types], default=0)
            new_type_data['id'] = max_id + 1

            # Добавляем стандартные поля
            new_type_data['code'] = new_type_data.get('name', '')[:3].upper()
            new_type_data['description'] = new_type_data.get('description', '')
            new_type_data['documents_count'] = 0

            # Добавляем в список
            self.document_types.append(new_type_data)

            # Обновляем отображение
            self.update_display()

            # Показываем сообщение об успехе
            QMessageBox.information(
                self,
                "Успешно",
                f"Тип документа «{new_type_data.get('name')}» успешно создан."
            )

    def on_edit_type(self, type_data):
        """Обработка редактирования типа документа"""
        # Находим полные данные типа
        full_type_data = None
        for dt in self.document_types:
            if dt.get('id') == type_data.get('id'):
                full_type_data = dt.copy()
                break

        if not full_type_data:
            QMessageBox.warning(self, "Ошибка", "Тип документа не найден")
            return

        # Создаем диалог с существующими данными
        dialog = DocumentTypeDialog(self, item=full_type_data)

        if dialog.exec():
            # Получаем обновленные данные
            updated_data = dialog.get_data()

            # Обновляем существующий тип
            for i, dt in enumerate(self.document_types):
                if dt.get('id') == type_data.get('id'):
                    # Сохраняем ID и другие неизменяемые поля
                    updated_data['id'] = dt.get('id')
                    updated_data['code'] = dt.get('code', '')
                    updated_data['documents_count'] = dt.get('documents_count', 0)

                    # Обновляем данные
                    self.document_types[i].update(updated_data)
                    break

            # Обновляем отображение
            self.update_display()

            # Показываем сообщение об успехе
            QMessageBox.information(
                self,
                "Успешно",
                f"Тип документа «{updated_data.get('name')}» успешно обновлен."
            )

    def on_delete_type(self, type_id):
        """Обработка удаления типа документа"""
        type_name = "Неизвестный тип"
        for dt in self.document_types:
            if dt.get('id') == type_id:
                type_name = dt.get('name', 'Неизвестный тип')
                break

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить тип документа «{type_name}»?\n\n"
            f"Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            print(f"Удаление типа ID: {type_id}")
            self.document_types = [dt for dt in self.document_types if dt.get('id') != type_id]
            self.update_display()
            QMessageBox.information(
                self,
                "Успешно",
                f"Тип документа «{type_name}» успешно удален."
            )

    def add_type(self, type_data):
        """Добавление нового типа документа"""
        max_id = max([dt.get('id', 0) for dt in self.document_types], default=0)
        type_data['id'] = max_id + 1

        self.document_types.append(type_data)
        self.update_display()

    def update_type(self, type_id, new_data):
        """Обновление существующего типа документа"""
        for i, dt in enumerate(self.document_types):
            if dt.get('id') == type_id:
                self.document_types[i].update(new_data)
                break

        self.update_display()

    def get_all_types(self):
        """Возвращает список всех типов документов"""
        return self.document_types.copy()

    def get_filtered_types(self):
        """Возвращает список отфильтрованных типов"""
        return self.filtered_types.copy()


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = QWidget()
    window.setWindowTitle("Тест - Типы документов")
    window.setGeometry(100, 100, 1000, 700)

    types_page = DocumentTypesPage()

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(types_page)

    window.show()
    sys.exit(app.exec())