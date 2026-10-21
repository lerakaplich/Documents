# client/windows/documents/table/create/document_dialog_extra_fields.py
"""
Дополнительные реквизиты документа: номер копии, входящий номер/дата, гриф,
конфиденциальность, «требуется ответ», подписант, статус.
Виджеты создаются программно (если нарисуешь их в Designer под теми же
именами — _build_extra_fields можно не вызывать).
"""

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QCheckBox, QComboBox, QGridLayout, QLabel, QLineEdit, QWidget

try:
    from client.windows.date_edit import CustomCalendarDateEdit as _DateEdit
except ImportError:
    from PyQt6.QtWidgets import QDateEdit as _DateEdit

from client.windows.documents.table.create.document_dialog_constants import STATUSES


class ExtraFieldsMixin:
    def _build_extra_fields(self):
        root = self.layout()
        if root is None:
            return

        self.extraFieldsBox = QWidget(self)
        grid = QGridLayout(self.extraFieldsBox)
        grid.setContentsMargins(0, 0, 0, 0)

        self.labelExtra = QLabel("Дополнительные реквизиты", self.extraFieldsBox)
        self.labelExtra.setObjectName("labelExtra")
        grid.addWidget(self.labelExtra, 0, 0, 1, 2)

        def add(row, col, label_attr, text, widget_attr, widget):
            label = QLabel(text, self.extraFieldsBox)
            setattr(self, label_attr, label)
            setattr(self, widget_attr, widget)
            grid.addWidget(label, row * 2 + 1, col)
            grid.addWidget(widget, row * 2 + 2, col)

        add(0, 0, "labelNumcopy", "Номер копии", "numcopy_edit", QLineEdit())
        add(0, 1, "labelClearance", "Гриф доступа", "clearance_box", QComboBox())
        add(1, 0, "labelIncomingNumb", "Входящий номер", "incoming_numb_edit", QLineEdit())
        add(1, 1, "labelIncomingDate", "Входящая дата", "incoming_date_edit", _DateEdit())
        add(2, 0, "labelSourceOfficial", "Подписант (ФИО / должность)", "source_official_edit", QLineEdit())
        add(2, 1, "labelStatus", "Статус", "status_box", QComboBox())

        self.confident_check = QCheckBox("Конфиденциально", self.extraFieldsBox)
        self.needs_response_check = QCheckBox("Требуется ответ", self.extraFieldsBox)
        grid.addWidget(self.confident_check, 7, 0)
        grid.addWidget(self.needs_response_check, 7, 1)

        # Входящая дата необязательна: минимальная дата = «пусто»
        self.incoming_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.incoming_date_edit.setCalendarPopup(True)
        self.incoming_date_edit.setSpecialValueText(" ")
        self.incoming_date_edit.setDate(self.incoming_date_edit.minimumDate())

        # Статус меняется только при редактировании
        for value, label in STATUSES:
            self.status_box.addItem(label, value)
        is_edit = self.mode == "edit"
        self.status_box.setVisible(is_edit)
        self.labelStatus.setVisible(is_edit)

        self._fill_clearance_box()

        # Вставляем перед последним элементом (ряд с кнопками) — подправь под свой .ui
        if hasattr(root, "insertWidget"):  # QVBoxLayout / QBoxLayout
            root.insertWidget(max(0, root.count() - 1), self.extraFieldsBox)
        elif hasattr(root, "rowCount"):  # QGridLayout
            root.addWidget(self.extraFieldsBox, root.rowCount(), 0, 1, -1)
        else:
            root.addWidget(self.extraFieldsBox)

    def _fill_clearance_box(self):
        current = self.clearance_box.currentData()
        self.clearance_box.clear()
        self.clearance_box.addItem("— не задан —", None)
        for c in getattr(self, "clearances", []):
            self.clearance_box.addItem(c.get("name", ""), c.get("id"))
        idx = self.clearance_box.findData(current)
        self.clearance_box.setCurrentIndex(max(idx, 0))

    def set_clearances_data(self, clearances: list[dict]):
        """Справочник грифов доступа (когда появится endpoint)."""
        self.clearances = clearances
        if hasattr(self, "clearance_box"):
            self._fill_clearance_box()
            # если документ уже загружен — восстановим выбранный гриф
            clearance_id = (self.document_data or {}).get("clearance_id")
            idx = self.clearance_box.findData(clearance_id)
            if idx >= 0:
                self.clearance_box.setCurrentIndex(idx)

    # ── форма → payload ──
    def _collect_extra_payload(self) -> dict:
        if not hasattr(self, "numcopy_edit"):
            return {}
        d = self.incoming_date_edit
        has_date = d.date() != d.minimumDate()
        payload = {
            "numcopy": self.numcopy_edit.text().strip() or None,
            "incoming_numb": self.incoming_numb_edit.text().strip() or None,
            "incoming_date": d.date().toString("yyyy-MM-dd") if has_date else None,
            "clearance_id": self.clearance_box.currentData(),
            "confident_flag": 1 if self.confident_check.isChecked() else 0,
            "needs_response": self.needs_response_check.isChecked(),
            "source_official_text": self.source_official_edit.text().strip() or None,
        }
        if self.mode == "edit" and self.status_box.currentData():
            payload["status"] = self.status_box.currentData()
        return payload

    # ── данные → форма ──
    def _load_extra_data(self, data: dict):
        if not hasattr(self, "numcopy_edit"):
            return
        self.numcopy_edit.setText(data.get("numcopy") or "")
        self.incoming_numb_edit.setText(data.get("incoming_numb") or "")
        self.source_official_edit.setText(data.get("source_official_text") or "")
        self.confident_check.setChecked(bool(data.get("confident_flag")))
        self.needs_response_check.setChecked(bool(data.get("needs_response")))

        raw = data.get("incoming_date")
        if raw:
            d = QDate.fromString(str(raw)[:10], "yyyy-MM-dd")
            if d.isValid():
                self.incoming_date_edit.setDate(d)

        idx = self.clearance_box.findData(data.get("clearance_id"))
        if idx >= 0:
            self.clearance_box.setCurrentIndex(idx)
        idx = self.status_box.findData(data.get("status"))
        if idx >= 0:
            self.status_box.setCurrentIndex(idx)
