# client/services/overtime_service.py
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from client.core.http_client import HttpClient


class OvertimeService:
    """Сервис для работы с API переработок"""

    def __init__(self, http_client: HttpClient):
        self.client = http_client

    def get_my_overtime(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            print("📤 Запрос на получение моих переработок")
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            params['page'] = 1
            params['size'] = 100  # чтобы получить все записи
            result = self.client.get("/overtime/my", params=params)
            items = result.get('items', []) if isinstance(result, dict) else []
            print(f"📥 Получено {len(items)} моих переработок")
            return items
        except Exception as e:
            print(f"❌ Ошибка получения моих переработок: {e}")
            return []

    def get_all_overtime(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[
        Dict[str, Any]]:
        try:
            print("📤 Запрос на получение всех переработок")
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            params['page'] = 1
            params['size'] = 100
            result = self.client.get("/overtime/all", params=params)
            items = result.get('items', []) if isinstance(result, dict) else []
            print(f"📥 Получено {len(items)} переработок")
            return items
        except Exception as e:
            print(f"❌ Ошибка получения всех переработок: {e}")
            return []

    def get_department_overtime(self, department_id: int, start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            print(f"📤 Запрос на получение переработок для отдела {department_id}")
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            params['page'] = 1
            params['size'] = 100
            result = self.client.get(f"/overtime/department/{department_id}", params=params)
            items = result.get('items', []) if isinstance(result, dict) else []
            print(f"📥 Получено {len(items)} переработок для отдела")
            return items
        except Exception as e:
            print(f"❌ Ошибка получения переработок для отдела: {e}")
            return []

    def create_overtime(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создать новую переработку
        POST /overtime
        """
        try:
            print("📤 Создание новой переработки")
            result = self.client.post("/overtime", json=data)
            print(f"✅ Переработка создана: {result.get('id')}")
            return result
        except Exception as e:
            print(f"❌ Ошибка создания переработки: {e}")
            raise

    def update_overtime(self, overtime_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновить переработку
        PATCH /overtime/{ot_id}
        """
        try:
            print(f"📤 Обновление переработки {overtime_id}")
            result = self.client.patch(f"/overtime/{overtime_id}", json=data)
            print(f"✅ Переработка {overtime_id} обновлена")
            return result
        except Exception as e:
            print(f"❌ Ошибка обновления переработки: {e}")
            raise

    def update_overtime_note(self, overtime_id: int, note: str) -> Dict[str, Any]:
        """
        Обновить заметку переработки
        PATCH /overtime/{ot_id}/description?note={note}
        """
        try:
            print(f"📤 Обновление заметки переработки {overtime_id}")
            result = self.client.patch(f"/overtime/{overtime_id}/description", params={"note": note})
            print(f"✅ Заметка переработки {overtime_id} обновлена")
            return result
        except Exception as e:
            print(f"❌ Ошибка обновления заметки: {e}")
            raise

    def delete_overtime(self, overtime_id: int) -> None:
        """
        Удалить переработку
        DELETE /overtime/{ot_id}
        """
        try:
            print(f"📤 Удаление переработки {overtime_id}")
            self.client.delete(f"/overtime/{overtime_id}")
            print(f"✅ Переработка {overtime_id} удалена")
        except Exception as e:
            print(f"❌ Ошибка удаления переработки: {e}")
            raise

    def import_overtime(self, file_path: str) -> dict:
        """
        Импорт переработок из Excel-файла выгрузки СКУД.
        POST /overtime/import-excel (multipart/form-data)
        """
        try:
            print(f"📤 Импорт переработок из файла: {file_path}")

            # Content-Type НЕ ставим — requests сам выставит multipart с boundary
            headers = self.client._get_headers()
            headers.pop("Content-Type", None)

            url = f"{self.client.base_url}/overtime/import-excel"

            with open(file_path, "rb") as f:
                files = {
                    "file": (
                        os.path.basename(file_path),
                        f,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                }
                response = self.client.session.post(
                    url,
                    headers=headers,
                    files=files,
                    timeout=120,
                )

            print(f"📥 Статус ответа: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Импорт выполнен: {result}")
                return result

            error_body = response.text
            print(f"❌ Ошибка импорта: {response.status_code}")
            print(f"❌ Тело ошибки: {error_body[:500]}")
            raise Exception(f"Ошибка импорта: {response.status_code}\n{error_body}")
        except Exception as e:
            print(f"❌ Ошибка импорта: {e}")
            raise

    def update_bulk_notes(self, overtime_ids: List[int], note: str) -> Dict[str, Any]:
        """
        Массовое обновление заметок
        PATCH /overtime/bulk-description
        """
        try:
            print(f"📤 Массовое обновление заметок для {len(overtime_ids)} переработок")
            data = {"overtime_ids": overtime_ids, "note": note}
            result = self.client.patch("/overtime/bulk-description", json=data)
            print(f"✅ Массовое обновление заметок выполнено")
            return result
        except Exception as e:
            print(f"❌ Ошибка массового обновления заметок: {e}")
            raise

    def export_overtime(self, dept_id: Optional[int] = None,
                        start_date: Optional[date] = None,
                        end_date: Optional[date] = None) -> bytes:
        """
        Экспорт переработок в Excel
        GET /overtime/export-excel
        """
        try:
            params = {}
            if dept_id:
                params["dept_id"] = dept_id
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()

            print(f"📤 Экспорт переработок с параметрами: {params}")

            # Используем сессию для получения бинарного файла
            headers = self.client._get_headers()
            url = f"{self.client.base_url}/overtime/export-excel"

            response = self.client.session.get(
                url,
                headers=headers,
                params=params,
                timeout=60
            )

            print(f"📥 Статус ответа: {response.status_code}")

            if response.status_code == 200:
                print(f"✅ Экспорт выполнен, размер: {len(response.content)} байт")
                return response.content
            else:
                # Пытаемся получить тело ошибки
                error_body = response.text
                print(f"❌ Ошибка экспорта: {response.status_code}")
                print(f"❌ Тело ошибки: {error_body[:500]}")
                raise Exception(f"Ошибка экспорта: {response.status_code}\n{error_body}")
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
            raise