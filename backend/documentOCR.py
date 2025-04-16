import os
import cv2
import numpy as np
import pytesseract
from PIL import Image
import easyocr
import json
import re
from pathlib import Path
from pdf2image import convert_from_path
from transliterate import translit
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class DocumentOCR:
    def __init__(self):
        self.reader = easyocr.Reader(['ru', 'en'])
        if os.name == 'nt':  # Windows
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\tesseract.exe'
            os.environ['TESSDATA_PREFIX'] = r'C:\Program Files (x86)\Tesseract-OCR\tessdata'
        os.makedirs('ocr_results', exist_ok=True)

    def preprocess_image(self, image_input):
        if isinstance(image_input, (str, Path)):
            img = cv2.imread(str(image_input))
        elif isinstance(image_input, np.ndarray):
            img = image_input
        else:
            raise ValueError(f"Неподдерживаемый тип входных данных: {type(image_input)}")
        if img is None:
            raise ValueError(f"Не удалось прочитать изображение: {image_input}")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        denoised = cv2.GaussianBlur(binary, (3, 3), 0)
        return denoised

    def recognize_with_tesseract(self, image):
        pil_image = Image.fromarray(image)
        text = pytesseract.image_to_string(pil_image, lang='rus+eng')
        return text

    def recognize_with_easyocr(self, image_path):
        results = self.reader.readtext(image_path)
        text = ' '.join([result[1] for result in results])
        return text

    def combine_results(self, tesseract_text, easyocr_text):
        keywords = ['фамилия', 'снилс', 'паспорт', 'дата рождения', 'иванов', 'стаж', 'баллы']
        tesseract_score = sum(1 for word in keywords if word in tesseract_text.lower())
        easyocr_score = sum(1 for word in keywords if word in easyocr_text.lower())
        return {
            "tesseract": tesseract_text,
            "easyocr": easyocr_text,
            "combined": easyocr_text if easyocr_score > tesseract_score else tesseract_text
        }

    def extract_document_info(self, text):
        info = {}
        # ФИО
        fio_pattern = r'^\s*([А-ЯЁ]+)\s+([А-ЯЁ]+)\s+([А-ЯЁ]+)\s*$'
        fio_match = re.search(fio_pattern, text, re.MULTILINE)
        if fio_match:
            info['last_name'] = fio_match.group(1)
            info['first_name'] = fio_match.group(2)
            info['middle_name'] = fio_match.group(3)

        # СНИЛС
        snils_pattern = r'(?:СНИЛС|страховой номер)[:\s—]*[\/]*([\d\s-]{9,14})'
        snils_match = re.search(snils_pattern, text, re.IGNORECASE)
        if snils_match:
            info['snils'] = snils_match.group(1).strip()

        # Паспорт
        passport_pattern = r'(?:паспорт|пасп\.)[\s:]*серия[\s\(при наличии\)]*(\d{4})[\s‚]*(?:номер|№)?[\s‚]*(\d{6})'
        passport_match = re.search(passport_pattern, text, re.IGNORECASE)
        if passport_match:
            info['passport'] = f"{passport_match.group(1)} {passport_match.group(2)}"

        # Дата рождения
        birth_date_pattern = r'(?:дата рождения|д\.р\.|родился)[\s:]*(\d{2}[\./-]\d{2}[\./-]\d{4})'
        birth_date_match = re.search(birth_date_pattern, text, re.IGNORECASE)
        if birth_date_match:
            info['birth_date'] = birth_date_match.group(1)

        # Стаж
        experience_pattern = r'(?:стаж|трудовой стаж|страховой стаж)[\s:]*(\d+)'
        experience_match = re.search(experience_pattern, text, re.IGNORECASE)
        if experience_match:
            info['experience_years'] = int(experience_match.group(1))

        # Периоды работы
        periods_pattern = r'(\d{2}\.\d{2}\.\d{4})\s*[—-]\s*(\d{2}\.\d{2}\.\d{4})'
        periods_matches = re.findall(periods_pattern, text)
        info['work_periods'] = [{"start_date": start, "end_date": end, "special_conditions": False} for start, end in periods_matches]

        # Пенсионные баллы
        points_pattern = r'(?:пенсионные баллы|баллы|коэффициент)[\s:]*(\d+[,\.]\d+|\d+)'
        points_match = re.search(points_pattern, text, re.IGNORECASE)
        if points_match:
            info['pension_points'] = float(points_match.group(1).replace(',', '.'))

        # Типы документов
        doc_types = []
        for doc in ['паспорт', 'снилс', 'трудовая книжка', 'справка о стаже']:
            if doc in text.lower():
                doc_types.append(doc.capitalize())
        info['documents'] = doc_types

        return info

    def format_for_classifier(self, extracted_info):
        """Форматирование данных для ErrorClassifier"""
        personal_data = {
            "full_name": f"{extracted_info.get('last_name', 'Неизвестно')} {extracted_info.get('first_name', 'Неизвестно')} {extracted_info.get('middle_name', 'Неизвестно')}",
            "snils": extracted_info.get('snils', ''),
            "birth_date": extracted_info.get('birth_date', ''),
            "gender": "unknown",
            "citizenship": "Российская Федерация",  # По умолчанию
            "name_change_info": {},  # Пока не извлекаем
            "dependents": 0
        }
        work_experience = {
            "total_years": extracted_info.get('experience_years', 0),
            "records": extracted_info.get('work_periods', [])
        }
        return {
            "personal_data": personal_data,
            "work_experience": work_experience,
            "pension_points": extracted_info.get('pension_points', 0.0),
            "benefits": [],  # Пока не извлекаем
            "documents": extracted_info.get('documents', [])
        }

    def process_document(self, file_path):
        try:
            filename = Path(file_path).stem
            safe_filename = translit(filename, 'ru', reversed=True).replace(' ', '_')
            if file_path.lower().endswith('.pdf'):
                images = convert_from_path(file_path, poppler_path=r"C:\poppler-24.08.0\Library\bin")
                preprocessed_image = self.preprocess_image(np.array(images[0]))
                temp_image_path = f'ocr_results/{safe_filename}_temp.png'
                cv2.imwrite(temp_image_path, preprocessed_image)
            else:
                preprocessed_image = self.preprocess_image(file_path)
                temp_image_path = file_path
            
            cv2.imwrite(f'ocr_results/{safe_filename}_preprocessed.png', preprocessed_image)
            tesseract_text = self.recognize_with_tesseract(preprocessed_image)
            easyocr_text = self.recognize_with_easyocr(temp_image_path)
            combined_results = self.combine_results(tesseract_text, easyocr_text)
            document_info = self.extract_document_info(combined_results["combined"])
            formatted_data = self.format_for_classifier(document_info)
            
            results = {
                "filename": file_path,
                "ocr_results": combined_results,
                "extracted_info": document_info,
                "formatted_data": formatted_data
            }
            with open(f'ocr_results/{safe_filename}_results.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            logger.info(f"Обработан документ: {file_path}")
            return results
        except Exception as e:
            logger.error(f"Ошибка при обработке документа {file_path}: {str(e)}")
            return {"error": str(e)}

if __name__ == "__main__":
    ocr = DocumentOCR()
    result = ocr.process_document('sample_document.jpg')
    print(json.dumps(result, ensure_ascii=False, indent=4))