"""
Модуль диалогового окна для создания/редактирования организаций с древовидной структурой подразделений
"""
import os
import sys
import re
from PyQt6.QtWidgets import (
    QDialog, QMessageBox, QApplication, QTreeWidgetItem, QInputDialog, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi


class OrganizationDialog(QDialog):
    """Диалог создания/редактирования организации с поддержкой древовидной структуры отделов"""

    # Тестовые данные для замены БД
    TEST_ORGANIZATIONS = [
        {
            'id': 1,
            'unp': '123456789',
            'smdo_code': 'BELAZ',
            'name': 'ОАО "БЕЛАЗ"',
            'phone_number': '+375 1775 2-13-45',
            'address': 'г. Жодино, ул. 40 лет Октября, 4',
            'email': 'info@belaz.by',
            'is_subscriber': True,
            'departments': [
                {
                    'id': 1,
                    'name': 'Канцелярия',
                    'number': 101,
                    'phone_number': '2-10-10',
                    'children': []
                },
                {
                    'id': 2,
                    'name': 'ОИТ',
                    'number': 102,
                    'phone_number': '2-20-20',
                    'children': [
                        {
                            'id': 3,
                            'name': 'Отдел разработки',
                            'number': 201,
                            'phone_number': '2-20-21',
                            'children': []
                        },
                        {
                            'id': 4,
                            'name': 'Отдел тестирования',
                            'number': 202,
                            'phone_number': '2-20-22',
                            'children': []
                        }
                    ]
                },
                {
                    'id': 5,
                    'name': 'Бухгалтерия',
                    'number': 103,
                    'phone_number': '2-30-30',
                    'children': []
                }
            ]
        },
        {
            'id': 2,
            'unp': '987654321',
            'smdo_code': 'SMDO-SERVICE',
            'name': 'ЧТУП "СМДО-Сервис"',
            'phone_number': '+375 29 123-45-67',
            'address': 'г. Минск, ул. Ленина, 10',
            'email': 'info@smdo-service.by',
            'is_subscriber': True,
            'departments': [
                {
                    'id': 6,
                    'name': 'Руководство',
                    'number': 1,
                    'phone_number': '123-45-67',
                    'children': []
                }
            ]
        }
    ]

    def __init__(self, parent=None, org_id=None):
        """
        Инициализация диалога

        Args:
            parent: Родительский виджет
            org_id: ID организации для редактирования (None для создания новой)
        """
        super().__init__(parent)
        self.org_id = org_id
        self.editing_org = None
        # Счетчик для генерации временных ID новых отделов
        self._temp_dept_id_counter = -1
        # Словарь для отслеживания новых отделов (которые еще не сохранены в БД)
        self._new_departments = []
        # Словарь для отслеживания удаленных отделов
        self._deleted_department_ids = []

        self._load_ui()
        self._setup_connections()
        self._load_org_data()

        # Установка заголовка в зависимости от режима
        if org_id:
            self.titleLabel.setText("Редактирование организации")
        else:
            self.titleLabel.setText("Новая организация")

    def _load_ui(self):
        """Загружает UI из .ui файла"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(
            current_dir, '..', '..', '..', 'ui', 'system', 'organizations', 'organization_dialog.ui'
        )
        ui_path = os.path.normpath(ui_path)

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI file not found: {ui_path}")

        loadUi(ui_path, self)

    def _setup_connections(self):
        """Настраивает сигналы и слоты"""
        # Кнопки сохранения/отмены
        self.btnSave.clicked.connect(self._on_save)
        self.btnCancel.clicked.connect(self.reject)

        # Кнопки управления отделами
        self.btnAddRootDepartment.clicked.connect(self._on_add_root_department)
        self.btnAddChildDepartment.clicked.connect(self._on_add_child_department)
        self.btnEditDepartment.clicked.connect(self._on_edit_department)
        self.btnDeleteDepartment.clicked.connect(self._on_delete_department)

        # Двойной клик по отделу для редактирования
        self.treeWidgetDepartments.itemDoubleClicked.connect(self._on_department_double_clicked)

    def _load_org_data(self):
        """Загружает данные организации для редактирования"""
        if not self.org_id:
            return

        # Поиск организации в тестовых данных
        self.editing_org = next(
            (org for org in self.TEST_ORGANIZATIONS if org['id'] == self.org_id),
            None
        )

        if not self.editing_org:
            QMessageBox.warning(self, "Ошибка", f"Организация с ID {self.org_id} не найдена")
            self.reject()
            return

        # Заполняем поля
        self.lineEditUNP.setText(self.editing_org.get('unp', ''))
        self.lineEditSmdoCode.setText(self.editing_org.get('smdo_code', ''))
        self.lineEditName.setText(self.editing_org.get('name', ''))
        self.lineEditPhone.setText(self.editing_org.get('phone_number', ''))
        self.lineEditAddress.setText(self.editing_org.get('address', ''))
        self.lineEditEmail.setText(self.editing_org.get('email', ''))
        self.checkBoxSubscriber.setChecked(self.editing_org.get('is_subscriber', True))

        # Загружаем дерево отделов
        self._populate_department_tree(self.editing_org.get('departments', []))

    def _populate_department_tree(self, departments, parent_item=None):
        """
        Рекурсивно заполняет дерево отделов

        Args:
            departments: Список отделов
            parent_item: Родительский элемент дерева (None для корневых)
        """
        for dept in departments:
            if parent_item is None:
                item = QTreeWidgetItem(self.treeWidgetDepartments)
            else:
                item = QTreeWidgetItem(parent_item)

            item.setText(0, dept['name'])
            item.setText(1, str(dept.get('number', '')))
            item.setText(2, dept.get('phone_number', ''))

            # Сохраняем ID отдела в данных элемента
            item.setData(0, Qt.ItemDataRole.UserRole, dept['id'])
            # Сохраняем полные данные отдела
            item.setData(0, Qt.ItemDataRole.UserRole + 1, dept)

            # Рекурсивно добавляем дочерние отделы
            if 'children' in dept and dept['children']:
                self._populate_department_tree(dept['children'], item)

    def _on_add_root_department(self):
        """Добавляет корневой отдел (верхнего уровня)"""
        dept_data = self._show_department_dialog("Добавить отдел")
        if dept_data:
            # Присваиваем временный ID для нового отдела
            dept_id = self._temp_dept_id_counter
            self._temp_dept_id_counter -= 1
            dept_data['id'] = dept_id
            dept_data['children'] = []

            item = self._add_department_to_tree(dept_data, None)
            self._new_departments.append(dept_data)

            # Раскрываем родительский узел
            self.treeWidgetDepartments.expandItem(item)

    def _on_add_child_department(self):
        """Добавляет дочерний отдел к выбранному"""
        current_item = self.treeWidgetDepartments.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Предупреждение", "Выберите родительский отдел")
            return

        dept_data = self._show_department_dialog("Добавить подотдел")
        if dept_data:
            dept_id = self._temp_dept_id_counter
            self._temp_dept_id_counter -= 1
            dept_data['id'] = dept_id
            dept_data['children'] = []

            item = self._add_department_to_tree(dept_data, current_item)
            self._new_departments.append(dept_data)

            # Раскрываем родительский узел
            self.treeWidgetDepartments.expandItem(current_item)

    def _on_edit_department(self):
        """Редактирует выбранный отдел"""
        current_item = self.treeWidgetDepartments.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Предупреждение", "Выберите отдел для редактирования")
            return

        dept_data = current_item.data(0, Qt.ItemDataRole.UserRole + 1)
        if not dept_data:
            return

        new_data = self._show_department_dialog(
            "Редактировать отдел",
            name=dept_data.get('name', ''),
            number=str(dept_data.get('number', '')),
            phone=dept_data.get('phone_number', '')
        )

        if new_data:
            # Обновляем данные в элементе дерева
            new_data['id'] = dept_data['id']
            new_data['children'] = dept_data.get('children', [])

            current_item.setText(0, new_data['name'])
            current_item.setText(1, str(new_data.get('number', '')))
            current_item.setText(2, new_data.get('phone_number', ''))
            current_item.setData(0, Qt.ItemDataRole.UserRole, new_data['id'])
            current_item.setData(0, Qt.ItemDataRole.UserRole + 1, new_data)

            # Обновляем в списке новых отделов, если это новый отдел
            if dept_data['id'] < 0:
                for i, dept in enumerate(self._new_departments):
                    if dept['id'] == dept_data['id']:
                        self._new_departments[i] = new_data
                        break

    def _on_delete_department(self):
        """Удаляет выбранный отдел"""
        current_item = self.treeWidgetDepartments.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Предупреждение", "Выберите отдел для удаления")
            return

        dept_name = current_item.text(0)
        dept_id = current_item.data(0, Qt.ItemDataRole.UserRole)

        # Подтверждение удаления
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить отдел '{dept_name}'?\n\n"
            "Все дочерние подразделения также будут удалены.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Если это существующий отдел (не новый), добавляем в список удаленных
            if dept_id and dept_id > 0:
                self._deleted_department_ids.append(dept_id)

            # Удаляем из списка новых отделов
            if dept_id and dept_id < 0:
                self._new_departments = [
                    d for d in self._new_departments if d['id'] != dept_id
                ]

            # Удаляем из дерева
            parent = current_item.parent()
            if parent:
                parent.removeChild(current_item)
            else:
                index = self.treeWidgetDepartments.indexOfTopLevelItem(current_item)
                self.treeWidgetDepartments.takeTopLevelItem(index)

    def _on_department_double_clicked(self, item, column):
        """Обработчик двойного клика по отделу"""
        self.treeWidgetDepartments.setCurrentItem(item)
        self._on_edit_department()

    def _add_department_to_tree(self, dept_data, parent_item=None):
        """
        Добавляет отдел в дерево

        Args:
            dept_data: Данные отдела
            parent_item: Родительский элемент (None для корневого)

        Returns:
            QTreeWidgetItem: Созданный элемент
        """
        if parent_item is None:
            item = QTreeWidgetItem(self.treeWidgetDepartments)
        else:
            item = QTreeWidgetItem(parent_item)

        item.setText(0, dept_data['name'])
        item.setText(1, str(dept_data.get('number', '')))
        item.setText(2, dept_data.get('phone_number', ''))
        item.setData(0, Qt.ItemDataRole.UserRole, dept_data['id'])
        item.setData(0, Qt.ItemDataRole.UserRole + 1, dept_data)

        return item

    def _show_department_dialog(self, title, name='', number='', phone=''):
        """
        Показывает диалог для ввода данных отдела

        Args:
            title: Заголовок диалога
            name: Текущее название (для редактирования)
            number: Текущий номер (для редактирования)
            phone: Текущий телефон (для редактирования)

        Returns:
            dict or None: Данные отдела или None при отмене
        """
        # Создаем простой диалог с тремя полями
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText("Название отдела *:")
        dialog.setTextValue(name)
        dialog.setInputMode(QInputDialog.InputMode.TextInput)
        dialog.resize(400, 200)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        dept_name = dialog.textValue().strip()
        if not dept_name:
            QMessageBox.warning(self, "Ошибка", "Название отдела обязательно")
            return None

        # Запрашиваем номер отдела
        number, ok = QInputDialog.getText(
            self, title, "Номер отдела:",
            QLineEdit.EchoMode.Normal, number
        )
        if not ok:
            return None

        # Запрашиваем телефон отдела
        phone, ok = QInputDialog.getText(
            self, title, "Телефон отдела:",
            QLineEdit.EchoMode.Normal, phone
        )
        if not ok:
            return None

        # Парсим номер в целое число, если возможно
        try:
            dept_number = int(number) if number.strip() else None
        except ValueError:
            dept_number = None

        return {
            'name': dept_name,
            'number': dept_number,
            'phone_number': phone.strip() or None
        }

    def _collect_departments_from_tree(self, parent_item=None):
        """
        Рекурсивно собирает структуру отделов из дерева

        Args:
            parent_item: Родительский элемент (None для корневых)

        Returns:
            list: Список отделов
        """
        departments = []

        if parent_item is None:
            # Корневые элементы
            for i in range(self.treeWidgetDepartments.topLevelItemCount()):
                item = self.treeWidgetDepartments.topLevelItem(i)
                dept_data = self._item_to_department(item)
                if dept_data:
                    departments.append(dept_data)
        else:
            # Дочерние элементы
            for i in range(parent_item.childCount()):
                item = parent_item.child(i)
                dept_data = self._item_to_department(item)
                if dept_data:
                    departments.append(dept_data)

        return departments

    def _item_to_department(self, item):
        """
        Преобразует элемент дерева в словарь отдела

        Args:
            item: Элемент дерева

        Returns:
            dict: Данные отдела
        """
        dept_data = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if not dept_data:
            dept_data = {
                'id': item.data(0, Qt.ItemDataRole.UserRole),
                'name': item.text(0),
                'number': int(item.text(1)) if item.text(1).strip() else None,
                'phone_number': item.text(2).strip() or None,
                'children': []
            }

        # Рекурсивно собираем дочерние отделы
        children = self._collect_departments_from_tree(item)
        dept_data['children'] = children

        return dept_data

    def _validate_input(self):
        """Валидирует введенные данные"""
        # Проверка УНП
        unp = self.lineEditUNP.text().strip()
        if not unp:
            QMessageBox.warning(self, "Ошибка валидации", "УНП обязателен для заполнения")
            self.lineEditUNP.setFocus()
            return False

        # Проверка формата УНП (9 цифр)
        if not re.match(r'^\d{9}$', unp):
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "УНП должен содержать ровно 9 цифр"
            )
            self.lineEditUNP.setFocus()
            return False

        # Проверка уникальности УНП
        for org in self.TEST_ORGANIZATIONS:
            if org['unp'] == unp:
                if not self.editing_org or org['id'] != self.editing_org['id']:
                    QMessageBox.warning(
                        self,
                        "Ошибка валидации",
                        f"Организация с УНП '{unp}' уже существует"
                    )
                    self.lineEditUNP.setFocus()
                    return False

        # Проверка наименования
        name = self.lineEditName.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка валидации", "Наименование организации обязательно")
            self.lineEditName.setFocus()
            return False

        # Проверка Email (если указан)
        email = self.lineEditEmail.text().strip()
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            QMessageBox.warning(
                self,
                "Ошибка валидации",
                "Некорректный формат Email"
            )
            self.lineEditEmail.setFocus()
            return False

        return True

    def _on_save(self):
        """Обработчик сохранения организации"""
        if not self._validate_input():
            return

        # Собираем данные организации
        org_data = {
            'unp': self.lineEditUNP.text().strip(),
            'smdo_code': self.lineEditSmdoCode.text().strip() or None,
            'name': self.lineEditName.text().strip(),
            'phone_number': self.lineEditPhone.text().strip() or None,
            'address': self.lineEditAddress.text().strip() or None,
            'email': self.lineEditEmail.text().strip() or None,
            'is_subscriber': self.checkBoxSubscriber.isChecked(),
            'departments': self._collect_departments_from_tree()
        }

        if self.editing_org:
            # Обновление существующей организации
            org_data['id'] = self.editing_org['id']
            for i, org in enumerate(self.TEST_ORGANIZATIONS):
                if org['id'] == self.editing_org['id']:
                    self.TEST_ORGANIZATIONS[i].update(org_data)
                    break
            print(f"[INFO] Организация обновлена: {org_data}")
        else:
            # Создание новой организации
            new_id = max([org['id'] for org in self.TEST_ORGANIZATIONS], default=0) + 1
            org_data['id'] = new_id
            self.TEST_ORGANIZATIONS.append(org_data)
            print(f"[INFO] Создана новая организация: {org_data}")

        # Логируем информацию о новых и удаленных отделах
        if self._new_departments:
            print(f"[INFO] Новые отделы: {len(self._new_departments)}")
        if self._deleted_department_ids:
            print(f"[INFO] Удалены отделы с ID: {self._deleted_department_ids}")

        # Показываем сообщение об успехе
        action = "обновлена" if self.editing_org else "создана"
        QMessageBox.information(
            self,
            "Успешно",
            f"Организация '{org_data['name']}' успешно {action}"
        )

        self.accept()

    def get_org_data(self):
        """Возвращает данные созданной/отредактированной организации"""
        org_data = {
            'unp': self.lineEditUNP.text().strip(),
            'smdo_code': self.lineEditSmdoCode.text().strip() or None,
            'name': self.lineEditName.text().strip(),
            'phone_number': self.lineEditPhone.text().strip() or None,
            'address': self.lineEditAddress.text().strip() or None,
            'email': self.lineEditEmail.text().strip() or None,
            'is_subscriber': self.checkBoxSubscriber.isChecked(),
            'departments': self._collect_departments_from_tree()
        }

        if self.editing_org:
            org_data['id'] = self.editing_org['id']

        return org_data


# ============================================================================
# ТЕСТОВЫЙ ЗАПУСК
# ============================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Тест 1: Создание новой организации
    print("=" * 50)
    print("ТЕСТ 1: Создание новой организации")
    dialog = OrganizationDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("Создана организация:", dialog.get_org_data())

    # Тест 2: Редактирование существующей организации
    print("\n" + "=" * 50)
    print("ТЕСТ 2: Редактирование существующей организации")
    dialog_edit = OrganizationDialog(org_id=1)
    if dialog_edit.exec() == QDialog.DialogCode.Accepted:
        print("Обновлена организация:", dialog_edit.get_org_data())

    # Вывод всех организаций
    print("\n" + "=" * 50)
    print("ВСЕ ОРГАНИЗАЦИИ ПОСЛЕ ИЗМЕНЕНИЙ:")
    for org in OrganizationDialog.TEST_ORGANIZATIONS:
        print(f"  ID: {org['id']}, УНП: {org['unp']}, Название: {org['name']}")
        print(f"  Отделы ({len(org.get('departments', []))}):")

        def print_departments(departments, level=1):
            for dept in departments:
                indent = "    " * level
                print(f"{indent}📁 {dept['name']} (ID: {dept['id']}, Номер: {dept.get('number', '')})")
                if dept.get('children'):
                    print_departments(dept['children'], level + 1)

        print_departments(org.get('departments', []))

    sys.exit(0)