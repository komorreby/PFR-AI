from datetime import datetime
import random
import json
import os
import time
import logging
from faker import Faker

fake = Faker('ru_RU')

TOTAL_CASES = 500

ERROR_CLASSIFIER = {
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

ALL_ERROR_CODES = sorted(ERROR_CLASSIFIER.keys())

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def generate_personal_data():
    try:
        gender = random.choice(['male', 'female'])
        full_name = fake.name_male() if gender == 'male' else fake.name_female()
        birth_date = fake.date_of_birth(minimum_age=45, maximum_age=65).strftime('%d.%m.%Y')
        snils = fake.unique.numerify(text='###-###-### ##')
        citizenship = random.choice(["Российская Федерация", "Украина", "Беларусь"])
        has_name_change = random.choice([True, False])
        name_change_info = {"old_full_name": fake.name(), "date_changed": fake.date_this_decade().strftime('%d.%m.%Y')} if has_name_change else {}
        dependents = random.randint(0, 3)
        return {
            "full_name": full_name,
            "birth_date": birth_date,
            "snils": snils,
            "gender": gender,
            "citizenship": citizenship,
            "name_change_info": name_change_info,
            "dependents": dependents
        }
    except Exception as e:
        logger.error(f"Ошибка генерации персональных данных: {e}")
        return None

def generate_work_experience(birth_date, pension_type):
    if pension_type != 'retirement_standard':
        return {"total_years": 0, "records": []}

    total_years = random.randint(5, 40)
    records = []
    for _ in range(random.randint(1, 5)):
        special_conditions = random.random() < 0.3
        start_date = fake.date_between(start_date='-40y', end_date='-5y').strftime('%d.%m.%Y')
        end_date = fake.date_between(start_date='-40y', end_date='today').strftime('%d.%m.%Y')
        start_dt = datetime.strptime(start_date, '%d.%m.%Y')
        end_dt = datetime.strptime(end_date, '%d.%m.%Y')
        if start_dt >= end_dt:
            start_date, end_date = end_date, start_date
        records.append({
            "organization": fake.company(),
            "start_date": start_date,
            "end_date": end_date,
            "position": fake.job(),
            "special_conditions": special_conditions
        })
    return {"total_years": total_years, "records": records}

def generate_pension_points(total_years, pension_type):
    if pension_type != 'retirement_standard':
        return 0

    base_points = total_years * random.uniform(0.8, 2.0)
    points = max(0, base_points + random.uniform(-10, 10))
    return round(points, 2)

def generate_benefits():
    benefits = ["Ветеран труда", "Многодетная мать", "Инвалид 2 группы"]
    return random.sample(benefits, k=random.randint(0, len(benefits)))

def generate_documents(pension_type):
    base_docs = {"Паспорт", "СНИЛС"}
    required_docs = set(base_docs)
    all_possible_docs = list(base_docs) + ["Трудовая книжка", "Справка о стаже", "Справка МСЭ", "Военный билет"]

    if pension_type == 'retirement_standard':
        required_docs.add("Трудовая книжка")
    elif pension_type == 'disability_social':
        pass

    present_docs = list(all_possible_docs)
    if random.random() < 0.2:
        missing_doc = random.choice(list(required_docs))
        if missing_doc in present_docs:
            present_docs.remove(missing_doc)
        logger.debug(f"Имитация E004: Удален документ '{missing_doc}'")

    random.shuffle(present_docs)
    return present_docs

def generate_disability_info(pension_type):
    if pension_type != 'disability_social':
        return None

    if random.random() < 0.3:
        logger.debug("Имитация E009: Данные об инвалидности не предоставлены")
        return None

    group = random.choice(["1", "2", "3", "child"])
    date = fake.date_between(start_date='-5y', end_date='today').strftime('%Y-%m-%d')
    cert_number = fake.numerify(text='##########') if random.random() < 0.8 else None

    return {
        "group": group,
        "date": date,
        "cert_number": cert_number
    }

def mask_personal_data(personal_data):
    if not personal_data:
        return None
    masked = personal_data.copy()
    masked["full_name"] = "ФИО скрыто"
    masked["snils"] = "***-***-*** **"
    masked["birth_date"] = "**.**.****"
    masked["citizenship"] = "Гражданство скрыто"
    if masked["name_change_info"]:
        masked["name_change_info"]["old_full_name"] = "ФИО скрыто"
    masked["dependents"] = "Данные скрыты"
    return masked

def calculate_actual_experience(records):
    periods = [(datetime.strptime(r["start_date"], "%d.%m.%Y"), 
                datetime.strptime(r["end_date"], "%d.%m.%Y")) for r in records]
    periods.sort()
    total_days = 0
    if not periods:
        return 0
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

def calculate_special_experience(records):
    special_days = 0
    for record in records:
        if record["special_conditions"]:
            start = datetime.strptime(record["start_date"], "%d.%m.%Y")
            end = datetime.strptime(record["end_date"], "%d.%m.%Y")
            special_days += (end - start).days
    return special_days / 365.25

def calculate_overlap_percentage(records):
    periods = [(datetime.strptime(r["start_date"], "%d.%m.%Y"), 
                datetime.strptime(r["end_date"], "%d.%m.%Y")) for r in records]
    periods.sort()
    overlap_days = 0
    for i in range(1, len(periods)):
        if periods[i][0] <= periods[i-1][1]:
            overlap_end = min(periods[i][1], periods[i-1][1])
            overlap_start = periods[i][0]
            overlap_days += (overlap_end - overlap_start).days
    total_days = sum((p[1] - p[0]).days for p in periods)
    return overlap_days / total_days if total_days > 0 else 0

def generate_case(case_id):
    pension_type = random.choice(['retirement_standard', 'disability_social'])
    logger.info(f"Генерация дела {case_id} (Тип: {pension_type})")

    personal_data = generate_personal_data()
    if not personal_data:
        return None
    
    work_experience = generate_work_experience(personal_data["birth_date"], pension_type)
    pension_points = generate_pension_points(work_experience["total_years"], pension_type)
    disability_info = generate_disability_info(pension_type)
    benefits = generate_benefits()
    documents = generate_documents(pension_type)
    has_incorrect_document = random.random() < 0.15

    case_data = {
        "pension_type": pension_type,
        "personal_data": personal_data,
        "work_experience": work_experience,
        "pension_points": pension_points,
        "disability": disability_info,
        "benefits": benefits,
        "documents": documents,
        "has_incorrect_document": has_incorrect_document
    }

    errors = []

    required_docs_common = {"Паспорт", "СНИЛС"}
    if not required_docs_common.issubset(set(documents)):
        if "E004" not in [e["code"] for e in errors]: errors.append({"code": "E004", **ERROR_CLASSIFIER["E004"]})
    if has_incorrect_document:
        if "E005" not in [e["code"] for e in errors]: errors.append({"code": "E005", **ERROR_CLASSIFIER["E005"]})
    if personal_data["name_change_info"] and random.random() < 0.2:
        if "E006" not in [e["code"] for e in errors]: errors.append({"code": "E006", **ERROR_CLASSIFIER["E006"]})

    if pension_type == 'retirement_standard':
        if work_experience["total_years"] < 15:
            if "E001" not in [e["code"] for e in errors]: errors.append({"code": "E001", **ERROR_CLASSIFIER["E001"]})
        if pension_points < 30:
            if "E002" not in [e["code"] for e in errors]: errors.append({"code": "E002", **ERROR_CLASSIFIER["E002"]})

        actual_years = calculate_actual_experience(work_experience["records"])
        has_overlap = False
        has_mismatch = abs(work_experience["total_years"] - actual_years) / max(1, work_experience["total_years"], actual_years) > 0.2 if max(1, work_experience["total_years"], actual_years) > 0 else False
        if len(work_experience["records"]) > 1:
            periods = [(datetime.strptime(r["start_date"], "%d.%m.%Y"), 
                        datetime.strptime(r["end_date"], "%d.%m.%Y")) for r in work_experience["records"]]
            for i in range(len(periods)):
                for j in range(i + 1, len(periods)):
                    if periods[i][0] <= periods[j][1] and periods[j][0] <= periods[i][1]:
                        has_overlap = True
                        break
                if has_overlap:
                    break
        if has_overlap or has_mismatch:
            error_description = "Противоречия в датах трудового стажа"
            if has_overlap and has_mismatch:
                error_description += " (пересечение периодов и несоответствие общему стажу)"
            elif has_overlap:
                error_description += " (пересечение периодов)"
            elif has_mismatch:
                error_description += " (несоответствие общему стажу)"
            if "E003" not in [e["code"] for e in errors]: errors.append({"code": "E003", "description": error_description, **{k:v for k,v in ERROR_CLASSIFIER["E003"].items() if k != 'description'}})

        required_docs_retirement = {"Трудовая книжка"}
        if not required_docs_retirement.issubset(set(documents)):
            if "E004" not in [e["code"] for e in errors]: errors.append({"code": "E004", **ERROR_CLASSIFIER["E004"]})

        special_years = calculate_special_experience(work_experience["records"])
        has_special_conditions_flag = any(r["special_conditions"] for r in work_experience["records"])
        if has_special_conditions_flag and random.random() < 0.6:
            if "E007" not in [e["code"] for e in errors]: errors.append({"code": "E007", **ERROR_CLASSIFIER["E007"]})
        if has_special_conditions_flag and special_years < 15 and random.random() < 0.5:
            if "E008" not in [e["code"] for e in errors]: errors.append({"code": "E008", **ERROR_CLASSIFIER["E008"]})

    elif pension_type == 'disability_social':
        if not disability_info:
            if "E009" not in [e["code"] for e in errors]: errors.append({"code": "E009", **ERROR_CLASSIFIER["E009"]})
        if "Справка МСЭ" not in documents and random.random() < 0.4:
            if "E010" not in [e["code"] for e in errors]: errors.append({"code": "E010", **ERROR_CLASSIFIER["E010"]})

    errors.sort(key=lambda x: x["code"])

    return {"case_data": case_data, "errors": errors}

def generate_dataset(total_cases):
    start_time = time.time()
    os.makedirs("dataset", exist_ok=True)
    os.makedirs("dataset/masked", exist_ok=True)
    os.makedirs("dataset/errors", exist_ok=True)
    os.makedirs("dataset/documents", exist_ok=True)

    dataset = []
    logger.info(f"Генерация {total_cases} синтетических дел")
    for case_id in range(1, total_cases + 1):
        result = generate_case(case_id)
        if result:
            case_file = f"dataset/case_{case_id:04d}.json"
            error_file = f"dataset/errors/errors_{case_id:04d}.json"
            with open(case_file, "w", encoding="utf-8") as f:
                json.dump(result["case_data"], f, ensure_ascii=False, indent=4)
            with open(error_file, "w", encoding="utf-8") as f:
                json.dump(result["errors"], f, ensure_ascii=False, indent=4)

    elapsed_time = time.time() - start_time
    logger.info(f"Набор данных сгенерирован за {elapsed_time:.2f} сек.")

if __name__ == "__main__":
    generate_dataset(TOTAL_CASES)