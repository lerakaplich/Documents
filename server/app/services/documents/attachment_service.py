import io
import logging
import os
import time
import uuid
from datetime import date, datetime
import zipfile
import shutil

from fastapi import UploadFile, HTTPException, status

from server.app.repositories.attachment_repo import AttachmentRepository
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.common.security_service import SecurityService
from server.app.services.common.tiff_converter import DocumentProcessor

logger = logging.getLogger("app.services.attachment_service")

class AttachmentService:
    def __init__(self, repo: AttachmentRepository, processor: DocumentProcessor, security: SecurityService):
        self.repo = repo
        self.processor = processor
        self.security = security

    def _get_doc_dir(self, sent_date: date, doc_id: int) -> str:
        """Формирует путь storage/YYYY/MM/DD/doc_id/"""
        path = os.path.join(
            "storage",
            sent_date.strftime("%Y"),
            sent_date.strftime("%m"),
            sent_date.strftime("%d"),
            f"doc_{doc_id}"
        )
        os.makedirs(path, exist_ok=True)
        return path

    def archive_attachments(self, doc_id: int, sent_date: date):
        """Архивирует все файлы в папке документа"""
        start_time = time.perf_counter()
        folder_path = self._get_doc_dir(sent_date, doc_id)
        zip_path = os.path.join(folder_path, "attachments.zip")

        logger.debug(
            f"Archiving attachment directory for doc_id={doc_id}",
            extra={"event_type": "attach_archive_start", "doc_id": doc_id, "folder_path": folder_path}
        )

        try:
            files_archived = 0
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file != "attachments.zip":  # Не архивируем сам архив
                            file_full_path = os.path.join(root, file)
                            zipf.write(file_full_path, file)
                            os.remove(file_full_path)
                            files_archived += 1

            elapsed = round(time.perf_counter() - start_time, 3)
            logger.info(
                f"Archived {files_archived} files into {zip_path} in {elapsed}s",
                extra={
                    "event_type": "attach_archive_success",
                    "doc_id": doc_id,
                    "files_count": files_archived,
                    "duration_sec": elapsed
                }
            )
        except Exception as e:
            logger.exception(
                f"Failed to archive attachments for doc_id={doc_id}: {e}",
                extra={"event_type": "attach_archive_error", "doc_id": doc_id}
            )
            raise

    def extract_attachments(self, doc_id: int, sent_date: date) -> str:
        """Разархивирует вложение для просмотра и возвращает путь к папке"""
        folder_path = self._get_doc_dir(sent_date, doc_id)
        zip_path = os.path.join(folder_path, "attachments.zip")

        temp_view_path = f"temp/view_{doc_id}_{uuid.uuid4().hex}"
        os.makedirs(temp_view_path, exist_ok=True)

        logger.debug(
            f"Extracting attachments archive for doc_id={doc_id} to {temp_view_path}",
            extra={"event_type": "attach_extract_start", "doc_id": doc_id, "zip_path": zip_path}
        )

        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(temp_view_path)

            logger.info(
                f"Extracted attachments for doc_id={doc_id} to {temp_view_path}",
                extra={"event_type": "attach_extract_success", "doc_id": doc_id, "temp_view_path": temp_view_path}
            )
            return temp_view_path
        except Exception as e:
            logger.exception(
                f"Failed to extract attachments zip '{zip_path}': {e}",
                extra={"event_type": "attach_extract_error", "doc_id": doc_id, "zip_path": zip_path}
            )
            raise

    async def add_attachment(self, doc_id: int, file: UploadFile, current_user: CurrentUser, sent_date: date = None):
        user_id = getattr(current_user, 'id', None)
        start_time = time.perf_counter()

        if not await self.security.can_access_document(current_user, doc_id):
            logger.warning(
                f"Access denied for user_id={user_id} to document doc_id={doc_id} during attachment upload",
                extra={"event_type": "attach_access_denied", "user_id": user_id, "doc_id": doc_id}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к данному документу",
            )

        if not sent_date:
            sent_date = await self.repo.get_document_sent_date(doc_id) or datetime.now().date()

        doc_dir = self._get_doc_dir(sent_date, doc_id)
        zip_path = os.path.join(doc_dir, "attachments.zip")
        work_dir = os.path.join(doc_dir, f"temp_{uuid.uuid4().hex}")
        os.makedirs(work_dir, exist_ok=True)

        logger.info(
            f"Starting attachment upload for doc_id={doc_id}, file_name='{file.filename}', user_id={user_id}",
            extra={"event_type": "attach_upload_start", "doc_id": doc_id, "filename": file.filename, "user_id": user_id}
        )

        try:
            # 1. Извлечение существующих файлов из ZIP (если есть)
            if os.path.exists(zip_path):
                with zipfile.ZipFile(zip_path, 'r') as zipf:
                    zipf.extractall(work_dir)

            file_uuid = uuid.uuid4().hex
            file_ext = os.path.splitext(file.filename)[1]
            temp_input = os.path.join(work_dir, f"raw_{file_uuid}{file_ext}")

            # Сохраняем входящий файл во временную директорию
            contents = await file.read()
            with open(temp_input, "wb") as f:
                f.write(contents)

            # 2. Определяем формат и проводим конвертацию
            file_type = self.processor.get_file_type(file.filename)

            if file_type == 'pdf':
                img_size, text_size = self.processor.analyze_pdf_content(temp_input)
                if img_size > text_size:
                    final_ext = ".tiff"
                    final_path = os.path.join(work_dir, f"{file_uuid}{final_ext}")
                    self.processor.convert_pdf_to_tiff(temp_input, final_path)
                    logger.debug(f"PDF identified as scan; converted to TIFF: doc_id={doc_id}")
                else:
                    final_ext = ".pdf"
                    final_path = os.path.join(work_dir, f"{file_uuid}{final_ext}")
                    shutil.copy(temp_input, final_path)
                    logger.debug(f"PDF identified as native text; copied as PDF: doc_id={doc_id}")
            else:
                final_ext = ".tiff"
                final_path = os.path.join(work_dir, f"{file_uuid}{final_ext}")
                self.processor.convert_image_to_tiff(temp_input, final_path)

            # 3. Генерация превью (только для raster TIFF)
            if final_ext == ".tiff":
                self.processor.create_thumbnail(final_path)

            if os.path.exists(temp_input):
                os.remove(temp_input)

            # 4. Пересборка ZIP
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for f in os.listdir(work_dir):
                    zipf.write(os.path.join(work_dir, f), f)

            final_file_size = os.path.getsize(final_path)
            storage_path = f"{zip_path}#{file_uuid}{final_ext}"

            # 5. Обновление записи в БД
            await self.repo.add({
                "document_id": doc_id,
                "file_name": file.filename,
                "storage_path": storage_path,
                "file_size": final_file_size,
                "uploaded_at": datetime.now()
            })

            elapsed = round(time.perf_counter() - start_time, 3)
            logger.info(
                f"Successfully added attachment for doc_id={doc_id}: '{file.filename}' -> '{storage_path}' in {elapsed}s",
                extra={
                    "event_type": "attach_upload_success",
                    "doc_id": doc_id,
                    "filename": file.filename,
                    "file_size": final_file_size,
                    "duration_sec": elapsed,
                    "user_id": user_id
                }
            )

        except Exception as e:
            logger.exception(
                f"Error occurred while processing attachment upload for doc_id={doc_id}, file='{file.filename}': {e}",
                extra={"event_type": "attach_upload_error", "doc_id": doc_id, "filename": file.filename}
            )
            raise
        finally:
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir)

    async def get_attachments_info(self, doc_id: int, current_user: CurrentUser):
        user_id = getattr(current_user, 'id', None)
        if not await self.security.can_access_document(current_user, doc_id):
            logger.warning(
                f"Access denied for user_id={user_id} to document doc_id={doc_id} on getting attachments list",
                extra={"event_type": "attach_access_denied", "user_id": user_id, "doc_id": doc_id}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к данному документу",
            )

        attachments = await self.repo.get_all_by_doc(doc_id)
        logger.debug(
            f"Retrieved {len(attachments)} attachments info for doc_id={doc_id}",
            extra={"event_type": "attach_get_info_list", "doc_id": doc_id, "count": len(attachments)}
        )
        return [
            {
                "id": attach.id,
                "file_name": attach.file_name,
                "file_size": attach.file_size,
                "preview_url": f"/attachments/{attach.id}/preview",
                "uploaded_at": attach.uploaded_at.isoformat() if attach.uploaded_at else None
            }
            for attach in attachments
        ]

    async def delete_attachment(self, doc_id: int, attach_id: int, current_user: CurrentUser):
        user_id = getattr(current_user, 'id', None)
        attachment = await self.repo.get_by_id(attach_id)
        if not attachment:
            logger.warning(
                f"Delete requested for non-existent attachment attach_id={attach_id}",
                extra={"event_type": "attach_not_found", "attach_id": attach_id}
            )
            raise HTTPException(status_code=404, detail="Вложение не найдено")

        if not await self.security.can_access_document(current_user, attachment.document_id):
            logger.warning(
                f"Access denied for user_id={user_id} to delete attach_id={attach_id} on doc_id={attachment.document_id}",
                extra={"event_type": "attach_access_denied", "user_id": user_id, "attach_id": attach_id, "doc_id": attachment.document_id}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к данному документу",
            )

        if '#' not in attachment.storage_path:
            logger.error(
                f"Corrupted storage path format in DB for attach_id={attach_id}: '{attachment.storage_path}'",
                extra={"event_type": "attach_path_corrupted", "attach_id": attach_id, "path": attachment.storage_path}
            )
            raise HTTPException(status_code=500, detail="Ошибка формата пути к файлу в БД")

        if attachment.document_id != doc_id:
            logger.warning(
                f"Attachment attach_id={attach_id} belongs to doc_id={attachment.document_id}, not requested doc_id={doc_id}",
                extra={"event_type": "attach_doc_mismatch", "attach_id": attach_id, "requested_doc_id": doc_id}
            )
            raise HTTPException(status_code=403, detail="Вложение не принадлежит этому документу")

        attachments_count = await self.repo.count_by_doc(doc_id)
        if attachments_count <= 1:
            logger.warning(
                f"Attempted to delete the last remaining attachment attach_id={attach_id} for doc_id={doc_id}",
                extra={"event_type": "attach_delete_last_prevented", "doc_id": doc_id, "attach_id": attach_id}
            )
            raise HTTPException(status_code=400, detail="Нельзя удалить последнее вложение")

        archive_path, file_name = attachment.storage_path.split('#')
        work_dir = os.path.join(os.path.dirname(archive_path), f"temp_del_{uuid.uuid4().hex}")
        os.makedirs(work_dir, exist_ok=True)

        try:
            # Извлекаем все файлы, исключая удаляемый
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                for member in zipf.namelist():
                    if member != file_name and member != file_name.replace('.tiff', '_thumb.jpg'):
                        zipf.extract(member, work_dir)

            # Пересобираем ZIP без него
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for f in os.listdir(work_dir):
                    zipf.write(os.path.join(work_dir, f), f)

            await self.repo.delete(attach_id)

            logger.info(
                f"Successfully deleted attachment attach_id={attach_id} from doc_id={doc_id}",
                extra={"event_type": "attach_delete_success", "attach_id": attach_id, "doc_id": doc_id, "user_id": user_id}
            )

        except Exception as e:
            logger.exception(
                f"Error deleting attachment attach_id={attach_id} from archive '{archive_path}': {e}",
                extra={"event_type": "attach_delete_error", "attach_id": attach_id, "doc_id": doc_id}
            )
            raise
        finally:
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir)

    async def get_page_count(self, attach_id: int, current_user: CurrentUser) -> int:
        user_id = getattr(current_user, 'id', None)
        attachment = await self.repo.get_by_id(attach_id)
        if not attachment:
            logger.warning(
                f"Requested page count for non-existent attachment attach_id={attach_id}",
                extra={"event_type": "attach_not_found", "attach_id": attach_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вложение не найдено",
            )

        if not await self.security.can_access_document(current_user, attachment.document_id):
            logger.warning(
                f"Access denied for user_id={user_id} on getting page count for attach_id={attach_id}",
                extra={"event_type": "attach_access_denied", "user_id": user_id, "attach_id": attach_id}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к данному документу",
            )

        if "#" not in attachment.storage_path:
            logger.error(
                f"Corrupted storage path format in DB for attach_id={attach_id}: '{attachment.storage_path}'",
                extra={"event_type": "attach_path_corrupted", "attach_id": attach_id}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка формата пути к файлу в БД",
            )

        archive_path, file_name = attachment.storage_path.split("#")

        os.makedirs("temp", exist_ok=True)
        ext = os.path.splitext(file_name)[1]
        temp_path = os.path.join("temp", f"view_{attach_id}_{uuid.uuid4().hex}{ext}")

        try:
            with zipfile.ZipFile(archive_path, "r") as zipf:
                with open(temp_path, "wb") as f:
                    f.write(zipf.read(file_name))

            page_count = self.processor.get_page_count(temp_path)
            logger.debug(
                f"Retrieved page count ({page_count}) for attach_id={attach_id}",
                extra={"event_type": "attach_get_page_count", "attach_id": attach_id, "page_count": page_count}
            )
            return page_count
        except Exception as e:
            logger.exception(
                f"Failed to read page count for attach_id={attach_id}: {e}",
                extra={"event_type": "attach_get_page_count_error", "attach_id": attach_id}
            )
            raise
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def get_page_as_stream(self, attach_id: int, page_num: int, current_user: CurrentUser) -> io.BytesIO:
        user_id = getattr(current_user, 'id', None)
        attachment = await self.repo.get_by_id(attach_id)
        if not attachment:
            logger.warning(
                f"Requested page stream for non-existent attachment attach_id={attach_id}",
                extra={"event_type": "attach_not_found", "attach_id": attach_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вложение не найдено",
            )

        if not await self.security.can_access_document(current_user, attachment.document_id):
            logger.warning(
                f"Access denied for user_id={user_id} on getting page stream for attach_id={attach_id}",
                extra={"event_type": "attach_access_denied", "user_id": user_id, "attach_id": attach_id}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к данному документу",
            )

        if "#" not in attachment.storage_path:
            logger.error(
                f"Corrupted storage path format in DB for attach_id={attach_id}: '{attachment.storage_path}'",
                extra={"event_type": "attach_path_corrupted", "attach_id": attach_id}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка формата пути к файлу в БД",
            )

        archive_path, file_name = attachment.storage_path.split("#")

        os.makedirs("temp", exist_ok=True)
        ext = os.path.splitext(file_name)[1]
        temp_path = os.path.join("temp", f"view_{attach_id}_{uuid.uuid4().hex}{ext}")

        try:
            with zipfile.ZipFile(archive_path, "r") as zipf:
                with open(temp_path, "wb") as f:
                    f.write(zipf.read(file_name))

            stream = self.processor.get_page_as_stream(temp_path, page_num)
            logger.debug(
                f"Streamed page {page_num} for attach_id={attach_id}",
                extra={"event_type": "attach_stream_page_success", "attach_id": attach_id, "page_num": page_num}
            )
            return stream
        except Exception as e:
            logger.exception(
                f"Failed to stream page {page_num} for attach_id={attach_id}: {e}",
                extra={"event_type": "attach_stream_page_error", "attach_id": attach_id, "page_num": page_num}
            )
            raise
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)