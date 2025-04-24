from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
# --- Добавляем импорты для RAG и Lifespan ---
from contextlib import asynccontextmanager
from pydantic import BaseModel
from app.rag_core.query_engine import get_query_engine, query_case
# -------------------------------------------
# Добавляем импорты моделей и классификатора
# Обратите внимание: предполагается, что error_classifier.py находится в папке backend/
# Возможно, потребуется настроить PYTHONPATH или изменить импорт в зависимости от структуры
import sys
import os
# <<< Исправляем добавление пути: нужно добавить корень проекта (на уровень выше backend) >>>
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root) # Используем insert(0, ...) для приоритета
# logger.debug(f"Добавлен project_root в sys.path: {project_root}") # Опциональный дебаг
# logger.debug(f"Текущий sys.path: {sys.path}")
# ----------------------------------------------------------------------------
from app.models import CaseDataInput, ProcessOutput, ErrorOutput, CaseHistoryEntry, DocumentFormat, DisabilityInfo
from error_classifier import ErrorClassifier # Теперь импорт из корня должен работать
# Импорты для БД
from app.database import create_db_and_tables, get_db_connection, async_engine
from sqlalchemy.ext.asyncio import AsyncConnection
from app import crud # Импортируем crud
from app import services # Импортируем services
from typing import List # Добавляем List

# --- Инициализация при старте через Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.classifier = None # Инициализируем состояние для классификатора
    print("Starting up...")
    # Создаем таблицы БД
    print("Creating DB tables if they don't exist...")
    create_db_and_tables()
    
    # Инициализируем RAG Query Engine
    print("Initializing RAG Query Engine...")
    try:
        get_query_engine() # Вызываем для загрузки/создания индекса
        print("RAG Query Engine initialized.")
    except Exception as e:
        print(f"!!! ERROR initializing RAG Query Engine: {e}")
        # Можно добавить логику обработки, если RAG критичен
    
    # --- Инициализируем ErrorClassifier ЗДЕСЬ --- 
    print("Initializing Error Classifier...")
    try:
        # Сохраняем экземпляр в состоянии приложения
        app.state.classifier = ErrorClassifier()
        print("Error Classifier initialized.")
    except Exception as e:
        print(f"!!! ERROR initializing ErrorClassifier: {e}")
        app.state.classifier = None # Убедимся, что None, если ошибка
    # -------------------------------------------

    print("Startup complete.")
    yield # Приложение работает здесь
    # --- Shutdown --- 
    print("Shutting down...")
    await async_engine.dispose()
    print("Database connection pool closed.")
    print("Shutdown complete.")
# ---------------------------------------------

# Передаем lifespan менеджер в FastAPI
app = FastAPI(lifespan=lifespan)

# --- Настройка CORS --- 
# Список источников (origins), которым разрешено делать запросы
# В продакшене здесь должен быть URL вашего фронтенда
origins = [
    "http://localhost:5173", # URL сервера разработки Vite
    "http://127.0.0.1:5173",
    # Можно добавить другие, например, URL развернутого фронтенда
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Разрешенные источники
    allow_credentials=True,    # Разрешить куки (если потребуются в будущем)
    allow_methods=["*"],         # Разрешить все методы (GET, POST, OPTIONS и т.д.)
    allow_headers=["*"],         # Разрешить все заголовки
)
# -----------------------

# --- Pydantic модели для RAG эндпоинта ---
class CaseAnalysisRequest(BaseModel):
    case_description: str

class CaseAnalysisResponse(BaseModel):
    analysis_result: str
# ---------------------------------------

# --- API Endpoints --- 

@app.get("/")
async def read_root():
    return {"message": "PFR-AI Backend is running!"}

# --- НОВЫЙ ЭНДПОИНТ ДЛЯ RAG АНАЛИЗА ---
@app.post("/api/v1/analyze_case", response_model=CaseAnalysisResponse)
async def analyze_pension_case(request: CaseAnalysisRequest):
    print(f"Received case analysis request: {request.case_description[:100]}...")
    try:
        # Вызываем функцию RAG анализа
        analysis = query_case(request.case_description)
        print(f"RAG analysis result (start): {analysis[:100]}...")
        return CaseAnalysisResponse(analysis_result=analysis)
    except Exception as e:
        print(f"!!! ERROR during RAG analysis: {e}")
        import traceback
        traceback.print_exc()
        # Возвращаем 500 ошибку, если RAG не сработал
        raise HTTPException(status_code=500, detail=f"Internal server error during RAG analysis: {str(e)}")
# ---------------------------------------

# --- Вспомогательная функция для форматирования описания дела --- 
def format_case_description_for_rag(case_data: CaseDataInput) -> str:
    parts = []
    # Персональные данные
    pd = case_data.personal_data
    parts.append(f"Заявитель: {pd.full_name}, Дата рождения: {pd.birth_date.strftime('%d.%m.%Y')}, Пол: {pd.gender}, Гражданство: {pd.citizenship}, Иждивенцы: {pd.dependents}.")
    if pd.name_change_info:
        parts.append(f"Была смена ФИО: Старое ФИО: {pd.name_change_info.old_full_name}, Дата: {pd.name_change_info.date_changed.strftime('%d.%m.%Y') if pd.name_change_info.date_changed else 'Не указ.'}.")

    # Тип пенсии
    pension_type_map = {
        'retirement_standard': 'Страховая по старости (общий случай)',
        'disability_social': 'Социальная по инвалидности',
        # Добавить другие типы по мере необходимости
    }
    parts.append(f"Запрашиваемый тип пенсии: {pension_type_map.get(case_data.pension_type, case_data.pension_type)}.")

    # Инвалидность (если есть)
    if case_data.disability:
        dis_info = case_data.disability
        group_text = f"{dis_info.group} группа" if dis_info.group != 'child' else "Ребенок-инвалид"
        parts.append(f"Инвалидность: {group_text}, Дата установления: {dis_info.date.strftime('%d.%m.%Y')}. " +
                     (f"Номер справки МСЭ: {dis_info.cert_number}." if dis_info.cert_number else ""))

    # Стаж и баллы (если применимо к типу пенсии, например, retirement_standard)
    if case_data.pension_type == 'retirement_standard':
        we = case_data.work_experience
        parts.append(f"Общий страховой стаж: {we.total_years} лет.")
        parts.append(f"Пенсионные баллы (ИПК): {case_data.pension_points}.")
        if we.records:
            parts.append("Записи о стаже:")
            for i, r in enumerate(we.records):
                special_text = " (Особые условия)" if r.special_conditions else ""
                parts.append(f"  {i+1}. {r.organization} ({r.start_date.strftime('%d.%m.%Y')} - {r.end_date.strftime('%d.%m.%Y')}), Должность: {r.position}{special_text}.")
        else:
            parts.append("Записи о стаже отсутствуют.")

    # Льготы и документы
    if case_data.benefits:
        parts.append(f"Заявленные льготы: {', '.join(case_data.benefits)}.")
    if case_data.documents:
        parts.append(f"Представленные документы: {', '.join(case_data.documents)}.")
    else:
         parts.append("Документы не представлены.")

    if case_data.has_incorrect_document:
        parts.append("Заявлено наличие некорректно оформленных документов.")

    return "\n".join(parts)
# -------------------------------------------------------------

# --- Новая функция для анализа текста RAG на соответствие --- 
def analyze_rag_for_compliance(rag_text: str) -> bool:
    """ 
    Анализирует текст ответа RAG на наличие явной финальной фразы.
    Возвращает True, если найдена фраза 'ИТОГ: СООТВЕТСТВУЕТ',
    False - если найдена фраза 'ИТОГ: НЕ СООТВЕТСТВУЕТ'.
    Если ни одна фраза не найдена, возвращает False (считаем, что есть проблема).
    """
    lower_text = rag_text.lower()
    
    # Ищем точные фразы в конце (учитывая возможные пробелы)
    if "итог: соответствует" in lower_text.strip():
        print("[Compliance Check] Найдена фраза 'ИТОГ: СООТВЕТСТВУЕТ' -> СООТВЕТСТВУЕТ")
        return True
    elif "итог: не соответствует" in lower_text.strip():
        print("[Compliance Check] Найдена фраза 'ИТОГ: НЕ СООТВЕТСТВУЕТ' -> НЕ СООТВЕТСТВУЕТ")
        return False
    else:
        # Если LLM не выдал четкий итог, считаем, что есть проблемы
        print("[Compliance Check] Четкая фраза ИТОГ не найдена -> ПРЕДПОЛАГАЕМ НЕ СООТВЕТСТВУЕТ")
        return False # Убираем fallback на ключевые слова
# ---------------------------------------------------------

# Эндпоинт /process
@app.post("/process", response_model=ProcessOutput)
async def process_case(request: Request, case_data: CaseDataInput, conn: AsyncConnection = Depends(get_db_connection)):
    classifier = request.app.state.classifier
    if classifier is None:
        raise HTTPException(status_code=500, detail="Error Classifier not initialized")

    try:
        # 1. Получаем ошибки от ML классификатора
        case_data_dict_json_compatible = case_data.model_dump(mode='json')
        ml_errors = classifier.classify_errors(case_data_dict_json_compatible)
        ml_errors_output = [ErrorOutput(**error) for error in ml_errors]

        # 2. Формируем описание дела для RAG
        # Используем оригинальную case_data с объектами дат для форматирования
        case_description_full = format_case_description_for_rag(case_data)
        print("--- RAG Input Description ---")
        print(case_description_full)
        print("---------------------------")

        # 3. Выполняем RAG-анализ
        rag_analysis_text = ""
        try:
            # <<< Передаем pension_type и disability_info в query_case
            rag_analysis_text = query_case(
                case_description=case_description_full,
                pension_type=case_data.pension_type,
                disability_info=case_data_dict_json_compatible.get("disability")
            )
            print("--- RAG Analysis Result ---")
            print(rag_analysis_text)
            print("---------------------------")
        except Exception as rag_e:
            print(f"!!! ERROR during RAG query_case call: {rag_e}")
            import traceback
            traceback.print_exc()
            rag_analysis_text = f"Ошибка выполнения RAG анализа: {rag_e}" # Записываем ошибку в результат

        # 4. Комбинируем результаты и определяем статус
        final_explanation_parts = []
        has_rejecting_issues = False

        # Добавляем ошибки от ML
        if ml_errors_output:
            has_rejecting_issues = True
            final_explanation_parts.append("**Выявлены следующие ошибки:**")
            for error in ml_errors_output:
                final_explanation_parts.append(f"- **{error.code}: {error.description}**")
                final_explanation_parts.append(f"  *Основание:* {error.law}")
                final_explanation_parts.append(f"  *Рекомендация:* {error.recommendation}")
            final_explanation_parts.append("\n") # Добавляем отступ

        # Добавляем результат RAG анализа
        final_explanation_parts.append("**Анализ соответствия законодательству (RAG):**")
        final_explanation_parts.append(rag_analysis_text)

        # --- Определяем статус на основе ML и RAG --- 
        rag_compliant = analyze_rag_for_compliance(rag_analysis_text)
        has_rejecting_issues = bool(ml_errors_output) or not rag_compliant # Отказ если есть ML ошибки ИЛИ RAG НЕ соответствует
        # ---------------------------------------------
        
        final_status = "rejected" if has_rejecting_issues else "approved"
        final_explanation = "\n".join(final_explanation_parts)

        # 5. Сохранение в базу данных (можно добавить pension_type и disability)
        # TODO: Адаптировать crud.create_case для сохранения доп. полей
        errors_to_save = [error.model_dump() for error in ml_errors_output]
        case_id = await crud.create_case(
            conn=conn,
            personal_data=case_data_dict_json_compatible["personal_data"],
            errors=errors_to_save,
            pension_type=case_data.pension_type,
            disability=case_data_dict_json_compatible.get("disability") # Используем .get для опционального поля
        )
        print(f"Case saved with ID: {case_id}")

        # 6. Возвращаем полный результат
        return ProcessOutput(
            errors=ml_errors_output, # Возвращаем ML ошибки
            status=final_status,
            explanation=final_explanation
        )

    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error during processing: {str(e)}")

# Новый эндпоинт для истории
@app.get("/history", response_model=List[CaseHistoryEntry])
async def get_history(
    skip: int = 0, 
    limit: int = 100, 
    conn: AsyncConnection = Depends(get_db_connection)
):
    try:
        history_data = await crud.get_cases(conn=conn, skip=skip, limit=limit)
        # Преобразуем данные из БД (словари) в Pydantic модели CaseHistoryEntry
        # Это обеспечит валидацию формата ответа
        history_response = []
        for item in history_data:
             # Убедимся, что ошибки парсятся как список ErrorOutput
            parsed_errors = [ErrorOutput(**err) for err in item['errors']]
            history_response.append(
                CaseHistoryEntry(
                    id=item['id'],
                    personal_data=item['personal_data'],
                    errors=parsed_errors
                )
            )
        return history_response
        # return history_data # Можно возвращать и так, если response_model не использовать
    except Exception as e:
        print(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error fetching history: {str(e)}")

# Новый эндпоинт для скачивания документа
@app.get("/download_document/{case_id}")
async def download_document(
    case_id: int,
    format: DocumentFormat = DocumentFormat.pdf, # Используем Enum для формата
    conn: AsyncConnection = Depends(get_db_connection)
):
    # Получаем данные дела из БД
    case_data = await crud.get_case_by_id(conn=conn, case_id=case_id)
    if not case_data:
        raise HTTPException(status_code=404, detail=f"Case with ID {case_id} not found")

    try:
        # Генерируем документ
        file_buffer, filename, mimetype = services.generate_document(
            personal_data=case_data["personal_data"],
            errors=case_data["errors"],
            doc_format=format
        )

        # Отправляем файл как поток
        return StreamingResponse(
            content=file_buffer,
            media_type=mimetype,
            headers={f'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except ValueError as ve:
         # Ошибка, если формат не поддерживается (хотя Enum должен это предотвратить)
         print(f"Value error during document generation: {ve}")
         raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error generating document for case {case_id}: {e}")
        # В продакшене здесь должно быть более детальное логгирование
        raise HTTPException(status_code=500, detail=f"Internal server error generating document: {str(e)}") 