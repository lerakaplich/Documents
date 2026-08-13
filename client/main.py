import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from client.windows.login.login_window import LoginWindow

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


def main():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)

    try:
        # Устанавливаем имя приложения
        app.setApplicationName("Документооборот")
        app.setOrganizationName("ОАО «МАЗ» - управляющая компания холдинга БЕЛАВТОМАЗ")
        window = LoginWindow()
        window.showMaximized()
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Ошибка при запуске приложения: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()