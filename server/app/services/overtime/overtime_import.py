import logging
import re
import pandas as pd
from datetime import datetime, time, date
from typing import Optional, BinaryIO

from server.app.services.common.notification_service import NotificationService

logger = logging.getLogger(__name__)

class OvertimeImportService:
    """Сервис для парсинга Excel-файлов и импорта переработок в БД"""

    def __init__(
        self,
        overtime_repo,
        employee_repo,
        security,
        notification_service: NotificationService
    ):
        self.overtime_repo = overtime_repo
        self.employee_repo = employee_repo
        self.security = security
        self.notifications = notification_service
        self.employees_cache = {}

    async def _load_employees_cache(self):
        """Загружает сотрудников в память для минимизации запросов к БД"""
        # Теперь метод get_all_active() существует в репозитории!
        employees = await self.employee_repo.get_all_active()

        for emp in employees:
            # Собираем полное ФИО для кэша
            full_name_parts = [emp.last_name, emp.first_name, emp.patronymic]
            # Убираем None, если вдруг отчество отсутствует
            full_name_str = " ".join([part for part in full_name_parts if part])

            full_name_norm = self._normalize_name(full_name_str)
            if full_name_norm:
                self.employees_cache[full_name_norm] = emp.id

            # Кэшируем также по формату "Фамилия И.О."
            last_name = emp.last_name
            first_initial = emp.first_name[:1] if emp.first_name else ''
            middle_initial = emp.patronymic[:1] if emp.patronymic else ''

            if last_name and first_initial:
                short_name = f"{last_name} {first_initial}."
                if middle_initial:
                    short_name += f"{middle_initial}."
                self.employees_cache[short_name.lower()] = emp.id

        logger.info(
            "Employee cache loaded for overtime import",
            extra={"cached_names_count": len(self.employees_cache)},
        )

    @staticmethod
    def _normalize_name(name: str) -> str:
        if not name:
            return ""
        return ' '.join(name.split()).lower()

    @staticmethod
    def is_date_string(value: str) -> bool:
        if not value or not isinstance(value, str):
            return False
        return bool(re.match(r'^\d{2}\.\d{2}\.\d{2,4}$', value.strip()))

    @staticmethod
    def is_time_range_string(value: str) -> bool:
        if not value or not isinstance(value, str):
            return False
        return bool(re.search(r'\d{2}:\d{2}(?::\d{2})?\s*-\s*\d{2}:\d{2}(?::\d{2})?', value))

    @staticmethod
    def parse_time_range(time_str: str) -> tuple[Optional[time], Optional[time]]:
        if not time_str or not isinstance(time_str, str):
            return None, None

        # HH:MM:SS - HH:MM:SS
        match = re.search(r'(\d{2}):(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2}):(\d{2})', time_str)
        if match:
            return time(int(match.group(1)), int(match.group(2))), time(int(match.group(4)), int(match.group(5)))

        # HH:MM - HH:MM
        match = re.search(r'(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})', time_str)
        if match:
            return time(int(match.group(1)), int(match.group(2))), time(int(match.group(3)), int(match.group(4)))

        return None, None

    @staticmethod
    def parse_shift(shift_str: str) -> tuple[time, time]:
        if not shift_str or not isinstance(shift_str, str):
            return time(8, 0), time(16, 30)

        pattern = r'(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})'
        match = re.search(pattern, shift_str)
        if match:
            return time(int(match.group(1)), int(match.group(2))), time(int(match.group(3)), int(match.group(4)))
        return time(8, 0), time(16, 30)

    @staticmethod
    def parse_date(date_str) -> Optional[date]:
        if not date_str:
            return None
        if isinstance(date_str, (date, datetime)):
            return date_str.date() if isinstance(date_str, datetime) else date_str
        for fmt in ['%d.%m.%Y', '%Y-%m-%d', '%d.%m.%y']:
            try:
                return datetime.strptime(str(date_str).strip(), fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def round_to_30_minutes_up(dt: datetime) -> datetime:
        if dt.minute == 0 and dt.second == 0:
            return dt
        if dt.minute == 30 and dt.second == 0:
            return dt
        if dt.minute < 30:
            return dt.replace(minute=30, second=0, microsecond=0)
        next_hour = dt.hour + 1 if dt.hour + 1 < 24 else 0
        return dt.replace(hour=next_hour, minute=0, second=0, microsecond=0)

    @staticmethod
    def round_to_30_minutes_down(dt: datetime) -> datetime:
        return dt.replace(minute=0 if dt.minute < 30 else 30, second=0, microsecond=0)

    def calculate_overtime_separate(self, start_time: time, end_time: time, shift_start: time, shift_end: time) -> list[
        tuple[float, time, time]]:
        today = date.today()
        shift_start_dt = datetime.combine(today, shift_start)
        shift_end_dt = datetime.combine(today, shift_end)

        rounded_start = self.round_to_30_minutes_up(datetime.combine(today, start_time))
        rounded_end = self.round_to_30_minutes_down(datetime.combine(today, end_time))

        results = []
        # ДО смены
        if rounded_start < shift_start_dt:
            hours = round(((shift_start_dt - rounded_start).total_seconds() / 60.0) / 60.0, 2)
            results.append((hours, rounded_start.time(), shift_start_dt.time()))
        # ПОСЛЕ смены
        if rounded_end > shift_end_dt:
            hours = round(((rounded_end - shift_end_dt).total_seconds() / 60.0) / 60.0, 2)
            results.append((hours, shift_end_dt.time(), rounded_end.time()))

        return results

    def detect_columns(self, row) -> dict[str, Optional[int]]:
        detected = {'name': None, 'date': None, 'time_range': None, 'shift': None}
        for col_idx, value in enumerate(row):
            if value is None or pd.isna(value):
                continue
            val_str = str(value).strip()

            if self.is_time_range_string(val_str):
                if re.search(r'\d{2}:\d{2}:\d{2}', val_str):
                    if detected['time_range'] is None: detected['time_range'] = col_idx
                else:
                    if detected['shift'] is None: detected['shift'] = col_idx
            elif self.is_date_string(val_str):
                if detected['date'] is None: detected['date'] = col_idx
            elif re.search(r'[а-яА-ЯёЁ]', val_str) and ' ' in val_str:
                if detected['name'] is None: detected['name'] = col_idx
        logger.debug(
            "Excel columns auto-detected", extra={"detected_columns": detected}
        )
        return detected

    def find_employee_by_name(self, full_name: str) -> Optional[int]:
        if not full_name:
            return None
        norm = self._normalize_name(full_name)
        if norm in self.employees_cache:
            return self.employees_cache[norm]

        # Поиск по усеченной фамилии (если в кэше совпадает начало слова)
        last_name = norm.split()[0] if norm.split() else ""
        for cached_name, emp_id in self.employees_cache.items():
            if cached_name.startswith(last_name):
                return emp_id

        logger.warning(
            "Employee not found in cache by name during import",
            extra={"raw_name": full_name, "normalized_name": norm},
        )
        return None

    async def import_from_excel_file(self, file_stream: BinaryIO) -> dict:
        """Основной метод парсинга потока файла и сохранения в БД"""
        result = {'total_rows': 0, 'imported': 0, 'duplicates': 0, 'skipped': 0, 'errors': 0, 'error_details': []}

        imported_employee_ids: set[int] = set()
        logger.info("Starting overtime Excel import process")

        try:
            await self._load_employees_cache()

            # --- УМНОЕ ЧТЕНИЕ ФОРМАТОВ .XLS и .XLSX ---
            # Читаем первые байты (сигнатуру), чтобы понять, какой перед нами формат
            header_bytes = file_stream.read(8)
            file_stream.seek(0)  # Возвращаем указатель в начало потока

            # Байт-код OLE2 (старый формат XLS) начинается с D0 CF 11 E0 A1 B1 1A E1
            is_old_xls = header_bytes.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')

            format_str = "XLS (xlrd)" if is_old_xls else "XLSX (openpyxl)"
            logger.info(
                "Detected file format for overtime import",
                extra={"format": format_str},
            )

            if is_old_xls:
                try:
                    # Для .xls принудительно используем xlrd
                    df = pd.read_excel(file_stream, header=None, dtype=str, engine='xlrd')
                except ImportError as ie:
                    msg = "Критическая ошибка: Для поддержки файлов .xls установите пакет xlrd (pip install xlrd)."
                    logger.error(
                        "Failed to import .xls file: xlrd engine is missing",
                        exc_info=ie,
                    )
                    result["errors"] += 1
                    result["error_details"].append(msg)
                    return result
            else:
                # Для .xlsx используем стандартный openpyxl
                df = pd.read_excel(file_stream, header=None, dtype=str, engine='openpyxl')
            # ------------------------------------------

            # Ищем начало данных
            data_start_row = 0
            for idx, row in df.iterrows():
                first_cell = str(row.iloc[0]) if len(row) > 0 else ""
                if first_cell.isdigit() and int(first_cell) > 0:
                    data_start_row = idx
                    break

            data_rows = [df.iloc[i] for i in range(data_start_row, len(df)) if str(df.iloc[i].iloc[0]).isdigit()]
            result['total_rows'] = len(data_rows)

            if not data_rows:
                msg = "В файле не обнаружены строки с данными."
                logger.warning("Overtime import canceled: no data rows found in file")
                result["error_details"].append(msg)
                return result

            columns = self.detect_columns(data_rows[0])
            name_col = columns["name"] if columns["name"] is not None else 7
            date_col = columns["date"] if columns["date"] is not None else 10
            time_col = (
                columns["time_range"] if columns["time_range"] is not None else 11
            )
            shift_col = columns["shift"] if columns["shift"] is not None else 12

            for i, row in enumerate(data_rows):
                row_idx_display = data_start_row + i + 1
                try:
                    full_name = (
                        str(row.iloc[name_col]) if len(row) > name_col else ""
                    )
                    overtime_date = self.parse_date(
                        row.iloc[date_col] if len(row) > date_col else None
                    )
                    start_time, end_time = self.parse_time_range(
                        str(row.iloc[time_col]) if len(row) > time_col else ""
                    )
                    shift_start, shift_end = self.parse_shift(
                        str(row.iloc[shift_col]) if len(row) > shift_col else ""
                    )

                    employee_id = self.find_employee_by_name(full_name)
                    if (
                            not employee_id
                            or not overtime_date
                            or not start_time
                            or not end_time
                    ):
                        logger.warning(
                            "Skipping row during overtime import due to missing required data",
                            extra={
                                "file_row": row_idx_display,
                                "has_employee_id": bool(employee_id),
                                "has_date": bool(overtime_date),
                                "has_start_time": bool(start_time),
                                "has_end_time": bool(end_time),
                                "raw_name": full_name,
                            },
                        )
                        result["skipped"] += 1
                        continue

                    overtime_records = self.calculate_overtime_separate(
                        start_time, end_time, shift_start, shift_end
                    )
                    if not overtime_records:
                        logger.debug(
                            "Skipping row: work time falls within normal shift hours",
                            extra={
                                "file_row": row_idx_display,
                                "employee_id": employee_id,
                            },
                        )
                        result["skipped"] += 1
                        continue

                    for hours, ot_start, ot_end in overtime_records:
                        is_dup = await self.overtime_repo.check_exists(
                            employee_id, overtime_date, ot_start, ot_end
                        )
                        if is_dup:
                            logger.info(
                                "Duplicate overtime record skipped",
                                extra={
                                    "employee_id": employee_id,
                                    "date": str(overtime_date),
                                    "start_time": str(ot_start),
                                    "end_time": str(ot_end),
                                },
                            )
                            result["duplicates"] += 1
                            continue

                        await self.overtime_repo.create_overtime_direct(
                            employee_id=employee_id,
                            overtime_date=overtime_date,
                            start_time=ot_start,
                            end_time=ot_end,
                            description="Импорт из Excel"
                        )
                        result["imported"] += 1
                        imported_employee_ids.add(employee_id)

                except Exception as row_error:
                    result["errors"] += 1
                    err_msg = f"Строка {row_idx_display}: {str(row_error)}"
                    logger.warning(
                        "Error parsing individual row in overtime import",
                        extra={"file_row": row_idx_display, "error": str(row_error)},
                    )
                    result["error_details"].append(err_msg)

            await self.overtime_repo.db.commit()

            if imported_employee_ids:
                logger.info(
                    "Sending import notifications to employees",
                    extra={"notified_employees_count": len(imported_employee_ids)},
                )
                await self.notifications.notify_overtimes_imported(
                    imported_employee_ids
                )

            logger.info(
                "Overtime import completed successfully",
                extra={
                    "total_rows": result["total_rows"],
                    "imported": result["imported"],
                    "duplicates": result["duplicates"],
                    "skipped": result["skipped"],
                    "errors": result["errors"],
                },
            )
            return result

        except Exception as file_error:
            logger.error(
                "Critical error during overtime Excel file import",
                exc_info=file_error,
            )
            result["errors"] += 1
            result["error_details"].append(
                f"Критическая ошибка файла: {str(file_error)}"
            )
            return result


