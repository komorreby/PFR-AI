import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, hamming_loss, accuracy_score
from imblearn.over_sampling import SMOTE
import logging
import os

# <<< Переносим инициализацию логгера ВВЕРХ >>>
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
# -----------------------------------------------

# <<< Импортируем определения колонок из error_classifier >>>
# (Чтобы гарантировать согласованность)
try:
    # Попытка импорта ErrorClassifier для получения списков колонок
    from error_classifier import ErrorClassifier 
    # Создаем временный экземпляр, чтобы получить списки
    # Указываем путь к модели, но НЕ загружаем ее здесь (изменено в ErrorClassifier)
    temp_classifier = ErrorClassifier(model_path="dummy_path_for_columns") 
    FEATURE_COLUMNS = temp_classifier.feature_columns
    TARGET_COLUMNS = temp_classifier.target_columns
    logger.info("Успешно импортированы списки колонок из ErrorClassifier.")
    logger.info(f"Признаки ({len(FEATURE_COLUMNS)}): {FEATURE_COLUMNS}")
    logger.info(f"Цели ({len(TARGET_COLUMNS)}): {TARGET_COLUMNS}")
except ImportError:
    logger.error("Не удалось импортировать ErrorClassifier. Используются ПРЕДУСТАНОВЛЕННЫЕ списки колонок.")
    # Фоллбек (менее надежный, убедитесь, что списки АКТУАЛЬНЫ)
    FEATURE_COLUMNS = [
        'age', 'gender', 'citizenship_rf', 'has_name_change', 'dependents',
        'is_retirement_standard', 'is_disability_social', 
        'total_years_declared', 'actual_experience_calc', 'special_experience_calc',
        'experience_mismatch', 'pension_points', 'record_count', 'has_special_conditions_flag',
        'has_disability', 'disability_group_1', 'disability_group_2', 'disability_group_3',
        'disability_group_child', 'disability_cert_provided', 'benefit_count', 
        'document_count', 'has_incorrect_document_flag', 'has_passport', 'has_snils',
        'has_work_book', 'has_disability_cert_doc'
    ]
    TARGET_COLUMNS = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
except FileNotFoundError: # Обработка ошибки, если dummy_path не сработал
     # Теперь logger определен здесь
     logger.error("Не удалось инициализировать ErrorClassifier для получения колонок (возможно, проблема с путем или зависимостями). Используются ПРЕДУСТАНОВЛЕННЫЕ списки.")
     # Используем те же фоллбек-списки
     FEATURE_COLUMNS = [
        'age', 'gender', 'citizenship_rf', 'has_name_change', 'dependents',
        'is_retirement_standard', 'is_disability_social', 
        'total_years_declared', 'actual_experience_calc', 'special_experience_calc',
        'experience_mismatch', 'pension_points', 'record_count', 'has_special_conditions_flag',
        'has_disability', 'disability_group_1', 'disability_group_2', 'disability_group_3',
        'disability_group_child', 'disability_cert_provided', 'benefit_count', 
        'document_count', 'has_incorrect_document_flag', 'has_passport', 'has_snils',
        'has_work_book', 'has_disability_cert_doc'
    ]
     TARGET_COLUMNS = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
except Exception as e:
     # Теперь logger определен здесь
     logger.error(f"Непредвиденная ошибка при получении списков колонок: {e}. Используются ПРЕДУСТАНОВЛЕННЫЕ списки.")
     # Используем те же фоллбек-списки
     FEATURE_COLUMNS = [
        'age', 'gender', 'citizenship_rf', 'has_name_change', 'dependents',
        'is_retirement_standard', 'is_disability_social', 
        'total_years_declared', 'actual_experience_calc', 'special_experience_calc',
        'experience_mismatch', 'pension_points', 'record_count', 'has_special_conditions_flag',
        'has_disability', 'disability_group_1', 'disability_group_2', 'disability_group_3',
        'disability_group_child', 'disability_cert_provided', 'benefit_count', 
        'document_count', 'has_incorrect_document_flag', 'has_passport', 'has_snils',
        'has_work_book', 'has_disability_cert_doc'
    ]
     TARGET_COLUMNS = ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009", "E010"]
# ----------------------------------------------------------

# --- Константы --- 
# <<< Используем обновленный CSV файл >>>
DATA_PATH = "dataset/pension_cases_features_errors.csv"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "error_classifier_model.joblib")
TEST_SIZE = 0.2
RANDOM_STATE = 42
# Параметры RandomForest
N_ESTIMATORS = 150 # Можно увеличить для потенциально лучшей точности
MAX_DEPTH = 20     # Ограничение глубины для предотвращения переобучения
CLASS_WEIGHT = 'balanced' # Важно для несбалансированных ошибок
# ----------------

def train_and_evaluate_model():
    # 1. Загрузка данных
    try:
        logger.info(f"Загрузка данных из {DATA_PATH}...")
        df = pd.read_csv(DATA_PATH)
        logger.info(f"Данные успешно загружены. Форма: {df.shape}")
    except FileNotFoundError:
        logger.error(f"Ошибка: Файл данных не найден по пути {DATA_PATH}. Запустите generate_data.py и convert_to_csv.py.")
        return
    except Exception as e:
        logger.error(f"Ошибка при загрузке или чтении CSV файла {DATA_PATH}: {e}")
        return

    # Проверка наличия всех необходимых колонок
    missing_features = [col for col in FEATURE_COLUMNS if col not in df.columns]
    missing_targets = [col for col in TARGET_COLUMNS if col not in df.columns]
    if missing_features:
         logger.error(f"В CSV отсутствуют необходимые колонки признаков: {missing_features}")
         return
    if missing_targets:
         logger.error(f"В CSV отсутствуют необходимые целевые колонки: {missing_targets}")
         return
    logger.info("Все необходимые колонки присутствуют в CSV.")

    # 2. Подготовка данных
    # <<< Используем импортированные/фоллбек списки колонок >>>
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMNS]
    # ---------------------------------------------------

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    logger.info(f"Данные разделены на обучающую ({X_train.shape[0]} записей) и тестовую ({X_test.shape[0]} записей) выборки.")

    # 3. Обучение модели
    logger.info(f"Обучение MultiOutputClassifier с RandomForestClassifier (n_estimators={N_ESTIMATORS}, max_depth={MAX_DEPTH}, class_weight={CLASS_WEIGHT})...")
    # Используем RandomForestClassifier внутри MultiOutputClassifier
    base_classifier = RandomForestClassifier(
        n_estimators=N_ESTIMATORS, 
        max_depth=MAX_DEPTH,
        random_state=RANDOM_STATE,
        class_weight=CLASS_WEIGHT, # Важно!
        n_jobs=-1 # Используем все доступные ядра процессора
    )
    multi_output_model = MultiOutputClassifier(base_classifier, n_jobs=-1)
    
    try:
        multi_output_model.fit(X_train, y_train)
        logger.info("Модель успешно обучена.")
    except Exception as e:
         logger.error(f"Ошибка во время обучения модели: {e}")
         return

    # 4. Оценка модели
    logger.info("Оценка модели на тестовой выборке...")
    y_pred = multi_output_model.predict(X_test)
    
    # Hamming Loss: доля неправильно предсказанных меток (чем меньше, тем лучше)
    h_loss = hamming_loss(y_test, y_pred)
    logger.info(f"Hamming Loss: {h_loss:.4f}")
    
    # Accuracy Score (Subset Accuracy): доля полностью правильно предсказанных наборов меток
    acc_score = accuracy_score(y_test, y_pred)
    logger.info(f"Subset Accuracy: {acc_score:.4f}")
    
    # Classification Report (для каждой метки отдельно)
    logger.info("Classification Report (по каждой ошибке):")
    # <<< Используем TARGET_COLUMNS для имен меток >>>
    try:
         report = classification_report(y_test, y_pred, target_names=TARGET_COLUMNS, zero_division=0)
         print(report)
    except ValueError as e:
         logger.warning(f"Не удалось сгенерировать classification_report с target_names: {e}. Вывод без имен.")
         report = classification_report(y_test, y_pred, zero_division=0)
         print(report)
    # ---------------------------------------------

    # 5. Сохранение модели
    os.makedirs(MODEL_DIR, exist_ok=True)
    try:
        joblib.dump(multi_output_model, MODEL_PATH)
        logger.info(f"Обученная модель сохранена в {MODEL_PATH}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении модели в {MODEL_PATH}: {e}")

if __name__ == "__main__":
    train_and_evaluate_model()