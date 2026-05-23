from fastapi import FastAPI
from server.app.api.auth import router as auth_router
from server.app.api.documents import router as doc_router

app = FastAPI(
    title="СЭД Документооборот — Тестовый Сервер",
    version="1.0.0"
)

# Подключаем наш написанный модуль авторизации
app.include_router(auth_router, prefix="/api/v1")
app.include_router(doc_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"status": "working", "message": "Сервер запущен. Перейдите на /docs для тестов."}