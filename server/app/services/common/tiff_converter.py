import io
import logging
import os
import time

import fitz as pymupdf
from PIL import Image, ImageFilter, ImageEnhance, UnidentifiedImageError, ImageOps

logger = logging.getLogger("app.services.document_processor")

class DocumentProcessor:

    ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'}

    def __init__(self):
        # Перенесены ваши настройки для достижения нужного качества
        self.DEFAULT_DPI = 200
        self.THRESHOLD = 128
        self.CONTRAST_FACTOR = 0.5
        self.SHARPEN_RADIUS = 3

        # Дополнительные флаги из вашего примера
        self.REMOVE_BLEED_THROUGH = False
        self.TEXT_THINNING_ENABLED = False
        self.ADAPTIVE_THRESHOLD = True
        self.BLACK_ONLY = True

    def is_supported(self, file_path: str) -> bool:
        """Проверяет, поддерживается ли формат файла."""
        _, ext = os.path.splitext(file_path)
        supported = ext.lower() in self.ALLOWED_EXTENSIONS
        if not supported:
            logger.warning(
                f"Attempted to process file with unsupported extension '{ext}': {file_path}",
                extra={"event_type": "doc_unsupported_extension", "file_path": file_path, "ext": ext}
            )
        return supported

    def get_file_type(self, file_path: str) -> str:
        """Возвращает категорию файла для выбора алгоритма обработки."""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext == '.pdf':
            return 'pdf'
        elif ext in {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}:
            return 'image'
        else:
            logger.error(
                f"Cannot classify unsupported file format '{ext}' for path: {file_path}",
                extra={"event_type": "doc_unknown_type", "file_path": file_path, "ext": ext}
            )
            raise ValueError(f"Формат {ext} не поддерживается")

    def preprocess_image(self, img: Image.Image) -> Image.Image:
        """Предобработка изображения: перевод в оттенки серого, контраст, резкость и бинаризация."""
        if img.mode != 'L':
            img = img.convert('L')

        # Увеличение контраста
        if self.CONTRAST_FACTOR != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(self.CONTRAST_FACTOR)

        # Резкость
        if self.SHARPEN_RADIUS > 0:
            img = img.filter(ImageFilter.UnsharpMask(radius=self.SHARPEN_RADIUS, percent=100, threshold=5))

        threshold = self.THRESHOLD
        if self.ADAPTIVE_THRESHOLD:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)

        # ПРАВИЛЬНАЯ БИНАРИЗАЦИЯ:
        img = img.point(lambda x: 0 if x > threshold else 255, mode='1')

        return img

    def convert_image_to_tiff(self, input_path: str, output_path: str) -> str:
        """Конвертирует изображение в TIFF (бинарный/CCITT)"""
        start_time = time.perf_counter()
        logger.debug(
            f"Converting image to TIFF: {input_path} -> {output_path}",
            extra={"event_type": "doc_convert_image_start", "input_path": input_path, "output_path": output_path}
        )
        try:
            with Image.open(input_path) as img:
                processed_img = self.preprocess_image(img.convert("RGB"))
                processed_img.save(
                    output_path,
                    compression='tiff_ccitt',
                    dpi=(self.DEFAULT_DPI, self.DEFAULT_DPI)
                )

            elapsed = round(time.perf_counter() - start_time, 3)
            logger.info(
                f"Successfully converted image to TIFF in {elapsed}s: {output_path}",
                extra={
                    "event_type": "doc_convert_image_success",
                    "input_path": input_path,
                    "output_path": output_path,
                    "duration_sec": elapsed
                }
            )
            return output_path
        except UnidentifiedImageError:
            logger.error(
                f"Cannot identify image file (corrupted or invalid format): {input_path}",
                extra={"event_type": "doc_invalid_image", "input_path": input_path}
            )
            raise
        except Exception as e:
            logger.exception(
                f"Failed to convert image '{input_path}' to TIFF: {e}",
                extra={"event_type": "doc_convert_image_error", "input_path": input_path}
            )
            raise

    def convert_pdf_to_tiff(self, input_path: str, output_path: str) -> str:
        """Конвертирует PDF в TIFF и сохраняет по указанному пути."""
        start_time = time.perf_counter()
        logger.debug(
            f"Starting PDF to TIFF conversion: {input_path}",
            extra={"event_type": "doc_convert_pdf_start", "input_path": input_path}
        )
        try:
            doc = pymupdf.open(input_path)
            page_count = len(doc)
            images = []
            zoom = self.DEFAULT_DPI / 72
            matrix = pymupdf.Matrix(zoom, zoom)

            for page_num in range(page_count):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(self.preprocess_image(img))

            doc.close()

            if images:
                images[0].save(
                    output_path,
                    save_all=True,
                    append_images=images[1:],
                    compression='tiff_ccitt',
                    dpi=(self.DEFAULT_DPI, self.DEFAULT_DPI)
                )
                elapsed = round(time.perf_counter() - start_time, 3)
                logger.info(
                    f"PDF ({page_count} pages) converted to TIFF in {elapsed}s: {output_path}",
                    extra={
                        "event_type": "doc_convert_pdf_success",
                        "input_path": input_path,
                        "output_path": output_path,
                        "page_count": page_count,
                        "duration_sec": elapsed
                    }
                )
            else:
                logger.warning(
                    f"PDF document had 0 pages: {input_path}",
                    extra={"event_type": "doc_pdf_empty", "input_path": input_path}
                )

            return output_path
        except Exception as e:
            logger.exception(
                f"Failed to convert PDF '{input_path}' to TIFF: {e}",
                extra={"event_type": "doc_convert_pdf_error", "input_path": input_path}
            )
            raise

    def create_thumbnail(self, tiff_path: str) -> str:
        """Создание качественного превью из первой страницы TIFF"""
        thumb_path = tiff_path.replace('.tiff', '_thumb.jpg').replace('.tif', '_thumb.jpg')
        logger.debug(
            f"Creating thumbnail from TIFF: {tiff_path}",
            extra={"event_type": "doc_thumbnail_start", "tiff_path": tiff_path}
        )
        try:
            with Image.open(tiff_path) as img:
                img.seek(0)
                img.thumbnail((300, 300))
                # Переводим в RGB для безопасного сохранения бинарного изображения в JPEG
                img.convert("RGB").save(thumb_path, "JPEG", quality=85)

            logger.info(
                f"Thumbnail created: {thumb_path}",
                extra={"event_type": "doc_thumbnail_success", "thumb_path": thumb_path}
            )
            return thumb_path
        except Exception as e:
            logger.exception(
                f"Failed to create thumbnail for '{tiff_path}': {e}",
                extra={"event_type": "doc_thumbnail_error", "tiff_path": tiff_path}
            )
            raise

    def analyze_pdf_content(self, pdf_path: str) -> tuple[int, int]:
        """Анализ соотношения изображений и текста в PDF."""
        try:
            doc = pymupdf.open(pdf_path)
            total_images_size = 0
            total_page_area = 0

            for page in doc:
                img_list = page.get_images(full=True)
                for img in img_list:
                    xref = img[0]
                    img_info = doc.extract_image(xref)
                    if img_info:
                        total_images_size += len(img_info["image"])

                text = page.get_text()
                total_page_area += len(text)

            doc.close()

            logger.debug(
                f"Analyzed PDF metrics: images_bytes={total_images_size}, text_chars={total_page_area}",
                extra={
                    "event_type": "doc_analyze_pdf",
                    "pdf_path": pdf_path,
                    "images_bytes": total_images_size,
                    "text_chars": total_page_area
                }
            )
            return total_images_size, total_page_area
        except Exception as e:
            logger.error(
                f"Failed to analyze PDF content for '{pdf_path}': {e}",
                extra={"event_type": "doc_analyze_pdf_error", "pdf_path": pdf_path}
            )
            raise

    def get_page_as_stream(self, file_path: str, page_num: int) -> io.BytesIO:
        """Извлекает страницу из TIFF или PDF и отдает как JPEG-поток"""
        ext = os.path.splitext(file_path)[1].lower()
        logger.debug(
            f"Getting page stream: page={page_num}, file={file_path}",
            extra={"event_type": "doc_get_page_stream_start", "file_path": file_path, "page_num": page_num}
        )

        try:
            if ext == '.pdf':
                doc = pymupdf.open(file_path)
                if page_num >= len(doc):
                    logger.warning(
                        f"Requested page {page_num} is out of bounds for PDF with {len(doc)} pages",
                        extra={"event_type": "doc_page_out_of_bounds", "file_path": file_path, "page_num": page_num}
                    )
                    doc.close()
                    raise IndexError("Page number out of range")

                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                doc.close()
            else:
                img = Image.open(file_path)
                img.seek(page_num)

                # Если изображение бинарное (mode '1')
                if img.mode == '1':
                    # Переводим в оттенки серого
                    gray_img = img.convert("L")

                    # Подсчитываем преобладающий цвет
                    # Если 0 (черных пикселей) больше, чем 255 (белых),
                    # значит при открытии Pillow декодировал фон как черный, инвертируем его
                    hist = gray_img.histogram()
                    if hist[0] > hist[255]:
                        gray_img = ImageOps.invert(gray_img)

                    img = gray_img.convert("RGB")
                else:
                    img = img.convert("RGB")

            stream = io.BytesIO()
            img.save(stream, format="JPEG", quality=85)
            stream.seek(0)
            return stream

        except (IndexError, EOFError):
            logger.warning(
                f"Page index {page_num} out of bounds for file: {file_path}",
                extra={"event_type": "doc_page_not_found", "file_path": file_path, "page_num": page_num}
            )
            raise
        except Exception as e:
            logger.exception(
                f"Error retrieving page stream (page {page_num}) from '{file_path}': {e}",
                extra={"event_type": "doc_get_page_stream_error", "file_path": file_path, "page_num": page_num}
            )
            raise

    def get_page_count(self, file_path: str) -> int:
        """Получает количество страниц в документе."""
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == '.pdf':
                doc = pymupdf.open(file_path)
                count = len(doc)
                doc.close()
            else:
                with Image.open(file_path) as img:
                    count = getattr(img, 'n_frames', 1)

            logger.debug(
                f"Page count for file '{file_path}': {count}",
                extra={"event_type": "doc_get_page_count", "file_path": file_path, "count": count}
            )
            return count
        except Exception as e:
            logger.error(
                f"Failed to get page count for '{file_path}': {e}",
                extra={"event_type": "doc_page_count_error", "file_path": file_path}
            )
            raise


# =========================================================
# Пример использования в сервисе (RegistryService)
# =========================================================
"""
processor = DocumentProcessor()

# При получении файла:
# 1. Сохранили временно (temp_path)
# 2. tiff_path = processor.convert_file_to_tiff(temp_path, storage_dir)
# 3. thumb_path = processor.create_thumbnail(tiff_path, storage_dir)
# 4. Сохранили пути в БД
"""