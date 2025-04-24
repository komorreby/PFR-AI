import joblib
import pandas as pd
import os
import logging
from datetime import datetime # <<< Добавляем импорт

logger = logging.getLogger(__name__)

# <<< Копируем функции из convert_to_csv.py для самодостаточности >>>
# (В реальном проекте лучше вынести в общий модуль utils)

# --- Вспомогательные функции --- 
def calculate_actual_experience(records):
    if not records: return 0
    try:
        periods = [(datetime.strptime(r["start_date"], "%d.%m.%Y"), 
                    datetime.strptime(r["end_date"], "%d.%m.%Y")) for r in records]
        periods.sort()
        total_days = 0
        if not periods: return 0
        current_start = periods[0][0]
        current_end = periods[0][1]
        for start, end in periods[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                total_days += (current_end - current_start).days
                current_start = start
                current_end = end
        total_days += (current_end - current_start).days
        return total_days / 365.25
    except (ValueError, TypeError, KeyError) as e:
        logger.warning(f"Ошибка расчета actual_experience: {e}. Возвращаем 0.")
        return 0

def calculate_special_experience(records):
    if not records: return 0
    special_days = 0
    try:
        for record in records:
            if record.get("special_conditions", False):
                start = datetime.strptime(record["start_date"], "%d.%m.%Y")
                end = datetime.strptime(record["end_date"], "%d.%m.%Y")
                special_days += (end - start).days
        return special_days / 365.25
    except (ValueError, TypeError, KeyError) as e:
        logger.warning(f"Ошибка расчета special_experience: {e}. Возвращаем 0.")
        return 0

# --- Функция извлечения признаков (адаптированная) --- 
def extract_features(case_data):
    if not isinstance(case_data, dict): 
        logger.error("extract_features ожидает словарь, получен другой тип.")
        return None
    features = {}

    # Персональные данные
    pd_data = case_data.get("personal_data", {})
    try:
        # Используем ISO формат даты рождения, как в Pydantic модели
        birth_date_str = pd_data.get("birth_date")
        if birth_date_str:
             birth_date = datetime.fromisoformat(birth_date_str.split('T')[0]) # Убираем время, если есть
             features["age"] = (datetime.now() - birth_date).days // 365.25
        else:
             features["age"] = 50 # Fallback
    except (ValueError, TypeError) as e:
        logger.warning(f"Ошибка парсинга birth_date '{birth_date_str}': {e}. Используем fallback age.")
        features["age"] = 50
        
    features["gender"] = 1 if pd_data.get("gender") == "male" else 0
    features["citizenship_rf"] = 1 if pd_data.get("citizenship") == "Российская Федерация" else 0
    features["has_name_change"] = 1 if pd_data.get("name_change_info") else 0
    features["dependents"] = pd_data.get("dependents", 0)

    # Тип пенсии
    pension_type = case_data.get("pension_type", "unknown")
    features["is_retirement_standard"] = 1 if pension_type == "retirement_standard" else 0
    features["is_disability_social"] = 1 if pension_type == "disability_social" else 0

    # Стаж и Баллы
    we_data = case_data.get("work_experience", {})
    features["total_years_declared"] = we_data.get("total_years", 0)
    records = we_data.get("records", [])
    # ВАЖНО: Передаем записи в функции расчета
    features["actual_experience_calc"] = calculate_actual_experience(records) 
    features["special_experience_calc"] = calculate_special_experience(records)
    features["experience_mismatch"] = abs(features["total_years_declared"] - features["actual_experience_calc"])
    features["pension_points"] = case_data.get("pension_points", 0)
    features["record_count"] = len(records)
    features["has_special_conditions_flag"] = 1 if any(r.get("special_conditions", False) for r in records) else 0

    # Инвалидность
    disability_data = case_data.get("disability") # disability_info -> disability_data
    features["has_disability"] = 1 if disability_data else 0
    features["disability_group_1"] = 0
    features["disability_group_2"] = 0
    features["disability_group_3"] = 0
    features["disability_group_child"] = 0
    features["disability_cert_provided"] = 0 # Наличие номера справки
    if disability_data:
        group = disability_data.get("group")
        if group == "1": features["disability_group_1"] = 1
        elif group == "2": features["disability_group_2"] = 1
        elif group == "3": features["disability_group_3"] = 1
        elif group == "child": features["disability_group_child"] = 1
        
        if disability_data.get("cert_number"):
             features["disability_cert_provided"] = 1

    # Льготы и Документы
    features["benefit_count"] = len(case_data.get("benefits", []))
    features["document_count"] = len(case_data.get("documents", []))
    features["has_incorrect_document_flag"] = 1 if case_data.get("has_incorrect_document", False) else 0
    docs_set = set(case_data.get("documents", []))
    features["has_passport"] = 1 if "Паспорт" in docs_set else 0
    features["has_snils"] = 1 if "СНИЛС" in docs_set else 0
    features["has_work_book"] = 1 if "Трудовая книжка" in docs_set else 0
    features["has_disability_cert_doc"] = 1 if "Справка МСЭ" in docs_set else 0

    return features
# <<< Конец скопированных/адаптированных функций >>>


class ErrorClassifier:
    def __init__(self, model_path="models/error_classifier_model.joblib"):
        self.model_path = model_path
        self.model = None # <<< Инициализируем как None, НЕ загружаем сразу
        # <<< Обновляем словарь ошибок внутри класса >>>
        self.ERROR_CLASSIFIER = {
            "E001": {"description": "Недостаточный страховой стаж (для страх. пенсии)", "law": "ст. 8 ФЗ №400-ФЗ", "recommendation": "Подтвердите стаж документами"},
            "E002": {"description": "Недостаточное количество пенсионных баллов (для страх. пенсии)", "law": "ст. 8 ФЗ №400-ФЗ", "recommendation": "Продолжите трудовую деятельность"},
            "E003": {"description": "Противоречия в датах трудового стажа", "law": "Постановление №1015", "recommendation": "Предоставьте корректные документы"},
            "E004": {"description": "Отсутствуют обязательные документы (общие)", "law": "Приказ №958н", "recommendation": "Предоставьте полный комплект документов"},
            "E005": {"description": "Некорректно оформленный документ", "law": "Приказ №14н", "recommendation": "Исправьте документ"},
            "E006": {"description": "Несоответствие паспортных данных", "law": "Приказ №14н", "recommendation": "Предоставьте действующий паспорт"},
            "E007": {"description": "Не подтверждены особые условия труда", "law": "ст. 30 ФЗ №400-ФЗ", "recommendation": "Подтвердите условия труда"},
            "E008": {"description": "Недостаточный специальный стаж", "law": "ст. 30, 31 ФЗ №400-ФЗ", "recommendation": "Подтвердите специальный стаж"},
            "E009": {"description": "Не предоставлены основные сведения об инвалидности (группа, дата)", "law": "ФЗ-166", "recommendation": "Укажите группу и дату установления инвалидности"},
            "E010": {"description": "Отсутствует обязательный документ: Справка МСЭ", "law": "ФЗ-166 / Приказ X", "recommendation": "Предоставьте скан/копию справки МСЭ"},
        }
        # -----------------------------------------------
        self.target_columns = sorted(self.ERROR_CLASSIFIER.keys()) 
        # --- Определяем колонки признаков --- 
        dummy_case_data = {
             "personal_data": {},
             "work_experience": { "records": [] },
        }
        try:
             dummy_features = extract_features(dummy_case_data)
             if dummy_features is None: raise ValueError("Dummy feature extraction failed")
             self.feature_columns = list(dummy_features.keys()) 
             # Убрали логгирование отсюда, т.к. оно не критично для инициализации
        except Exception as e:
             # Логгирование ошибки определения колонок
             logger.error(f"Не удалось определить feature_columns из extract_features в __init__: {e}. Используется ПРЕДУСТАНОВЛЕННЫЙ список.")
             self.feature_columns = [
                'age', 'gender', 'citizenship_rf', 'has_name_change', 'dependents',
                'is_retirement_standard', 'is_disability_social', 
                'total_years_declared', 'actual_experience_calc', 'special_experience_calc',
                'experience_mismatch', 'pension_points', 'record_count', 'has_special_conditions_flag',
                'has_disability', 'disability_group_1', 'disability_group_2', 'disability_group_3',
                'disability_group_child', 'disability_cert_provided', 'benefit_count', 
                'document_count', 'has_incorrect_document_flag', 'has_passport', 'has_snils',
                'has_work_book', 'has_disability_cert_doc'
            ]
        # <<< Убираем вызов self._load_model() отсюда >>>
        # self._load_model()

    def _load_model(self):
        """Загружает модель. Вызывается из classify_errors при необходимости."""
        # Добавляем проверку, чтобы не загружать повторно
        if self.model is not None:
             return
             
        logger.info(f"Попытка загрузки модели из {self.model_path}...") # Лог перед загрузкой
        if not os.path.exists(self.model_path):
            logger.error(f"Файл модели не найден по пути: {self.model_path}")
            # Не выбрасываем исключение здесь, classify_errors обработает self.model == None
            return 
        try:
            self.model = joblib.load(self.model_path)
            logger.info(f"Модель классификатора ошибок успешно загружена из {self.model_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели из {self.model_path}: {e}")
            self.model = None # Убедимся, что модель None при ошибке
            # Не выбрасываем исключение здесь, classify_errors обработает

    def classify_errors(self, case_data):
        """ 
        Принимает на вход словарь с данными дела (формат как в CaseDataInput Pydantic).
        Возвращает список словарей с ошибками.
        """
        # <<< Ленивая загрузка модели >>>
        if self.model is None:
            self._load_model()
            # Если модель все еще не загрузилась (ошибка или не найдена)
            if self.model is None:
                 logger.error("Модель не загружена (возможно, не найдена или ошибка загрузки). Классификация невозможна.")
                 return [] 
        # ------------------------------
        
        try:
            features = extract_features(case_data)
            if features is None: 
                 logger.error("Не удалось извлечь признаки из case_data.")
                 return []
            # Создаем DataFrame с ОДНОЙ строкой
            # Убедимся, что колонки в том же порядке, что и self.feature_columns
            features_df = pd.DataFrame([features], columns=self.feature_columns)
            
            # Предсказание (модель должна возвращать массив numpy [n_samples, n_targets])
            predictions = self.model.predict(features_df)
            
            detected_errors = []
            # predictions[0] - это предсказания для нашей единственной строки
            # Итерируемся по предсказанным значениям и self.target_columns
            # <<< Используем обновленный self.target_columns >>>
            for i, error_code in enumerate(self.target_columns):
                if predictions[0, i] == 1: # Если модель предсказала ошибку (значение 1)
                    error_info = self.ERROR_CLASSIFIER.get(error_code)
                    if error_info:
                        detected_errors.append({
                            "code": error_code,
                            "description": error_info["description"],
                            "law": error_info["law"],
                            "recommendation": error_info["recommendation"]
                        })
                    else:
                        logger.warning(f"Описание для предсказанного кода ошибки '{error_code}' не найдено в ERROR_CLASSIFIER.")
                        detected_errors.append({
                            "code": error_code,
                            "description": "Описание ошибки не найдено",
                            "law": "N/A",
                            "recommendation": "N/A"
                        })
            # ------------------------------------------
            return detected_errors
            
        except KeyError as e:
            logger.error(f"Ошибка доступа к ключу при извлечении признаков или предсказании: {e}. Убедитесь, что входные данные case_data имеют ожидаемую структуру.")
            return []
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при классификации ошибок: {e}")
            import traceback
            traceback.print_exc() # Печатаем traceback для дебага
            return []

# Пример использования (если нужно протестировать отдельно)
if __name__ == '__main__':
    logger.info("Тестирование ErrorClassifier...")
    
    # --- Создаем тестовые данные --- 
    # Пример дела с ошибками для пенсии по старости
    test_case_retirement = {
        "pension_type": "retirement_standard",
        "personal_data": {
            "full_name": "Иванов Иван Иванович", 
            "birth_date": "1960-05-15T00:00:00", # Используем ISO формат
            "gender": "male", 
            "citizenship": "Российская Федерация", 
            "name_change_info": None, 
            "dependents": 1
            },
        "work_experience": {
            "total_years": 12, # < 15 лет -> E001
            "records": [
                {"organization": "ООО Ромашка", "start_date": "01.01.2000", "end_date": "31.12.2011", "position": "Инженер", "special_conditions": False}
            ]
            },
        "pension_points": 25.5, # < 30 -> E002
        "disability": None,
        "benefits": [],
        "documents": ["Паспорт", "СНИЛС"], # Нет трудовой -> E004
        "has_incorrect_document": False
    }
    
    # Пример дела с ошибками для социальной пенсии
    test_case_disability = {
        "pension_type": "disability_social",
        "personal_data": {
            "full_name": "Петрова Мария Сергеевна", 
            "birth_date": "1985-11-20T00:00:00", 
            "gender": "female", 
            "citizenship": "Российская Федерация", 
            "name_change_info": None, 
            "dependents": 0
            },
        "work_experience": {"total_years": 0, "records": []},
        "pension_points": 0,
        "disability": None, # Нет данных об инвалидности -> E009
        "benefits": ["Инвалид"], # Это поле не используется для E009/E010
        "documents": ["Паспорт", "СНИЛС"], # Нет справки МСЭ -> E010 (если модель научится это видеть)
        "has_incorrect_document": False
    }
    
    # --- Инициализация и классификация ---
    try:
        classifier = ErrorClassifier(model_path="models/error_classifier_model.joblib") # Укажите правильный путь!
        
        print("\n--- Тест 1: Пенсия по старости (ожидаются E001, E002, E004) ---")
        errors1 = classifier.classify_errors(test_case_retirement)
        print("Обнаруженные ошибки:")
        for err in errors1:
            print(f"  - {err['code']}: {err['description']}")
        
        print("\n--- Тест 2: Социальная пенсия (ожидаются E009, возможно E010) ---")
        errors2 = classifier.classify_errors(test_case_disability)
        print("Обнаруженные ошибки:")
        for err in errors2:
            print(f"  - {err['code']}: {err['description']}")
            
    except FileNotFoundError as e:
        logger.error(f"Тестирование прервано: {e}")
    except Exception as e:
        logger.error(f"Ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc() 