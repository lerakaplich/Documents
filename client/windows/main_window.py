import os
import sys
import traceback
from PyQt6.QtWidgets import QMainWindow, QApplication, QHBoxLayout, QWidget, QStackedWidget, QMessageBox
from PyQt6.QtCore import Qt

from client.windows.documents.table.documents_panel import DocumentsPanel
from client.windows.left_panel.left_panel import LeftPanel
from client.windows.profile.profile_window import ProfileForm
from client.windows.system.tab_system import SystemTab




class MainWindow(QMainWindow):
    """Главное окно приложения - ТОЛЬКО НАВИГАЦИЯ"""

    def __init__(self):
        super().__init__()

        try:

            print("Инициализация MainWindow...")


            self.setWindowTitle("Система документооборота МАЗ")
            self.setGeometry(100, 100, 1200, 800)

            self.setup_app_style()

            # Центральный виджет
            central_widget = QWidget()
            self.setCentralWidget(central_widget)

            layout = QHBoxLayout(central_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # Создаем панели
            print("Создание LeftPanel...")
            self.left_panel = LeftPanel()
            print("✓ LeftPanel создан успешно")

            self.content_stack = QStackedWidget()

            print("Создание DocumentsPanel...")
            self.documents_panel = DocumentsPanel()
            print("✓ DocumentsPanel создан успешно")

            print("Создание ProfileForm...")
            self.profile_form = ProfileForm()
            print("✓ ProfileForm создан успешно")

            print("Создание SystemTab...")
            self.system_tab = SystemTab()
            print("✓ SystemTab создан успешно")

            # Добавляем панели
            self.content_stack.addWidget(self.documents_panel)  # index 0
            self.content_stack.addWidget(self.profile_form)      # index 1
            self.content_stack.addWidget(self.system_tab)        # index 2

            layout.addWidget(self.left_panel)
            layout.addWidget(self.content_stack)

            layout.setStretch(0, 0)
            layout.setStretch(1, 1)

            # Подключаем сигналы
            self.setup_connections()

            # По умолчанию - документы
            self.content_stack.setCurrentWidget(self.documents_panel)

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
            QMainWindow { background-color: #F8F9FA; }
            QStatusBar { background-color: #2c3e50; color: white; }
            QScrollArea { border: none; background-color: transparent; }
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

            # Левая панель -> навигация
            if hasattr(self.left_panel, 'type_clicked'):
                self.left_panel.type_clicked.connect(self.on_type_selected)
                print("✓ type_clicked подключен")

            if hasattr(self.left_panel, 'direction_clicked'):
                self.left_panel.direction_clicked.connect(self.on_direction_selected)
                print("✓ direction_clicked подключен")

            if hasattr(self.left_panel, 'profile_clicked'):
                self.left_panel.profile_clicked.connect(self.on_profile_clicked)
                print("✓ profile_clicked подключен")

            if hasattr(self.left_panel, 'all_documents_clicked'):
                self.left_panel.all_documents_clicked.connect(self.on_all_documents_clicked)
                print("✓ all_documents_clicked подключен")

            if hasattr(self.left_panel, 'system_clicked'):
                self.left_panel.system_clicked.connect(self.on_system_clicked)
                print("✓ system_clicked подключен")

            # Статус-бар
            if hasattr(self.documents_panel, 'data_loaded'):
                self.documents_panel.data_loaded.connect(
                    lambda count: self.statusBar().showMessage(f"Загружено {count} документов", 3000)
                )
                print("✓ data_loaded подключен")

            print("✓ Все сигналы настроены успешно")

        except Exception as e:
            print(f"✗ Ошибка при настройке сигналов: {e}")
            traceback.print_exc()

    # ========== НАВИГАЦИЯ ==========

    def on_profile_clicked(self):
        """Переключение на профиль"""
        self.content_stack.setCurrentWidget(self.profile_form)
        self.statusBar().showMessage("Профиль пользователя", 3000)

    def on_all_documents_clicked(self):
        """Переключение на все документы"""
        self.content_stack.setCurrentWidget(self.documents_panel)
        self.documents_panel.load_all_documents()
        self.statusBar().showMessage("Все документы", 3000)

    def on_system_clicked(self):
        """Переключение на систему"""
        self.content_stack.setCurrentWidget(self.system_tab)
        self.statusBar().showMessage("Системные настройки", 3000)

    def on_type_selected(self, type_id: int, type_name: str):
        """Выбор типа документа"""
        self.content_stack.setCurrentWidget(self.documents_panel)
        self.documents_panel.load_documents_by_type(type_id)

    def on_direction_selected(self, direction_name: str, group_name: str = ""):
        """Выбор направления"""
        self.content_stack.setCurrentWidget(self.documents_panel)
        direction_key = "internal" if "внутр" in group_name.lower() else "external"
        self.documents_panel.load_documents_by_direction(direction_key, direction_name)

    def closeEvent(self, event):
        """Обработка закрытия"""
        reply = QMessageBox.question(
            self,
            "Подтверждение выхода",
            "Вы уверены, что хотите выйти?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    try:
        print("Запуск приложения...")


        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()

        print("Вход в цикл обработки событий...")
        print("=" * 50 + "\n")

        sys.exit(app.exec())

    except Exception as e:
        print(f"\n✗ Критическая ошибка: {e}")
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")