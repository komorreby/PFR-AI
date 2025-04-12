import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from imblearn.over_sampling import SMOTE
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def train_model():
    # Загрузка данных
    df = pd.read_csv("pension_cases.csv")
    X = df.drop(columns=["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008"])
    y = df[["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008"]]

    # Проверка на NaN в y
    if y.isna().any().any():
        logger.error("Обнаружены NaN в y перед разделением данных")
        raise ValueError("Input y contains NaN before splitting")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Проверка на NaN в X_train_scaled
    if np.isnan(X_train_scaled).any():
        logger.error("Обнаружены NaN в X_train_scaled после масштабирования")
        raise ValueError("Input X contains NaN after scaling")

    # Применение SMOTE для каждого класса с синхронизацией
    smote = SMOTE(random_state=42)
    X_train_balanced_list = []
    y_train_balanced_list = []

    for column in y_train.columns:
        X_resampled, y_resampled = smote.fit_resample(X_train_scaled, y_train[column])
        X_train_balanced_list.append(X_resampled)
        y_train_balanced_list.append(y_resampled)

    # Выбираем минимальное количество примеров после SMOTE, чтобы синхронизировать размеры
    min_samples = min(len(y_resampled) for y_resampled in y_train_balanced_list)
    X_train_balanced = X_train_balanced_list[0][:min_samples]
    y_train_balanced = pd.DataFrame({
        col: y_resampled[:min_samples] for col, y_resampled in zip(y_train.columns, y_train_balanced_list)
    })

    # Проверка на NaN после SMOTE
    if np.isnan(X_train_balanced).any():
        logger.error("Обнаружены NaN в X_train_balanced после SMOTE")
        raise ValueError("Input X contains NaN after SMOTE")
    if y_train_balanced.isna().any().any():
        logger.error("Обнаружены NaN в y_train_balanced после SMOTE")
        raise ValueError("Input y contains NaN after SMOTE")

    # Настройка гиперпараметров с помощью GridSearchCV
    param_grid = {
        'estimator__n_estimators': [300],
        'estimator__max_depth': [10, 20, None],
        'estimator__min_samples_split': [2, 5],
        'estimator__min_samples_leaf': [1, 2]
    }
    base_model = RandomForestClassifier(class_weight="balanced", random_state=42)
    model = MultiOutputClassifier(base_model)
    grid_search = GridSearchCV(model, param_grid, cv=5, scoring='f1_macro', n_jobs=-1)

    logger.info("Начинаем GridSearchCV...")

    grid_search.fit(X_train_balanced, y_train_balanced)

    logger.info("GridSearchCV завершён.")

    logger.info(f"Лучшие параметры: {grid_search.best_params_}")
    model = grid_search.best_estimator_

    # Предсказания и метрики
    y_pred = model.predict(X_test_scaled)
    for i, column in enumerate(y.columns):
        logger.info(f"Метрики для {column}:")
        print(classification_report(y_test[column], y_pred[:, i], zero_division=0))

    cv_scores = cross_val_score(model, X_train_balanced, y_train_balanced, cv=3, scoring="f1_macro")
    logger.info(f"Кросс-валидация (F1-macro): {cv_scores.mean():.2f} (+/- {cv_scores.std() * 2:.2f})")

    # Сохранение модели
    joblib.dump(model, "pension_error_model.pkl")
    joblib.dump(scaler, "scaler.pkl")
    logger.info("Модель и масштабировщик сохранены.")

if __name__ == "__main__":
    train_model()