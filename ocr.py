import os
import io
import platform
import numpy as np
import cv2
import pytesseract
from PIL import Image
import pdfplumber
import docx

# Автоматический выбор пути Tesseract под Windows или Linux
tess_env = os.getenv("TESSERACT_CMD")
if tess_env and os.path.exists(tess_env):
    pytesseract.pytesseract.tesseract_cmd = tess_env
elif platform.system() != "Windows":
    pytesseract.pytesseract.tesseract_cmd = "tesseract"
else:
    default_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_win_path):
        pytesseract.pytesseract.tesseract_cmd = default_win_path


def preprocess_image_for_ocr(image_bytes: bytes) -> np.ndarray:
    """Улучшение читаемости: оттенки серого, удаление шумов, адаптивный порог."""
    file_bytes = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Не удалось декодировать изображение.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return binary


def extract_from_image(image_bytes: bytes) -> str:
    """Оптическое распознавание символов с изображения (русский + английский)."""
    processed_img = preprocess_image_for_ocr(image_bytes)
    custom_config = r"--oem 3 --psm 6"
    text = pytesseract.image_to_string(processed_img, lang="rus+eng", config=custom_config)
    return text.strip()


def extract_from_pdf(file_bytes: bytes) -> str:
    """Извлечение текста из PDF (цифровой слой или OCR при наличии только сканов)."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted and len(extracted.strip()) > 30:
                text_parts.append(extracted)
            else:
                page_img = page.to_image(resolution=300).original
                img_byte_arr = io.BytesIO()
                page_img.save(img_byte_arr, format="PNG")
                page_text = extract_from_image(img_byte_arr.getvalue())
                text_parts.append(page_text)
    return "\n\n".join(text_parts).strip()


def extract_from_docx(file_bytes: bytes) -> str:
    """Чтение текста из документов формата Microsoft Word."""
    doc = docx.Document(io.BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()]).strip()


def extract_from_txt(file_bytes: bytes) -> str:
    """Чтение текстовых файлов с автоопределением кодировки (UTF-8 / CP1251)."""
    try:
        return file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return file_bytes.decode("cp1251", errors="ignore").strip()


def read_uploaded_file(filename: str, file_bytes: bytes) -> str:
    """Определение формата файла и вызов соответствующего экстрактора."""
    ext = filename.lower().split(".")[-1]
    if ext == "txt":
        return extract_from_txt(file_bytes)
    elif ext == "docx":
        return extract_from_docx(file_bytes)
    elif ext == "pdf":
        return extract_from_pdf(file_bytes)
    elif ext in ["png", "jpg", "jpeg"]:
        return extract_from_image(file_bytes)
    else:
        raise ValueError(f"Неподдерживаемый формат: {ext}")