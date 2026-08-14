import os
from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal


class DeleteDialog(QDialog):
    """
    Диалог подтверждения удаления.
    Загружает UI из файла delete_dialog.ui.
    """
    deleted = pyqtSignal()

    def __init__(self, parent=None, ui_path: str = None):
        super().__init__(parent)

        # Определяем путь к UI-файлу, если он не передан
        if ui_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Правильный путь: client/ui/system/delete_dialog.ui
            # Относительно текущего файла (windows/system/delete_dialog.py)
            ui_path = os.path.join(current_dir, '..', '..', 'ui', 'system', 'delete_dialog.ui')
            ui_path = os.path.normpath(ui_path)

        print(f"[DEBUG] DeleteDialog ищет UI: {ui_path}")

        # Проверяем существование файла
        if not os.path.exists(ui_path):
            print(f"[ERROR] UI файл не найден: {ui_path}")
            QMessageBox.warning(self, "Ошибка", f"UI файл не найден: {ui_path}")
            self.reject()
            return

        # Загружаем UI
        try:
            uic.loadUi(ui_path, self)
            print(f"[DEBUG] DeleteDialog UI загружен успешно")
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки UI: {e}")
            import traceback
            traceback.print_exc()
            self.reject()
            return

        # Настраиваем кнопки
        if hasattr(self, 'buttonYes'):
            self.buttonYes.clicked.connect(self._on_yes_clicked)
        else:
            print(f"[WARNING] buttonYes не найден в UI")

        if hasattr(self, 'buttonNo'):
            self.buttonNo.clicked.connect(self.reject)
        else:
            print(f"[WARNING] buttonNo не найден в UI")

        self.setModal(True)

    def _on_yes_clicked(self):
        """Обработчик нажатия 'Да'."""
        print("[DEBUG] DeleteDialog: нажата кнопка 'Да'")
        self.deleted.emit()
        self.accept()

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
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = DeleteDialog()
    result = dialog.exec()

    if result == QDialog.DialogCode.Accepted:
        print("Пользователь подтвердил удаление")
    else:
        print("Пользователь отменил удаление")

    sys.exit(app.exec())