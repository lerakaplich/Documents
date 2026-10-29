from datetime import datetime
from io import BytesIO

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

from server.app.schemas.doc.document_dto import UnansweredDocumentStat

FONT_TITLE = Font(name="Calibri", size=14, bold=True)
FONT_HEADER = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
FONT_REGULAR = Font(name="Calibri", size=11)
FONT_BOLD = Font(name="Calibri", size=11, bold=True)
FONT_ALERT = Font(name="Calibri", size=11, bold=True, color="C00000")

HEADER_FILL = PatternFill(start_color="1B232A", end_color="1B232A", fill_type="solid")
SUBTOTAL_FILL = PatternFill(start_color="F7F9FA", end_color="F7F9FA", fill_type="solid")

THIN_BORDER = Border(
    left=Side(style="thin", color="D3D3D3"),
    right=Side(style="thin", color="D3D3D3"),
    top=Side(style="thin", color="D3D3D3"),
    bottom=Side(style="thin", color="D3D3D3"),
)

ALIGN_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
ALIGN_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")

HEADERS = [
    "№",
    "Рег. номер",
    "Тема / Название",
    "Дедлайн",
    "Ответственные лица",
    "Штраф / Просрочка (руб.)",
]
COL_WIDTHS = {"A": 6, "B": 18, "C": 35, "D": 15, "E": 35, "F": 22}


def _write_title(ws: Worksheet) -> None:
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    ws.append([f"Отчет по документам, требующим ответа (по состоянию на {date_str})"])
    ws.cell(row=1, column=1).font = FONT_TITLE
    ws.row_dimensions[1].height = 30
    ws.append([])  # пустая строка


def _write_header(ws: Worksheet) -> None:
    ws.append(HEADERS)
    ws.row_dimensions[3].height = 25

    for col_idx in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=3, column=col_idx)
        cell.font = FONT_HEADER
        cell.fill = HEADER_FILL
        cell.alignment = ALIGN_CENTER
        cell.border = THIN_BORDER


def _write_data_rows(ws: Worksheet, stats: list[UnansweredDocumentStat]) -> float:
    total_penalty = 0.0

    for idx, item in enumerate(stats, start=1):
        assignees_str = ", ".join(item.assignees) if item.assignees else "Не назначены"
        deadline_str = item.deadline.strftime("%d.%m.%Y") if item.deadline else "Без дедлайна"
        delay = item.delay_info if item.delay_info > 0 else 0

        total_penalty += item.delay_info

        ws.append([idx, item.reg_number, item.title or "", deadline_str, assignees_str, delay])
        _style_data_row(ws, ws.max_row, has_penalty=item.delay_info > 0)

    return total_penalty


def _style_data_row(ws: Worksheet, row_idx: int, has_penalty: bool) -> None:
    ws.row_dimensions[row_idx].height = 22

    for c in range(1, 7):
        cell = ws.cell(row=row_idx, column=c)
        cell.font = FONT_REGULAR
        cell.border = THIN_BORDER
        cell.alignment = _data_cell_alignment(c)

        if c == 6 and has_penalty:
            cell.font = FONT_ALERT


def _data_cell_alignment(column: int) -> Alignment:
    if column in (1, 2, 4, 6):
        return ALIGN_CENTER
    return ALIGN_LEFT


def _write_total_row(ws: Worksheet, total_penalty: float) -> None:
    ws.append(["", "", "", "", "ИТОГО ШТРАФОВ / ПРОСРОЧЕК:", total_penalty])
    total_row_idx = ws.max_row
    ws.merge_cells(
        start_row=total_row_idx, start_column=1,
        end_row=total_row_idx, end_column=4,
    )

    for c in range(1, 7):
        cell = ws.cell(row=total_row_idx, column=c)
        cell.fill = SUBTOTAL_FILL
        cell.border = THIN_BORDER
        cell.font = FONT_BOLD

    ws.cell(row=total_row_idx, column=5).alignment = ALIGN_RIGHT
    total_cell = ws.cell(row=total_row_idx, column=6)
    total_cell.alignment = ALIGN_CENTER
    total_cell.font = FONT_ALERT
    ws.row_dimensions[total_row_idx].height = 25


def _set_column_widths(ws: Worksheet) -> None:
    for col, width in COL_WIDTHS.items():
        ws.column_dimensions[col].width = width


# Основная функция

def generate_unanswered_report_buffer(stats: list[UnansweredDocumentStat]) -> tuple[BytesIO, str]:
    """Чистая функция для генерации Excel-файла по неотвеченным документам."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Требующие ответа"

    _write_title(ws)
    _write_header(ws)
    total_penalty = _write_data_rows(ws, stats)
    _write_total_row(ws, total_penalty)
    _set_column_widths(ws)

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"unanswered_documents_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return stream, filename