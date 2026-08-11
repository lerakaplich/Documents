import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import pyqtSignal

class DeleteDialog(QDialog):
    """
    Диалог подтверждения удаления.
    Загружает UI из файла delete_dialog.ui.
    """
    # Сигнал, который можно использовать для дополнительной обработки
    # (например, когда нажата кнопка "Да")
    deleted = pyqtSignal()

    def __init__(self, parent=None, ui_path: str = None):
        """
        :param parent: родительский виджет
        :param ui_path: путь к файлу delete_dialog.ui.
                        Если не указан, ищется в стандартной папке '../ui/'
                        относительно местоположения этого файла.
        """
        super().__init__(parent)

        # Определяем путь к UI-файлу, если он не передан
        if ui_path is None:
            # Предполагаем, что файл лежит в папке ui на уровень выше
            current_dir = os.path.dirname(os.path.abspath(__file__))
            ui_path = os.path.join(current_dir, '..', 'ui', 'delete_dialog.ui')
            ui_path = os.path.normpath(ui_path)

        # Загружаем UI в текущий объект (self)
        uic.loadUi(ui_path, self)

        # Настраиваем кнопки
        self.buttonYes.clicked.connect(self._on_yes_clicked)
        self.buttonNo.clicked.connect(self.reject)  # Закрыть с отклонением

        # Дополнительно можно настроить модальность
        self.setModal(True)

    def _on_yes_clicked(self):
        """Обработчик нажатия 'Да'."""
        self.deleted.emit()  # Сигнал об удалении
        self.accept()        # Закрыть диалог с кодом Accepted

    @staticmethod
    def show_confirmation(parent=None, ui_path: str = None) -> bool:
        """
        Удобный статический метод для показа диалога.
        Возвращает True, если пользователь нажал 'Да', иначе False.
        """
        dialog = DeleteDialog(parent, ui_path)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted


if __name__ == "__main__":
    import sys
    import os
    from PyQt6.QtWidgets import QApplication, QDialog

    # Создаём приложение
    app = QApplication(sys.argv)

    # Определяем путь к UI-файлу (можно передать явно, если он не там)
    # В этом примере предполагается, что файл delete_dialog.ui лежит
    # в папке "../ui/" относительно текущего скрипта.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ui_path = os.path.join(current_dir, '..', 'ui', 'delete_dialog.ui')
    ui_path = os.path.normpath(ui_path)

    # Проверяем, существует ли файл, иначе используем путь по умолчанию
    if not os.path.exists(ui_path):
        print(f"Файл {ui_path} не найден, пробуем использовать путь по умолчанию")
        ui_path = None  # Тогда класс сам попробует найти по тому же пути

    # Создаём диалог
    dialog = DeleteDialog(ui_path=ui_path)

    # Показываем и ждём результата
    result = dialog.exec()

    if result == QDialog.DialogCode.Accepted:
        print("Пользователь подтвердил удаление")
    else:
        print("Пользователь отменил удаление")

    # Завершаем приложение
    sys.exit(app.exec())