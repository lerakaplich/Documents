import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QApplication,
    QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.uic import loadUi

from client.windows.system.tags.tag_card import TagCard
from client.windows.animations.floating_action_button import FloatingActionButton


class TagsPage(QWidget):
    """Страница тегов с поиском, сортировкой и отображением в сетке (2 колонки)"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Данные
        self.tags = []
        self.filtered_tags = []

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
        self.floating_btn.clicked.connect(self.on_add_tag)

        # Подключаемся к скроллу
        self.scrollArea.verticalScrollBar().valueChanged.connect(self.on_scroll)

        # Скрываем кнопку сброса при старте
        self.btnResetFilters.hide()

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'tags', 'tag_page.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Настройка сигналов"""
        self.btnSort.clicked.connect(self.show_sort_menu)
        self.searchEdit.textChanged.connect(self.on_search_changed)
        self.btnResetFilters.clicked.connect(self.reset_all_filters)

    def load_test_data(self):
        """Загрузка тестовых данных"""
        self.tags = [
            {"id": 1, "name": "Срочно", "color": "#FF4444", "documents_count": 12},
            {"id": 2, "name": "Важно", "color": "#FF8800", "documents_count": 8},
            {"id": 3, "name": "На согласовании", "color": "#44AAFF", "documents_count": 5},
            {"id": 4, "name": "Исполнено", "color": "#44CC44", "documents_count": 23},
            {"id": 5, "name": "На контроле", "color": "#AA66CC", "documents_count": 3},
            {"id": 6, "name": "Черновик", "color": "#999999", "documents_count": 7},
            {"id": 7, "name": "Отклонено", "color": "#CC3333", "documents_count": 2},
            {"id": 8, "name": "В работе", "color": "#33CC99", "documents_count": 15},
            {"id": 9, "name": "Архивный", "color": "#6C757D", "documents_count": 45},
            {"id": 10, "name": "Для руководства", "color": "#E83E8C", "documents_count": 6},
            {"id": 11, "name": "Публичный", "color": "#17A2B8", "documents_count": 30},
            {"id": 12, "name": "Конфиденциально", "color": "#DC3545", "documents_count": 4},
            {"id": 13, "name": "Договор", "color": "#FF6B6B", "documents_count": 18},
            {"id": 14, "name": "Приказ", "color": "#4ECDC4", "documents_count": 25},
            {"id": 15, "name": "Распоряжение", "color": "#45B7D1", "documents_count": 14},
            {"id": 16, "name": "Акт", "color": "#96CEB4", "documents_count": 9},
            {"id": 17, "name": "Протокол", "color": "#FFEAA7", "documents_count": 11},
            {"id": 18, "name": "Служебная записка", "color": "#DDA0DD", "documents_count": 33},
            {"id": 19, "name": "Заявление", "color": "#98D8C8", "documents_count": 7},
            {"id": 20, "name": "Отчет", "color": "#F7DC6F", "documents_count": 28},
            {"id": 21, "name": "План работ", "color": "#BB8FCE", "documents_count": 6},
            {"id": 22, "name": "График", "color": "#85C1E9", "documents_count": 4},
            {"id": 23, "name": "Смета", "color": "#F8C471", "documents_count": 16},
            {"id": 24, "name": "Проект", "color": "#82E0AA", "documents_count": 21},
            {"id": 25, "name": "Спецификация", "color": "#F1948A", "documents_count": 3},
            {"id": 26, "name": "Инструкция", "color": "#85929E", "documents_count": 19},
            {"id": 27, "name": "Регламент", "color": "#AED6F1", "documents_count": 8},
            {"id": 28, "name": "Положение", "color": "#D5F5E3", "documents_count": 5},
            {"id": 29, "name": "Устав", "color": "#FADBD8", "documents_count": 1},
            {"id": 30, "name": "Сертификат", "color": "#D4EFDF", "documents_count": 12},
            {"id": 31, "name": "Лицензия", "color": "#F9E79F", "documents_count": 2},
            {"id": 32, "name": "Паспорт изделия", "color": "#D2B4DE", "documents_count": 7},
            {"id": 33, "name": "Технические условия", "color": "#A9DFBF", "documents_count": 4},
            {"id": 34, "name": "Ревизия", "color": "#F5B7B1", "documents_count": 0},
            {"id": 35, "name": "Проверено", "color": "#27AE60", "documents_count": 38},
            {"id": 36, "name": "На доработку", "color": "#E74C3C", "documents_count": 13},
            {"id": 37, "name": "Ожидает ответа", "color": "#F39C12", "documents_count": 9},
            {"id": 38, "name": "Просрочено", "color": "#C0392B", "documents_count": 6},
            {"id": 39, "name": "Выполнено", "color": "#2ECC71", "documents_count": 52},
            {"id": 40, "name": "Отменено", "color": "#95A5A6", "documents_count": 3},
            {"id": 41, "name": "Перенесено", "color": "#7F8C8D", "documents_count": 5},
            {"id": 42, "name": "Приостановлено", "color": "#E67E22", "documents_count": 2},
            {"id": 43, "name": "На экспертизе", "color": "#9B59B6", "documents_count": 8},
            {"id": 44, "name": "Утверждено", "color": "#1ABC9C", "documents_count": 41},
            {"id": 45, "name": "Завизировано", "color": "#3498DB", "documents_count": 17},
            {"id": 46, "name": "На подпись", "color": "#E91E63", "documents_count": 11},
            {"id": 47, "name": "Входящий", "color": "#00BCD4", "documents_count": 24},
            {"id": 48, "name": "Исходящий", "color": "#FF5722", "documents_count": 19},
            {"id": 49, "name": "Внутренний", "color": "#8BC34A", "documents_count": 35},
            {"id": 50, "name": "Для служебного пользования", "color": "#673AB7", "documents_count": 10},
        ]

    def show_sort_menu(self):
        """Показать меню сортировки"""
        menu = QMenu(self)

        # Стилизуем меню
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

    def sort_by_name_asc(self, tags):
        """Сортировка по названию А→Я"""
        return sorted(tags, key=lambda x: x.get('name', '').lower())

    def sort_by_name_desc(self, tags):
        """Сортировка по названию Я→А"""
        return sorted(tags, key=lambda x: x.get('name', '').lower(), reverse=True)

    def sort_by_count_asc(self, tags):
        """Сортировка по количеству документов (возрастание)"""
        return sorted(tags, key=lambda x: x.get('documents_count', 0))

    def sort_by_count_desc(self, tags):
        """Сортировка по количеству документов (убывание)"""
        return sorted(tags, key=lambda x: x.get('documents_count', 0), reverse=True)

    def apply_sort(self, sort_func, sort_name):
        """Применить сортировку"""
        self.current_sort = sort_name
        # Показываем короткое имя сортировки
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

    def filter_and_sort_tags(self):
        """Фильтрация и сортировка тегов"""
        filtered = self.tags.copy()

        # Поиск
        search_text = self.searchEdit.text().strip().lower()
        if search_text:
            filtered = [
                tag for tag in filtered
                if search_text in tag.get('name', '').lower()
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
        """Обновление отображения тегов в сетке (2 колонки)"""
        # Очищаем сетку
        for i in reversed(range(self.tagsGridLayout.count())):
            widget = self.tagsGridLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Получаем отфильтрованные и отсортированные теги
        self.filtered_tags = self.filter_and_sort_tags()

        # Отображаем теги в сетке - 2 КОЛОНКИ
        row, col = 0, 0
        max_cols = 2

        for tag in self.filtered_tags:
            tag_card = TagCard(tag)
            tag_card.edit_clicked.connect(self.on_edit_tag)
            tag_card.delete_clicked.connect(self.on_delete_tag)

            # Растягиваем карточку по ширине колонки
            tag_card.setMinimumWidth(350)

            self.tagsGridLayout.addWidget(tag_card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Добавляем растяжку в конец, чтобы карточки прижимались к верху
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.tagsGridLayout.addWidget(spacer, row + 1, 0, 1, max_cols)

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

    def on_add_tag(self):
        """Обработчик нажатия на плавающую кнопку добавления тега"""
        print("Добавление нового тега")
        QMessageBox.information(
            self,
            "Новый тег",
            "Создание нового тега\n\nЭта функция в разработке."
        )

    def on_edit_tag(self, tag_data):
        """Обработка редактирования тега"""
        print(f"Редактирование тега: {tag_data.get('name')} (ID: {tag_data.get('id')})")
        QMessageBox.information(
            self,
            "Редактирование тега",
            f"Редактирование тега: {tag_data.get('name')}\n\nЭта функция в разработке."
        )

    def on_delete_tag(self, tag_id):
        """Обработка удаления тега"""
        tag_name = "Неизвестный тег"
        for tag in self.tags:
            if tag.get('id') == tag_id:
                tag_name = tag.get('name', 'Неизвестный тег')
                break

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить тег «{tag_name}»?\n\n"
            f"Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            print(f"Удаление тега ID: {tag_id}")
            # Удаляем тег из списка
            self.tags = [tag for tag in self.tags if tag.get('id') != tag_id]
            self.update_display()
            QMessageBox.information(
                self,
                "Успешно",
                f"Тег «{tag_name}» успешно удален."
            )

    def add_tag(self, tag_data):
        """Добавление нового тега"""
        # Генерируем новый ID
        max_id = max([tag.get('id', 0) for tag in self.tags], default=0)
        tag_data['id'] = max_id + 1

        self.tags.append(tag_data)
        self.update_display()

    def update_tag(self, tag_id, new_data):
        """Обновление существующего тега"""
        for i, tag in enumerate(self.tags):
            if tag.get('id') == tag_id:
                self.tags[i].update(new_data)
                break

        self.update_display()

    def get_all_tags(self):
        """Возвращает список всех тегов"""
        return self.tags.copy()

    def get_filtered_tags(self):
        """Возвращает список отфильтрованных тегов"""
        return self.filtered_tags.copy()


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = QWidget()
    window.setWindowTitle("Тест - Теги")
    window.setGeometry(100, 100, 1000, 700)

    tags_page = TagsPage()

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(tags_page)

    window.show()
    sys.exit(app.exec())