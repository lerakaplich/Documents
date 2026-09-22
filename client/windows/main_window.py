import os
import sys
import traceback
from PyQt6.QtWidgets import QMainWindow, QApplication, QHBoxLayout, QWidget, QStackedWidget, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal

from client.core import http_client
from client.core.state.app_state import AppState
from client.windows.documents.table.documents_panel import DocumentsPanel
from client.windows.left_panel.left_panel import LeftPanel
from client.windows.profile.profile_window import ProfileForm
from client.windows.system.tab_system import SystemTab




class MainWindow(QMainWindow):
    """Главное окно приложения - ТОЛЬКО НАВИГАЦИЯ"""
    logout_requested = pyqtSignal()

    def __init__(self):
        super().__init__()

        try:
            print("Инициализация MainWindow...")
            self.http_client = AppState().http_client

            self.setWindowTitle("Система документооборота МАЗ")
            self.setGeometry(100, 100, 1200, 800)

            self.setup_app_style()

            # ── Тема (нужна и ниже) ──
            from client.core.themes import get_manager
            _t = get_manager().current

            # Центральный виджет
            central_widget = QWidget()
            self.setCentralWidget(central_widget)


            layout = QHBoxLayout(central_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            print("Создание LeftPanel...")
            self.left_panel = LeftPanel()
            print("✓ LeftPanel создан успешно")

            self.content_stack = QStackedWidget()
            # ← убираем повторный импорт и присваивание _t — уже есть выше
            self.content_stack.setStyleSheet(
                f"QStackedWidget {{ background-color: {_t.BG_DIALOG_ALT}; }}"
            )


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
        from client.core.themes import get_manager
        t = get_manager().current
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {t.BG_DIALOG_ALT};
            }}
            QStatusBar {{
                background-color: {t.SIDEBAR_BG};
                color: {t.SIDEBAR_TEXT};
            }}
            
        """)

    def reapply_theme(self):
        """Переприменить стили MainWindow к актуальной теме."""
        self.setup_app_style()

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

            if hasattr(self.left_panel, 'logout_clicked'):
                self.left_panel.logout_clicked.connect(self.on_logout_clicked)
                print("✓ logout_clicked подключен")

            print("✓ Все сигналы настроены успешно")

        except Exception as e:
            print(f"✗ Ошибка при настройке сигналов: {e}")
            traceback.print_exc()

    # ========== НАВИГАЦИЯ ==========
    def on_logout_clicked(self):
        """Обработка выхода из аккаунта."""
        from PyQt6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Выход из аккаунта",
            "Вы уверены, что хотите выйти из аккаунта?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # ─── Серверный logout + очистка токенов и сохранённой сессии ───
        try:
            from client.services.auth_service import AuthService
            from client.core.state.app_state import AppState

            auth = AuthService(AppState().http_client)
            auth.logout()
        except Exception as e:
            print(f"⚠️ Ошибка при выходе из аккаунта: {e}")

        # ─── Оповещаем LoginWindow ───
        self.logout_requested.emit()

        # ─── Прячем окно (НЕ close(), иначе closeEvent завершит всё приложение) ───
        self.hide()

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
        """Закрытие приложения без подтверждения."""
        event.accept()
        QApplication.instance().quit()


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