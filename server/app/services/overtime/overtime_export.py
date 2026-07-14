import os
from io import BytesIO
from datetime import date, datetime
from typing import Optional, List, Dict
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from sqlalchemy import select

from server.app.database.employee_models import Department, Overtime, Employee


# Твои импорты моделей и зависимостей СЭД
# from server.app.database.employee_models import Overtime, Employee, Department

class OvertimeExportService:
    def __init__(self, db_session):
        self.db = db_session

    async def get_department_name(self, dept_id: int) -> str:
        """Получить название департамента по ID"""
        stmt = select(Department.name).where(Department.id == dept_id)
        result = await self.db.execute(stmt)
        name = result.scalar_one_or_none()
        return name or f"Отдел ID {dept_id}"

    async def get_department_overtimes(
            self,
            dept_id: int,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> List[Dict]:
        """Получить все переработки сотрудников отдела за период"""
        stmt = (
            select(
                Overtime,
                Employee.last_name,
                Employee.first_name,
                Employee.patronymic,
                Employee.positions
            )
            .join(Employee, Overtime.employee_id == Employee.id)
            .where(Employee.dept_id == dept_id)
        )

        if start_date:
            stmt = stmt.where(Overtime.overtime_date >= start_date)
        if end_date:
            stmt = stmt.where(Overtime.overtime_date <= end_date)

        # Сортируем по ФИО, а затем по дате переработки
        stmt = stmt.order_by(Employee.last_name, Employee.first_name, Overtime.overtime_date)

        result = await self.db.execute(stmt)

        notes = []
        for row in result.all():
            ot, last_name, first_name, middle_name, position = row
            fio = f"{last_name or ''} {first_name or ''} {middle_name or ''}".strip()

            notes.append({
                "fio": fio if fio else f"Сотрудник ID: {ot.employee_id}",
                "position": position or "Не указана",
                "overtime_date": ot.overtime_date,
                "overtime_start": ot.time_start,
                "overtime_end": ot.time_end,
                "duration_hours": float(ot.duration),
                "note_text": ot.note_text or ""
            })
        return notes

    def format_hours(self, decimal_hours: float) -> str:
        """Преобразование десятичных часов в формат ЧЧ:ММ (как в Desktop-приложении)"""
        hours = int(decimal_hours)
        minutes = int(round((decimal_hours - hours) * 60))
        # Корректировка округления минут до 60
        if minutes == 60:
            hours += 1
            minutes = 0
        return f"{hours}:{minutes:02d}"

    async def generate_department_excel_report(
            self,
            dept_id: int,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None
    ) -> tuple[BytesIO, str]:
        """Генерация Excel-файла в буфер памяти"""

        # 1. Получаем данные
        notes = await self.get_department_overtimes(dept_id, start_date, end_date)
        dept_name = await self.get_department_name(dept_id)

        # 2. Создаем Excel книгу
        wb = Workbook()
        ws = wb.active
        ws.title = "Сводный отчет"

        # Стилизация шрифтов и рамок
        font_title = Font(name="Calibri", size=14, bold=True)
        font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        font_regular = Font(name="Calibri", size=11)
        font_bold = Font(name="Calibri", size=11, bold=True)

        # Красивая шапка (темно-синий цвет, как в СЭД)
        header_fill = PatternFill(start_color="1B232A", end_color="1B232A", fill_type="solid")
        subtotal_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

        thin_border = Border(
            left=Side(style='thin', color='D3D3D3'),
            right=Side(style='thin', color='D3D3D3'),
            top=Side(style='thin', color='D3D3D3'),
            bottom=Side(style='thin', color='D3D3D3')
        )

        # Записываем название отчета
        period_str = f"за период с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}" if start_date and end_date else "за всё время"
        ws.append([f"Сводный отчет по переработкам: {dept_name} ({period_str})"])
        ws.cell(row=1, column=1).font = font_title
        ws.row_dimensions[1].height = 30
        ws.append([])  # Пустая строка

        # Заголовки таблицы
        headers = [
            "ФИО",
            "Должность",
            "Дата переработки",
            "Время начала",
            "Время окончания",
            "Длительность (часы)",
            "Описание переработки"
        ]
        ws.append(headers)

        # Стилизуем строку заголовков
        header_row_idx = 3
        ws.row_dimensions[header_row_idx].height = 25
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=header_row_idx, column=col_idx)
            cell.font = font_header
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        # 3. Группируем записи по сотрудникам для расчета промежуточных итогов
        employee_hours = {}
        employee_notes = {}

        for note in notes:
            fio = note["fio"]
            if fio not in employee_hours:
                employee_hours[fio] = 0.0
                employee_notes[fio] = []

            employee_hours[fio] += note["duration_hours"]
            employee_notes[fio].append(note)

        # 4. Заполняем таблицу данными
        sorted_employees = sorted(employee_hours.keys())

        for employee in sorted_employees:
            notes_list = employee_notes[employee]

            for i, note_data in enumerate(notes_list):
                date_str = note_data['overtime_date'].strftime('%d.%m.%Y') if note_data['overtime_date'] else ''
                start_str = note_data['overtime_start'].strftime('%H:%M') if note_data['overtime_start'] else ''
                end_str = note_data['overtime_end'].strftime('%H:%M') if note_data['overtime_end'] else ''
                hours_str = self.format_hours(note_data['duration_hours'])

                row_values = [
                    note_data['fio'],
                    note_data['position'],
                    date_str,
                    start_str,
                    end_str,
                    hours_str,
                    note_data['note_text']
                ]
                ws.append(row_values)

                # Стилизуем добавленную строку
                current_row = ws.max_row
                ws.row_dimensions[current_row].height = 20
                for col_idx in range(1, len(row_values) + 1):
                    cell = ws.cell(row=current_row, column=col_idx)
                    cell.font = font_regular
                    cell.border = thin_border
                    if col_idx in [3, 4, 5, 6]:
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        cell.alignment = Alignment(horizontal="left", vertical="center")

                # Добавляем строку «ИТОГО» для каждого сотрудника
                if i == len(notes_list) - 1:
                    total_hours_emp = self.format_hours(employee_hours[employee])

                    # Создаем строку с пустыми ячейками и итогом
                    ws.append(["", "", "", "", "", f"ИТОГО: {total_hours_emp}", ""])
                    subtotal_row = ws.max_row
                    ws.row_dimensions[subtotal_row].height = 22

                    # Стилизуем ячейку ИТОГО
                    for col_idx in range(1, len(headers) + 1):
                        cell = ws.cell(row=subtotal_row, column=col_idx)
                        cell.fill = subtotal_fill
                        cell.border = thin_border

                    cell_total = ws.cell(row=subtotal_row, column=6)
                    cell_total.font = font_bold
                    cell_total.alignment = Alignment(horizontal="center", vertical="center")

        # 5. Добавляем общий итог в самый конец таблицы
        total_hours_all = sum(employee_hours.values())
        ws.append([])  # Пустая строка-разделитель

        total_row_idx = ws.max_row + 1
        ws.append(["", "", "", "", "", f"ОБЩИЙ ИТОГ: {self.format_hours(total_hours_all)}", ""])
        ws.row_dimensions[total_row_idx].height = 25

        # Стилизуем общий итог ярким цветом
        cell_total_all = ws.cell(row=total_row_idx, column=6)
        cell_total_all.font = Font(name="Calibri", size=12, bold=True, color="FF0000")  # Красный цвет
        cell_total_all.alignment = Alignment(horizontal="center", vertical="center")

        # 6. Настраиваем ширину колонок для красивого отображения
        column_widths = {
            'A': 35,  # ФИО
            'B': 25,  # Должность
            'C': 18,  # Дата
            'D': 15,  # Начало
            'E': 15,  # Окончание
            'F': 22,  # Длительность (часы)
            'G': 40,  # Описание
        }

        for col, width in column_widths.items():
            ws.column_dimensions[col].width = width

        # 7. Сохраняем книгу в буфер памяти
        file_stream = BytesIO()
        wb.save(file_stream)
        file_stream.seek(0)

        # Формируем красивое название файла
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"overtime_report_{dept_id}_{timestamp}.xlsx"

        return file_stream, filename