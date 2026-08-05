"""
Модуль асинхронных операций с сотрудниками
"""

import asyncio
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox


class EmployeeAsyncOperations:
    """Выполняет асинхронные операции с сотрудниками"""

    def __init__(self, parent_dialog, data_manager):
        self.parent = parent_dialog
        self.data_manager = data_manager
        self.profile_manager = parent_dialog.profile_manager

    async def load_data_async(self, filter_external_only=False):
        """Асинхронная загрузка данных справочников"""
        print("[DEBUG] load_data_async() вызван")
        try:
            print("[INFO] Начало загрузки данных...")

            if self.profile_manager:
                await self.profile_manager.initialize()

                orgs = await self.profile_manager.get_all_organizations()
                self.parent.hierarchy_manager.organizations = {org['id']: org['name'] for org in orgs}
                print(f"[INFO] Загружено организаций: {len(self.parent.hierarchy_manager.organizations)}")

                depts = await self.profile_manager.get_all_departments()
                self.parent.hierarchy_manager.build_departments_tree(depts)
                print(f"[INFO] Загружено подразделений: {len(self.parent.hierarchy_manager.departments_tree)}")

                self.parent.hierarchy_manager.group_departments_by_organization()

            self.data_manager._data_loaded = True
            print("[DEBUG] Данные загружены, строим иерархию...")

            self.parent.hierarchy_manager.build_initial_hierarchy(
                filter_external_only=filter_external_only,
                employee=self.data_manager.employee
            )

            if self.data_manager.employee:
                self.data_manager.fill_employee_data()

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки данных: {e}")
            import traceback
            traceback.print_exc()
            self._fill_test_data()

    def _fill_test_data(self):
        """Заполняет тестовые данные для отладки"""
        self.parent.hierarchy_manager.set_test_data()
        self.data_manager._data_loaded = True
        self.parent.hierarchy_manager.build_initial_hierarchy(
            filter_external_only=self.parent.filter_external_only,
            employee=self.data_manager.employee
        )
        if self.data_manager.employee:
            self.data_manager.fill_employee_data()

    async def create_employee(self, data):
        """Асинхронное создание сотрудника"""
        try:
            data['service_number'] = f"EMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            if self.profile_manager:
                employee_id = await self.profile_manager.add_employee(data)
                if employee_id:
                    self.parent.employee_created.emit(employee_id)
                    self.parent.accept()
                else:
                    self.show_error("Не удалось создать сотрудника")
            else:
                print(f"[TEST] Создание сотрудника: {data}")
                self.parent.accept()

        except Exception as e:
            print(f"[ERROR] Ошибка создания сотрудника: {e}")
            self.show_error(f"Ошибка: {str(e)}")

    async def update_employee(self, data):
        """Асинхронное обновление сотрудника"""
        try:
            employee_id = self.data_manager.employee['id']

            if self.profile_manager:
                success = await self.profile_manager.update_employee(employee_id, data)
                if success:
                    self.parent.employee_updated.emit(employee_id)
                    self.parent.accept()
                else:
                    self.show_error("Не удалось обновить данные сотрудника")
            else:
                print(f"[TEST] Обновление сотрудника {employee_id}: {data}")
                self.parent.accept()

        except Exception as e:
            print(f"[ERROR] Ошибка обновления сотрудника: {e}")
            self.show_error(f"Ошибка: {str(e)}")

    def show_error(self, message):
        """Показывает ошибку"""
        QMessageBox.critical(self.parent, "Ошибка", message)

    def start_async_create(self, data):
        """Запускает асинхронное создание сотрудника"""
        if self.profile_manager:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.create_employee(data))
            except RuntimeError:
                asyncio.run(self.create_employee(data))
        else:
            print(f"[TEST] Создание сотрудника: {data}")
            self.parent.accept()

    def start_async_update(self, data):
        """Запускает асинхронное обновление сотрудника"""
        if self.profile_manager:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.update_employee(data))
            except RuntimeError:
                asyncio.run(self.update_employee(data))
        else:
            print(f"[TEST] Обновление сотрудника: {data}")
            self.parent.accept()