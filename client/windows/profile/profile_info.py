import os
from PyQt6.QtWidgets import QWidget, QFormLayout, QLabel, QPushButton, QHBoxLayout, QMessageBox, QFrame
from PyQt6.QtCore import Qt

from client.windows.profile.user_data.email_edit_window import EmailEditWindow
from client.windows.profile.user_data.phone_edit_window import PhoneEditWindow


class ProfileInfo:
    """Управление информацией профиля сотрудника (ФИО, должность, отделы, телефон, email, дата рождения)."""

    def __init__(self, parent=None):
        self.parent = parent
        self.current_phone_raw = ""
        self.current_email_raw = ""
        self.department_rows = []

        # Виджеты (будут переданы через setup_ui_elements)
        self.infoFrame = None
        self.labelTitle = None
        self.label_position_value = None
        self.label_phone_value = None
        self.label_email_value = None
        self.label_birth_date_value = None
        self.btnEditPhone = None
        self.btnEditEmail = None
        self.mainLayout = None

    def setup_ui_elements(self, infoFrame, labelTitle, label_position_value, label_phone_value,
                          label_email_value, label_birth_date_value, btnEditPhone, btnEditEmail,
                          mainLayout=None):
        """Передаёт ссылки на виджеты из главного окна."""
        self.infoFrame = infoFrame
        self.labelTitle = labelTitle
        self.label_position_value = label_position_value
        self.label_phone_value = label_phone_value
        self.label_email_value = label_email_value
        self.label_birth_date_value = label_birth_date_value
        self.btnEditPhone = btnEditPhone
        self.btnEditEmail = btnEditEmail
        self.mainLayout = mainLayout

    def connect_signals(self):
        """Подключает сигналы кнопок редактирования."""
        if self.btnEditPhone:
            self.btnEditPhone.clicked.connect(self.on_edit_phone_clicked)
        if self.btnEditEmail:
            self.btnEditEmail.clicked.connect(self.on_edit_email_clicked)

    def update_profile(self, full_name, position, department_chain, phone, email, birth_date):
        """Обновляет все данные профиля и перестраивает информационную панель."""
        print("update_profile вызван")
        if self.labelTitle:
            self.labelTitle.setText(full_name)
        else:
            print("labelTitle не найден")

        self.current_phone_raw = phone
        self.current_email_raw = email
        self.rebuild_info_layout(position, department_chain, phone, email, birth_date)

    def rebuild_info_layout(self, position, department_chain, phone, email, birth_date):
        """Полностью перестраивает форму с информацией о сотруднике."""
        print("rebuild_info_layout вызван")

        # Создаём infoFrame, если его нет
        if self.infoFrame is None:
            print("infoFrame не найден, создаём новый")
            self.infoFrame = QFrame(self.parent)
            self.infoFrame.setObjectName("infoFrame")
            self.infoFrame.setStyleSheet(
                "padding: 20px; background-color: white; border-radius: 16px; border: 1px solid #E0E0E0;")
            if self.mainLayout:
                for i in range(self.mainLayout.count()):
                    item = self.mainLayout.itemAt(i)
                    if item.widget() and item.widget().objectName() == "infoFrame":
                        self.mainLayout.removeWidget(item.widget())
                        break
                self.mainLayout.insertWidget(1, self.infoFrame)
            else:
                layout = self.parent.layout()
                if layout:
                    layout.insertWidget(1, self.infoFrame)

        # Настраиваем layout внутри infoFrame
        layout = self.infoFrame.layout()
        if layout is None:
            layout = QFormLayout()
            layout.setSpacing(10)
            layout.setContentsMargins(0, 0, 0, 0)
            self.infoFrame.setLayout(layout)
        else:
            # Очищаем старые виджеты
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                if item.layout():
                    item.layout().deleteLater()

        title_style = "font-size: 24px; color: black; background-color: transparent;"
        value_style = "font-size: 24px; color: black; background-color: transparent;"

        # Должность
        label_pos_title = QLabel("Должность:")
        label_pos_title.setStyleSheet(title_style)
        label_pos_value = QLabel(position if position else "Не указана")
        label_pos_value.setStyleSheet(value_style)
        layout.addRow(label_pos_title, label_pos_value)
        self.label_position_value = label_pos_value

        # Подразделения (цепочка)
        self.department_rows = []
        for type_name, dept_name in department_chain:
            title = QLabel(f"{type_name}:")
            title.setStyleSheet(title_style)
            value = QLabel(dept_name if dept_name else "Не указано")
            value.setStyleSheet(value_style)
            layout.addRow(title, value)
            self.department_rows.append((title, value))

        # Телефон
        label_phone_title = QLabel("Номер телефона:")
        label_phone_title.setStyleSheet(title_style)
        label_phone_value = QLabel(self.format_phone_display(phone) if phone else "Не указан")
        label_phone_value.setStyleSheet(value_style)
        if self.btnEditPhone is None:
            self.btnEditPhone = QPushButton("✏️")
            self.btnEditPhone.setStyleSheet(
                "background-color: transparent; color: #ccab6e; font-size: 20px; border: none;")
            self.btnEditPhone.setMinimumSize(30, 30)
        phone_widget = QWidget()
        phone_widget.setStyleSheet("background-color: transparent;")
        phone_layout = QHBoxLayout(phone_widget)
        phone_layout.setContentsMargins(0, 0, 0, 0)
        phone_layout.setSpacing(5)
        phone_layout.addWidget(label_phone_value)
        phone_layout.addWidget(self.btnEditPhone)
        phone_layout.addStretch()
        layout.addRow(label_phone_title, phone_widget)
        self.label_phone_value = label_phone_value

        # Email
        label_email_title = QLabel("Электронная почта:")
        label_email_title.setStyleSheet(title_style)
        label_email_value = QLabel(email if email else "Не указан")
        label_email_value.setStyleSheet(value_style)
        if self.btnEditEmail is None:
            self.btnEditEmail = QPushButton("✏️")
            self.btnEditEmail.setStyleSheet(
                "background-color: transparent; color: #ccab6e; font-size: 20px; border: none;")
            self.btnEditEmail.setMinimumSize(30, 30)
        email_widget = QWidget()
        email_widget.setStyleSheet("background-color: transparent;")
        email_layout = QHBoxLayout(email_widget)
        email_layout.setContentsMargins(0, 0, 0, 0)
        email_layout.setSpacing(5)
        email_layout.addWidget(label_email_value)
        email_layout.addWidget(self.btnEditEmail)
        email_layout.addStretch()
        layout.addRow(label_email_title, email_widget)
        self.label_email_value = label_email_value

        # Дата рождения
        label_birth_title = QLabel("Дата рождения:")
        label_birth_title.setStyleSheet(title_style)
        label_birth_value = QLabel(birth_date if birth_date else "Не указана")
        label_birth_value.setStyleSheet(value_style)
        layout.addRow(label_birth_title, label_birth_value)
        self.label_birth_date_value = label_birth_value

        # Подключаем сигналы (если ещё не подключены)
        self.connect_signals()
        print("rebuild_info_layout завершён")

    @staticmethod
    def format_phone_display(phone: str) -> str:
        """Форматирует номер телефона в читаемый вид."""
        if len(phone) == 12 and phone.isdigit():
            return f"+{phone[:3]} ({phone[3:5]}) {phone[5:8]}-{phone[8:10]}-{phone[10:12]}"
        return phone

    def on_edit_phone_clicked(self):
        """Открывает диалог редактирования телефона."""
        try:
            dialog = PhoneEditWindow(self.current_phone_raw, parent=None)
            dialog.phone_updated.connect(self.on_phone_updated)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось открыть окно редактирования телефона\n{str(e)}")

    def on_phone_updated(self, new_phone: str):
        """Обновляет отображение телефона после редактирования."""
        self.current_phone_raw = new_phone
        if self.label_phone_value:
            self.label_phone_value.setText(self.format_phone_display(new_phone))
        QMessageBox.information(self.parent, "Успешно", f"Номер телефона обновлён\n+{new_phone}")

    def on_edit_email_clicked(self):
        """Открывает диалог редактирования email."""
        try:
            dialog = EmailEditWindow(self.current_email_raw, parent=None)
            dialog.email_updated.connect(self.on_email_updated)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self.parent, "Ошибка", f"Не удалось открыть окно редактирования email\n{str(e)}")

    def on_email_updated(self, new_email: str):
        """Обновляет отображение email после редактирования."""
        self.current_email_raw = new_email
        if self.label_email_value:
            self.label_email_value.setText(new_email if new_email else "Не указан")
        QMessageBox.information(self.parent, "Успешно", "Email обновлён" if new_email else "Email удалён")