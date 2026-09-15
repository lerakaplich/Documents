import sys
import os
from PyQt6.QtWidgets import QMainWindow, QWidget, QGraphicsDropShadowEffect, QApplication
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QUrl, QPoint, QParallelAnimationGroup, pyqtSignal, \
    QObject, QThread, QTimer
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.uic import loadUi
import logging

from client.core.state.app_state import AppState
from client.windows.login.auth_widget import AuthWidget
from client.windows.login.new_password_widget import NewPasswordWidget
from client.windows.login.reset_password_widget import ResetPasswordWidget
from client.windows.main_window import MainWindow
from client.windows.animations.animated_notification import NotificationManager

logger = logging.getLogger(__name__)

from client.services.auth_service import AuthService


class AutoLoginWorker(QObject):
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def run(self):
        try:
            app_state = AppState()
            auth = AuthService(app_state.http_client)
            result = auth.try_restore_session()

            if not result:
                self.failed.emit("Нет сохранённой сессии")
                return

            try:
                user_data = app_state.employee_service.get_my_profile()
            except Exception as e:
                logger.warning(f"Не удалось получить профиль: {e}")
                user_data = {}

            app_state.set_user(user_data)
            self.finished.emit(user_data)
        except Exception as e:
            logger.error(f"Ошибка автовхода: {e}")
            self.failed.emit(str(e))

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Получаем корневую директорию проекта (client)
        self.root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Правильный путь к back_login.ui
        ui_path = os.path.join(self.root_dir, "ui", "login", "back_login.ui")
        print(f"Загрузка UI: {ui_path}")

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI файл не найден: {ui_path}")

        loadUi(ui_path, self)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._is_reset_mode = False
        self._is_new_password_mode = False

        # Состояние приложения
        self.app_state = AppState()

        # 2. Анимация звёзд — создаётся через отдельный метод, чтобы можно было
        #    полностью уничтожать и пересоздавать её при входе/выходе из аккаунта.
        self.web_view = None
        self._create_star_animation()

        self.setMouseTracking(True)
        self.backgroundWidget.setMouseTracking(True)

        # 3. Инициализация виджетов-карточек
        self.auth_card = AuthWidget()
        self.auth_card.setParent(self.backgroundWidget)

        self.reset_card = ResetPasswordWidget()
        self.reset_card.setParent(self.backgroundWidget)

        self.new_password_card = NewPasswordWidget()
        self.new_password_card.setParent(self.backgroundWidget)

        self._apply_shadow(self.auth_card)
        self._apply_shadow(self.reset_card)
        self._apply_shadow(self.new_password_card)

        # 4. Загрузка логотипа
        logo_path = os.path.join(self.root_dir, "icons", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                self.logoLabel.setStyleSheet("background-color: transparent;")
                self.logoLabel.setText("")
                scaled_pixmap = pixmap.scaled(
                    200, 150,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.logoLabel.setPixmap(scaled_pixmap)
                self.logoLabel.setScaledContents(False)

        # ===== ИНИЦИАЛИЗАЦИЯ МЕНЕДЖЕРА УВЕДОМЛЕНИЙ =====
        self.notification_manager = NotificationManager(self, max_visible=3)
        # ==============================================

        # 5. Подключение сигналов переключения

        if hasattr(self.new_password_card, 'password_changed_successfully'):
            self.new_password_card.password_changed_successfully.connect(self.switch_to_main_window)

        if hasattr(self.new_password_card, 'password_changed_successfully'):
            self.new_password_card.password_changed_successfully.connect(self.switch_to_main_window)

        if hasattr(self.auth_card, 'forgotPasswordButton'):
            self.auth_card.forgotPasswordButton.clicked.connect(self.show_reset_password)

        if hasattr(self.reset_card, 'back_to_login'):
            self.reset_card.back_to_login.connect(self.show_login_card)

        # ВАЖНО: Подключаем сигнал go_to_new_password к обработчику
        if hasattr(self.reset_card, 'go_to_new_password'):
            self.reset_card.go_to_new_password.connect(self._on_go_to_new_password)

        if hasattr(self.new_password_card, 'backToLoginButton'):
            self.new_password_card.backToLoginButton.clicked.connect(self.show_login_card)

        # 6. Подключение сигналов для перехода в MainWindow
        if hasattr(self.auth_card, 'login_successful'):
            self.auth_card.login_successful.connect(self.switch_to_main_window)

        if hasattr(self.new_password_card, 'password_changed_successfully'):
            self.new_password_card.password_changed_successfully.connect(self.switch_to_main_window)

        # Передаем менеджер уведомлений в виджеты
        self.auth_card.set_notification_manager(self.notification_manager)
        self.reset_card.set_notification_manager(self.notification_manager)
        self.new_password_card.set_notification_manager(self.notification_manager)

        # Ссылка на главное окно
        self.main_window = None

        # Проверяем сохраненную сессию
        self._check_saved_session()

    # ==================== WEB VIEW LIFECYCLE ====================

    def _create_star_animation(self):
        """Создаёт QWebEngineView с анимацией звёзд."""
        if self.web_view is not None:
            return

        self.web_view = QWebEngineView(self.backgroundWidget)
        self.web_view.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, False
        )

        # Геометрия — по текущему размеру окна.
        # resizeEvent подправит при следующем изменении размера.
        self.web_view.setGeometry(0, 0, self.width(), self.height())

        html_path = os.path.join(self.root_dir, "html", "star_animation.html")
        if os.path.exists(html_path):
            self.web_view.setUrl(QUrl.fromLocalFile(html_path))
        else:
            print(f"Warning: HTML файл не найден: {html_path}")

        self.web_view.lower()
        # Показываем сразу — иначе виджет может остаться скрытым после
        # повторного создания (deleteLater мог его спрятать).
        self.web_view.show()

        print("✨ WebEngine (звёзды) создан")

    def _destroy_star_animation(self):
        """Полностью уничтожает QWebEngineView и его страницу, чтобы
        освободить память и завершить QtWebEngineProcess."""
        if self.web_view is None:
            return

        print("🗑️ Уничтожаем WebEngine (звёзды)...")

        # 1. Явно удаляем страницу — иначе Qt ругается
        #    "Release of profile requested but WebEnginePage still not deleted"
        try:
            page = self.web_view.page()
            if page is not None:
                page.deleteLater()
        except RuntimeError:
            # Объект уже удалён C++-стороной — игнорируем
            pass

        # 2. Планируем удаление самого виджета
        try:
            self.web_view.deleteLater()
        except RuntimeError:
            pass

        # 3. Обнуляем Python-ссылку — это важно, иначе WebEngine
        #    не отпустит профиль до следующего gc
        self.web_view = None

        # 4. Даём Qt обработать отложенные deleteLater прямо сейчас.
        #    Без этого объект уничтожится только после возврата в event loop,
        #    а нам нужно освободить память как можно раньше.
        QApplication.processEvents()

    def switch_to_main_window(self, user_data=None):
        """Переключение на главное окно с данными пользователя"""
        print("Переход в главное окно...")

        # ─── Освобождаем память QtWebEngine ───
        #     Делаем это ДО скрытия/создания MainWindow, чтобы пик
        #     потребления памяти пришёлся на момент, когда старый экран
        #     уже не нужен.
        self._destroy_star_animation()

        if self.main_window is None:
            self.main_window = MainWindow()
            self.main_window.logout_requested.connect(self.on_logout_from_main)
            self.main_window.showMaximized()

        if user_data and hasattr(self.main_window, 'set_user_data'):
            logger.info("📥 Устанавливаем данные пользователя в MainWindow")
            self.main_window.set_user_data(user_data)

        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

        self.hide()

        # ─── Форсируем сборщик мусора через мгновение.
        #     К этому моменту deleteLater() уже обработан, и gc
        #     заберёт оставшиеся Python-ссылки на обёртки QWebEngine. ───
        QTimer.singleShot(0, self._collect_garbage)

    def _collect_garbage(self):
        """Принудительный сборщик мусора после уничтожения WebEngine."""
        import gc
        collected = gc.collect()
        logger.info(f"🧹 gc.collect() освободил {collected} объектов")

    def on_logout_from_main(self):
        """Пользователь вышел из аккаунта из MainWindow — возвращаемся на логин."""
        print("🚪 Выход из аккаунта — возврат на окно логина")

        # ─── Уничтожаем MainWindow ───
        if self.main_window is not None:
            self.main_window.deleteLater()
            self.main_window = None

        # ─── Показываем себя заново ───
        self.showMaximized()
        self.raise_()
        self.activateWindow()

        # ─── Возвращаем на карточку авторизации ───
        self._reset_to_login_view()

        # ─── Чистим поля ───
        self._clear_auth_fields()

        # ─── Пересоздаём анимацию звёзд ───
        #     Делаем это ПОСЛЕ showMaximized(), чтобы у окна был актуальный
        #     размер и web_view получил корректную геометрию.
        self._create_star_animation()

        # ─── Пересчитываем позиции карточек и звёзд ───
        QTimer.singleShot(0, self._after_logout_layout)

    def _after_logout_layout(self):
        """Отложенный пересчёт после возврата на логин."""
        # Позиции карточек
        self._update_cards_position()

        # Растягиваем web_view на весь backgroundWidget
        if self.web_view is not None:
            self.web_view.setGeometry(0, 0, self.width(), self.height())

    def _reset_to_login_view(self):
        """Мгновенно возвращает на карточку авторизации, отодвигая остальные за экран."""
        self._is_reset_mode = False
        self._is_new_password_mode = False

        bg_w = self.backgroundWidget.width()
        bg_h = self.backgroundWidget.height()

        auth_x = (bg_w - self.auth_card.width()) // 2
        auth_y = (bg_h - self.auth_card.height()) // 2
        self.auth_card.move(auth_x, auth_y)
        self.auth_card.show()

        self.reset_card.move(
            bg_w + 100,
            (bg_h - self.reset_card.height()) // 2
        )
        self.new_password_card.move(
            bg_w + 100,
            (bg_h - self.new_password_card.height()) // 2
        )

    def _clear_auth_fields(self):
        """Очищает поля авторизации и снимает галочку 'Запомнить меня'."""
        if hasattr(self.auth_card, 'phoneInput'):
            self.auth_card.phoneInput.clear()
        if hasattr(self.auth_card, 'passwordInput'):
            self.auth_card.passwordInput.clear()
        if hasattr(self.auth_card, 'rememberCheckBox'):
            self.auth_card.rememberCheckBox.setChecked(False)

    def _check_saved_session(self):
        """Проверяет сохранённую сессию ДО показа окна."""
        from client.core.settings.settings_manager import SettingsManager

        session = SettingsManager().get_auth_session()
        if not session.get("refresh_token"):
            # Сессии нет — сразу показываем логин
            self.showMaximized()
            return

        print("🔑 Найдена сохранённая сессия, пробуем автовход без показа окна...")
        # Окно НЕ показываем — ждём результат автовхода в фоне.
        self._auto_login_thread = QThread()
        self._auto_login_worker = AutoLoginWorker()
        self._auto_login_worker.moveToThread(self._auto_login_thread)

        self._auto_login_thread.started.connect(self._auto_login_worker.run)
        self._auto_login_worker.finished.connect(self._on_auto_login_success)
        self._auto_login_worker.failed.connect(self._on_auto_login_failed)
        self._auto_login_worker.finished.connect(self._auto_login_thread.quit)
        self._auto_login_worker.failed.connect(self._auto_login_thread.quit)
        self._auto_login_thread.finished.connect(self._auto_login_thread.deleteLater)

        self._auto_login_thread.start()

    def _on_auto_login_success(self, user_data):
        print("✅ Автовход выполнен")
        self.switch_to_main_window(user_data)

    def _on_auto_login_failed(self, error_msg):
        print(f"ℹ️ Автовход не выполнен: {error_msg}")
        # Показываем окно логина (автовход провалился)
        self.showMaximized()

    def _apply_shadow(self, widget: QWidget):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 10)
        widget.setGraphicsEffect(shadow)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'web_view') and self.web_view:
            self.web_view.setGeometry(0, 0, self.width(), self.height())
        self._update_cards_position()
        # Обновляем позиции уведомлений
        if hasattr(self, 'notification_manager'):
            self.notification_manager._update_notifications_position()

    def _update_cards_position(self):
        bg_size = self.backgroundWidget.size()
        auth_size = self.auth_card.size()
        reset_size = self.reset_card.size()
        new_password_size = self.new_password_card.size()

        auth_y = (bg_size.height() - auth_size.height()) // 2
        reset_y = (bg_size.height() - reset_size.height()) // 2
        new_password_y = (bg_size.height() - new_password_size.height()) // 2

        if self._is_new_password_mode:
            new_password_x = (bg_size.width() - new_password_size.width()) // 2
            self.new_password_card.move(new_password_x, new_password_y)
            self.auth_card.move(-auth_size.width() - 100, auth_y)
            self.reset_card.move(bg_size.width() + 100, reset_y)
        elif self._is_reset_mode:
            reset_x = (bg_size.width() - reset_size.width()) // 2
            self.reset_card.move(reset_x, reset_y)
            self.auth_card.move(-auth_size.width() - 100, auth_y)
            self.new_password_card.move(bg_size.width() + 100, new_password_y)
        else:
            auth_x = (bg_size.width() - auth_size.width()) // 2
            self.auth_card.move(auth_x, auth_y)
            self.reset_card.move(bg_size.width() + 100, reset_y)
            self.new_password_card.move(bg_size.width() + 100, new_password_y)

    def _on_go_to_new_password(self, phone_number: str, code: str):
        """
        Обработчик перехода к виджету нового пароля
        Вызывается из reset_card при успешной верификации кода
        """
        logger.info(f"📥 Получены данные в LoginWindow: phone={phone_number}, code={code}")

        # Передаем данные в виджет нового пароля
        if hasattr(self, 'new_password_card'):
            self.new_password_card.set_reset_data(phone_number, code)
            logger.info(f"✅ Данные переданы в NewPasswordWidget")
        else:
            logger.error("❌ new_password_card не найден в LoginWindow")
            return

        # Показываем виджет нового пароля
        self.show_new_password()

    def show_reset_password(self):
        """Показать окно восстановления пароля"""
        # Получаем номер телефона из поля ввода
        phone = ""
        if hasattr(self.auth_card, 'phoneInput'):
            phone = self.auth_card.phoneInput.text().strip()
            print(f"📱 Номер телефона для восстановления: {phone}")

        # Передаем номер в виджет восстановления
        if hasattr(self.reset_card, 'set_phone_number'):
            self.reset_card.set_phone_number(phone)
        else:
            print("⚠️ ResetPasswordWidget не имеет метода set_phone_number")

        self._is_reset_mode = True
        self._is_new_password_mode = False
        bg_w, bg_h = self.backgroundWidget.width(), self.backgroundWidget.height()

        auth_target_x = -self.auth_card.width() - 100
        reset_target_x = (bg_w - self.reset_card.width()) // 2
        reset_y = (bg_h - self.reset_card.height()) // 2
        new_password_x = bg_w + 100
        new_password_y = (bg_h - self.new_password_card.height()) // 2

        self.reset_card.move(bg_w + 100, reset_y)
        self.reset_card.show()
        self.new_password_card.move(new_password_x, new_password_y)

        self.anim_group = QParallelAnimationGroup()

        anim_auth = QPropertyAnimation(self.auth_card, b"pos")
        anim_auth.setDuration(450)
        anim_auth.setStartValue(self.auth_card.pos())
        anim_auth.setEndValue(QPoint(auth_target_x, self.auth_card.y()))
        anim_auth.setEasingCurve(QEasingCurve.Type.InOutCubic)

        anim_reset = QPropertyAnimation(self.reset_card, b"pos")
        anim_reset.setDuration(450)
        anim_reset.setStartValue(QPoint(bg_w + 100, reset_y))
        anim_reset.setEndValue(QPoint(reset_target_x, reset_y))
        anim_reset.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self.anim_group.addAnimation(anim_auth)
        self.anim_group.addAnimation(anim_reset)
        self.anim_group.start()

    def show_new_password(self):
        """Показать окно смены пароля"""
        self._is_new_password_mode = True
        self._is_reset_mode = False
        bg_w, bg_h = self.backgroundWidget.width(), self.backgroundWidget.height()

        reset_target_x = -self.reset_card.width() - 100
        new_password_x = (bg_w - self.new_password_card.width()) // 2
        new_password_y = (bg_h - self.new_password_card.height()) // 2

        self.new_password_card.move(bg_w + 100, new_password_y)
        self.new_password_card.show()

        self.anim_group = QParallelAnimationGroup()

        anim_reset = QPropertyAnimation(self.reset_card, b"pos")
        anim_reset.setDuration(450)
        anim_reset.setStartValue(self.reset_card.pos())
        anim_reset.setEndValue(QPoint(reset_target_x, self.reset_card.y()))
        anim_reset.setEasingCurve(QEasingCurve.Type.InOutCubic)

        anim_new_password = QPropertyAnimation(self.new_password_card, b"pos")
        anim_new_password.setDuration(450)
        anim_new_password.setStartValue(QPoint(bg_w + 100, new_password_y))
        anim_new_password.setEndValue(QPoint(new_password_x, new_password_y))
        anim_new_password.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self.anim_group.addAnimation(anim_reset)
        self.anim_group.addAnimation(anim_new_password)
        self.anim_group.start()

    def show_login_card(self):
        """Показать окно авторизации"""
        self._is_reset_mode = False
        self._is_new_password_mode = False
        bg_w, bg_h = self.backgroundWidget.width(), self.backgroundWidget.height()

        auth_target_x = (bg_w - self.auth_card.width()) // 2
        auth_y = (bg_h - self.auth_card.height()) // 2
        reset_target_x = bg_w + 100
        new_password_target_x = bg_w + 100

        self.anim_group = QParallelAnimationGroup()

        anim_auth = QPropertyAnimation(self.auth_card, b"pos")
        anim_auth.setDuration(450)
        anim_auth.setStartValue(self.auth_card.pos())
        anim_auth.setEndValue(QPoint(auth_target_x, auth_y))
        anim_auth.setEasingCurve(QEasingCurve.Type.InOutCubic)

        anim_reset = QPropertyAnimation(self.reset_card, b"pos")
        anim_reset.setDuration(450)
        anim_reset.setStartValue(self.reset_card.pos())
        anim_reset.setEndValue(QPoint(reset_target_x, self.reset_card.y()))
        anim_reset.setEasingCurve(QEasingCurve.Type.InOutCubic)

        anim_new_password = QPropertyAnimation(self.new_password_card, b"pos")
        anim_new_password.setDuration(450)
        anim_new_password.setStartValue(self.new_password_card.pos())
        anim_new_password.setEndValue(QPoint(new_password_target_x, self.new_password_card.y()))
        anim_new_password.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self.anim_group.addAnimation(anim_auth)
        self.anim_group.addAnimation(anim_reset)
        self.anim_group.addAnimation(anim_new_password)
        self.anim_group.start()



    def on_main_window_closed(self):
        """Обработка закрытия главного окна"""
        print("Главное окно закрыто")
        self.show()
        self.raise_()
        self.activateWindow()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.web_view is not None:
            pos = self.web_view.mapFromGlobal(event.globalPosition().toPoint())
            js_code = f"if (typeof updateMousePos === 'function') {{ updateMousePos({pos.x()}, {pos.y()}); }}"
            self.web_view.page().runJavaScript(js_code)


if __name__ == "__main__":
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.showMaximized()
    sys.exit(app.exec())