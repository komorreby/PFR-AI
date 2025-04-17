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
# Добавляем родительскую директорию (backend) в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models import CaseDataInput, ProcessOutput, ErrorOutput, CaseHistoryEntry, DocumentFormat
from error_classifier import ErrorClassifier # Импорт из корневой папки backend
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

# Эндпоинт /process
@app.post("/process", response_model=ProcessOutput)
async def process_case(request: Request, case_data: CaseDataInput, conn: AsyncConnection = Depends(get_db_connection)):
    # Получаем классификатор из состояния приложения
    classifier = request.app.state.classifier
    if classifier is None:
        raise HTTPException(status_code=500, detail="Error Classifier not initialized or failed to initialize")

    try:
        # Используем model_dump(mode='json') для получения JSON-совместимого словаря
        # Это преобразует datetime.date в строки 'YYYY-MM-DD'
        case_data_dict_json_compatible = case_data.model_dump(mode='json')
        
        # Передаем словарь со строками дат в классификатор
        raw_errors = classifier.classify_errors(case_data_dict_json_compatible) 
        
        # Преобразуем результат классификатора (ожидаем dict) в объекты ErrorOutput
        errors_output = [ErrorOutput(**error) for error in raw_errors]
        
        # Сериализуем ошибки обратно в dict для сохранения (это ок, т.к. ErrorOutput не содержит дат)
        errors_to_save = [error.model_dump() for error in errors_output]

        # Сохранение в базу данных - передаем personal_data из JSON-совместимого словаря
        case_id = await crud.create_case(
            conn=conn, 
            personal_data=case_data_dict_json_compatible["personal_data"], # Теперь здесь строки дат
            errors=errors_to_save
        )
        print(f"Case saved with ID: {case_id}") # Логгирование для отладки

        return ProcessOutput(errors=errors_output)
    except Exception as e:
        # Важно откатить транзакцию при ошибке, если она была начата
        # await conn.rollback() # SQLAlchemy Core с `await conn.commit()` не требует явного rollback здесь
        print(f"Error during processing: {e}")
        # В продакшене здесь должно быть более детальное логгирование
        import traceback
        traceback.print_exc() # Печатаем полный traceback для лучшей диагностики
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