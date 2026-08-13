#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Главный файл запуска приложения Документооборот
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем окно входа
from client.windows.login.login_window import LoginWindow


def main():
    """Главная функция запуска приложения"""

    # Настройка высокого DPI для корректного отображения на мониторах с высоким разрешением

    # Включаем поддержку OpenGL для WebEngine
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    # Создаем приложение
    app = QApplication(sys.argv)

    # Устанавливаем имя приложения
    app.setApplicationName("Документооборот")
    app.setOrganizationName("ОАО «МАЗ» - управляющая компания холдинга БЕЛАВТОМАЗ")

    # Создаем и показываем окно входа
    window = LoginWindow()
    window.showMaximized()

    # Запускаем главный цикл приложения
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
