import asyncio
import json
import asyncpg
from server.app.services.common.connection_manager import manager
from server.app.database.session import DOCUMENTS_DB_URL


async def listen_to_db_notifications(db_url: str):
    """Фоновая задача, которая слушает базу данных."""
    while True:
        try:
            conn = await asyncpg.connect(db_url)
            async def handle_notify(conn, pid, channel, payload):
                data = json.loads(payload)
                emp_id = data.get("employee_id")
                doc_id = data.get("document_id")
                if emp_id:
                    await manager.send_personal_message({"type": "new_doc", "doc_id": doc_id}, emp_id)

            await conn.add_listener('new_document_channel', handle_notify)

            while True:
                await asyncio.sleep(60)

        except Exception as e:
            print(f"Ошибка в слушателе БД: {e}. Переподключение через 5 сек...")
            await asyncio.sleep(5)