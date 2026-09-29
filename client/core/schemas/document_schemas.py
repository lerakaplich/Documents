# client/core/schemas/document_schemas.py


class DocumentSchema:
    """Схема документа для клиента"""

    @staticmethod
    def from_api(data: dict) -> dict:
        """Преобразует данные из API в формат клиента"""
        return {
            "id": data.get("id"),
            "type_id": data.get("type_id"),
            "type_name": data.get("type", {}).get("name") if data.get("type") else None,
            "direction": data.get("direction"),
            "status": data.get("status"),
            "title": data.get("title", ""),
            "about": data.get("about", ""),
            "reg_number": data.get("reg_number", ""),
            "sequence_number": data.get("sequence_number"),
            "deadline": data.get("deadline"),
            "needs_response": data.get("needs_response", False),
            "created_at": data.get("created_at"),
            "sender": DocumentSchema._get_sender(data),
            "receivers": DocumentSchema._get_receivers(data),
            "executors": DocumentSchema._get_executors(data),
            "tags": DocumentSchema._get_tags(data),
            "is_read": data.get("is_read", False),
            "is_pinned": data.get("is_pinned", False),
            "has_attachments": data.get("has_attachments", False),
            "has_reply": data.get("has_reply", False),
            "comments_count": data.get("comments_count", 0),
        }

    @staticmethod
    def _get_sender(data: dict) -> str:
        """Получить отправителя"""
        employees = data.get("employees", [])
        for emp in employees:
            if emp.get("role") == "sender":
                return emp.get("fio", "")
        return ""

    @staticmethod
    def _get_receivers(data: dict) -> list[str]:
        """Получить получателей"""
        employees = data.get("employees", [])
        return [
            emp.get("fio", "") for emp in employees if emp.get("role") == "recipient"
        ]

    @staticmethod
    def _get_executors(data: dict) -> list[str]:
        """Получить исполнителей"""
        employees = data.get("employees", [])
        return [
            emp.get("fio", "") for emp in employees if emp.get("role") == "executor"
        ]

    @staticmethod
    def _get_tags(data: dict) -> list[dict]:
        """Получить теги"""
        return data.get("tags", [])
