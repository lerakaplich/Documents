"""
Модуль со стилями для таблицы документов
"""


class TableStyles:
    """Стили для таблицы документов"""

    @staticmethod
    def get_main_style():
        """Основной стиль виджета"""
        return """
            QWidget {
                background-color: #E7EDF2;
            }
        """

    @staticmethod
    def get_table_style():
        """Стиль таблицы с чередованием строк"""
        return """
            QTableWidget {
                background-color: #E7EDF2;
                alternate-background-color: #F5F7FA;  /* Цвет для нечетных строк */
                border: 1px solid #E0E0E0;
                gridline-color: #D3D3D3;
                selection-background-color: #E3F2FD;
                selection-color: #1B232A;
                outline: 0;
            }

            QTableWidget::item {
                padding: 4px 8px;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
                background-color: transparent;  /* Прозрачный фон, чтобы работал alternate-background-color */
            }

            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #1B232A;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }

            QTableWidget::item:selected:active {
                background-color: #BBDEFB;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }

            QTableWidget::item:selected:!active {
                background-color: #E3F2FD;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }

            QTableWidget::item:hover {
                background-color: #EDF0F5;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }

            QTableWidget::item:selected:hover {
                background-color: #E3F2FD;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }

            /* Вертикальные линии между столбцами */
            QTableWidget::item:first {
                border-left: 1px solid #D3D3D3;
            }

            QTableWidget::item:last {
                border-right: 1px solid #D3D3D3;
            }

            QTableWidget::item:selected:first {
                border-left: 1px solid #D3D3D3;
            }

            QTableWidget::item:selected:last {
                border-right: 1px solid #D3D3D3;
            }

            QHeaderView::section {
                background-color: #1B232A;
                color: white;
                padding: 6px 8px;
                border: none;
                border-right: 1px solid #2A3A4A;
                border-bottom: 2px solid #2A3A4A;
                font-weight: bold;
                font-size: 13px;
            }

            QHeaderView::section:hover {
                background-color: #2A3A4A;
            }

            QHeaderView::section:last {
                border-right: none;
            }

            QHeaderView::section:checked {
                background-color: #2A3A4A;
            }

            /* Вертикальная полоса прокрутки */
            QScrollBar:vertical {
                background: #F5F5F5;
                width: 8px;
                border-radius: 4px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background: #C1C1C1;
                border-radius: 4px;
                min-height: 20px;
            }

            QScrollBar::handle:vertical:hover {
                background: #A0A0A0;
            }

            QScrollBar::handle:vertical:pressed {
                background: #888888;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                width: 0px;
                height: 0px;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }

            /* Горизонтальная полоса прокрутки */
            QScrollBar:horizontal {
                border: none;
                background: #F5F5F5;
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }

            QScrollBar::handle:horizontal {
                background: #C1C1C1;
                border-radius: 4px;
                min-width: 20px;
            }

            QScrollBar::handle:horizontal:hover {
                background: #A0A0A0;
            }

            QScrollBar::handle:horizontal:pressed {
                background: #888888;
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
                height: 0px;
            }

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: none;
            }

            /* Стиль для угла таблицы */
            QTableCornerButton::section {
                background-color: #1B232A;
                border: none;
            }
        """

    @staticmethod
    def get_custom_alternating_style(odd_color="#FFFFFF", even_color="#F5F7FA"):
        """Стиль с пользовательскими цветами для чередования строк"""
        return f"""
            QTableWidget {{
                background-color: {odd_color};
                alternate-background-color: {even_color};
                border: 1px solid #E0E0E0;
                gridline-color: #D3D3D3;
                selection-background-color: #E3F2FD;
                selection-color: #1B232A;
                outline: 0;
            }}

            QTableWidget::item {{
                padding: 4px 8px;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
                background-color: transparent;
            }}

            QTableWidget::item:selected {{
                background-color: #E3F2FD;
                color: #1B232A;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }}

            QTableWidget::item:selected:active {{
                background-color: #BBDEFB;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }}

            QTableWidget::item:selected:!active {{
                background-color: #E3F2FD;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }}

            QTableWidget::item:hover {{
                background-color: #EDF0F5;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }}

            QTableWidget::item:selected:hover {{
                background-color: #E3F2FD;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }}

            QTableWidget::item:first {{
                border-left: 1px solid #D3D3D3;
            }}

            QTableWidget::item:last {{
                border-right: 1px solid #D3D3D3;
            }}

            QTableWidget::item:selected:first {{
                border-left: 1px solid #D3D3D3;
            }}

            QTableWidget::item:selected:last {{
                border-right: 1px solid #D3D3D3;
            }}

            QHeaderView::section {{
                background-color: #1B232A;
                color: white;
                padding: 6px 8px;
                border: none;
                border-right: 1px solid #2A3A4A;
                border-bottom: 2px solid #2A3A4A;
                font-weight: bold;
                font-size: 13px;
            }}

            QHeaderView::section:hover {{
                background-color: #2A3A4A;
            }}

            QHeaderView::section:last {{
                border-right: none;
            }}

            QTableCornerButton::section {{
                background-color: #1B232A;
                border: none;
            }}

            QScrollBar:vertical {{
                background: #F5F5F5;
                width: 8px;
                border-radius: 4px;
                margin: 0px;
                border: none;
            }}

            QScrollBar::handle:vertical {{
                background: #C1C1C1;
                border-radius: 4px;
                min-height: 20px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: #A0A0A0;
            }}

            QScrollBar::handle:vertical:pressed {{
                background: #888888;
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                width: 0px;
                height: 0px;
            }}

            QScrollBar:horizontal {{
                border: none;
                background: #F5F5F5;
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }}

            QScrollBar::handle:horizontal {{
                background: #C1C1C1;
                border-radius: 4px;
                min-width: 20px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background: #A0A0A0;
            }}

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
                height: 0px;
            }}
        """

    @staticmethod
    def get_compact_style():
        """Компактный стиль таблицы с чередованием строк"""
        return """
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                gridline-color: #D3D3D3;
                selection-background-color: #E3F2FD;
                selection-color: #1B232A;
                outline: 0;
            }

            QTableWidget::item {
                padding: 2px 4px;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
                background-color: transparent;
            }

            QTableWidget::item:selected {
                background-color: #E3F2FD;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }

            QTableWidget::item:hover {
                background-color: #F0F0F0;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }

            QTableWidget::item:first {
                border-left: 1px solid #D3D3D3;
            }

            QTableWidget::item:last {
                border-right: 1px solid #D3D3D3;
            }

            QTableWidget::item:selected:first {
                border-left: 1px solid #D3D3D3;
            }

            QTableWidget::item:selected:last {
                border-right: 1px solid #D3D3D3;
            }

            QHeaderView::section {
                background-color: #1B232A;
                color: white;
                padding: 4px 6px;
                border: none;
                border-right: 1px solid #2A3A4A;
                border-bottom: 2px solid #2A3A4A;
                font-weight: bold;
                font-size: 12px;
            }

            QHeaderView::section:last {
                border-right: none;
            }

            QTableCornerButton::section {
                background-color: #1B232A;
                border: none;
            }
        """

    @staticmethod
    def get_menu_style():
        """Стиль контекстного меню"""
        return """
            QMenu { 
                background-color: white; 
                border: 1px solid #c0c0c0; 
                border-radius: 5px; 
                padding: 5px; 
                color: black;
            }
            QMenu::item { 
                padding: 8px 25px 8px 15px; 
                border-radius: 3px; 
                font-size: 14px; 
            }
            QMenu::item:selected { 
                background-color: #e3f2fd; 
            }
            QMenu::separator { 
                height: 1px; 
                background: #e0e0e0; 
                margin: 5px 10px; 
            }
        """

    @staticmethod
    def get_border_style():
        """Стиль с акцентными границами и чередованием строк"""
        return """
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #FFFBF5;
                border: 2px solid #ccab6e;
                gridline-color: #D3D3D3;
                selection-background-color: #E3F2FD;
                selection-color: #1B232A;
                outline: 0;
            }

            QTableWidget::item {
                padding: 4px 8px;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
                background-color: transparent;
            }

            QTableWidget::item:selected {
                background-color: #E3F2FD;
                color: #1B232A;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }

            QTableWidget::item:hover {
                background-color: #F5F0EA;
                border: 1px solid #D3D3D3;
                border-top: none;
                border-bottom: 1px solid #D3D3D3;
            }

            QTableWidget::item:first {
                border-left: 1px solid #D3D3D3;
            }

            QTableWidget::item:last {
                border-right: 1px solid #D3D3D3;
            }

            QTableWidget::item:selected:first {
                border-left: 1px solid #D3D3D3;
            }

            QTableWidget::item:selected:last {
                border-right: 1px solid #D3D3D3;
            }

            QHeaderView::section {
                background-color: #1B232A;
                color: white;
                padding: 6px 8px;
                border: none;
                border-right: 1px solid #2A3A4A;
                border-bottom: 2px solid #ccab6e;
                font-weight: bold;
                font-size: 13px;
            }

            QHeaderView::section:last {
                border-right: none;
            }

            QTableCornerButton::section {
                background-color: #1B232A;
                border: none;
            }
        """