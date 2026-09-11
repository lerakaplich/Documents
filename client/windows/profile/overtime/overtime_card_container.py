from PyQt6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QSizePolicy, QSpacerItem
from PyQt6.QtCore import Qt

from client.windows.profile.overtime.overtime_card import OvertimeCard


class OvertimeCardContainer:
    """Управление контейнерами с карточками переработок."""

    def __init__(self, parent=None):
        self.parent = parent
        self.myOvertimeContainer = None
        self.allOvertimeContainer = None

    def create_card_container(self):
        """Создаёт QWidget с QGridLayout для размещения карточек."""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)  # ← добавить

        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        grid_layout.setColumnMinimumWidth(0, 450)
        grid_layout.setColumnMinimumWidth(1, 450)

        main_layout.addLayout(grid_layout)

        container.grid_layout = grid_layout
        container.main_layout = main_layout
        container.cards = []
        return container

    def setup_card_containers(self):
        """Создаёт контейнеры для карточек вместо таблиц."""
        if hasattr(self.parent, 'myOvertimeTable'):
            self.parent.myOvertimeTable.deleteLater()
            self.parent.myOvertimeTable = None
        if hasattr(self.parent, 'allOvertimeTable'):
            self.parent.allOvertimeTable.deleteLater()
            self.parent.allOvertimeTable = None

        self.myOvertimeContainer = self.create_card_container()
        self.allOvertimeContainer = self.create_card_container()

        self.replace_widget_in_tab('tabMyOvertime', self.myOvertimeContainer)
        self.replace_widget_in_tab('tabAllOvertime', self.allOvertimeContainer)

    def replace_widget_in_tab(self, tab_name, new_widget):
        """Заменяет старую таблицу на новый контейнер внутри вкладки."""
        tab = getattr(self.parent, tab_name, None)
        if not tab:
            return
        layout = tab.layout()
        if not layout:
            return
        old_table_name = "myOvertimeTable" if tab_name == "tabMyOvertime" else "allOvertimeTable"
        replaced = False
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget()
            if widget and widget.objectName() == old_table_name:
                layout.replaceWidget(widget, new_widget)
                widget.deleteLater()
                replaced = True
                break

        # Если заменили — добавляем растяжку в конец, чтобы контейнер не растягивался
        if replaced and layout.count() > 0:
            last_item = layout.itemAt(layout.count() - 1)
            if last_item is not None and last_item.spacerItem() is None:
                layout.addStretch()

    def populate_card_container(self, container, data_list, edit_callback, delete_callback):
        """Заполняет контейнер карточками."""
        try:
            if not container:
                print("Контейнер не существует, пропускаем обновление")
                return

            if not hasattr(container, 'grid_layout'):
                print(f"У контейнера нет grid_layout, создаем...")
                grid_layout = QGridLayout()
                grid_layout.setSpacing(15)
                grid_layout.setContentsMargins(10, 10, 10, 10)
                grid_layout.setColumnMinimumWidth(0, 450)
                grid_layout.setColumnMinimumWidth(1, 450)
                container.grid_layout = grid_layout

                if not hasattr(container, 'main_layout'):
                    main_layout = QVBoxLayout(container)
                    main_layout.setSpacing(0)
                    main_layout.setContentsMargins(0, 0, 0, 0)
                    main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                    container.main_layout = main_layout

                container.main_layout.insertLayout(0, grid_layout)

            grid_layout = container.grid_layout

            # Очищаем
            while grid_layout.count():
                item = grid_layout.takeAt(0)
                if item and item.widget():
                    widget = item.widget()
                    widget.deleteLater()

            if not hasattr(container, 'cards'):
                container.cards = []
            else:
                container.cards.clear()

            # Добавляем карточки
            for i, data in enumerate(data_list):
                real_id = data.get('id')
                if real_id is None:
                    print(f"⚠️ Пропущена запись без id: {data}")
                    continue

                card = OvertimeCard(real_id, data)
                card.edit_clicked.connect(lambda checked, oid=real_id: edit_callback(oid))
                card.delete_clicked.connect(lambda checked, oid=real_id: delete_callback(oid))
                card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

                row = i // 2
                col = i % 2
                grid_layout.addWidget(card, row, col, alignment=Qt.AlignmentFlag.AlignTop)
                container.cards.append(card)
            # Пересчитываем размер контейнера после перерисовки
            container.updateGeometry()
            container.adjustSize()
            if hasattr(container, 'main_layout'):
                container.main_layout.activate()
                container.main_layout.update()

            # После пересчёта контейнера — попросить родителя обновить высоту вкладки
            p = self.parent
            if p and hasattr(p, '_resize_tab_widget'):
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, p._resize_tab_widget)


        except Exception as e:
            print(f"Ошибка в populate_card_container: {e}")
            import traceback
            traceback.print_exc()

    def update_total_hours(self, label, data_list):
        """Обновляет надпись с итоговым количеством часов."""
        total = sum(item.get('duration', 0) for item in data_list)
        if label:
            label.setText(f"Итого часов: {total:.1f}")