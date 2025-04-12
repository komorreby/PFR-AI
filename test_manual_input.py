import json
from error_classifier import ErrorClassifier
import logging
from pathlib import Path
from sklearn.metrics import precision_score, recall_score, f1_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def evaluate_metrics(expected_errors, predicted_errors):
    all_errors = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008"]
    y_true = [1 if err in expected_errors else 0 for err in all_errors]
    y_pred = [1 if err in predicted_errors else 0 for err in all_errors]
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    return precision, recall, f1

def test_manual_input():
    classifier = ErrorClassifier()
    test_files = list(Path("manual_input").glob("case_*.json"))

    if not test_files:
        logger.warning("В папке manual_input нет сохранённых дел.")
        print("В папке manual_input нет сохранённых дел. Пожалуйста, введите данные через веб-интерфейс.")
        return

    # Загрузка ожидаемых ошибок
    try:
        with open("expected_errors.json", "r", encoding="utf-8") as f:
            expected_errors_dict = json.load(f)
    except FileNotFoundError:
        logger.error("Файл expected_errors.json не найден.")
        print("Файл expected_errors.json не найден. Пожалуйста, создайте его с ожидаемыми ошибками.")
        return

    precisions, recalls, f1s = [], [], []
    for test_file in test_files:
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                case_data = json.load(f)
            case_id = test_file.stem
            errors = classifier.classify_errors(case_data)
            notification = classifier.generate_notification(case_id, errors)
            print(notification)

            # Оценка метрик
            expected = expected_errors_dict.get(case_id, [])
            if not expected:
                print(f"Ожидаемые ошибки для {case_id} не указаны в expected_errors.json.")
            else:
                precision, recall, f1 = evaluate_metrics(expected, errors)
                precisions.append(precision)
                recalls.append(recall)
                f1s.append(f1)
                print(f"Метрики для {case_id}: Precision={precision:.2f}, Recall={recall:.2f}, F1={f1:.2f}")
            print("-" * 50)
        except Exception as e:
            logger.error(f"Ошибка при обработке файла {test_file}: {str(e)}")
            print(f"Ошибка при обработке файла {test_file}: {str(e)}")

    # Средние метрики
    if precisions:
        print(f"\nСредние метрики по всем делам:")
        print(f"Precision: {sum(precisions)/len(precisions):.2f}")
        print(f"Recall: {sum(recalls)/len(recalls):.2f}")
        print(f"F1: {sum(f1s)/len(f1s):.2f}")

if __name__ == "__main__":
    test_manual_input()