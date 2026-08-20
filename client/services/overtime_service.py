# client/services/overtime_service.py
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from client.core.http_client import HttpClient


class OvertimeService:
    """Сервис для работы с API переработок"""

    def __init__(self, http_client: HttpClient):
        self.client = http_client

    def get_my_overtime(self) -> List[Dict[str, Any]]:
        """
        Получить переработки текущего пользователя
        GET /overtime/my
        """
        try:
            print("📤 Запрос на получение моих переработок")
            result = self.client.get("/overtime/my")
            print(f"📥 Получено {len(result) if result else 0} моих переработок")
            return result if result else []
        except Exception as e:
            print(f"❌ Ошибка получения моих переработок: {e}")
            return []

    def get_all_overtime(self) -> List[Dict[str, Any]]:
        """
        Получить все переработки
        GET /overtime/all
        """
        try:
            print("📤 Запрос на получение всех переработок")
            result = self.client.get("/overtime/all")
            print(f"📥 Получено {len(result) if result else 0} переработок")
            return result if result else []
        except Exception as e:
            print(f"❌ Ошибка получения всех переработок: {e}")
            return []

    def get_department_overtime(self, department_id: int) -> List[Dict[str, Any]]:
        """
        Получить переработки по отделу
        GET /overtime/department/{dept_id}
        """
        try:
            print(f"📤 Запрос на получение переработок для отдела {department_id}")
            result = self.client.get(f"/overtime/department/{department_id}")
            print(f"📥 Получено {len(result) if result else 0} переработок для отдела")
            return result if result else []
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