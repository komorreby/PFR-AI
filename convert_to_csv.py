import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def check_overlaps(records):
    if len(records) < 2:
        return 0
    periods = [(datetime.strptime(r["start_date"], "%d.%m.%Y"), 
                datetime.strptime(r["end_date"], "%d.%m.%Y")) for r in records]
    for i in range(len(periods)):
        for j in range(i + 1, len(periods)):
            if periods[i][0] <= periods[j][1] and periods[j][0] <= periods[i][1]:
                return 1
    return 0

def calculate_special_experience(records):
    special_years = 0
    for record in records:
        if record.get("special_conditions", False):
            start = datetime.strptime(record["start_date"], "%d.%m.%Y")
            end = datetime.strptime(record["end_date"], "%d.%m.%Y")
            special_years += (end - start).days / 365.25
    return special_years

def process_json_to_csv():
    test_files = list(Path("dataset").glob("case_*.json"))
    if not test_files:
        logger.error("В папке dataset нет файлов.")
        return

    data = []
    for test_file in test_files:
        with open(test_file, "r", encoding="utf-8") as f:
            case_data = json.load(f)

        # Читаем ожидаемые ошибки из dataset/errors
        error_file = Path(f"dataset/errors/errors_{test_file.stem[5:]}.json")
        expected_errors = []
        if error_file.exists():
            with open(error_file, "r", encoding="utf-8") as f:
                expected_errors = [e["code"] for e in json.load(f)]

        features = {
            "experience_years": case_data["work_experience"]["total_years"],
            "pension_points": case_data["pension_points"],
            "num_documents": len(case_data["documents"]),
            "has_benefits": 1 if case_data["benefits"] else 0,
            "num_job_periods": len(case_data["work_experience"]["records"]),
            "has_name_change": 1 if case_data["personal_data"]["name_change_info"] else 0,
            "special_experience_years": calculate_special_experience(case_data["work_experience"]["records"]),
            "has_overlaps": check_overlaps(case_data["work_experience"]["records"]),
            "has_incorrect_document": 1 if case_data.get("has_incorrect_document", False) else 0
        }
        for err in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008"]:
            features[err] = 1 if err in expected_errors else 0
        data.append(features)

    df = pd.DataFrame(data)
    df.to_csv("pension_cases.csv", index=False)
    logger.info("Данные сохранены в pension_cases.csv")

if __name__ == "__main__":
    process_json_to_csv()