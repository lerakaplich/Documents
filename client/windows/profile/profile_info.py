import os
from PyQt6.QtWidgets import QLabel, QMessageBox, QFormLayout


class ProfileInfo:
    """Управление информацией профиля сотрудника.

    Все QLabel'ы берутся из profile.ui (статические — Должность, Телефон,
    Email, Дата рождения; динамические — строки подразделений из
    department_chain). Цвета заданы токенами {TEXT_*} в .ui и подставляются
    ThemeManager'ом при смене темы.
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.current_phone_raw = ""
        self.current_email_raw = ""
        self.http_client = None

        self.infoFrame = None
        self.labelTitle = None

        self.label_position_value = None
        self.label_phone_value = None
        self.label_email_value = None
        self.label_birth_date_value = None

        self.mainLayout = None

        # Динамически созданные лейблы строк подразделений
        self._dept_type_labels = []
        self._dept_name_labels = []

        from client.core.state.data_events import get_data_events
        get_data_events().profile_changed.connect(self._on_profile_changed)

        # в SettingsTab.__init__
        from client.core.state.data_events import get_data_events
        get_data_events().profile_changed.connect(self._on_profile_changed)

    def _on_profile_changed(self, data: dict):
        if "phone_number" in data:
            phone = data["phone_number"] or ""
            self.current_phone_raw = phone
            if self.label_phone_value:
                self.label_phone_value.setText(
                    self.format_phone_display(phone) if phone else "Не указан"
                )
        if "email" in data:
            email = data["email"] or ""
            self.current_email_raw = email
            if self.label_email_value:
                self.label_email_value.setText(email or "Не указан")

    # ─────────────────────────────────────────────
    # Инъекция виджетов


    def set_http_client(self, http_client):
        self.http_client = http_client
        print("✅ HTTP клиент установлен в ProfileInfo")

    def setup_ui_elements(
        self,
        infoFrame,
        labelTitle,
        label_position_value,
        label_phone_value,
        label_email_value,
        label_birth_date_value,
        mainLayout=None,
    ):
        self.infoFrame = infoFrame
        self.labelTitle = labelTitle
        self.label_position_value = label_position_value
        self.label_phone_value = label_phone_value
        self.label_email_value = label_email_value
        self.label_birth_date_value = label_birth_date_value
        self.mainLayout = mainLayout


    # ─────────────────────────────────────────────
    # Обновление данных

    def update_profile(self, full_name, position, department_chain, phone, email, birth_date):
        print("update_profile вызван")
        self._last_department_chain = department_chain

        if self.labelTitle:
            self.labelTitle.setText(full_name)

        self.current_phone_raw = phone
        self.current_email_raw = email

        # ── Должность ──
        if self.label_position_value:
            self.label_position_value.setText(position or "Не указана")

        # ── Подразделения (динамические строки) ──
        # department_chain: [(type, name), ...] сверху вниз от ВЕРХНЕГО к ГЛУБОКОМУ,
        # например:
        #   [('Подразделение', 'НТЦ'), ('Отдел', 'Телематика'), ('Сектор', 'Бэкенд')]
        # В UI нужно наоборот — от глубокого к верхнему:
        #   Сектор: Бэкенд
        #   Отдел: Телематика
        #   Подразделение: НТЦ
        self._rebuild_department_rows(department_chain)

        # ── Телефон ──
        if self.label_phone_value:
            self.label_phone_value.setText(
                self.format_phone_display(phone) if phone else "Не указан"
            )

        # ── Email ──
        if self.label_email_value:
            self.label_email_value.setText(email if email else "Не указан")

        # ── Дата рождения ──
        if self.label_birth_date_value:
            self.label_birth_date_value.setText(
                birth_date if birth_date else "Не указана"
            )

        from client.core.state.data_events import get_data_events
        get_data_events().profile_changed.emit({
            "phone_number": phone or "",
            "email": email or "",
        })

        print("update_profile завершён")

    def _rebuild_department_rows(self, department_chain):
        """
        Создаёт строки подразделений в QFormLayout infoFrame динамически.
        Каждая строка: [Тип]: [Название], сверху вниз от глубокого к верхнему.
        Старые строки удаляются.
        """
        if not self.infoFrame:
            return

        layout = self.infoFrame.layout()
        if not isinstance(layout, QFormLayout):
            return

        # 1. Удаляем ранее созданные строки подразделений
        for lbl in self._dept_type_labels + self._dept_name_labels:
            try:
                layout.removeWidget(lbl)
                lbl.deleteLater()
            except Exception:
                pass
        self._dept_type_labels.clear()
        self._dept_name_labels.clear()

        if not department_chain:
            return

        # 2. Идём по цепочке в обратном порядке: от глубокого к верхнему.
        # department_chain[0] — самый верхний (напр. Подразделение),
        # department_chain[-1] — самый глубокий (напр. Сектор).
        ordered = list(reversed(department_chain))

        # 3. Вставляем строки сразу после строки «Должность» (row 0),
        # перед строкой «Телефон». В .ui телефон и остальные сдвинуты на
        # большие индексы (100+), поэтому вставим с row=1, 2, 3...
        # QFormLayout сам сдвинет существующие строки, если задать явный row.
        insert_row = 1
        for dept_type, dept_name in ordered:
            # Тип: «Отдел», «Сектор», «Подразделение» — как пришло из БД
            type_text = (dept_type or "").strip()
            type_label_text = f"{type_text}:" if type_text else "—"

            type_lbl = QLabel(type_label_text)
            type_lbl.setObjectName("label_dept_type_title")

            name_lbl = QLabel(dept_name or "—")
            name_lbl.setObjectName("label_dept_name_value")

            # Применяем стили темы (в .ui для этих objectName заданы стили)
            from client.core.themes import apply_theme_to_widget
            # Пока просто зададим objectName — ThemeManager подставит по нему
            # при следующем apply_theme_to_all_windows(). Но чтобы цвета
            # применились СРАЗУ при создании, скопируем стиль у соседнего
            # лейбла «Должность» — у него тот же objectName-паттерн.

            # Берём актуальные стили из label_position_title / value
            title_style = self._style_for("label_position_title")
            value_style = self._style_for("label_position_value")
            if title_style:
                type_lbl.setStyleSheet(title_style)
            if value_style:
                name_lbl.setStyleSheet(value_style)

            layout.insertRow(insert_row, type_lbl, name_lbl)
            self._dept_type_labels.append(type_lbl)
            self._dept_name_labels.append(name_lbl)
            insert_row += 1

    def _style_for(self, object_name: str) -> str:
        """
        Возвращает styleSheet лейбла с данным objectName внутри infoFrame
        (уже с подставленными токенами темы).
        """
        if not self.infoFrame:
            return ""
        for child in self.infoFrame.findChildren(QLabel):
            if child.objectName() == object_name:
                return child.styleSheet()
        return ""

    @staticmethod
    def format_phone_display(phone: str) -> str:
        digits = "".join(filter(str.isdigit, phone or ""))
        if len(digits) == 12:
            return f"+{digits[:3]} ({digits[3:5]}) {digits[5:8]}-{digits[8:10]}-{digits[10:12]}"
        return phone

    def on_phone_updated(self, new_phone: str):
        self.current_phone_raw = new_phone
        if self.label_phone_value:
            self.label_phone_value.setText(self.format_phone_display(new_phone))

        if self.http_client:
            try:
                from client.services.employee_service import EmployeeService
                EmployeeService(self.http_client).update_my_profile(
                    {"phone_number": new_phone}
                )
                QMessageBox.information(self.parent, "Успешно", "Номер телефона обновлён")
            except Exception as e:
                QMessageBox.warning(
                    self.parent, "Ошибка",
                    f"Не удалось обновить телефон на сервере:\n{str(e)}"
                )
        else:
            QMessageBox.information(self.parent, "Успешно",
                                    "Номер телефона обновлён (локально)")



    def on_email_updated(self, new_email: str):
        self.current_email_raw = new_email
        if self.label_email_value:
            self.label_email_value.setText(new_email if new_email else "Не указан")

        if self.http_client:
            try:
                from client.services.employee_service import EmployeeService
                EmployeeService(self.http_client).update_my_profile({"email": new_email})
                QMessageBox.information(self.parent, "Успешно", "Email обновлён")
            except Exception as e:
                QMessageBox.warning(
                    self.parent, "Ошибка",
                    f"Не удалось обновить email на сервере:\n{str(e)}"
                )
        else:
            QMessageBox.information(self.parent, "Успешно",
                                    "Email обновлён (локально)")

    def reapply_theme(self):
        """Пересоздать строки подразделений с актуальными стилями темы."""
        # Сохраняем последний department_chain
        if hasattr(self, "_last_department_chain"):
            self._rebuild_department_rows(self._last_department_chain)