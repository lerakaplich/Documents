# client/main.py (или где у тебя точка входа)

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from client.core.themes import set_theme, apply_theme_to_all_windows, apply_saved_theme
from client.core.themes.dark.pink_dark import PinkDarkTheme
from client.core.themes.light.blue import BlueTheme
from client.core.themes.light.green import GreenTheme
from client.core.themes.light.pink import PinkTheme
from client.windows.login.login_window import LoginWindow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)


def main():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)

    try:
        app.setApplicationName("Документооборот")
        app.setOrganizationName("ОАО «МАЗ» - управляющая компания холдинга БЕЛАВТОМАЗ")

        # LoginWindow сам решит: показать себя или сразу открыть MainWindow
        set_theme(PinkDarkTheme)
        apply_saved_theme()
        window = LoginWindow()
        # window.showMaximized()  ← УБРАТЬ! Окно покажет сам LoginWindow

        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Ошибка при запуске приложения: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()