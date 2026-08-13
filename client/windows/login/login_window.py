import sys
import os
from PyQt6.QtWidgets import QMainWindow, QWidget, QGraphicsDropShadowEffect, QApplication, QVBoxLayout
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QUrl, QTimer, QPoint, QParallelAnimationGroup
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.uic import loadUi

# Импорты из новой структуры
from client.windows.login.auth_widget import AuthWidget
from client.windows.login.new_password_widget import NewPasswordWidget
from client.windows.login.reset_password_widget import ResetPasswordWidget

# Импортируем MainWindow
from client.windows.main_window import MainWindow


class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Загружаем чистый фон
        ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "ui", "login", "back_login.ui")
        loadUi(ui_path, self)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._is_reset_mode = False
        self._is_new_password_mode = False

        # 2. Анимация звезд WebEngine
        self.web_view = QWebEngineView(self.backgroundWidget)
        self.web_view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        self.backgroundWidget.setMouseTracking(True)

        html_path = os.path.join(os.path.dirname(__file__), "..", "..", "html", "star_animation.html")
        self.web_view.setUrl(QUrl.fromLocalFile(html_path))
        self.web_view.lower()

        # 3. Инициализация виджетов-карточек
        self.auth_card = AuthWidget()
        self.auth_card.setParent(self.backgroundWidget)

        self.reset_card = ResetPasswordWidget()
        self.reset_card.setParent(self.backgroundWidget)

        self.new_password_card = NewPasswordWidget()
        self.new_password_card.setParent(self.backgroundWidget)

        # Добавляем тени
        self._apply_shadow(self.auth_card)
        self._apply_shadow(self.reset_card)
        self._apply_shadow(self.new_password_card)

        # 4. Загрузка логотипа
        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "icons", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                # Очищаем стили и устанавливаем изображение
                self.logoLabel.setStyleSheet("background-color: transparent;")
                self.logoLabel.setText("")
                scaled_pixmap = pixmap.scaled(
                    200, 150,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.logoLabel.setPixmap(scaled_pixmap)
                self.logoLabel.setScaledContents(False)

        # 5. Подключение сигналов переключения
        self.auth_card.forgotPasswordButton.clicked.connect(self.show_reset_password)
        self.reset_card.back_to_login.connect(self.show_login_card)
        self.reset_card.go_to_new_password.connect(self.show_new_password)

        # Подключаем кнопку "Назад к входу" из окна смены пароля
        if hasattr(self.new_password_card, 'backToLoginButton'):
            self.new_password_card.backToLoginButton.clicked.connect(self.show_login_card)

        # 6. Подключение сигналов для перехода в MainWindow
        self.auth_card.login_successful.connect(self.switch_to_main_window)
        self.new_password_card.password_changed_successfully.connect(self.switch_to_main_window)

        # Ссылка на главное окно
        self.main_window = None

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

    def _update_cards_position(self):
        bg_size = self.backgroundWidget.size()
        auth_size = self.auth_card.size()
        reset_size = self.reset_card.size()
        new_password_size = self.new_password_card.size()

        auth_y = (bg_size.height() - auth_size.height()) // 2
        reset_y = (bg_size.height() - reset_size.height()) // 2
        new_password_y = (bg_size.height() - new_password_size.height()) // 2

        if self._is_new_password_mode:
            # Показываем окно смены пароля
            new_password_x = (bg_size.width() - new_password_size.width()) // 2
            self.new_password_card.move(new_password_x, new_password_y)
            self.auth_card.move(-auth_size.width() - 100, auth_y)
            self.reset_card.move(bg_size.width() + 100, reset_y)
        elif self._is_reset_mode:
            # Показываем окно восстановления
            reset_x = (bg_size.width() - reset_size.width()) // 2
            self.reset_card.move(reset_x, reset_y)
            self.auth_card.move(-auth_size.width() - 100, auth_y)
            self.new_password_card.move(bg_size.width() + 100, new_password_y)
        else:
            # Показываем окно авторизации
            auth_x = (bg_size.width() - auth_size.width()) // 2
            self.auth_card.move(auth_x, auth_y)
            self.reset_card.move(bg_size.width() + 100, reset_y)
            self.new_password_card.move(bg_size.width() + 100, new_password_y)

    def show_reset_password(self):
        """Показать окно восстановления пароля"""
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

    def switch_to_main_window(self):
        """Переключение на главное окно"""
        print("Переход в главное окно...")

        if self.main_window is None:
            self.main_window = MainWindow()
            self.main_window.showMaximized()

        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

        # Скрываем окно входа
        self.hide()

        # Обработка закрытия главного окна
        self.main_window.closeEvent = lambda event: self.on_main_window_closed()

    def on_main_window_closed(self):
        """Обработка закрытия главного окна"""
        print("Главное окно закрыто")
        # Показываем окно входа снова
        self.show()
        self.raise_()
        self.activateWindow()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if hasattr(self, 'web_view') and self.web_view:
            pos = self.web_view.mapFromGlobal(event.globalPosition().toPoint())
            js_code = f"if (typeof updateMousePos === 'function') {{ updateMousePos({pos.x()}, {pos.y()}); }}"
            self.web_view.page().runJavaScript(js_code)


if __name__ == "__main__":
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.showMaximized()
    sys.exit(app.exec())