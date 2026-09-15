import asyncio
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox

from client.services.employee_service import EmployeeService
from client.services.org_service import OrgService


class EmployeeAsyncOperations:
    def __init__(self, parent_dialog, data_manager):
        self.parent = parent_dialog
        self.data_manager = data_manager
        self.http_client = parent_dialog.http_client
        if self.http_client is not None:
            self.employee_service = EmployeeService(self.http_client)
            self.org_service = OrgService(self.http_client)
        else:
            self.employee_service = None
            self.org_service = None

    async def load_data_async(self, filter_external_only=False):
        print("[DEBUG] load_data_async() вызван")
        try:
            if not self.http_client:
                self._fill_test_data()
                return

            orgs = self.org_service.get_all_organizations(limit=500) or []
            self.parent.hierarchy_manager.organizations = {
                o['id']: o['name'] for o in orgs if isinstance(o, dict) and o.get('id')
            }
            print(f"[INFO] Загружено организаций: {len(self.parent.hierarchy_manager.organizations)}")

            # отделы по каждой организации, разворачиваем в плоский список
            depts = []
            for org in orgs:
                oid = org.get('id') if isinstance(org, dict) else None
                if not oid:
                    continue
                try:
                    struct = self.org_service.get_org_structure(oid) or []
                except Exception as e:
                    print(f"[WARN] structure org {oid}: {e}")
                    continue
                depts.extend(self._flatten(struct))
            self.parent.hierarchy_manager.build_departments_tree(depts)
            print(f"[INFO] Загружено подразделений: {len(self.parent.hierarchy_manager.departments_tree)}")

            self.parent.hierarchy_manager.group_departments_by_organization()

            self.data_manager._data_loaded = True
            self.parent.hierarchy_manager.build_initial_hierarchy(
                filter_external_only=filter_external_only,
                employee=self.data_manager.employee
            )
            if self.data_manager.employee:
                self.data_manager.fill_employee_data()
        except Exception as e:
            print(f"[ERROR] load_data_async: {e}")
            import traceback; traceback.print_exc()
            self._fill_test_data()

    def _flatten(self, nodes):
        out = []
        if not isinstance(nodes, list):
            return out
        for n in nodes:
            if not isinstance(n, dict):
                continue
            out.append(n)
            out.extend(self._flatten(n.get("children") or n.get("subdepartments") or []))
        return out

    def _fill_test_data(self):
        self.parent.hierarchy_manager.set_test_data()
        self.data_manager._data_loaded = True
        self.parent.hierarchy_manager.build_initial_hierarchy(
            filter_external_only=self.parent.filter_external_only,
            employee=self.data_manager.employee
        )
        if self.data_manager.employee:
            self.data_manager.fill_employee_data()

    async def create_employee(self, data):
        try:
            data['service_number'] = f"EMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            if self.employee_service:
                result = self.employee_service.client.post("/employees/", json=data)
                employee_id = result.get('id') if isinstance(result, dict) else None
                if employee_id:
                    self.parent.employee_created.emit(employee_id)
                    self.parent.accept()
                    return
            print(f"[TEST] Создание: {data}")
            self.parent.accept()
        except Exception as e:
            print(f"[ERROR] create: {e}")
            self.show_error(f"Ошибка: {e}")

    async def update_employee(self, data):
        try:
            employee_id = self.data_manager.employee['id']
            if self.employee_service:
                self.employee_service.client.patch(f"/employees/{employee_id}", json=data)
                self.parent.employee_updated.emit(employee_id)
                self.parent.accept()
                return
            print(f"[TEST] Обновление {employee_id}: {data}")
            self.parent.accept()
        except Exception as e:
            print(f"[ERROR] update: {e}")
            self.show_error(f"Ошибка: {e}")

    def show_error(self, message):
        QMessageBox.critical(self.parent, "Ошибка", message)

    def start_async_create(self, data):
        if self.http_client:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.create_employee(data))
            except RuntimeError:
                asyncio.run(self.create_employee(data))
        else:
            print(f"[TEST] Создание: {data}")
            self.parent.accept()

    def start_async_update(self, data):
        if self.http_client:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.update_employee(data))
            except RuntimeError:
                asyncio.run(self.update_employee(data))
        else:
            print(f"[TEST] Обновление: {data}")
            self.parent.accept()