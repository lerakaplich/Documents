"""
Модуль со стилями для таблицы документов
"""
from client.core.themes import get_manager, get_menu_style as _get_menu_style


class TableStyles:
    """Стили для таблицы документов"""

    @staticmethod
    def _t():
        """Возвращает актуальную тему (не кэшируется на уровне модуля)."""
        return get_manager().current

    @staticmethod
    def get_main_style():
        """Основной стиль виджета"""
        t = TableStyles._t()
        return f"""
            QWidget {{
                background-color: {t.BG_CARD};
            }}
        """

    @staticmethod
    def get_table_style():
        """Стиль таблицы с чередованием строк"""
        t = TableStyles._t()
        return f"""
            QTableWidget {{
                background-color: {t.TABLE_BG};
                alternate-background-color: {t.TABLE_ROW_ALT};
                border: 1px solid {t.BORDER_LIGHT};
                gridline-color: {t.TABLE_GRID};
                selection-background-color: {t.TABLE_SELECTION_BG};
                selection-color: {t.TABLE_SELECTION_TEXT};
                outline: 0;
                icon-size: 22px;
            }}

            QTableWidget::item {{
                padding: 4px 8px;
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
                background-color: transparent;
            }}

            QTableWidget::item:selected {{
                background-color: {t.TABLE_SELECTION_BG};
                color: {t.TABLE_SELECTION_TEXT};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:active {{
                background-color: {t.TABLE_SELECTION_BG_ACTIVE};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:!active {{
                background-color: {t.TABLE_SELECTION_BG};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:hover {{
                background-color: {t.TABLE_ROW_HOVER};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:hover {{
                background-color: {t.TABLE_SELECTION_BG};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:first {{
                border-left: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:last {{
                border-right: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:first {{
                border-left: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:last {{
                border-right: 1px solid {t.TABLE_GRID};
            }}

            QHeaderView::section {{
                background-color: {t.TABLE_HEADER_BG};
                color: {t.TABLE_HEADER_TEXT};
                padding: 6px 8px;
                border: none;
                border-right: 1px solid {t.TABLE_HEADER_BORDER};
                border-bottom: 2px solid {t.TABLE_HEADER_BORDER};
                font-weight: bold;
                font-size: 13px;
            }}

            QHeaderView::section:hover {{
                background-color: {t.TABLE_HEADER_HOVER_BG};
            }}

            QHeaderView::section:last {{
                border-right: none;
            }}

            QHeaderView::section:checked {{
                background-color: {t.TABLE_HEADER_HOVER_BG};
            }}

            QScrollBar:vertical {{
                background: {t.SCROLLBAR_BG};
                width: 8px;
                border-radius: 4px;
                margin: 0px;
                border: none;
            }}

            QScrollBar::handle:vertical {{
                background: {t.SCROLLBAR_HANDLE};
                border-radius: 4px;
                min-height: 20px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {t.SCROLLBAR_HANDLE_HOVER};
            }}

            QScrollBar::handle:vertical:pressed {{
                background: {t.SCROLLBAR_HANDLE_PRESSED};
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                width: 0px;
                height: 0px;
            }}

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QScrollBar:horizontal {{
                border: none;
                background: {t.SCROLLBAR_BG};
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }}

            QScrollBar::handle:horizontal {{
                background: {t.SCROLLBAR_HANDLE};
                border-radius: 4px;
                min-width: 20px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background: {t.SCROLLBAR_HANDLE_HOVER};
            }}

            QScrollBar::handle:horizontal:pressed {{
                background: {t.SCROLLBAR_HANDLE_PRESSED};
            }}

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
                width: 0px;
                height: 0px;
            }}

            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: none;
            }}

            QTableCornerButton::section {{
                background-color: {t.TABLE_HEADER_BG};
                border: none;
            }}
        """

    @staticmethod
    def get_custom_alternating_style(odd_color=None, even_color=None):
        """Стиль с пользовательскими цветами для чередования строк"""
        t = TableStyles._t()
        odd_color = odd_color or t.TABLE_BG
        even_color = even_color or t.TABLE_ROW_ALT
        return f"""
            QTableWidget {{
                background-color: {odd_color};
                alternate-background-color: {even_color};
                border: 1px solid {t.BORDER_LIGHT};
                gridline-color: {t.TABLE_GRID};
                selection-background-color: {t.TABLE_SELECTION_BG};
                selection-color: {t.TABLE_SELECTION_TEXT};
                outline: 0;
            }}

            QTableWidget::item {{
                padding: 4px 8px;
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
                background-color: transparent;
            }}

            QTableWidget::item:selected {{
                background-color: {t.TABLE_SELECTION_BG};
                color: {t.TABLE_SELECTION_TEXT};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:active {{
                background-color: {t.TABLE_SELECTION_BG_ACTIVE};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:!active {{
                background-color: {t.TABLE_SELECTION_BG};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:hover {{
                background-color: {t.TABLE_ROW_HOVER};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:hover {{
                background-color: {t.TABLE_SELECTION_BG};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:first {{
                border-left: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:last {{
                border-right: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:first {{
                border-left: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:last {{
                border-right: 1px solid {t.TABLE_GRID};
            }}

            QHeaderView::section {{
                background-color: {t.TABLE_HEADER_BG};
                color: {t.TABLE_HEADER_TEXT};
                padding: 6px 8px;
                border: none;
                border-right: 1px solid {t.TABLE_HEADER_BORDER};
                border-bottom: 2px solid {t.TABLE_HEADER_BORDER};
                font-weight: bold;
                font-size: 13px;
            }}

            QHeaderView::section:hover {{
                background-color: {t.TABLE_HEADER_HOVER_BG};
            }}

            QHeaderView::section:last {{
                border-right: none;
            }}

            QTableCornerButton::section {{
                background-color: {t.TABLE_HEADER_BG};
                border: none;
            }}

            QScrollBar:vertical {{
                background: {t.SCROLLBAR_BG};
                width: 8px;
                border-radius: 4px;
                margin: 0px;
                border: none;
            }}

            QScrollBar::handle:vertical {{
                background: {t.SCROLLBAR_HANDLE};
                border-radius: 4px;
                min-height: 20px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {t.SCROLLBAR_HANDLE_HOVER};
            }}

            QScrollBar::handle:vertical:pressed {{
                background: {t.SCROLLBAR_HANDLE_PRESSED};
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
                background: {t.SCROLLBAR_BG};
                height: 8px;
                margin: 0px;
                border-radius: 4px;
            }}

            QScrollBar::handle:horizontal {{
                background: {t.SCROLLBAR_HANDLE};
                border-radius: 4px;
                min-width: 20px;
            }}

            QScrollBar::handle:horizontal:hover {{
                background: {t.SCROLLBAR_HANDLE_HOVER};
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
        t = TableStyles._t()
        return f"""
            QTableWidget {{
                background-color: {t.TABLE_BG};
                alternate-background-color: {t.BG_SURFACE_HEADER};
                border: 1px solid {t.BORDER_LIGHT};
                gridline-color: {t.TABLE_GRID};
                selection-background-color: {t.TABLE_SELECTION_BG};
                selection-color: {t.TABLE_SELECTION_TEXT};
                outline: 0;
            }}

            QTableWidget::item {{
                padding: 2px 4px;
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
                background-color: transparent;
            }}

            QTableWidget::item:selected {{
                background-color: {t.TABLE_SELECTION_BG};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:hover {{
                background-color: {t.BG_HOVER_LIGHT};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:first {{
                border-left: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:last {{
                border-right: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:first {{
                border-left: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:last {{
                border-right: 1px solid {t.TABLE_GRID};
            }}

            QHeaderView::section {{
                background-color: {t.TABLE_HEADER_BG};
                color: {t.TABLE_HEADER_TEXT};
                padding: 4px 6px;
                border: none;
                border-right: 1px solid {t.TABLE_HEADER_BORDER};
                border-bottom: 2px solid {t.TABLE_HEADER_BORDER};
                font-weight: bold;
                font-size: 12px;
            }}

            QHeaderView::section:last {{
                border-right: none;
            }}

            QTableCornerButton::section {{
                background-color: {t.TABLE_HEADER_BG};
                border: none;
            }}
        """

    @staticmethod
    def get_menu_style():
        """Стиль контекстного меню (делегируем в общий хелпер)."""
        return _get_menu_style()

    @staticmethod
    def get_border_style():
        """Стиль с акцентными границами и чередованием строк"""
        t = TableStyles._t()
        return f"""
            QTableWidget {{
                background-color: {t.TABLE_BG};
                alternate-background-color: {t.TABLE_ROW_ALT_ACCENT};
                border: 2px solid {t.ACCENT_PRIMARY};
                gridline-color: {t.TABLE_GRID};
                selection-background-color: {t.TABLE_SELECTION_BG};
                selection-color: {t.TABLE_SELECTION_TEXT};
                outline: 0;
            }}

            QTableWidget::item {{
                padding: 4px 8px;
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
                background-color: transparent;
            }}

            QTableWidget::item:selected {{
                background-color: {t.TABLE_SELECTION_BG};
                color: {t.TABLE_SELECTION_TEXT};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:hover {{
                background-color: {t.TABLE_ROW_HOVER_ACCENT};
                border: 1px solid {t.TABLE_GRID};
                border-top: none;
                border-bottom: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:first {{
                border-left: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:last {{
                border-right: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:first {{
                border-left: 1px solid {t.TABLE_GRID};
            }}

            QTableWidget::item:selected:last {{
                border-right: 1px solid {t.TABLE_GRID};
            }}

            QHeaderView::section {{
                background-color: {t.TABLE_HEADER_BG};
                color: {t.TABLE_HEADER_TEXT};
                padding: 6px 8px;
                border: none;
                border-right: 1px solid {t.TABLE_HEADER_BORDER};
                border-bottom: 2px solid {t.ACCENT_PRIMARY};
                font-weight: bold;
                font-size: 13px;
            }}

            QHeaderView::section:last {{
                border-right: none;
            }}

            QTableCornerButton::section {{
                background-color: {t.TABLE_HEADER_BG};
                border: none;
            }}
        """