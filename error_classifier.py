import pandas as pd
import numpy as np
import joblib
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ErrorClassifier:
    def __init__(self, model_path="pension_error_model.pkl", scaler_path="scaler.pkl"):
        self.error_definitions = {
            "E001": {"description": "Недостаточный страховой стаж", "law": "ст. 8 ФЗ №400-ФЗ", "recommendation": "Подтвердите стаж документами"},
            "E002": {"description": "Недостаточное количество пенсионных баллов", "law": "ст. 8 ФЗ №400-ФЗ", "recommendation": "Продолжите трудовую деятельность"},
            "E003": {"description": "Противоречия в датах трудового стажа", "law": "Постановление №1015", "recommendation": "Предоставьте корректные документы"},
            "E004": {"description": "Отсутствуют обязательные документы", "law": "Приказ №958н", "recommendation": "Предоставьте полный комплект документов"},
            "E005": {"description": "Некорректно оформленный документ", "law": "Приказ №14н", "recommendation": "Исправьте документ"},
            "E006": {"description": "Несоответствие паспортных данных", "law": "Приказ №14н", "recommendation": "Предоставьте действующий паспорт"},
            "E007": {"description": "Не подтверждены особые условия труда", "law": "ст. 30 ФЗ №400-ФЗ", "recommendation": "Подтвердите условия труда"},
            "E008": {"description": "Недостаточный специальный стаж", "law": "ст. 30, 31 ФЗ №400-ФЗ", "recommendation": "Подтвердите специальный стаж"}
        }
        try:
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            logger.info("Модель и масштатификатор успешно загружены")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели или масштабатора: {e}")
            raise

    def calculate_special_experience(self, records):
        special_days = 0
        for record in records:
            if record.get("special_conditions", False):
                start = datetime.strptime(record["start_date"], "%d.%m.%Y")
                end = datetime.strptime(record["end_date"], "%d.%m.%Y")
                special_days += (end - start).days
        return special_days / 365.25

    def check_overlaps(self, records):
        periods = [(datetime.strptime(r["start_date"], "%d.%m.%Y"), 
                    datetime.strptime(r["end_date"], "%d.%m.%Y")) for r in records]
        periods.sort()
        for i in range(1, len(periods)):
            if periods[i][0] <= periods[i-1][1]:
                return 1
        return 0

    def preprocess_case_data(self, case_data):
        try: 
            features = {
                "experience_years": case_data["work_experience"]["total_years"],
                "pension_points": case_data["pension_points"],
                "num_documents": len(case_data["documents"]),
                "has_benefits": 1 if case_data["benefits"] else 0,
                "num_job_periods": len(case_data["work_experience"]["records"]),
                "has_name_change": 1 if case_data["personal_data"]["name_change_info"] else 0,
                "special_experience_years": self.calculate_special_experience(case_data["work_experience"]["records"]),
                "has_overlaps": self.check_overlaps(case_data["work_experience"]["records"]),
                "has_incorrect_document": 1 if case_data.get("has_incorrect_document", False) else 0
            }
            df = pd.DataFrame([features])
            scaled_features = self.scaler.transform(df)
            return scaled_features
        except Exception as e:
            logger.error(f"Ошибка предобработки данных: {e}")
            raise

    def classify_errors(self, case_data):
        start_time = time.time()
        logger.info("Классификация ошибок начата")
        
        try:
            features = self.preprocess_case_data(case_data)
            predictions = self.model.predict(features)[0]
            error_codes = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008"]
            errors = [code for code, pred in zip(error_codes, predictions) if pred == 1]
            
            # Явная проверка E004 для точности
            required_docs = {"Паспорт", "СНИЛС", "Трудовая книжка"}
            if not required_docs.issubset(set(case_data["documents"])) and "E004" not in errors:
                errors.append("E004")
            
            elapsed_time = time.time() - start_time
            logger.info(f"Классификация завершена за {elapsed_time:.2f} сек. Ошибки: {errors}")
            if elapsed_time > 3:
                logger.warning(f"Время классификации превышает 3 сек: {elapsed_time:.2f} сек")
            
            return errors
        except Exception as e:
            logger.error(f"Ошибка классификации: {e}")
            return []

    def generate_notification(self, case_id, errors):
        if not errors:
            return f"Дело {case_id}: Ошибок не выявлено."
        
        notification = f"Дело {case_id}: Выявлены следующие ошибки:\n"
        for error_code in errors:
            error_info = self.error_definitions.get(error_code, {"description": "Неизвестная ошибка", "law": "", "recommendation": ""})
            notification += (f"- {error_code}: {error_info['description']}\n"
                            f"  Закон: {error_info['law']}\n"
                            f"  Рекомендация: {error_info['recommendation']}\n")
        return notification

if __name__ == "__main__":
    classifier = ErrorClassifier()
    
    case_data = {
        "personal_data": {
            "full_name": "Иванов Иван Иванович",
            "birth_date": "12.03.1960",
            "snils": "123-456-789 00",
            "gender": "male",
            "citizenship": "Российская Федерация",
            "name_change_info": {"old_full_name": "Петров Петр Петрович", "date_changed": "15.05.2023"},
            "dependents": 1
        },
        "work_experience": {
            "total_years": 10,
            "records": [
                {"organization": "ООО Ромашка", "start_date": "01.01.2000", "end_date": "01.01.2010", "position": "Инженер", "special_conditions": True},
                {"organization": "АО Лютик", "start_date": "01.02.2005", "end_date": "01.02.2015", "position": "Менеджер", "special_conditions": False}
            ]
        },
        "pension_points": 25,
        "benefits": ["Ветеран труда"],
        "documents": ["Паспорт", "СНИЛС"]
    }
    
    errors = classifier.classify_errors(case_data)
    notification = classifier.generate_notification("case_0001", errors)
    print(notification)