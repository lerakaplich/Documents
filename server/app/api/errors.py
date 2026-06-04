from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


async def integrity_exception_handler(request: Request, exc: IntegrityError):
    # Эта функция теперь срабатывает ТОЛЬКО на IntegrityError
    err_msg = str(exc.orig)
    if "employees_service_number_key" in err_msg:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Сотрудник с таким табельным номером уже существует."}
        )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Ошибка целостности данных."}
    )


async def global_exception_handler(request: Request, exc: Exception):
    # Теперь здесь внутри проверяем, является ли ошибка IntegrityError
    if isinstance(exc, IntegrityError):
        err_msg = str(exc.orig)

        if "employees_service_number_key" in err_msg:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"detail": "Сотрудник с таким табельным номером уже существует."}
            )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Ошибка целостности данных."}
        )

    # Для всех остальных ошибок
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервера."}
    )