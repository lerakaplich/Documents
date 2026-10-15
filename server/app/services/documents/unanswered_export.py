import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from io import BytesIO
from datetime import datetime

from server.app.schemas.doc.document_dto import UnansweredDocumentStat


def generate_unanswered_report_buffer(stats: list[UnansweredDocumentStat]) -> tuple[BytesIO, str]:
    """Чистая функция для генерации Excel-файла по неотвеченным документам."""

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Требующие ответа"

    # Стили отчета
    font_title = Font(name="Calibri", size=14, bold=True)
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_regular = Font(name="Calibri", size=11)
    font_bold = Font(name="Calibri", size=11, bold=True)
    font_alert = Font(name="Calibri", size=11, bold=True, color="C00000")

    header_fill = PatternFill(start_color="1B232A", end_color="1B232A", fill_type="solid")
    subtotal_fill = PatternFill(start_color="F7F9FA", end_color="F7F9FA", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='D3D3D3'),
        right=Side(style='thin', color='D3D3D3'),
        top=Side(style='thin', color='D3D3D3'),
        bottom=Side(style='thin', color='D3D3D3')
    )

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # 1. Заголовок
    date_str = datetime.now().strftime('%d.%m.%Y %H:%M')
    ws.append([f"Отчет по документам, требующим ответа (по состоянию на {date_str})"])
    ws.cell(row=1, column=1).font = font_title
    ws.row_dimensions[1].height = 30
    ws.append([])

    # 2. Шапка таблицы
    headers = ["№", "Рег. номер", "Тема / Название", "Дедлайн", "Ответственные лица", "Штраф / Просрочка (руб.)"]
    ws.append(headers)
    ws.row_dimensions[3].height = 25

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=col_idx)
        cell.font = font_header
        cell.fill = header_fill
        cell.alignment = align_center
        cell.border = thin_border

    # 3. Данные
    total_penalty = 0.0
    row_idx = 4

    for idx, item in enumerate(stats, start=1):
        assignees_str = ", ".join(item.assignees) if item.assignees else "Не назначены"
        deadline_str = item.deadline.strftime('%d.%m.%Y') if item.deadline else "Без дедлайна"

        total_penalty += item.delay_info

        ws.append([
            idx,
            item.reg_number,
            item.title or "",
            deadline_str,
            assignees_str,
            item.delay_info if item.delay_info > 0 else 0
        ])

        ws.row_dimensions[row_idx].height = 22

        for c in range(1, 7):
            cell = ws.cell(row=row_idx, column=c)
            cell.font = font_regular
            cell.border = thin_border

            if c in [1, 2, 4]:
                cell.alignment = align_center
            elif c == 6:
                cell.alignment = align_center
                if item.delay_info > 0:
                    cell.font = font_alert
            else:
                cell.alignment = align_left

        row_idx += 1

    # 4. Итоговая строка
    ws.append(["", "", "", "", "ИТОГО ШТРАФОВ / ПРОСРОЧЕК:", total_penalty])
    total_row_idx = ws.max_row
    ws.merge_cells(start_row=total_row_idx, start_column=1, end_row=total_row_idx, end_column=4)

    for c in range(1, 7):
        cell = ws.cell(row=total_row_idx, column=c)
        cell.fill = subtotal_fill
        cell.border = thin_border
        cell.font = font_bold

    ws.cell(row=total_row_idx, column=5).alignment = Alignment(horizontal="right", vertical="center")
    ws.cell(row=total_row_idx, column=6).alignment = align_center
    ws.cell(row=total_row_idx, column=6).font = font_alert
    ws.row_dimensions[total_row_idx].height = 25

    # 5. Ширина колонок
    col_widths = {'A': 6, 'B': 18, 'C': 35, 'D': 15, 'E': 35, 'F': 22}
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width

    # 6. Сохранение в поток
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"unanswered_documents_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return stream, filename