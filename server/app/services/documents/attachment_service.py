import os
import uuid
from datetime import date, datetime
import zipfile
import shutil

from fastapi import UploadFile, HTTPException

from server.app.repositories.attachment_repo import AttachmentRepository
from server.app.services.common.tiff_converter import DocumentProcessor


class AttachmentService:
    def __init__(self, repo: AttachmentRepository, processor: DocumentProcessor):
        self.repo = repo
        self.processor = processor

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
        folder_path = self._get_doc_dir(sent_date, doc_id)
        zip_path = os.path.join(folder_path, "attachments.zip")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file != "attachments.zip":  # Не архивируем сам архив
                        zipf.write(os.path.join(root, file), file)
                        os.remove(os.path.join(root, file))  # Удаляем исходник

    def extract_attachments(self, doc_id: int, sent_date: date) -> str:
        """Разархивирует вложение для просмотра и возвращает путь к папке"""
        folder_path = self._get_doc_dir(sent_date, doc_id)
        zip_path = os.path.join(folder_path, "attachments.zip")

        # Создаем временную папку для просмотра
        temp_view_path = f"temp/view_{doc_id}_{uuid.uuid4()}"
        os.makedirs(temp_view_path, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(temp_view_path)

        return temp_view_path

    async def add_attachment(self, doc_id: int, file: UploadFile, sent_date: date = None):
        if not sent_date:
            sent_date = await self.repo.get_document_sent_date(doc_id) or datetime.now().date()

        doc_dir = self._get_doc_dir(sent_date, doc_id)
        zip_path = os.path.join(doc_dir, "attachments.zip")
        work_dir = os.path.join(doc_dir, f"temp_{uuid.uuid4().hex}")
        os.makedirs(work_dir, exist_ok=True)

        try:
            if os.path.exists(zip_path):
                with zipfile.ZipFile(zip_path, 'r') as zipf:
                    zipf.extractall(work_dir)

            file_uuid = uuid.uuid4().hex
            temp_input = os.path.join(work_dir, f"raw_{file_uuid}{os.path.splitext(file.filename)[1]}")

            with open(temp_input, "wb") as f:
                f.write(await file.read())

            # 2. ОПРЕДЕЛЯЕМ ФОРМАТ СОХРАНЕНИЯ
            file_type = self.processor.get_file_type(file.filename)

            if file_type == 'pdf':
                img_size, text_size = self.processor.analyze_pdf_content(temp_input)
                if img_size > text_size:  # Это скан
                    final_ext = ".tiff"
                    final_path = os.path.join(work_dir, f"{file_uuid}{final_ext}")
                    self.processor.convert_pdf_to_tiff(temp_input, final_path)
                else:  # Цифровой PDF
                    final_ext = ".pdf"
                    final_path = os.path.join(work_dir, f"{file_uuid}{final_ext}")
                    shutil.copy(temp_input, final_path)
            else:  # Это картинка
                final_ext = ".tiff"
                final_path = os.path.join(work_dir, f"{file_uuid}{final_ext}")
                self.processor.convert_image_to_tiff(temp_input, final_path)

            # 3. Создаем превью (только если это растр)
            # Внимание: если это PDF, превью можно сделать из первой страницы PDF
            # Но для простоты: генерируем превью только для TIFF
            if final_ext == ".tiff":
                self.processor.create_thumbnail(final_path)

            # Удаляем временный исходник, оставляем только обработанный файл
            os.remove(temp_input)

            # 4. Упаковка в ZIP
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for f in os.listdir(work_dir):
                    zipf.write(os.path.join(work_dir, f), f)

            # 5. Обновление БД
            await self.repo.add({
                "document_id": doc_id,
                "file_name": file.filename,
                "storage_path": f"{zip_path}#{file_uuid}{final_ext}",  # Путь к файлу внутри архива
                "file_size": os.path.getsize(final_path),
                "uploaded_at": datetime.now()
            })

        finally:
            shutil.rmtree(work_dir)


