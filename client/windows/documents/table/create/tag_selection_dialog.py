import sys
import os
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QTreeWidget, QTreeWidgetItem, QPushButton,
                             QFrame, QWidget, QApplication, QHeaderView,
                             QStyledItemDelegate, QStyle, QStyleOptionViewItem)
from PyQt6.QtCore import Qt, QEvent, QTimer, pyqtSignal, QRect, QSize, QPoint, QPersistentModelIndex
from PyQt6.QtGui import QIcon, QPixmap, QColor, QFont, QPainter, QPen, QBrush, QPalette, QMouseEvent
from PyQt6.uic import loadUi


class TagItemDelegate(QStyledItemDelegate):
    """
    Делегат для отображения тегов с кастомными чекбоксами, цветом и приоритетом
    """

    def __init__(self, checked_path, unchecked_path, parent=None):
        super().__init__(parent)
        self.checked_pixmap = QPixmap(checked_path)
        self.unchecked_pixmap = QPixmap(unchecked_path)
        self.hovered_index = None  # Индекс элемента под мышью
        self.tree_widget = parent

        # Масштабируем иконки до размера 18x18
        self.checked_pixmap = self.checked_pixmap.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio,
                                                         Qt.TransformationMode.SmoothTransformation)
        self.unchecked_pixmap = self.unchecked_pixmap.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio,
                                                             Qt.TransformationMode.SmoothTransformation)

    def paint(self, painter, option, index):
        """
        Отрисовка элемента с кастомным чекбоксом, цветом и приоритетом
        """
        # Получаем данные
        tag_data = index.data(Qt.ItemDataRole.UserRole)
        if not tag_data:
            super().paint(painter, option, index)
            return

        # Сохраняем состояние painter
        painter.save()

        # Определяем состояние
        is_selected = option.state & QStyle.StateFlag.State_Selected

        # Проверяем наведение
        is_hovered = False
        if self.hovered_index is not None and self.hovered_index.isValid():
            hover_row = self.hovered_index.row()
            hover_parent = self.hovered_index.parent()
            current_row = index.row()
            current_parent = index.parent()
            if hover_row == current_row and hover_parent == current_parent:
                is_hovered = True

        # Фон - как у сотрудников
        if is_selected:
            bg_color = QColor(204, 171, 110)  # #ccab6e - золотой
            text_color = QColor(255, 255, 255)  # белый текст на золотом фоне
        elif is_hovered:
            bg_color = QColor(240, 240, 240)  # светло-серый
            text_color = QColor(0, 0, 0)
        else:
            bg_color = QColor(255, 255, 255)  # белый фон по умолчанию
            text_color = QColor(0, 0, 0)  # черный текст

        # Заливаем фон на ВСЮ ширину элемента
        painter.fillRect(option.rect, bg_color)

        # Определяем цвет приоритета
        priority = tag_data.get('priority', 'normal')
        priority_colors = {
            'urgent': QColor(255, 0, 0),
            'important': QColor(255, 165, 0),
            'normal': QColor(128, 128, 128)
        }
        priority_color = priority_colors.get(priority, QColor(128, 128, 128))

        # Если выделено - приоритет белый (как у сотрудников)
        if is_selected:
            priority_color = QColor(255, 255, 255)

        # Параметры отступов
        left_margin = 8
        item_height = option.rect.height()

        # 1. Рисуем чекбокс
        check_x = option.rect.x() + left_margin
        check_y = option.rect.y() + (item_height - 18) // 2
        check_rect = QRect(check_x, check_y, 18, 18)

        is_checked = tag_data.get('checked', False)
        if is_checked:
            painter.drawPixmap(check_rect, self.checked_pixmap)
        else:
            painter.drawPixmap(check_rect, self.unchecked_pixmap)

        # 2. Рисуем цветовой кружок
        circle_x = check_x + 18 + 12
        circle_size = 20
        circle_y = option.rect.y() + (item_height - circle_size) // 2
        circle_rect = QRect(circle_x, circle_y, circle_size, circle_size)

        # Получаем цвет тега
        color_hex = tag_data.get('color', '#808080')
        color = QColor(color_hex)

        # Если выделено, делаем кружок светлее
        if is_selected:
            color = color.lighter(150)

        # Рисуем кружок
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor(232, 220, 200), 1))
        painter.drawEllipse(circle_rect)

        # 3. Рисуем название тега
        name_x = circle_x + circle_size + 12
        name_rect = QRect(name_x, option.rect.y(),
                          option.rect.width() - name_x - 130,
                          item_height)

        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(text_color)

        name = tag_data.get('name', '')
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        # 4. Рисуем приоритет (справа)
        priority_x = option.rect.width() - 120
        priority_rect = QRect(priority_x, option.rect.y(), 110, item_height)

        priority_text = self.get_priority_text(priority)

        # Цвет текста приоритета
        painter.setPen(priority_color)

        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(priority_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                         priority_text)

        painter.restore()

    def get_priority_text(self, priority):
        """Возвращает текст для отображения приоритета"""
        priority_map = {
            'urgent': 'Приоритет: 1',
            'important': 'Приоритет: 2',
            'normal': 'Приоритет: 3'
        }
        return priority_map.get(priority, 'Приоритет: 3')

    def sizeHint(self, option, index):
        """Возвращает рекомендуемый размер для элемента"""
        return QSize(option.rect.width(), 40)


class TagTreeWidget(QTreeWidget):
    """Кастомный QTreeWidget для отслеживания наведения мыши"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.delegate = None
        self.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.viewport().setMouseTracking(True)

    def setItemDelegate(self, delegate):
        super().setItemDelegate(delegate)
        self.delegate = delegate

    def mouseMoveEvent(self, event):
        if self.delegate:
            pos = event.position().toPoint()
            index = self.indexAt(pos)
            old_hover = self.delegate.hovered_index

            if index.isValid():
                persistent_index = QPersistentModelIndex(index)
                is_new = False
                if old_hover is None or not old_hover.isValid():
                    is_new = True
                elif old_hover.row() != persistent_index.row() or old_hover.parent() != persistent_index.parent():
                    is_new = True

                if is_new:
                    self.delegate.hovered_index = persistent_index
                    self.viewport().update()
            else:
                if old_hover is not None and old_hover.isValid():
                    self.delegate.hovered_index = None
                    self.viewport().update()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.delegate and self.delegate.hovered_index is not None and self.delegate.hovered_index.isValid():
            self.delegate.hovered_index = None
            self.viewport().update()
        super().leaveEvent(event)


class TagSelectionDialog(QDialog):
    """
    Диалог выбора тегов с кастомными чекбоксами, цветами и приоритетами
    """
    tags_selected = pyqtSignal(list)

    def __init__(self, tags_list=None, parent=None):
        super().__init__(parent)

        # Инициализация данных
        self.tags = tags_list or []
        self.filtered_tags = self.tags.copy()
        self.selected_tags = []

        # Пути к иконкам чекбоксов
        self.checked_icon_path = self.get_icon_path("cb_checked.png")
        self.unchecked_icon_path = self.get_icon_path("cb_unchecked.png")

        # Загружаем UI
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)
        else:
            print(f"UI файл не найден: {ui_path}")
            # Создаем UI программно, если файл не найден
            self._create_ui()

        # Заменяем стандартный QTreeWidget на кастомный
        self.replace_tree_widget()

        # Настройка дерева
        self.setup_tree_widget()

        # Загрузка данных
        self.load_tags()

        # Подключение сигналов
        if hasattr(self, 'searchEdit'):
            self.searchEdit.textChanged.connect(self.filter_tags)
        if hasattr(self, 'treeWidget'):
            self.treeWidget.itemClicked.connect(self.on_item_clicked)
        if hasattr(self, 'selectButton'):
            self.selectButton.clicked.connect(self.on_select)
        if hasattr(self, 'cancelButton'):
            self.cancelButton.clicked.connect(self.reject)

        # Обновление информации о выбранных тегах
        self.update_selection_info()

        # Установка фокуса на поле поиска
        if hasattr(self, 'searchEdit'):
            self.searchEdit.setFocus()

    def replace_tree_widget(self):
        """Заменяет стандартный QTreeWidget на кастомный TagTreeWidget"""
        if hasattr(self, 'treeWidget'):
            parent = self.treeWidget.parent()
            geometry = self.treeWidget.geometry()
            minimum_size = self.treeWidget.minimumSize()
            size_policy = self.treeWidget.sizePolicy()
            object_name = self.treeWidget.objectName()

            header_text = self.treeWidget.headerItem().text(0) if self.treeWidget.headerItem() else "Теги"

            old_tree = self.treeWidget
            new_tree = TagTreeWidget(parent)
            new_tree.setObjectName(object_name)
            new_tree.setGeometry(geometry)
            new_tree.setMinimumSize(minimum_size)
            new_tree.setSizePolicy(size_policy)
            new_tree.setHeaderLabel(header_text)

            layout = parent.layout()
            if layout:
                index = layout.indexOf(old_tree)
                if index >= 0:
                    layout.removeWidget(old_tree)
                    layout.insertWidget(index, new_tree)

            old_tree.deleteLater()
            self.treeWidget = new_tree

    def _create_ui(self):
        """Создает UI программно, если файл не найден"""
        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("Выбор тегов")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Инструкция
        instruction_label = QLabel("Выберите теги:")
        layout.addWidget(instruction_label)

        # Поиск
        self.searchEdit = QLineEdit()
        self.searchEdit.setPlaceholderText("Поиск тегов...")
        layout.addWidget(self.searchEdit)

        # Дерево
        self.treeWidget = TagTreeWidget()
        self.treeWidget.setHeaderLabel("Теги")
        layout.addWidget(self.treeWidget)

        # Информация о выбранных
        self.selectionInfoLabel = QLabel("Выбрано: 0 тегов")
        layout.addWidget(self.selectionInfoLabel)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.selectButton = QPushButton("Выбрать")
        self.cancelButton = QPushButton("Отмена")
        button_layout.addWidget(self.selectButton)
        button_layout.addWidget(self.cancelButton)
        layout.addLayout(button_layout)

    def get_icon_path(self, icon_name):
        """Определяет путь к иконке"""
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Путь к файлу: D:\Documents\client\windows\documents\table\create\tag_selection_dialog.py
        # Поднимаемся на 4 уровня, чтобы получить D:\Documents\client\
        root_dir = current_dir
        for _ in range(4):
            root_dir = os.path.dirname(root_dir)

        # Проверяем несколько возможных путей
        possible_paths = [
            os.path.join(root_dir, "icons", icon_name),  # D:\Documents\client\icons\cb_checked.png
            os.path.join(root_dir, "client", "icons", icon_name),
            os.path.join(current_dir, "icons", icon_name),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                print(f"Найдена иконка: {path}")
                return path

        # Если не найдено, возвращаем путь по умолчанию
        default_path = os.path.join(root_dir, "icons", icon_name)
        print(f"Иконка не найдена, используем путь по умолчанию: {default_path}")
        return default_path

    def get_ui_path(self):
        """Определяет путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Путь к файлу: D:\Documents\client\windows\documents\table\create\tag_selection_dialog.py
        # Поднимаемся на 4 уровня, чтобы получить D:\Documents\client\
        root_dir = current_dir
        for _ in range(4):
            root_dir = os.path.dirname(root_dir)

        ui_path = os.path.join(root_dir, 'ui', 'documents', 'create', 'tag_selection_dialog.ui')

        if not os.path.exists(ui_path):
            print(f"UI файл не найден: {ui_path}")
        return ui_path

    def _get_root_dir(self) -> str:
        """Определяет корневую директорию проекта"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = current_dir
        for _ in range(4):
            root_dir = os.path.dirname(root_dir)
        return root_dir

    def setup_tree_widget(self):
        """Настройка виджета дерева"""
        if not hasattr(self, 'treeWidget'):
            return

        # Настройка заголовка
        self.treeWidget.setHeaderLabel("Теги")
        self.treeWidget.setIndentation(10)

        # Создаем и устанавливаем делегат для кастомных чекбоксов
        if os.path.exists(self.checked_icon_path) and os.path.exists(self.unchecked_icon_path):
            self.delegate = TagItemDelegate(self.checked_icon_path,
                                            self.unchecked_icon_path,
                                            self.treeWidget)
            self.treeWidget.setItemDelegate(self.delegate)
            print("Делегат успешно установлен")
        else:
            print(f"Предупреждение: Не найдены иконки чекбоксов")
            print(f"Проверьте пути: {self.checked_icon_path}")
            print(f"и {self.unchecked_icon_path}")

    def load_tags(self):
        """Загрузка тегов в дерево"""
        if not hasattr(self, 'treeWidget'):
            return

        self.treeWidget.blockSignals(True)
        self.treeWidget.clear()

        # Сортируем теги по приоритету
        priority_order = {'urgent': 0, 'important': 1, 'normal': 2}
        sorted_tags = sorted(self.filtered_tags,
                             key=lambda x: priority_order.get(x.get('priority', 'normal'), 3))

        for tag in sorted_tags:
            # Создаем элемент
            item = QTreeWidgetItem()

            # Сохраняем данные тега в элементе
            tag_data = tag.copy()
            tag_data['checked'] = any(t.get('id') == tag.get('id') for t in self.selected_tags)

            item.setData(0, Qt.ItemDataRole.UserRole, tag_data)
            item.setSizeHint(0, QSize(0, 40))

            self.treeWidget.addTopLevelItem(item)

        self.treeWidget.blockSignals(False)

    def filter_tags(self, text):
        """Фильтрация тегов по строке поиска"""
        search_text = text.lower().strip()

        if not search_text:
            self.filtered_tags = self.tags.copy()
        else:
            self.filtered_tags = [tag for tag in self.tags
                                  if search_text in tag.get('name', '').lower()]

        self.load_tags()

    def on_item_clicked(self, item, column):
        """Обработка клика по элементу дерева"""
        # Получаем данные тега
        tag_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not tag_data:
            return

        # Переключаем состояние
        is_checked = not tag_data.get('checked', False)
        tag_data['checked'] = is_checked

        # Обновляем данные
        item.setData(0, Qt.ItemDataRole.UserRole, tag_data)

        # Обновляем список выбранных тегов
        if is_checked:
            # Добавляем тег в выбранные
            original_tag = next((t for t in self.tags if t.get('id') == tag_data.get('id')), None)
            if original_tag and original_tag not in self.selected_tags:
                self.selected_tags.append(original_tag)
        else:
            # Удаляем тег из выбранных
            self.selected_tags = [t for t in self.selected_tags
                                  if t.get('id') != tag_data.get('id')]

        # Обновляем информацию
        self.update_selection_info()

        # Принудительно перерисовываем элемент
        self.treeWidget.viewport().update()

    def on_select(self):
        """Обработка нажатия кнопки 'Выбрать'"""
        self.tags_selected.emit(self.selected_tags)
        self.accept()

    def update_selection_info(self):
        """Обновление информации о количестве выбранных тегов"""
        if not hasattr(self, 'selectionInfoLabel'):
            return

        count = len(self.selected_tags)
        self.selectionInfoLabel.setText(f"Выбрано: {count} тегов")

        if count > 0:
            names = [tag.get('name', '') for tag in self.selected_tags[:3]]
            if len(self.selected_tags) > 3:
                names.append('...')
            self.selectionInfoLabel.setToolTip(f"Выбраны: {', '.join(names)}")
        else:
            self.selectionInfoLabel.setToolTip("")

    def set_selected_tags(self, tag_ids):
        """Установка предварительно выбранных тегов"""
        if not tag_ids:
            return

        self.selected_tags = []
        for tag in self.tags:
            if tag.get('id') in tag_ids:
                self.selected_tags.append(tag)

        self.load_tags()
        self.update_selection_info()

    def get_selected_tags(self):
        """Возвращает список выбранных тегов"""
        return self.selected_tags

    def keyPressEvent(self, event):
        """Обработка нажатия клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if hasattr(self, 'searchEdit') and not self.searchEdit.hasFocus():
                self.on_select()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        """При показе диалога устанавливаем фокус на поле поиска"""
        super().showEvent(event)
        if hasattr(self, 'searchEdit'):
            self.searchEdit.setFocus()
            self.searchEdit.selectAll()


# Функция для создания тестовых данных
def create_test_tags():
    """Создание тестовых данных для примера"""
    return [
        {'id': 1, 'name': 'Срочно', 'priority': 'urgent', 'color': '#FF0000'},
        {'id': 2, 'name': 'Важно', 'priority': 'important', 'color': '#FFA500'},
        {'id': 3, 'name': 'Обычный', 'priority': 'normal', 'color': '#808080'},
        {'id': 4, 'name': 'Финансы', 'priority': 'important', 'color': '#008000'},
        {'id': 5, 'name': 'Кадры', 'priority': 'normal', 'color': '#0000FF'},
        {'id': 6, 'name': 'Юридический', 'priority': 'normal', 'color': '#800080'},
        {'id': 7, 'name': 'Договор', 'priority': 'urgent', 'color': '#FF4500'},
        {'id': 8, 'name': 'Отчет', 'priority': 'important', 'color': '#2E8B57'},
        {'id': 9, 'name': 'Технический', 'priority': 'normal', 'color': '#4169E1'},
        {'id': 10, 'name': 'Маркетинг', 'priority': 'normal', 'color': '#FF1493'},
    ]


# Пример использования
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Создаем тестовые данные
    test_tags = create_test_tags()


    # Подключаем сигнал для обработки выбора
    def on_tags_selected(tags):
        print(f"Выбраны теги: {[t.get('name') for t in tags]}")


    print("\n--- Прямое использование ---")
    dialog = TagSelectionDialog(test_tags)
    dialog.tags_selected.connect(on_tags_selected)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("Диалог завершен с выбором")
    else:
        print("Диалог отменен")

    sys.exit()