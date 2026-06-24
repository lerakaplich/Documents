"""
Модуль диалогового окна для создания/редактирования хэштегов
"""
import os
import sys
from PyQt6.QtWidgets import (
    QDialog, QColorDialog, QMessageBox, QApplication
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi


class TagDialog(QDialog):
    """Диалог создания/редактирования хэштега"""

    # Тестовые данные для замены БД
    TEST_TAGS = [
        {
            'id': 1,
            'name': 'Срочно',
            'color': '#D22730',
            'priority': 'urgent'
        },
        {
            'id': 2,
            'name': 'На согласование',
            'color': '#3498db',
            'priority': 'important'
        },
        {
            'id': 3,
            'name': 'Проект',
            'color': '#2ecc71',
            'priority': 'normal'
        }
    ]

    # Сопоставление названий цветов из ComboBox с HEX-кодами
    COLOR_MAP = {
        'Золотой (#ccab6e)': '#ccab6e',
        'Красный (#D22730)': '#D22730',
        'Синий (#3498db)': '#3498db',
        'Зеленый (#2ecc71)': '#2ecc71',
        'Фиолетовый (#9b59b6)': '#9b59b6',
        'Оранжевый (#e67e22)': '#e67e22'
    }

    # Обратное сопоставление HEX -> название
    COLOR_REVERSE_MAP = {v: k for k, v in COLOR_MAP.items()}

    # Сопоставление приоритетов
    PRIORITY_MAP = {
        '1 - Без приоритета': 'normal',
        '2 - Средний приоритет': 'important',
        '3 - Критический приоритет': 'urgent'
    }

    PRIORITY_REVERSE_MAP = {v: k for k, v in PRIORITY_MAP.items()}

    def __init__(self, parent=None, tag_id=None):
        """
        Инициализация диалога

        Args:
            parent: Родительский виджет
            tag_id: ID тега для редактирования (None для создания нового)
        """
        super().__init__(parent)
        self.tag_id = tag_id
        self.editing_tag = None

        self._load_ui()
        self._setup_connections()
        self._load_tag_data()

        # Установка заголовка в зависимости от режима
        if tag_id:
            self.titleLabel.setText("Редактирование хэштега")
        else:
            self.titleLabel.setText("Новый хэштег")

    def _load_ui(self):
        """Загружает UI из .ui файла"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(
            current_dir, '..', '..', '..', 'ui', 'system', 'tags', 'tag_dialog.ui'
        )
        ui_path = os.path.normpath(ui_path)

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI file not found: {ui_path}")

        loadUi(ui_path, self)

    def _setup_connections(self):
        """Настраивает сигналы и слоты"""
        # Кнопка сохранения
        self.btnSave.clicked.connect(self._on_save)

        # Выбор цвета через индикатор
        self.colorIndicator.mousePressEvent = self._on_color_indicator_click

        # Синхронизация цвета между ComboBox и индикатором
        self.comboBoxColor.currentTextChanged.connect(self._on_color_changed)

    def _on_color_indicator_click(self, event):
        """Обработчик клика по цветовому индикатору"""
        current_color = QColor(self._get_current_color())
        color = QColorDialog.getColor(current_color, self, "Выберите цвет хэштега")

        if color.isValid():
            hex_color = color.name()
            self._set_color(hex_color)

    def _on_color_changed(self, text):
        """Обработчик изменения цвета в ComboBox"""
        if text in self.COLOR_MAP:
            hex_color = self.COLOR_MAP[text]
            self._update_color_indicator(hex_color)

    def _get_current_color(self):
        """Получает текущий выбранный цвет"""
        # Пробуем получить из ComboBox
        current_text = self.comboBoxColor.currentText()
        if current_text in self.COLOR_MAP:
            return self.COLOR_MAP[current_text]

        # Если нет в списке, используем цвет индикатора
        style = self.colorIndicator.styleSheet()
        # Извлекаем цвет из стиля
        if 'background-color:' in style:
            color_part = style.split('background-color:')[1].split(';')[0].strip()
            return color_part

        return '#ccab6e'  # По умолчанию золотой

    def _set_color(self, hex_color):
        """Устанавливает цвет в ComboBox и индикатор"""
        # Обновляем индикатор
        self._update_color_indicator(hex_color)

        # Ищем в списке
        if hex_color in self.COLOR_REVERSE_MAP:
            self.comboBoxColor.setCurrentText(self.COLOR_REVERSE_MAP[hex_color])
        else:
            # Если цвета нет в списке, временно показываем в индикаторе
            self.comboBoxColor.setCurrentIndex(-1)

    def _update_color_indicator(self, hex_color):
        """Обновляет цвет индикатора"""
        self.colorIndicator.setStyleSheet(f"""
            QFrame {{
                border-radius: 16px;
                background-color: {hex_color};
                border: 2px solid #E0E0E0;
            }}
            QFrame:hover {{
                border-color: {hex_color};
            }}
        """)

    def _load_tag_data(self):
        """Загружает данные тега для редактирования"""
        if not self.tag_id:
            return

        # Поиск тега в тестовых данных
        self.editing_tag = next(
            (tag for tag in self.TEST_TAGS if tag['id'] == self.tag_id),
            None
        )

        if not self.editing_tag:
            QMessageBox.warning(self, "Ошибка", f"Тег с ID {self.tag_id} не найден")
            self.reject()
            return

        # Заполняем поля
        self.lineEditName.setText(self.editing_tag['name'])

        # Устанавливаем приоритет
        priority_text = self.PRIORITY_REVERSE_MAP.get(
            self.editing_tag['priority'],
            '1 - Без приоритета'
        )
        self.comboBoxPriority.setCurrentText(priority_text)

        # Устанавливаем цвет
        self._set_color(self.editing_tag['color'])

    def _validate_input(self):
        """Валидирует введенные данные"""
        name = self.lineEditName.text().strip()

        if not name:
            QMessageBox.warning(self, "Ошибка валидации", "Название хэштега обязательно для заполнения")
            self.lineEditName.setFocus()
            return False

        # Проверка на уникальность имени (исключая текущий редактируемый тег)
        for tag in self.TEST_TAGS:
            if tag['name'].lower() == name.lower():
                if not self.editing_tag or tag['id'] != self.editing_tag['id']:
                    QMessageBox.warning(
                        self,
                        "Ошибка валидации",
                        f"Хэштег с названием '{name}' уже существует"
                    )
                    self.lineEditName.setFocus()
                    return False

        # Проверка на наличие #
        if name.startswith('#'):
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Название хэштега не должно содержать символ # в начале"
            )
            self.lineEditName.setFocus()
            return False

        # Проверка длины
        if len(name) > 100:
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Название хэштега не должно превышать 100 символов"
            )
            self.lineEditName.setFocus()
            return False

        return True

    def _on_save(self):
        """Обработчик сохранения тега"""
        if not self._validate_input():
            return

        name = self.lineEditName.text().strip()
        priority_text = self.comboBoxPriority.currentText()
        priority = self.PRIORITY_MAP.get(priority_text, 'normal')
        color = self._get_current_color()

        # Формируем данные тега
        tag_data = {
            'name': name,
            'priority': priority,
            'color': color
        }

        if self.editing_tag:
            # Обновление существующего тега
            tag_data['id'] = self.editing_tag['id']
            for i, tag in enumerate(self.TEST_TAGS):
                if tag['id'] == self.editing_tag['id']:
                    self.TEST_TAGS[i].update(tag_data)
                    break
            print(f"[INFO] Тег обновлен: {tag_data}")
        else:
            # Создание нового тега
            new_id = max([tag['id'] for tag in self.TEST_TAGS], default=0) + 1
            tag_data['id'] = new_id
            self.TEST_TAGS.append(tag_data)
            print(f"[INFO] Создан новый тег: {tag_data}")

        # Показываем сообщение об успехе
        action = "обновлен" if self.editing_tag else "создан"
        QMessageBox.information(
            self,
            "Успешно",
            f"Хэштег '{name}' успешно {action}"
        )

        self.accept()

    def get_tag_data(self):
        """Возвращает данные созданного/отредактированного тега"""
        name = self.lineEditName.text().strip()
        priority_text = self.comboBoxPriority.currentText()
        priority = self.PRIORITY_MAP.get(priority_text, 'normal')
        color = self._get_current_color()

        tag_data = {
            'name': name,
            'priority': priority,
            'color': color
        }

        if self.editing_tag:
            tag_data['id'] = self.editing_tag['id']

        return tag_data


# ============================================================================
# ТЕСТОВЫЙ ЗАПУСК
# ============================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Тест 1: Создание нового тега
    print("=" * 50)
    print("ТЕСТ 1: Создание нового тега")
    dialog = TagDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("Создан тег:", dialog.get_tag_data())

    # Тест 2: Редактирование существующего тега
    print("\n" + "=" * 50)
    print("ТЕСТ 2: Редактирование существующего тега")
    dialog_edit = TagDialog(tag_id=1)
    if dialog_edit.exec() == QDialog.DialogCode.Accepted:
        print("Обновлен тег:", dialog_edit.get_tag_data())

    # Вывод всех тегов
    print("\n" + "=" * 50)
    print("ВСЕ ТЕГИ ПОСЛЕ ИЗМЕНЕНИЙ:")
    for tag in TagDialog.TEST_TAGS:
        print(f"  ID: {tag['id']}, Name: {tag['name']}, Color: {tag['color']}, Priority: {tag['priority']}")

    sys.exit(0)