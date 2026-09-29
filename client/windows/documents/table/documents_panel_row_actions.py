"""
Обработка действий из контекстного меню строки таблицы (удалить, вложение,
ответ, прочитано, закрепить, история, перенаправление, комментарий).

Вынесено из DocumentsPanel — панель только пересылает сюда сигнал
document_action_triggered (см. DocumentsPanel._on_document_action).
"""
from datetime import datetime

from PyQt6.QtWidgets import QMessageBox

from client.windows.documents.history.history_dialog import HistoryDialog


class DocumentsRowActionController:

    def __init__(self, panel):
        self.panel = panel

    def handle(self, action_type: str, document_data: dict):
        panel = self.panel
        if action_type == "redirect":
            self._redirect(document_data)
        elif action_type == "comment":
            self._comment(document_data)
        elif action_type == "history":
            self._history(document_data)
        elif action_type == "edit":
            panel.crud.open_edit_dialog(document_data)
        elif action_type == "delete":
            self._delete(document_data)
        elif action_type == "attachment":
            self._attachment(document_data)
        elif action_type == "reply_attachment":
            self._reply_attachment(document_data)
        elif action_type == "read_status":
            is_read = document_data.get("is_read", False)
            self._read_status(document_data, not is_read)
        elif action_type == "pin_toggle":
            self._pin_toggle(document_data)
        else:
            print(f"[DocumentsPanel] Неизвестное действие: {action_type}")

    # ---------- удаление ----------

    def _delete(self, document_data: dict):
        panel = self.panel
        doc_name = document_data.get('title', document_data.get('name', 'Документ'))
        reply = QMessageBox.question(
            panel, "Подтверждение удаления",
            f"Вы действительно хотите удалить документ '{doc_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            if hasattr(panel.controller, 'delete_document'):
                success = panel.controller.delete_document(document_data.get('id'))
                if success:
                    panel.refresh()
                    QMessageBox.information(panel, "Успешно", "Документ удален")
                else:
                    QMessageBox.warning(panel, "Ошибка", "Не удалось удалить документ")
            else:
                QMessageBox.warning(panel, "Ошибка", "Функция удаления пока не реализована")
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка при удалении: {e}")
            QMessageBox.critical(panel, "Ошибка", f"Ошибка удаления: {str(e)}")

    # ---------- вложения (заглушки — реальная подгрузка есть только в таблице, см. attachment_service.py) ----------

    def _attachment(self, document_data: dict):
        QMessageBox.information(self.panel, "Вложения", "Функция вложений будет добавлена в следующей версии")

    def _reply_attachment(self, document_data: dict):
        QMessageBox.information(self.panel, "Ответные вложения",
                                "Функция ответных вложений будет добавлена в следующей версии")

    # ---------- прочитано / закреплено ----------

    def _read_status(self, document_data: dict, is_read: bool):
        panel = self.panel
        doc_id = document_data.get('id')
        if hasattr(panel.controller, 'change_read_status'):
            success = panel.controller.change_read_status(doc_id, is_read)
            if success:
                panel.refresh()
                status_text = "прочитанным" if is_read else "непрочитанным"
                QMessageBox.information(panel, "Успешно", f"Документ отмечен как {status_text}")
        else:
            panel.documents_table.update_document_read_status(doc_id, is_read)
            QMessageBox.information(panel, "Информация", "Статус прочтения обновлен локально")

    def _pin_toggle(self, document_data: dict):
        panel = self.panel
        doc_id = document_data.get('id')
        if hasattr(panel.controller, 'toggle_pin_status'):
            success = panel.controller.toggle_pin_status(doc_id)
            if success:
                panel.refresh()
                QMessageBox.information(panel, "Успешно", "Статус закрепления обновлен")
        else:
            current_pin = document_data.get('is_pinned', False)
            new_pin = not current_pin
            panel.documents_table._controller.toggle_pin(doc_id, new_pin)
            QMessageBox.information(panel, "Информация", "Статус закрепления обновлен локально")

    # ---------- история ----------

    def _history(self, document_data: dict):
        panel = self.panel
        try:
            full_document_data = panel.controller.get_full_document_for_history(document_data)
            if not full_document_data:
                full_document_data = self._enrich_with_history(document_data)

            current_user = panel.controller.get_current_user() if hasattr(panel.controller, 'get_current_user') else {}

            dialog = HistoryDialog(
                document_data=full_document_data,
                parent=panel,
                current_user=current_user,
                http_client=panel.http_client,
            )
            dialog.exec()
        except Exception as e:
            print(f"[DocumentsPanel] Ошибка при открытии диалога истории: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(panel, "Ошибка", f"Не удалось открыть историю документа: {str(e)}")

    def _enrich_with_history(self, document_data: dict) -> dict:
        panel = self.panel
        enriched_data = document_data.copy()
        if hasattr(panel.controller, 'get_document_history'):
            history = panel.controller.get_document_history(document_data.get('id'))
            if history:
                enriched_data['history'] = history
                return enriched_data
        enriched_data['history'] = self._generate_history(document_data)
        return enriched_data

    @staticmethod
    def _generate_history(document_data: dict) -> list:
        history = []

        created_at = document_data.get('created_at')
        if created_at:
            creator = document_data.get('creator', document_data.get('author', 'Неизвестный пользователь'))
            if isinstance(creator, dict):
                creator_name = creator.get('full_name', creator.get('name', 'Неизвестный пользователь'))
            else:
                creator_name = str(creator)
            history.append({'type': 'created', 'user': creator_name, 'created_at': created_at})

        for comment in document_data.get('comments', []):
            author = comment.get('author_name', comment.get('author', 'Неизвестный пользователь'))
            history.append({
                'type': 'comment', 'user': author,
                'text': comment.get('text', ''),
                'created_at': comment.get('created_at', datetime.now()),
            })

        for redirect in document_data.get('redirects', []):
            history.append({
                'type': 'redirect',
                'from_user': redirect.get('from_user', 'Неизвестный пользователь'),
                'to_user': redirect.get('to_user', 'Неизвестный пользователь'),
                'created_at': redirect.get('redirected_at', datetime.now()),
            })

        for change in document_data.get('status_changes', []):
            history.append({
                'type': 'status_change',
                'user': change.get('user', 'Неизвестный пользователь'),
                'old_status': change.get('old_status', ''),
                'new_status': change.get('new_status', ''),
                'created_at': change.get('changed_at', datetime.now()),
            })

        history.sort(key=lambda x: x.get('created_at', datetime.min))
        return history

    # ---------- перенаправление ----------

    def _redirect(self, document_data: dict):
        panel = self.panel
        try:
            from client.windows.documents.redirect.redirect_dialog import RedirectDialog

            doc_id = document_data.get("id")
            current_recipients = document_data.get("delegates", [])
            all_employees = panel.controller.get_employees_for_redirect()

            dialog = RedirectDialog(current_recipients, all_employees, parent=panel)
            dialog.redirect_confirmed.connect(
                lambda ids, comment: self._confirm_redirect(doc_id, ids, comment)
            )
            dialog.exec()
        except Exception:
            import traceback
            traceback.print_exc()

    def _confirm_redirect(self, document_id: int, recipient_ids: list, comment: str):
        panel = self.panel
        success = panel.controller.redirect_document(document_id, recipient_ids, comment)
        if success:
            panel.refresh()

    # ---------- комментарии ----------

    def _comment(self, document_data: dict):
        panel = self.panel
        try:
            from client.windows.documents.comments.comment_dialog import CommentDialog

            document_to_pass = panel.controller.get_full_document_for_comment(document_data)
            current_user = panel.controller.get_current_user()

            dialog = CommentDialog(
                document_data=document_to_pass,
                parent=panel,
                current_user=current_user,
                http_client=panel.http_client,
            )
            dialog.comment_added.connect(
                lambda comment: self._on_comment_added(document_data.get("id"), comment)
            )
            dialog.exec()
        except Exception as e:
            import traceback
            print(f"[DocumentsPanel] Error opening comment dialog: {e}")
            traceback.print_exc()

    def _on_comment_added(self, document_id: int, new_comment: dict):
        panel = self.panel
        success = panel.controller.add_comment_to_document(document_id, new_comment)
        if success:
            panel.refresh()
            print(f"[DocumentsPanel] Комментарий сохранен через контроллер для документа {document_id}")