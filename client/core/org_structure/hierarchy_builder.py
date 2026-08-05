from typing import List, Dict, Any


class HierarchyBuilder:
    """Строитель иерархической структуры организаций"""

    def __init__(self, organizations: List[Dict], departments: List[Dict], employees: List[Dict]):
        self.organizations = {org['id']: org for org in organizations}
        self.departments = {dept['id']: dept for dept in departments}
        self.employees = {emp['id']: emp for emp in employees}

    def build(self) -> Dict[int, Dict[str, Any]]:
        """Строит иерархическую структуру организаций"""
        hierarchy = {}
        org_departments = self._group_departments_by_org()

        for org_id, org in self.organizations.items():
            org_struct = {
                'organization': org,
                'departments': [],
                'employees': []
            }

            root_depts = [d for d in org_departments.get(org_id, []) if d.get('parent_id') is None]
            for dept in root_depts:
                dept_tree = self._build_department_tree(dept, org_departments.get(org_id, []))
                org_struct['departments'].append(dept_tree)

            org_struct['employees'] = self._get_organization_employees(org_id)
            hierarchy[org_id] = org_struct

        return hierarchy

    def _group_departments_by_org(self) -> Dict[int, List[Dict]]:
        """Группирует отделы по организациям"""
        org_departments = {}
        for dept in self.departments.values():
            org_id = dept['organization_id']
            if org_id not in org_departments:
                org_departments[org_id] = []
            org_departments[org_id].append(dept)
        return org_departments

    def _build_department_tree(self, dept: Dict, all_depts: List[Dict]) -> Dict:
        """Рекурсивно строит дерево отдела"""
        tree = {
            'department': dept,
            'children': [],
            'employees': self._get_department_employees(dept['id'])
        }

        children = [d for d in all_depts if d.get('parent_id') == dept['id']]
        for child in children:
            child_tree = self._build_department_tree(child, all_depts)
            tree['children'].append(child_tree)

        return tree

    def _get_department_employees(self, department_id: int) -> List[Dict]:
        """Получает сотрудников отдела"""
        dept_employees = []
        for emp in self.employees.values():
            for pos in emp.get('positions', []):
                if pos.get('department_id') == department_id:
                    dept_employees.append(emp)
                    break
        return dept_employees

    def _get_organization_employees(self, organization_id: int) -> List[Dict]:
        """Получает сотрудников организации без отдела"""
        org_employees = []
        for emp in self.employees.values():
            if emp.get('organization_id') == organization_id:
                has_position = any(pos.get('department_id') in self.departments
                                  for pos in emp.get('positions', []))
                if not has_position:
                    org_employees.append(emp)
        return org_employees