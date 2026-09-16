# client/windows/system/departments/lazy/department_lazy_loader.py
from client.windows.system.departments.api_task import ApiTask, TaskKeeper
from client.windows.system.departments.builders.department_node_builder import build_child_node
from client.windows.system.departments.builders.employee_group_builder import build_employee_group


class DepartmentLazyLoader:
    """Управляет раскрытием узлов и фоновыми подгрузками."""

    def __init__(self, page, loader):
        self.page = page                # DepartmentPage (для build_employee_card)
        self.loader = loader            # DepartmentDataLoader
        self.tasks = TaskKeeper()

    def on_expand_requested(self, node):
        node_id = node.department_data.get('id')
        if node_id is None:
            node.set_children_nodes([])
            return

        if node_id in self.loader.cache.children_nodes:
            node.set_children_nodes(self.loader.cache.children_nodes[node_id])
            return

        if node.is_root:
            self._load_organization(node)
        else:
            self._load_department(node)

    def _on_org_loaded(self, node, org_id, org_name, bundle):
        structure, employees = bundle
        self.loader.apply_org_bundle(structure, employees)

        # ─── Карточка организации ───
        if node.is_root and not getattr(node, '_org_card_added', False):
            org_raw = node.department_data.get('_raw', {})
            if org_raw:
                from PyQt6.QtWidgets import QSizePolicy
                from client.windows.system.organizations.organization_card import OrganizationCard

                phone = org_raw.get('phone_number') or org_raw.get('phone') or ''

                org_card = OrganizationCard({
                    'id': org_raw.get('id'),
                    'name': org_raw.get('name', ''),
                    'unp': org_raw.get('unp', ''),
                    'address': org_raw.get('address', ''),
                    'phone': str(phone) if phone else '',
                    'email': org_raw.get('email', ''),
                    'director': org_raw.get('director', ''),
                })
                org_card.setSizePolicy(QSizePolicy.Policy.Expanding,
                                       QSizePolicy.Policy.Fixed)

                # редактирование / удаление организации (см. патч 3)
                org_card.edit_clicked.connect(self.page._on_org_card_edit)
                org_card.delete_clicked.connect(self.page._on_org_card_delete)

                node.add_content_widget(org_card)  # вставит в самое начало content
                node._org_card_added = True

        # ─── Дочерние отделы (как было) ───
        children = [
            build_child_node(d, org_name=org_name, page=self.page)
            for d in structure
        ]
        self.loader.cache.children_nodes[org_id] = children
        node.set_children_nodes(children)



    # ─── Организация: фоновый запрос ───

    def _load_organization(self, node):
        org_id = node.department_data['id']
        org_name = node.department_data.get('name', '')

        task = ApiTask(self.loader.fetch_org_bundle, org_id)
        task.signals.done.connect(
            lambda bundle: self._on_org_loaded(node, org_id, org_name, bundle)
        )
        task.signals.error.connect(node.set_load_error)
        self.tasks.submit(task)


    # ─── Отдел: только из кэша, мгновенно ───

    def _load_department(self, node):
        dept_id = node.department_data['id']
        org_name = node.department_data.get('organization', '')

        # Сотрудники
        employees = self.loader.employees_for_department(dept_id)
        print(f"[DEBUG] Раскрываем отдел {dept_id} "
              f"({node.department_data.get('name')}): сотрудников={len(employees)}")

        if employees:
            group = build_employee_group(f"Сотрудники ({len(employees)})")
            for emp in employees:
                group.add_card(self.page._create_employee_card(emp))
            node.add_content_widget(group)

        # Дочерние отделы
        children_data = self.loader.children_data_for_department(dept_id)
        children = [
            build_child_node(cd, org_name=org_name, page=self.page)
            for cd in children_data
        ]
        self.loader.cache.children_nodes[dept_id] = children
        node.set_children_nodes(children)