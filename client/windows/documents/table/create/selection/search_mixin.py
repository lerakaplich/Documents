"""Поиск в диалоге выбора (серверный и локальный)"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QTreeWidgetItem

from client.core.org_structure.search_hits import MIN_SEARCH_LEN, ORG, parse_search_hits


class SearchMixin:
    """Серверный поиск /org/structure/search и локальный запасной поиск."""

    def _on_search_text_changed(self, text: str):
        if not text.strip() and self._search_mode:
            self._last_query = ""
            self._set_search_busy(False)
            self._populate_tree()

    def _set_search_busy(self, busy: bool):
        if hasattr(self, "searchButton"):
            self.searchButton.setEnabled(not busy)
            self.searchButton.setText("Поиск…" if busy else getattr(self, "_search_button_text", "Поиск"))

    def _on_search(self, *_):
        if not hasattr(self, "searchEdit"):
            return
        query = self.searchEdit.text().strip()
        if not query:
            self._last_query = ""
            if self._search_mode:
                self._populate_tree()
            return

        # без сервера — локальный поиск по переданным спискам
        if not self._lazy:
            self._last_query = query
            self._show_local_search_results(query)
            return

        if len(query) < MIN_SEARCH_LEN:
            QMessageBox.information(self, "Поиск", f"Введите минимум {MIN_SEARCH_LEN} символа для поиска.")
            return

        self._last_query = query
        self._set_search_busy(True)

        from client.services.org_service import get_org_service

        service = get_org_service(self.http_client)
        loader = self.loader
        organizations = set(self.builder.organizations)

        def work():
            print(f"[EmployeeSelectionDialog] Поиск: GET /org/structure/search?q={query!r}")
            raw = service.search_structure(query)
            hits = parse_search_hits(raw)
            print(f"[EmployeeSelectionDialog] Поиск: найдено {len(hits)}")

            # Организации, где найдены отделы/сотрудники: грузим только их (и только ещё не загруженные)
            wanted_orgs = {org for t, _id, org in hits if t != ORG and org is not None}
            need = sorted(o for o in wanted_orgs if o in organizations and not self.builder.is_loaded(o))
            orgs_data = loader.load_all_orgs_data(need) if need else {}
            return hits, orgs_data

        self._tasks.pop(("search", query), None)
        self._start_task(("search", query), work)

    def _show_search_results(self, hits: list[tuple[int, int, int | None]]):
        """Результаты серверного поиска: только найденное и путь к нему."""
        self._set_search_busy(False)
        self._search_mode = True
        self._path_mode = True
        matches = {(t, i) for t, i, _org in hits}
        self._search_matches = matches

        missing = [(t, i) for t, i in sorted(matches) if t != ORG and not self.selection_manager.is_known(t, i)]
        if missing:
            print(f"[EmployeeSelectionDialog] Поиск: найдено, но нет в загруженных данных: {missing[:20]}")

        self.treeWidget.blockSignals(True)
        self._updating = True
        try:
            self.treeWidget.clear()
            items = self.tree_builder.build_match_items(matches)
            self._register_org_items(items)
            if not items:
                empty = QTreeWidgetItem(["Ничего не найдено"])
                empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.treeWidget.addTopLevelItem(empty)
            for item in items:
                self.treeWidget.addTopLevelItem(item)
                self._sync_item_states(item)
        finally:
            self._updating = False
            self.treeWidget.blockSignals(False)

    def _show_local_search_results(self, query: str):
        """Запасной вариант без http_client: поиск по уже имеющимся данным, как раньше."""
        self._search_mode = True
        self._path_mode = False
        self._search_matches = set()
        self.treeWidget.blockSignals(True)
        self._updating = True
        try:
            self.treeWidget.clear()
            self._org_items.clear()
            items = self.tree_builder.build_search_items(query)
            if not items:
                empty = QTreeWidgetItem(["Ничего не найдено"])
                empty.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.treeWidget.addTopLevelItem(empty)
            for item in items:
                self.treeWidget.addTopLevelItem(item)
        finally:
            self._updating = False
            self.treeWidget.blockSignals(False)
