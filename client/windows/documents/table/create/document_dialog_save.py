# client/windows/documents/table/create/document_dialog_save.py
"""
Сохранение документа: обработчики выбора направления/способа создания,
выбор файла и отправка данных на сервер
"""

import os
import uuid
from typing import Any

from PyQt6.QtWidgets import QFileDialog, QMessageBox


class SaveMixin:
    # ─────────────────── ПРОЧИЕ ОБРАБОТЧИКИ ───────────────────

    def _on_direction_changed(self, index):
        if index >= 0 and hasattr(self, "direction_box"):
            print(f"[UI] Выбрано направление: {self.direction_box.currentData()} ({self.direction_box.currentText()})")

    def _on_create_method_changed(self, index):
        if index < 0:
            return
        method = self.create_methods[index]
        print(f"[UI] Выбран метод создания: {method}")

        if method == "Загрузить файл":
            self._open_file_dialog()

    def _open_file_dialog(self):
        """
        Открывает системный проводник для выбора файла документа.
        Раньше выбор пункта "Загрузить файл" только логировался в консоль
        и никакого диалога не открывал — отсюда жалоба "не открывается
        проводник".
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл документа",
            "",
            "Документы (*.pdf *.doc *.docx *.rtf *.odt *.png *.jpg *.jpeg *.tiff);;Все файлы (*.*)",
        )

        if not file_path:
            # Отмена выбора — возвращаем комбобокс в состояние "не выбрано",
            # чтобы не оставалось враньё, что файл прикреплён.
            self.selected_file_path = None
            if hasattr(self, "select_box"):
                self.select_box.blockSignals(True)
                self.select_box.setCurrentIndex(-1)
                self.select_box.blockSignals(False)
            return

        self.selected_file_path = file_path
        print(f"[DocumentDialog] Выбран файл: {file_path}")

        # Показываем имя файла, если в .ui есть подходящий виджет;
        # в любом случае даём пользователю видимое подтверждение выбора.
        shown = False
        for attr_name in ("namedoc_browser", "file_name_label", "selectedFileLabel"):
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setText"):
                widget.setText(os.path.basename(file_path))
                shown = True
                break
        if not shown:
            QMessageBox.information(self, "Файл выбран", f"Выбран файл:\n{os.path.basename(file_path)}")

    # ─────────────────── СОХРАНЕНИЕ ───────────────────

    def save_document(self):
        """
        Сбор данных формы и (в режиме 'create') реальная отправка на сервер
        через DocumentService.create_document → POST /documents.

        Ключи в doc_data соответствуют тому, что ожидает
        DocumentService._build_create_payload: type_id, direction,
        sender_id, global_msg_id, receiver_ids/executor_ids (+ справочники
        _orgs/_depts/_emps для разбора получателей по типу узла).

        Поля, скрытые конфигом типа (types.fields), не валидируются
        и на сервер не отправляются.
        """
        print("🚨 save_document вызван!")
        print(f"   mode={self.mode}")
        print(f"   type_box currentIndex={getattr(self, 'type_box', None) and self.type_box.currentIndex()}")
        print(
            f"   direction_box currentIndex={getattr(self, 'direction_box', None) and self.direction_box.currentIndex()}"
        )
        print(f"   topic='{getattr(self, 'topic_edit', None) and self.topic_edit.toPlainText()}'")
        print(f"   receivers={self.selected_receivers}")
        print(f"   document_service={self.document_service}")
        print(f"   http_client={self.http_client}")

        en = self._field_enabled

        # ── Валидация на уровне формы ──
        if not hasattr(self, "type_box") or self.type_box.currentIndex() < 0:
            QMessageBox.warning(self, "Внимание", "Выберите тип документа")
            return

        if not hasattr(self, "direction_box") or self.direction_box.currentIndex() < 0:
            QMessageBox.warning(self, "Внимание", "Выберите направление документа")
            return

        # Тему и получателей проверяем, только если эти поля включены у типа
        if en("title") and (not hasattr(self, "topic_edit") or not self.topic_edit.toPlainText().strip()):
            QMessageBox.warning(self, "Внимание", "Введите тему документа")
            return

        if en("recipients") and not self.selected_receivers:
            QMessageBox.warning(self, "Внимание", "Выберите получателей документа")
            return

        type_id = self.type_box.currentData()
        direction = self.direction_box.currentData()

        sender_id = self.selected_sender.get("id") if self.selected_sender else None

        # global_msg_id обязателен на сервере (NOT NULL, уникален) — при
        # создании генерируем UUID один раз; при редактировании переиспользуем
        # тот, что уже есть у документа.
        if self.mode == "edit" and self.document_data.get("global_msg_id"):
            global_msg_id = self.document_data["global_msg_id"]
        else:
            global_msg_id = str(uuid.uuid4())

        doc_data: dict[str, Any] = {}

        if self.mode == "edit" and self.document_data:
            doc_data["id"] = self.document_data.get("id")

        doc_data.update(
            {
                "type_id": type_id,
                "direction": direction,
                "title": self.topic_edit.toPlainText().strip() if en("title") else "",
                "about": self.regarding_edit.toPlainText().strip() if en("about") else "",
                "reg_number": self.number_edit.toPlainText().strip() if en("reg_number") else "",
                "sender_id": sender_id if en("sender_id") else None,
                "receiver_ids": self._nodes_for_save(self.selected_receivers) if en("recipients") else [],
                "executor_ids": self._nodes_for_save(self.selected_executors) if en("executors") else [],
                "tags": self.selected_tags if en("tag_ids") else [],
                "global_msg_id": global_msg_id,
                # Справочники — нужны DocumentService, чтобы разложить
                # receiver_ids/executor_ids по target_department_id /
                # target_organization_id / employee_id.
                "_orgs": self.organizations,
                "_depts": self.departments,
                "_emps": self.employees,
            }
        )

        # Дата отправки (sent_date) и срок ответа (deadline)
        if hasattr(self, "date_edit") and en("sent_date"):
            doc_data["sent_date"] = self.date_edit.date().toString("yyyy-MM-dd")

        if hasattr(self, "date_deadline") and en("deadline"):
            doc_data["deadline"] = self.date_deadline.date().toString("yyyy-MM-dd")

        # Порядковый номер (QTextEdit): только целое число, иначе не отправляем
        if hasattr(self, "index_number_edit") and en("sequence_number"):
            seq_text = self.index_number_edit.toPlainText().strip()
            if seq_text:
                if not seq_text.isdigit():
                    QMessageBox.warning(self, "Внимание", "Порядковый номер должен быть целым числом")
                    return
                doc_data["sequence_number"] = int(seq_text)

        # «Требуется ответ»
        doc_data.update(self._collect_extra_payload())

        if self.parent_document_id is not None:
            doc_data["parent_document_id"] = self.parent_document_id  # связь «ответ → исходный документ»

        print(f"[DocumentDialog] {self.mode} документ: {doc_data}")

        if self.mode != "create":
            # Обновление документа (PATCH /documents/{id}) в текущей версии
            # DocumentService не реализовано — эмитим как раньше, чтобы не
            # ломать существующий edit-флоу, если он где-то уже обработан.
            self.document_updated.emit(doc_data)
            self.close()
            return

        if not self.document_service:
            QMessageBox.critical(
                self,
                "Ошибка",
                "Не удалось подключиться к серверу (нет http_client/DocumentService).",
            )
            return

        if hasattr(self, "btn_attach"):
            self.btn_attach.setEnabled(False)

        try:
            created = self.document_service.create_document(doc_data)
        except ValueError as e:
            # Клиентская валидация payload'а (validate_create_payload)
            QMessageBox.warning(self, "Внимание", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать документ:\n{e}")
            return
        finally:
            if hasattr(self, "btn_attach"):
                self.btn_attach.setEnabled(True)

        if not created:
            QMessageBox.critical(self, "Ошибка", "Сервер не вернул созданный документ")
            return

        # Если пользователь выбрал файл через "Загрузить файл" — прикрепляем
        # его к только что созданному документу. Ошибка загрузки вложения
        # не откатывает уже созданный документ — просто предупреждаем.
        if self.selected_file_path:
            new_id = created.get("id") if isinstance(created, dict) else None
            if new_id and self.attachment_service:
                attachment = self.attachment_service.upload_attachment(new_id, self.selected_file_path)
                if not attachment:
                    QMessageBox.warning(
                        self,
                        "Внимание",
                        "Документ создан, но не удалось загрузить прикреплённый файл.\n"
                        "Попробуйте прикрепить его повторно из карточки документа.",
                    )
            elif not self.attachment_service:
                QMessageBox.warning(
                    self,
                    "Внимание",
                    "Документ создан, но сервис загрузки вложений недоступен — файл не прикреплён.",
                )

        self.document_created.emit(created)
        self.close()