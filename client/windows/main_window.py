import os
import sys
import traceback
from PyQt6.QtWidgets import QMainWindow, QApplication, QHBoxLayout, QWidget, QStackedWidget, QMessageBox
from PyQt6.QtCore import Qt

from client.windows.documents.table.documents_panel import DocumentsPanel
from client.windows.left_panel.left_panel import LeftPanel
from client.windows.profile.profile_window import ProfileForm
from client.windows.system.tab_system import SystemTab

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()

        try:
            print("=" * 50)
            print("Инициализация MainWindow...")
            print("=" * 50)

            self.setWindowTitle("Система документооборота МАЗ")
            self.setGeometry(100, 100, 1200, 800)

            # Устанавливаем стиль приложения
            self.setup_app_style()

            # Центральный виджет
            central_widget = QWidget()
            self.setCentralWidget(central_widget)

            # Создаем горизонтальный layout
            layout = QHBoxLayout(central_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # Создаем панели
            print("Создание LeftPanel...")
            self.left_panel = LeftPanel()
            print("✓ LeftPanel создан успешно")

            # Создаем stacked widget для разных представлений
            self.content_stack = QStackedWidget()

            print("Создание DocumentsPanel...")
            self.documents_panel = DocumentsPanel()
            print("✓ DocumentsPanel создан успешно")

            print("Создание ProfileForm...")
            self.profile_form = ProfileForm()
            print("✓ ProfileForm создан успешно")

            print("Создание SystemTab...")
            self.system_tab = SystemTab()  # ← ДОБАВИТЬ СОЗДАНИЕ
            print("✓ SystemTab создан успешно")

            # Добавляем панели в stacked widget
            self.content_stack.addWidget(self.documents_panel)  # index 0
            self.content_stack.addWidget(self.profile_form)      # index 1
            self.content_stack.addWidget(self.system_tab)        # index 2 ← ДОБАВИТЬ

            # Добавляем панели в layout
            layout.addWidget(self.left_panel)
            layout.addWidget(self.content_stack)

            # Устанавливаем соотношение размеров
            layout.setStretch(0, 0)  # Левая панель не растягивается
            layout.setStretch(1, 1)  # Правая панель занимает всё место

            # Подключаем сигналы
            self.setup_connections()

            # Показываем панель документов по умолчанию
            self.content_stack.setCurrentWidget(self.documents_panel)

            # Статус бар
            self.statusBar().showMessage("Готов к работе")

            print("=" * 50)
            print("✓ MainWindow инициализирован успешно")
            print("=" * 50)

        except Exception as e:
            print(f"✗ Ошибка при инициализации MainWindow: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось инициализировать приложение:\n{str(e)}")
            raise

    def setup_app_style(self):
        """Устанавливает общий стиль приложения"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8F9FA;
            }
            QStatusBar {
                background-color: #2c3e50;
                color: white;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #2c3e50;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #5a6e7a;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6b8595;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

    def setup_connections(self):
        """Настройка связей между панелями"""
        try:
            print("Настройка сигналов...")

            # Подключаем сигналы из левой панели
            if hasattr(self.left_panel, 'direction_clicked'):
                self.left_panel.direction_clicked.connect(self.on_direction_selected)
                print("✓ Сигнал direction_clicked подключен")

            if hasattr(self.left_panel, 'profile_clicked'):
                self.left_panel.profile_clicked.connect(self.on_profile_clicked)
                print("✓ Сигнал profile_clicked подключен")

            if hasattr(self.left_panel, 'all_documents_clicked'):
                self.left_panel.all_documents_clicked.connect(self.on_all_documents_clicked)
                print("✓ Сигнал all_documents_clicked подключен")

            if hasattr(self.left_panel, 'system_clicked'):
                self.left_panel.system_clicked.connect(self.on_system_clicked)
                print("✓ Сигнал system_clicked подключен")

            # Подключаем сигналы из панели документов
            if hasattr(self.documents_panel, 'document_selected'):
                self.documents_panel.document_selected.connect(self.on_document_selected)
                print("✓ Сигнал document_selected подключен")

            if hasattr(self.documents_panel, 'search_requested'):
                self.documents_panel.search_requested.connect(self.on_search)
                print("✓ Сигнал search_requested подключен")

            if hasattr(self.documents_panel, 'filter_changed'):
                self.documents_panel.filter_changed.connect(self.on_filter_changed)
                print("✓ Сигнал filter_changed подключен")

            print("✓ Все сигналы настроены успешно")

        except Exception as e:
            print(f"✗ Ошибка при настройке сигналов: {e}")
            traceback.print_exc()

    def on_profile_clicked(self):
        """Обработка нажатия на кнопку профиля"""
        try:
            print("\n→ Открытие профиля пользователя")
            self.content_stack.setCurrentWidget(self.profile_form)
            self.statusBar().showMessage("Профиль пользователя", 3000)
        except Exception as e:
            print(f"✗ Ошибка при открытии профиля: {e}")

    def on_all_documents_clicked(self):
        """Обработка нажатия на кнопку всех документов"""
        try:
            print("\n→ Открытие всех документов")
            self.content_stack.setCurrentWidget(self.documents_panel)
            if hasattr(self.documents_panel, 'update_title'):
                self.documents_panel.update_title("Все документы")
            self.statusBar().showMessage("Все документы", 3000)
        except Exception as e:
            print(f"✗ Ошибка при открытии всех документов: {e}")

    def on_system_clicked(self):
        """Обработка нажатия на кнопку системы"""
        try:
            print("\n→ Открытие системных настроек")
            self.content_stack.setCurrentWidget(self.system_tab)  # ← ПЕРЕКЛЮЧАЕМ НА SYSTEMTAB
            self.statusBar().showMessage("Системные настройки", 3000)
        except Exception as e:
            print(f"✗ Ошибка при открытии системы: {e}")

    def on_direction_selected(self, direction_name: str, group_name: str = ""):
        """Обработка выбора направления"""
        try:
            print(f"\n→ Выбрано направление: {direction_name} (группа: {group_name})")

            # Переключаемся на панель документов
            self.content_stack.setCurrentWidget(self.documents_panel)

            # Обновляем заголовок в панели документов
            if hasattr(self.documents_panel, 'update_title'):
                title = direction_name if not group_name or group_name == direction_name else f"{direction_name}"
                self.documents_panel.update_title(title)

            # Обновляем статус
            self.statusBar().showMessage(f"Загрузка документов: {direction_name}", 3000)

            # TODO: Здесь будет загрузка реальных данных
            # self.load_documents(direction_name, group_name)

        except Exception as e:
            print(f"✗ Ошибка в on_direction_selected: {e}")
            self.statusBar().showMessage(f"Ошибка: {str(e)}", 5000)

    def on_document_selected(self, document):
        """Обработка выбора документа"""
        try:
            doc_title = document.get('title', 'Unknown')
            doc_number = document.get('number', 'Unknown')
            print(f"\n→ Выбран документ: {doc_title} (№{doc_number})")

            # Обновляем статус
            self.statusBar().showMessage(f"Выбран документ: {doc_title}", 3000)

            # TODO: Здесь будет открытие карточки документа
            # self.open_document_card(document)

        except Exception as e:
            print(f"✗ Ошибка в on_document_selected: {e}")

    def on_search(self, text):
        """Обработка поиска"""
        try:
            print(f"\n→ Поиск: '{text}'")

            if text and len(text) >= 3:
                self.statusBar().showMessage(f"Поиск: {text}", 2000)
                # TODO: Здесь будет выполнение поиска
                # self.perform_search(text)
            elif text:
                self.statusBar().showMessage(f"Введите минимум 3 символа для поиска", 2000)

        except Exception as e:
            print(f"✗ Ошибка в on_search: {e}")

    def on_filter_changed(self, filters):
        """Обработка изменения фильтров"""
        try:
            print(f"\n→ Фильтры изменены: {filters}")
            self.statusBar().showMessage("Применены новые фильтры", 2000)

            # TODO: Здесь будет применение фильтров
            # self.apply_filters(filters)

        except Exception as e:
            print(f"✗ Ошибка в on_filter_changed: {e}")

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        try:
            reply = QMessageBox.question(
                self,
                "Подтверждение выхода",
                "Вы уверены, что хотите выйти?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                print("\n→ Завершение работы приложения...")
                event.accept()
            else:
                event.ignore()

        except Exception as e:
            print(f"✗ Ошибка при закрытии: {e}")
            event.accept()


if __name__ == "__main__":
    try:
        print("\n" + "=" * 50)
        print("Запуск приложения...")
        print("=" * 50)

        app = QApplication(sys.argv)


        print("Создание MainWindow...")
        window = MainWindow()

        print("Показ окна...")
        window.show()

        print("Вход в цикл обработки событий...")
        print("=" * 50 + "\n")

        sys.exit(app.exec())

    except Exception as e:
        print(f"\n✗ Критическая ошибка: {e}")
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")