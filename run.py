import os
import uvicorn
from server.app.main import app  # Импортируем объект напрямую

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    uvicorn.run(app, host=host, port=port, reload=False)