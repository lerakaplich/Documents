from aiogram import F, Router
from aiogram.types import CallbackQuery

router = Router()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "ignore")
async def ignore(callback: CallbackQuery):
    await callback.answer("Действие недоступно", show_alert=True)