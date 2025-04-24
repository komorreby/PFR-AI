import json
import csv
import os
import logging
from datetime import datetime

# <<< Импортируем актуальный список кодов ошибок
try:
    from generate_data import ALL_ERROR_CODES, calculate_actual_experience, calculate_special_experience
except ImportError:
    # Фоллбек, если запускается отдельно или generate_data еще не обновлен
    ALL_ERROR_CODES = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"] # Включаем новые
    # Определим заглушки для функций, чтобы скрипт не падал
    def calculate_actual_experience(records): return 0
    def calculate_special_experience(records): return 0
    print("Warning: Could not import from generate_data. Using fallback error codes and dummy functions.")


DATASET_DIR = "dataset"
OUTPUT_CSV = "dataset/pension_cases_features_errors.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# <<< Обновляем функцию извлечения признаков
def extract_features(case_data):
    features = {}

    # --- Персональные данные --- 
    pd = case_data.get("personal_data", {})
    try:
        birth_date = datetime.strptime(pd.get("birth_date", "01.01.1970"), '%d.%m.%Y')
        features["age"] = (datetime.now() - birth_date).days // 365.25
    except (ValueError, TypeError):
        features["age"] = 50 # Fallback age
    features["gender"] = 1 if pd.get("gender") == "male" else 0
    features["citizenship_rf"] = 1 if pd.get("citizenship") == "Российская Федерация" else 0
    features["has_name_change"] = 1 if pd.get("name_change_info") else 0
    features["dependents"] = pd.get("dependents", 0)

    # --- Тип пенсии --- 
    pension_type = case_data.get("pension_type", "unknown")
    features["is_retirement_standard"] = 1 if pension_type == "retirement_standard" else 0
    features["is_disability_social"] = 1 if pension_type == "disability_social" else 0
    # Добавить другие типы при необходимости

    # --- Стаж и Баллы (могут быть 0 для disability_social) --- 
    we = case_data.get("work_experience", {})
    features["total_years_declared"] = we.get("total_years", 0)
    # Пересчитываем фактический и специальный стаж из записей, если они есть
    records = we.get("records", [])
    features["actual_experience_calc"] = calculate_actual_experience(records)
    features["special_experience_calc"] = calculate_special_experience(records)
    features["experience_mismatch"] = abs(features["total_years_declared"] - features["actual_experience_calc"])
    features["pension_points"] = case_data.get("pension_points", 0)
    features["record_count"] = len(records)
    features["has_special_conditions_flag"] = 1 if any(r.get("special_conditions", False) for r in records) else 0

    # --- Инвалидность --- 
    disability_info = case_data.get("disability")
    features["has_disability"] = 1 if disability_info else 0
    features["disability_group_1"] = 0
    features["disability_group_2"] = 0
    features["disability_group_3"] = 0
    features["disability_group_child"] = 0
    features["disability_cert_provided"] = 0
    if disability_info:
        group = disability_info.get("group")
        if group == "1": features["disability_group_1"] = 1
        elif group == "2": features["disability_group_2"] = 1
        elif group == "3": features["disability_group_3"] = 1
        elif group == "child": features["disability_group_child"] = 1
        
        if disability_info.get("cert_number"): # Проверяем наличие номера справки
             features["disability_cert_provided"] = 1
        # Можно добавить признак: возраст инвалидности (разница между текущей датой и датой установления), но пока опустим

    # --- Льготы и Документы --- 
    features["benefit_count"] = len(case_data.get("benefits", []))
    features["document_count"] = len(case_data.get("documents", []))
    features["has_incorrect_document_flag"] = 1 if case_data.get("has_incorrect_document", False) else 0
    # Можно добавить бинарные признаки для каждого типа документа, но это сильно увеличит число фичей
    docs_set = set(case_data.get("documents", []))
    features["has_passport"] = 1 if "Паспорт" in docs_set else 0
    features["has_snils"] = 1 if "СНИЛС" in docs_set else 0
    features["has_work_book"] = 1 if "Трудовая книжка" in docs_set else 0
    features["has_disability_cert_doc"] = 1 if "Справка МСЭ" in docs_set else 0 # Отдельный флаг для документа

    return features
# -------------------------------------------------------

def convert_dataset_to_csv():
    case_files = sorted([f for f in os.listdir(DATASET_DIR) if f.startswith("case_") and f.endswith(".json")])
    if not case_files:
        logger.error(f"Не найдены файлы case_*.json в папке {DATASET_DIR}")
        return

    logger.info(f"Начинаем конвертацию {len(case_files)} дел в CSV...")

    # --- Заголовки CSV --- 
    # Получаем ключи признаков из первого файла (предполагая, что они одинаковы)
    try:
        with open(os.path.join(DATASET_DIR, case_files[0]), 'r', encoding='utf-8') as f:
            sample_case = json.load(f)
        feature_keys = list(extract_features(sample_case).keys())
    except Exception as e:
        logger.error(f"Ошибка чтения или обработки первого файла {case_files[0]}: {e}. Невозможно определить заголовки.")
        return
    
    # Добавляем целевые переменные (коды ошибок)
    # <<< Используем импортированный/фоллбек список ALL_ERROR_CODES
    headers = ["case_id"] + feature_keys + ALL_ERROR_CODES 
    # ---------------------

    try:
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()

            processed_count = 0
            error_count = 0
            for filename in case_files:
                case_id_str = filename.replace("case_", "").replace(".json", "")
                case_path = os.path.join(DATASET_DIR, filename)
                error_path = os.path.join(DATASET_DIR, "errors", f"errors_{case_id_str}.json")

                try:
                    with open(case_path, 'r', encoding='utf-8') as f:
                        case_data = json.load(f)
                    
                    # Извлекаем признаки
                    features = extract_features(case_data)
                    
                    # Загружаем ошибки
                    actual_errors = {}
                    if os.path.exists(error_path):
                        with open(error_path, 'r', encoding='utf-8') as f:
                            errors_list = json.load(f)
                            actual_errors = {e["code"] for e in errors_list} # Множество кодов ошибок
                    
                    # Формируем строку для CSV
                    row_data = {"case_id": case_id_str}
                    row_data.update(features) # Добавляем признаки
                    # Добавляем целевые переменные (ошибки)
                    for err_code in ALL_ERROR_CODES:
                        row_data[err_code] = 1 if err_code in actual_errors else 0
                        
                    writer.writerow(row_data)
                    processed_count += 1
                    if processed_count % 100 == 0:
                         logger.info(f"Обработано {processed_count}/{len(case_files)} дел...")

                except Exception as e:
                    logger.error(f"Ошибка обработки файла {filename}: {e}")
                    error_count += 1
            
            logger.info(f"Конвертация завершена. Обработано: {processed_count}, Ошибок: {error_count}.")
            logger.info(f"CSV файл сохранен как: {OUTPUT_CSV}")

    except IOError as e:
        logger.error(f"Ошибка записи в CSV файл {OUTPUT_CSV}: {e}")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка во время конвертации: {e}")

if __name__ == "__main__":
    convert_dataset_to_csv()