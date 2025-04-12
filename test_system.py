import json
from error_classifier import ErrorClassifier
from documentOCR import DocumentOCR
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def test_system():
    ocr = DocumentOCR()
    classifier = ErrorClassifier()

    # Тест 1: Синтетические данные
    logger.info("Тест 1: Синтетические данные")
    with open("dataset/case_0002.json", "r", encoding="utf-8") as f:
        synthetic_data = json.load(f)
    errors = classifier.classify_errors(synthetic_data)
    notification = classifier.generate_notification("case_0002", errors)
    print(notification)
    print("-" * 50)

    # Тест 2: Реальный документ (нужен образец)
    logger.info("Тест 2: Реальный документ")
    image_path = "sample_image.png"  # Замени на путь к своему изображению
    ocr_result = ocr.process_document(image_path)
    formatted_data = ocr_result["formatted_data"]
    errors = classifier.classify_errors(formatted_data)
    notification = classifier.generate_notification("sample_document", errors)
    print(notification)
    print("-" * 50)

if __name__ == "__main__":
    test_system()