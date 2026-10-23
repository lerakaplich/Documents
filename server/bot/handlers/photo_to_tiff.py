import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from server.app.services.tiff.photo_tiff_service import PhotoTiffService
from server.bot.keyboards.menu_kb import get_main_menu
from server.bot.keyboards.photo_kb import PhotoCallback, get_photo_collect_kb
from server.bot.services import messages as msg
from server.bot.states.bot_states import PhotoToTiffFSM

router = Router()
logger = logging.getLogger("bot_photo_tiff")

MAX_PAGES = 20


async def open_photo_to_tiff(message: Message, state: FSMContext) -> None:
    """Точка входа (вызывается из handlers/menu.py)."""
    await state.clear()
    await state.set_state(PhotoToTiffFSM.collecting)
    await state.update_data(photo_files=[], photo_last_group=None)
    await message.answer(msg.PHOTO_START.format(max_pages=MAX_PAGES))


async def _register_file(message: Message, state: FSMContext, file_id: str) -> None:
    data = await state.get_data()
    files: list[list] = data.get("photo_files", [])

    if len(files) >= MAX_PAGES:
        await message.answer(msg.PHOTO_LIMIT.format(max_pages=MAX_PAGES),
                             reply_markup=get_photo_collect_kb())
        return

    # message_id нужен, чтобы сохранить порядок страниц в альбоме
    files.append([message.message_id, file_id])
    await state.update_data(photo_files=files)

    # На альбом отвечаем один раз — на первое сообщение группы
    group_id = message.media_group_id
    if group_id and data.get("photo_last_group") == group_id:
        return
    await state.update_data(photo_last_group=group_id)

    text = msg.PHOTO_ALBUM_ACCEPTED if group_id else msg.PHOTO_PAGE_ACCEPTED.format(n=len(files))
    await message.answer(text, reply_markup=get_photo_collect_kb())


@router.message(PhotoToTiffFSM.collecting, F.photo)
async def collect_photo(message: Message, state: FSMContext) -> None:
    await _register_file(message, state, message.photo[-1].file_id)  # самое большое разрешение


@router.message(PhotoToTiffFSM.collecting, F.document.mime_type.startswith("image/"))
async def collect_image_document(message: Message, state: FSMContext) -> None:
    await _register_file(message, state, message.document.file_id)


@router.message(PhotoToTiffFSM.collecting)
async def collect_unsupported(message: Message) -> None:
    await message.answer(msg.PHOTO_UNSUPPORTED, reply_markup=get_photo_collect_kb())


@router.callback_query(PhotoToTiffFSM.collecting, PhotoCallback.filter(F.action == "reset"))
async def reset_photos(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(photo_files=[], photo_last_group=None)
    await callback.answer("Список очищен")


@router.callback_query(PhotoToTiffFSM.collecting, PhotoCallback.filter(F.action == "cancel"))
async def cancel_photos(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await callback.message.edit_text("Конвертация отменена.")


@router.callback_query(PhotoToTiffFSM.collecting, PhotoCallback.filter(F.action == "convert"))
async def convert_photos(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    photo_service: PhotoTiffService,
) -> None:
    data = await state.get_data()
    items = sorted(data.get("photo_files", []))  # по message_id
    if not items:
        await callback.answer("Сначала отправьте хотя бы одно фото", show_alert=True)
        return

    await callback.answer()
    status_msg = await callback.message.answer(msg.PHOTO_CONVERTING)

    try:
        result = await photo_service.build_tiff(bot, [file_id for _, file_id in items])
    except Exception:
        logger.exception("TIFF conversion failed for user_id=%s", callback.from_user.id)
        await status_msg.edit_text(msg.PHOTO_ERROR)  # состояние сохраняем — можно повторить
        return

    await status_msg.delete()
    await callback.message.answer_document(
        BufferedInputFile(result.data, filename=result.filename),
        caption=msg.PHOTO_DONE.format(pages=result.pages),
    )
    await state.clear()
    await callback.message.answer(msg.BACK_TO_MENU, reply_markup=get_main_menu())