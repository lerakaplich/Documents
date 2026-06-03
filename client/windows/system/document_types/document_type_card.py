# document_type_card.py
import sys
import os
from PyQt6.QtWidgets import QApplication, QFrame, QVBoxLayout, QWidget, QHBoxLayout, QLabel, QPushButton, QSpacerItem, \
    QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.uic import loadUi


class DocumentTypeCard(QFrame):
    """Карточка типа документа на основе загруженного UI файла"""

    # Сигналы для взаимодействия с главным окном
    edit_clicked = pyqtSignal(dict)  # Передаем данные типа документа
    delete_clicked = pyqtSignal(int)  # Передаем ID типа документа

    def __init__(self, doc_type_data=None, parent=None):
        super().__init__(parent)

        # Загружаем UI дизайн
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)
        else:
            print(f"UI файл не найден: {ui_path}")
            # Создаем заглушку, если файл не найден
            self.setup_placeholder()

        # Сохраняем данные
        self.doc_type_data = doc_type_data or {}
        self.type_id = self.doc_type_data.get('id', 0)

        # Настраиваем карточку
        self.setup_card()

        # Подключаем сигналы кнопок
        if hasattr(self, 'editBtn'):
            self.editBtn.clicked.connect(self.on_edit_clicked)
        if hasattr(self, 'deleteBtn'):
            self.deleteBtn.clicked.connect(self.on_delete_clicked)

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        # Путь относительно текущего файла
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Поднимаемся на уровень выше до client/windows/system/document_types/
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'document_types', 'document_type_card.ui')
        return os.path.normpath(ui_path)

    def setup_card(self):
        """Заполняет карточку данными"""
        if not self.doc_type_data:
            return

        # Заполняем название
        if hasattr(self, 'nameLabel_2'):
            name = self.doc_type_data.get('name', '')
            self.nameLabel_2.setText(name if name else 'Без названия')

        # Заполняем количество дополнительных полей
        if hasattr(self, 'fieldsCountLabel'):
            fields_count = self.doc_type_data.get('fields_count', 0)
            self.fieldsCountLabel.setText(f"{fields_count} доп. полей" if fields_count != 1 else "1 доп. поле")

        # Заполняем статус автонумерации
        if hasattr(self, 'autoNumLabel'):
            auto_num = self.doc_type_data.get('auto_numbering', False)
            if auto_num:
                self.autoNumLabel.setText("✓ Автонумерация включена")
                self.autoNumLabel.setStyleSheet("border: none; font-size: 11px; color: #28A745;")
            else:
                self.autoNumLabel.setText("✗ Автонумерация отключена")
                self.autoNumLabel.setStyleSheet("border: none; font-size: 11px; color: #DC3545;")

        # Заполняем количество документов
        if hasattr(self, 'docsCountLabel'):
            docs_count = self.doc_type_data.get('documents_count', 0)
            # Склонение слова "документ"
            if docs_count % 10 == 1 and docs_count % 100 != 11:
                word = "документ"
            elif 2 <= docs_count % 10 <= 4 and (docs_count % 100 < 10 or docs_count % 100 >= 20):
                word = "документа"
            else:
                word = "документов"
            self.docsCountLabel.setText(f"{docs_count} {word}")

    def on_edit_clicked(self):
        """Обработчик кнопки редактирования"""
        self.edit_clicked.emit(self.doc_type_data)

    def on_delete_clicked(self):
        """Обработчик кнопки удаления"""
        self.delete_clicked.emit(self.type_id)

    def update_data(self, new_data):
        """Обновляет данные карточки"""
        self.doc_type_data.update(new_data)
        self.setup_card()

    def setup_placeholder(self):
        """Создает простую версию карточки, если UI не найден"""
        layout = QVBoxLayout(self)

        self.nameLabel_2 = QLabel("Document Type (UI not found)")
        self.nameLabel_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.nameLabel_2)

        self.fieldsCountLabel = QLabel("0 доп. полей")
        layout.addWidget(self.fieldsCountLabel)

        self.autoNumLabel = QLabel("Автонумерация")
        layout.addWidget(self.autoNumLabel)

        self.docsCountLabel = QLabel("0 документов")
        layout.addWidget(self.docsCountLabel)

        buttons_layout = QHBoxLayout()
        self.editBtn = QPushButton("Редактировать")
        self.deleteBtn = QPushButton("Удалить")
        buttons_layout.addWidget(self.editBtn)
        buttons_layout.addWidget(self.deleteBtn)
        layout.addLayout(buttons_layout)

        self.editBtn.clicked.connect(self.on_edit_clicked)
        self.deleteBtn.clicked.connect(self.on_delete_clicked)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Тест отдельной карточки
    test_data = {
        'id': 1,
        'name': 'Приказ',
        'fields_count': 4,
        'auto_numbering': True,
        'documents_count': 156
    }

    # Создаем и показываем карточку
    card = DocumentTypeCard(test_data)
    card.setWindowTitle("Тест карточки типа документа")
    card.edit_clicked.connect(lambda data: print(f"Редактировать: {data['name']}"))
    card.delete_clicked.connect(lambda type_id: print(f"Удалить ID: {type_id}"))
    card.show()

    # Альтернативно, показать панель со всеми карточками
    # panel = DocumentTypesPanel()
    # panel.setWindowTitle("Типы документов")
    # panel.resize(800, 600)
    # panel.show()

    sys.exit(app.exec())