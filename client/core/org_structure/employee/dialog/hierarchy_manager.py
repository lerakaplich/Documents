"""
Модуль управления иерархической структурой организаций и подразделений.

Схема выбора в диалоге сотрудника:

    Организация:      [ комбобокс организаций ]
    Цех/Подразделение:[ комбобокс отделов 1-го уровня ]      <- появляется после выбора организации
    Отдел:            [ комбобокс отделов 2-го уровня ]      <- после выбора отдела 1-го уровня
    ...
                      [x] Является руководителем «...»       <- всегда под последним уровнем

Структура БД:
  * отдел без parent_id — «нулевой» отдел организации, в нём числится руководитель организации;
  * отделы 1-го уровня — прямые потомки этого нулевого отдела;
  * подпись уровня — названия ТИПОВ отделов, которые на этом уровне встречаются
    (если их несколько — «Цех/Подразделение»), в комбобоксе — названия самих отделов.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QMessageBox

from client.core.themes import get_manager


class HierarchyManager:
    """Управляет динамической иерархией организаций и подразделений"""

    # запасные названия уровней, если у отделов не удалось определить тип
    LEVEL_NAMES = {
        0: "Организация",
        1: "Подразделение",
        2: "Отдел",
        3: "Сектор",
        4: "Группа",
        5: "Участок",
    }

    LABEL_WIDTH = 160
    ROW_HEIGHT = 36

    def __init__(self, parent_dialog):
        self.parent = parent_dialog
        self.hierarchy_combos = []  # [(combo_widget, label_widget, level), ...]
        self._row_layouts = []  # QHBoxLayout каждого уровня, параллельно hierarchy_combos
        self.current_hierarchy_path = []  # [org_id, dep1_id, dep2_id, ...] — только выбранные
        self.leader_checkbox = None
        self.leader_checkbox_label = None
        self.leader_checkbox_layout = None

        # Данные справочников
        self.organizations = {}
        self.department_types = {}  # {type_id: name}
        self.departments_tree = {}
        self.all_departments = {}
        self.departments_by_org = {}
        self.root_departments = {}
        self._structure_loaded = set()  # организации, чьё дерево уже подгружено из /org/{id}/structure

    # ==================== ДАННЫЕ ====================

    @staticmethod
    def _key(value):
        """id из API/комбобокса могут прийти как int или как str — приводим к int, если возможно."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    def set_department_types(self, types):
        """types — список {id, name}; нужен, если у отделов приходит только department_type_id."""
        self.department_types = {t.get("id"): t.get("name", "") for t in (types or [])}

    @staticmethod
    def _extract_type_name(dept):
        name = dept.get("department_type_name") or dept.get("type_name")
        if name:
            return name
        dtype = dept.get("department_type")
        if isinstance(dtype, dict):
            return dtype.get("name")
        if isinstance(dtype, str):
            return dtype
        return None

    def build_departments_tree(self, departments):
        """Строит дерево подразделений из плоского списка"""
        self.departments_tree = {}
        self.all_departments = {}
        self._structure_loaded = set()

        for dept in departments:
            dept_id = self._key(dept["id"])
            parent_raw = dept.get("parent_id")
            self.departments_tree[dept_id] = {
                "id": dept_id,
                "name": dept["name"],
                "parent_id": None if parent_raw in (None, "") else self._key(parent_raw),
                "organization_id": self._key(dept.get("organization_id")),
                "type_id": dept.get("department_type_id", dept.get("type_id")),
                "type_name": self._extract_type_name(dept),
                "children": [],
            }
            self.all_departments[dept_id] = dept["name"]

        for dept_id, dept_data in self.departments_tree.items():
            parent_id = dept_data["parent_id"]
            if parent_id and parent_id in self.departments_tree:
                self.departments_tree[parent_id]["children"].append(dept_id)

    def group_departments_by_organization(self):
        """Группирует подразделения по организациям и находит корневые (parent_id is None)"""
        self.departments_by_org = {}
        self.root_departments = {}

        for dept_id, dept_data in self.departments_tree.items():
            org_id = dept_data["organization_id"]
            self.departments_by_org.setdefault(org_id, []).append(dept_id)
            if dept_data["parent_id"] is None:
                self.root_departments.setdefault(org_id, []).append(dept_id)

    def _ensure_structure_loaded(self, organization_id):
        """Подгружает дерево отделов организации из GET /org/{org_id}/structure.

        Общий список отделов приходит без parent_id/organization_id, а структура — это
        вложенное дерево [{id, name, type_name, children: [...]}], где верхний уровень —
        корневые отделы организации (без parent_id).
        """
        org_key = self._key(organization_id)
        if org_key in self._structure_loaded:
            return

        http = getattr(self.parent, "http_client", None)
        if http is None:
            print("[HIER] нет http_client — структуру организации подгрузить нельзя")
            return

        try:
            from client.services.org_service import get_org_service

            nodes = get_org_service(http).get_org_structure(org_key)
        except Exception as e:
            print(f"[HIER] ошибка загрузки структуры организации {org_key}: {e}")
            return

        if not nodes:
            print(f"[HIER] структура организации {org_key} пуста или не получена")
            return

        self._merge_structure(org_key, nodes)
        self._structure_loaded.add(org_key)
        print(f"[HIER] структура организации {org_key} загружена, корневых отделов: {len(nodes)}")

    def _merge_structure(self, org_key, nodes):
        """Вливает вложенное дерево в departments_tree с корректными parent_id/organization_id."""

        def walk(node, parent_id):
            dept_id = self._key(node["id"])
            self.departments_tree[dept_id] = {
                "id": dept_id,
                "name": node.get("name", ""),
                "parent_id": parent_id,
                "organization_id": org_key,
                "type_id": self.departments_tree.get(dept_id, {}).get("type_id"),
                "type_name": node.get("type_name"),
                "children": [],
            }
            self.all_departments[dept_id] = node.get("name", "")
            if parent_id is not None and parent_id in self.departments_tree:
                self.departments_tree[parent_id]["children"].append(dept_id)
            for child in node.get("children") or []:
                walk(child, dept_id)

        for root in nodes:
            walk(root, None)

        self.group_departments_by_organization()

    @staticmethod
    def _is_root_parent(parent_id):
        """parent_id корневого отдела: None / пусто / 0."""
        return parent_id in (None, "", 0, "0")

    def _roots_of(self, organization_id):
        """Корневые отделы организации (без parent_id) — считаем прямо по дереву."""
        org_key = self._key(organization_id)
        return [
            dept_id
            for dept_id, node in self.departments_tree.items()
            if self._key(node.get("organization_id")) == org_key and self._is_root_parent(node.get("parent_id"))
        ]

    def _children_of(self, parent_id):
        """Прямые потомки отдела — считаем прямо по дереву."""
        parent_key = self._key(parent_id)
        return [
            dept_id
            for dept_id, node in self.departments_tree.items()
            if not self._is_root_parent(node.get("parent_id")) and self._key(node.get("parent_id")) == parent_key
        ]

    def get_children_for_parent(self, parent_id, organization_id=None):
        """Дочерние отделы. parent_id=None → корневые отделы организации (руководство организации)."""
        ids = self._roots_of(organization_id) if parent_id is None else self._children_of(parent_id)
        return [(dept_id, self.departments_tree[dept_id]["name"]) for dept_id in ids]

    def get_first_level_departments(self, organization_id):
        """Отделы 1-го уровня: потомки корневого отдела (без parent_id) организации."""
        items = []
        for root_id in self._roots_of(organization_id):
            items.extend(self.get_children_for_parent(root_id))
        return items

    def get_root_department_id(self, organization_id):
        """Отдел без parent_id — туда попадает руководитель организации."""
        roots = self._roots_of(organization_id)
        return roots[0] if roots else None

    def _type_name_of(self, dept_id):
        node = self.departments_tree.get(dept_id)
        if not node:
            return None
        return node.get("type_name") or self.department_types.get(node.get("type_id"))

    def get_level_name(self, level):
        """Запасное название уровня"""
        return self.LEVEL_NAMES.get(level, f"Уровень {level}")

    def get_level_label(self, level, items):
        """Подпись уровня: типы отделов уровня через «/» («Цех/Подразделение»)."""
        if level == 0:
            return self.get_level_name(0)
        names = []
        for dept_id, _name in items:
            type_name = self._type_name_of(dept_id)
            if type_name and type_name not in names:
                names.append(type_name)
        return "/".join(names) if names else self.get_level_name(level)

    def get_item_name(self, item_id):
        """Название организации или отдела по ID"""
        for variant in (item_id, self._key(item_id), str(item_id)):
            if variant in self.organizations:
                return self.organizations[variant]
        key = self._key(item_id)
        if key in self.all_departments:
            return self.all_departments[key]
        return None

    # ==================== ПОСТРОЕНИЕ UI ====================

    def clear_hierarchy_layout(self):
        """Очищает динамические комбобоксы, их лейблы и чекбокс"""
        layout = self.parent.hierarchyLayout
        while layout.count():
            item = layout.takeAt(0)
            if item.layout():
                self._delete_layout(item.layout())
            elif item.widget():
                item.widget().deleteLater()

        self.hierarchy_combos = []
        self._row_layouts = []
        self.current_hierarchy_path = []
        self.leader_checkbox = None
        self.leader_checkbox_label = None
        self.leader_checkbox_layout = None

    @staticmethod
    def _delete_layout(row):
        while row.count():
            child = row.takeAt(0)
            widget = child.widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        row.deleteLater()

    def build_initial_hierarchy(self, filter_external_only=False, employee=None):
        """Строит начальную иерархию: Организация → (отделы по мере выбора) → чекбокс руководителя"""
        self.clear_hierarchy_layout()

        # чекбокс создаём первым — все уровни вставляются перед ним
        self.add_leader_checkbox()

        org_items = list(self.organizations.items())
        if filter_external_only:
            org_items = [(org_id, name) for org_id, name in org_items if org_id != 1]

        if org_items:
            self.add_hierarchy_level(0, org_items)
        else:
            print("[WARNING] Список организаций пуст! Уровень 0 не добавлен")

        # редактирование: выставляем организацию (дальше — как при ручном выборе)
        if employee and employee.get("organization_id") and self.hierarchy_combos:
            combo = self.hierarchy_combos[0][0]
            index = combo.findData(employee.get("organization_id"))
            if index >= 0:
                combo.setCurrentIndex(index)

        self._refresh_path()
        self.update_leader_checkbox()

    def add_leader_checkbox(self):
        """Строка с чекбоксом руководителя — всегда под последним уровнем"""
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)

        label = QLabel("")
        label.setFixedWidth(self.LABEL_WIDTH)
        self.leader_checkbox_label = label

        self.leader_checkbox = QCheckBox("Является руководителем организации")
        self.leader_checkbox.setEnabled(False)
        self.leader_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.leader_checkbox.toggled.connect(self.on_leader_toggled)
        self._apply_leader_checkbox_style()

        row_layout.addWidget(label)
        row_layout.addWidget(self.leader_checkbox, 1)

        self.leader_checkbox_layout = row_layout
        self.parent.hierarchyLayout.addLayout(row_layout)

    def add_hierarchy_level(self, level, items, selected_id=None):
        """Добавляет уровень иерархии (вставляется ПЕРЕД чекбоксом руководителя)

        items — [(id, name), ...]. selected_id выставляется без автоматического
        построения следующего уровня (его строит вызывающий код).
        """
        if level < len(self.hierarchy_combos):
            self.remove_levels_after(level - 1)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)

        label_text = self.get_level_label(level, items)
        label = QLabel(f"{label_text}:")
        label.setFixedWidth(self.LABEL_WIDTH)
        label.setWordWrap(True)
        label.setProperty("base_text", f"{label_text}:")

        combo = QComboBox()
        combo.setMinimumHeight(self.ROW_HEIGHT)
        combo.addItem("Не выбрано", None)
        for item_id, item_name in items:
            combo.addItem(item_name, item_id)
        combo.setProperty("level", level)

        if selected_id:
            index = combo.findData(selected_id)
            if index >= 0:
                combo.setCurrentIndex(index)

        self._style_row(label, combo)
        combo.currentIndexChanged.connect(lambda _i, c=combo: self._handle_change(c))

        row_layout.addWidget(label)
        row_layout.addWidget(combo, 1)

        layout = self.parent.hierarchyLayout
        insert_index = layout.count()
        if self.leader_checkbox_layout is not None:
            leader_idx = layout.indexOf(self.leader_checkbox_layout)
            if leader_idx != -1:
                insert_index = leader_idx
        layout.insertLayout(insert_index, row_layout)

        self.hierarchy_combos.append((combo, label, level))
        self._row_layouts.append(row_layout)

        self._refresh_path()
        self.update_leader_checkbox()
        return combo, label

    def remove_levels_after(self, level):
        """Удаляет все уровни иерархии ПОСЛЕ указанного"""
        while len(self.hierarchy_combos) > level + 1:
            self.hierarchy_combos.pop()
            row = self._row_layouts.pop()
            self.parent.hierarchyLayout.removeItem(row)
            self._delete_layout(row)

    # ==================== ОБРАБОТЧИКИ ====================

    def on_hierarchy_changed(self, index):
        """Совместимость со старым подключением сигнала через sender()."""
        combo = self.parent.sender()
        if combo is not None:
            self._handle_change(combo)

    def _handle_change(self, combo):
        level = next((i for i, (c, _l, _lvl) in enumerate(self.hierarchy_combos) if c is combo), None)
        if level is None:
            return

        selected_id = combo.currentData()
        self.remove_levels_after(level)

        if selected_id:
            if level == 0:
                self._ensure_structure_loaded(selected_id)
                children = self.get_first_level_departments(selected_id)
                roots = self._roots_of(selected_id)
                print(
                    f"[HIER] org={selected_id!r} ({type(selected_id).__name__}) | "
                    f"отделов в дереве: {len(self.departments_tree)} | "
                    f"корневых у организации: {roots} | отделов 1-го уровня: {len(children)}"
                )
                if not roots and self.departments_tree:
                    org_key = self._key(selected_id)
                    mine = [n for n in self.departments_tree.values() if self._key(n.get("organization_id")) == org_key]
                    sample = next(iter(self.departments_tree.values()))
                    print(
                        f"[HIER] отделов этой организации в дереве: {len(mine)}; "
                        f"пример узла: { {k: sample.get(k) for k in ('id', 'organization_id', 'parent_id')} }"
                    )
            else:
                children = self.get_children_for_parent(selected_id)
                print(f"[HIER] отдел={selected_id!r} | дочерних: {len(children)}")
            if children:
                self.add_hierarchy_level(level + 1, children)

        self._refresh_path()
        self.update_leader_checkbox()

    def _refresh_path(self):
        self.current_hierarchy_path = self.get_current_hierarchy_path()

    def update_label_text(self, level, selected_id=None):
        """Совместимость: подпись уровня теперь определяется типами отделов и не зависит от выбора."""
        if level < len(self.hierarchy_combos):
            _combo, label, _lvl = self.hierarchy_combos[level]
            base_text = label.property("base_text")
            if base_text:
                label.setText(base_text)

    def update_leader_checkbox(self):
        """Состояние и текст чекбокса — руководитель последнего выбранного уровня"""
        cb = self.leader_checkbox
        if cb is None:
            return

        path = self.current_hierarchy_path
        if not path:
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
            cb.setEnabled(False)
            cb.setText("Является руководителем организации")
            return

        cb.setEnabled(True)
        name = self.get_item_name(path[-1])
        if len(path) == 1:
            cb.setText(f"Является руководителем организации «{name}»" if name else "Является руководителем организации")
        else:
            cb.setText(f"Является руководителем «{name}»" if name else "Является руководителем")

    def on_leader_toggled(self, checked):
        if checked and not self.current_hierarchy_path:
            self.leader_checkbox.blockSignals(True)
            self.leader_checkbox.setChecked(False)
            self.leader_checkbox.blockSignals(False)
            QMessageBox.warning(
                self.parent,
                "Предупреждение",
                "Для назначения руководителем необходимо выбрать организацию",
            )
            return
        self.update_leader_checkbox()

    # Раньше последний уровень скрывался при отметке руководителя; теперь он всегда виден.
    def hide_last_level(self):
        pass

    def show_last_level(self):
        pass

    # ==================== РЕЗУЛЬТАТ ====================

    def get_current_hierarchy_path(self):
        """Путь [org_id, dep1_id, dep2_id, ...] — до первого невыбранного уровня"""
        path = []
        for combo, _label, _level in self.hierarchy_combos:
            selected_id = combo.currentData()
            if not selected_id:
                break
            path.append(selected_id)
        return path

    def is_leader(self):
        return bool(self.leader_checkbox and self.leader_checkbox.isEnabled() and self.leader_checkbox.isChecked())

    def get_selected_department_id(self):
        """Отдел сотрудника: последний выбранный отдел; руководитель организации — отдел без parent_id."""
        path = self.get_current_hierarchy_path()
        if len(path) >= 2:
            return path[-1]
        if len(path) == 1 and self.is_leader():
            return self.get_root_department_id(path[0])
        return None

    def set_selection(self, org_id, dept_id=None, is_leader=False):
        """Восстанавливает выбор при редактировании: организация → цепочка отделов → чекбокс."""
        if not self.hierarchy_combos:
            return

        self._ensure_structure_loaded(org_id)
        root_ids = set(self._roots_of(org_id))
        chain, seen, cur = [], set(), dept_id
        cur = self._key(cur) if cur else None
        while cur and cur in self.departments_tree and cur not in root_ids and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            parent = self.departments_tree[cur].get("parent_id")
            cur = None if self._is_root_parent(parent) else self._key(parent)
        chain.reverse()

        for level, target in enumerate([org_id, *chain]):
            if level >= len(self.hierarchy_combos):
                break
            combo = self.hierarchy_combos[level][0]
            index = combo.findData(target)
            if index < 0:
                break
            combo.setCurrentIndex(index)  # сигнал построит следующий уровень

        if self.leader_checkbox is not None and self.leader_checkbox.isEnabled():
            self.leader_checkbox.setChecked(bool(is_leader))

    def set_test_data(self):
        """Заполняет тестовые данные для отладки"""
        print("[INFO] Используются тестовые данные")
        self.organizations = {1: "ОАО МАЗ", 2: "ООО Тестовая организация"}
        self.set_department_types(
            [
                {"id": 1, "name": "Управление"},
                {"id": 2, "name": "Отдел"},
                {"id": 3, "name": "Цех"},
                {"id": 4, "name": "Подразделение"},
            ]
        )
        self.build_departments_tree(
            [
                {"id": 1, "name": "Руководство МАЗ", "parent_id": None, "organization_id": 1, "department_type_id": 1},
                {"id": 2, "name": "Цех №1", "parent_id": 1, "organization_id": 1, "department_type_id": 3},
                {"id": 3, "name": "Информационные технологии", "parent_id": 1, "organization_id": 1, "department_type_id": 4},
                {"id": 4, "name": "Отдел разработки", "parent_id": 3, "organization_id": 1, "department_type_id": 2},
                {"id": 5, "name": "Руководство ТО", "parent_id": None, "organization_id": 2, "department_type_id": 1},
                {"id": 6, "name": "Отдел продаж", "parent_id": 5, "organization_id": 2, "department_type_id": 2},
            ]
        )
        self.group_departments_by_organization()

    # ==================== СТИЛИ ====================

    def _label_style(self):
        t = get_manager().current
        return f"color: {t.TEXT_PRIMARY}; font-weight: 500; font-size: 13px; background: transparent;"

    def _combo_style(self):
        from client.core.themes.icon_utils import icon_path

        t = get_manager().current
        arrow = icon_path("down_arrow", t.ICON_COLOR)
        return f"""
            QComboBox {{
                border: 1px solid {t.BORDER_DEFAULT};
                border-radius: 6px;
                padding: 6px;
                padding-right: 30px;
                background-color: {t.BG_INPUT};
                color: {t.TEXT_PRIMARY};
                font-size: 13px;
                min-height: 22px;
            }}
            QComboBox:hover {{
                border-color: {t.ACCENT_PRIMARY};
            }}
            QComboBox:focus {{
                border: 2px solid {t.ACCENT_PRIMARY};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: url({arrow});
                width: 16px;
                height: 16px;
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                border-radius: 6px;
                background-color: {t.BG_CARD};
                color: {t.TEXT_PRIMARY};
                padding: 4px;
                outline: none;
                border: 1px solid {t.ACCENT_PRIMARY};
                selection-background-color: {t.ACCENT_SELECTION_BG};
                selection-color: {t.TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px;
                color: {t.TEXT_PRIMARY};
                border: none;
                outline: none;
            }}
            QComboBox QAbstractItemView::item:hover,
            QComboBox QAbstractItemView::item:selected {{
                background-color: {t.ACCENT_SELECTION_BG};
                color: {t.TEXT_PRIMARY};
            }}
        """

    def _style_row(self, label, combo):
        label.setStyleSheet(self._label_style())
        combo.setStyleSheet(self._combo_style())

    def _apply_leader_checkbox_style(self):
        """Стиль чекбокса руководителя с иконками темы."""
        from client.core.themes.icon_utils import icon_path

        t = get_manager().current
        checked = icon_path("cb_checked", t.ICON_COLOR)
        unchecked = icon_path("cb_unchecked", t.ICON_COLOR)

        self.leader_checkbox.setStyleSheet(f"""
            QCheckBox {{
                spacing: 8px;
                color: {t.TEXT_PRIMARY};
                font-size: 13px;
                background: transparent;
            }}
            QCheckBox:disabled {{
                color: {t.TEXT_DISABLED};
            }}
            QCheckBox::indicator {{
                width: 18px; height: 18px;
                image: url({unchecked});
            }}
            QCheckBox::indicator:checked {{
                image: url({checked});
            }}
        """)

    def apply_theme(self):
        """Перекрасить динамически созданные виджеты (combos, labels, checkbox)."""
        for combo, label, _level in self.hierarchy_combos:
            self._style_row(label, combo)
        if self.leader_checkbox is not None:
            self._apply_leader_checkbox_style()