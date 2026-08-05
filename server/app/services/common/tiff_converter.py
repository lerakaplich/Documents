import io
import os
import fitz as pymupdf
from PIL import Image, ImageFilter, ImageEnhance


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
        return ext.lower() in self.ALLOWED_EXTENSIONS

    def get_file_type(self, file_path: str) -> str:
        """Возвращает категорию файла для выбора алгоритма обработки."""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if ext == '.pdf':
            return 'pdf'
        elif ext in {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}:
            return 'image'
        else:
            raise ValueError(f"Формат {ext} не поддерживается")

    def preprocess_image(self, img: Image.Image) -> Image.Image:
        """Ваш метод предобработки (полная версия)"""
        if img.mode != 'L':
            img = img.convert('L')

        # Увеличение контраста
        if self.CONTRAST_FACTOR != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(self.CONTRAST_FACTOR)

        # Резкость
        if self.SHARPEN_RADIUS > 0:
            img = img.filter(ImageFilter.UnsharpMask(radius=self.SHARPEN_RADIUS, percent=100, threshold=5))

        # Бинаризация
        if self.ADAPTIVE_THRESHOLD:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)
            img = img.point(lambda x: 255 if x > self.THRESHOLD else 0, '1')
        else:
            img = img.point(lambda x: 255 if x > self.THRESHOLD else 0, '1')

        if self.BLACK_ONLY:
            img = img.convert('1')
        return img

    def convert_image_to_tiff(self, input_path: str, output_path: str):
        """Конвертирует изображение в TIFF (бинарный/CCITT)"""
        with Image.open(input_path) as img:
            processed_img = self.preprocess_image(img.convert("RGB"))
            processed_img.save(
                output_path,
                compression='tiff_ccitt',
                dpi=(self.DEFAULT_DPI, self.DEFAULT_DPI)
            )
        return output_path

    def convert_pdf_to_tiff(self, input_path: str, output_path: str):
        """Конвертирует PDF в TIFF и сохраняет по указанному пути."""
        doc = pymupdf.open(input_path)
        images = []
        zoom = self.DEFAULT_DPI / 72
        matrix = pymupdf.Matrix(zoom, zoom)

        for page in doc:
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
        return output_path

    def create_thumbnail(self, tiff_path: str):
        """Создание качественного превью из первой страницы TIFF"""
        with Image.open(tiff_path) as img:
            thumb_path = tiff_path.replace('.tiff', '_thumb.jpg')
            # Важно: берем первую страницу многостраничного TIFF
            img.seek(0)
            img.thumbnail((300, 300))
            img.save(thumb_path, "JPEG", quality=85)
            return thumb_path

    def analyze_pdf_content(self, pdf_path):
        doc = pymupdf.open(pdf_path)
        total_images_size = 0
        total_page_area = 0

        for page in doc:
            # Считаем размер картинок на странице
            img_list = page.get_images(full=True)
            for img in img_list:
                xref = img[0]
                # Получаем размер картинки в байтах внутри PDF
                img_info = doc.extract_image(xref)
                total_images_size += len(img_info["image"])

            # Считаем "площадь" текста
            text = page.get_text()
            total_page_area += len(text)

        doc.close()

        # Если картинок много, а текста мало — это 100% скан
        # Возвращаем процент "картиночности"
        return total_images_size, total_page_area

    def get_page_as_stream(self, file_path: str, page_num: int) -> io.BytesIO:
        """Извлекает страницу из TIFF или PDF и отдает как JPEG-поток"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            doc = pymupdf.open(file_path)
            page = doc.load_page(page_num)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))  # DPI=144
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
        else:  # Предполагаем TIFF
            img = Image.open(file_path)
            img.seek(page_num)
            img = img.convert("RGB")

        stream = io.BytesIO()
        img.save(stream, format="JPEG", quality=80)
        stream.seek(0)
        return stream

    def get_page_count(self, file_path: str) -> int:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            doc = pymupdf.open(file_path)
            count = len(doc)
            doc.close()
            return count
        else:
            img = Image.open(file_path)
            return img.n_frames


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