# client/main.py (или где у тебя точка входа)

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
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