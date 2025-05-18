from fastapi import FastAPI, HTTPException, Depends, Request, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
# --- Добавляем импорты для RAG и Lifespan ---
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
# --- Изменяем импорт RAG ---
# from app.rag_core.engine import get_query_engine, query_case
from app.rag_core.engine import PensionRAG # Импортируем класс
# -------------------------------------------
# Добавляем импорты моделей и классификатора
# Обратите внимание: предполагается, что error_classifier.py находится в папке backend/
# Возможно, потребуется настроить PYTHONPATH или изменить импорт в зависимости от структуры
import sys
import os
# <<< Исправляем добавление пути: нужно добавить корень проекта (на уровень выше backend) >>>
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root) # Используем insert(0, ...) для приоритета
# ----------------------------------------------------------------------------
from app.models import CaseDataInput, ProcessOutput, ErrorOutput, CaseHistoryEntry, DocumentFormat, DisabilityInfo
# from error_classifier import ErrorClassifier # Теперь импорт из корня должен работать
# Импорты для БД
from app.database import create_db_and_tables, get_db_connection, async_engine
from sqlalchemy.ext.asyncio import AsyncConnection
from app import crud # Импортируем crud
from app import services # Импортируем services
from typing import List, Optional, Tuple, Dict, Any # Добавляем List, Optional, Tuple, Dict, Any
import traceback # <<< Добавляем traceback
import logging # <<< Импорт logging ОДИН РАЗ ЗДЕСЬ >>>

# Импортируем OCR модуль
from app.ocr.document_processor import process_document
from app.document_requirements import PENSION_DOCUMENT_REQUIREMENTS, PENSION_TYPE_CHOICES # Добавляем импорт

# <<< Инициализируем логгер для этого модуля ЗДЕСЬ >>>
logger = logging.getLogger(__name__)

# --- Инициализация при старте через Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # app.state.classifier = None # Инициализируем состояние для классификатора
    app.state.rag_engine = None # Инициализируем состояние для RAG движка
    print("Starting up...")
    # Создаем таблицы БД
    print("Creating DB tables if they don't exist...")
    create_db_and_tables()
    
    # --- Инициализируем RAG Engine ---
    print("Initializing PensionRAG Engine...")
    try:
        # Создаем экземпляр и сохраняем в состоянии
        app.state.rag_engine = PensionRAG()
        print("PensionRAG Engine initialized.")
    except Exception as e:
        print(f"!!! ERROR initializing PensionRAG Engine: {e}")
        app.state.rag_engine = None # Убедимся, что None, если ошибка
    # -------------------------------------------
    
    # --- Инициализируем ErrorClassifier ЗДЕСЬ --- 
    # print("Initializing Error Classifier...")
    # try:
    #     # Сохраняем экземпляр в состоянии приложения
    #     app.state.classifier = ErrorClassifier()
    #     print("Error Classifier initialized.")
    # except Exception as e:
    #     print(f"!!! ERROR initializing ErrorClassifier: {e}")
    #     app.state.classifier = None # Убедимся, что None, если ошибка
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
# <<< Удаляем старую модель CaseAnalysisRequest >>>
# class CaseAnalysisRequest(BaseModel):
#     case_description: str 

class CaseAnalysisResponse(BaseModel):
    analysis_result: str
    confidence_score: float = Field(ge=0, le=1)
# ---------------------------------------

# Добавляем модели для OCR
class OCRResponse(BaseModel):
    extracted_text: str
    extracted_fields: Dict[str, Any]

# Модели для нового эндпоинта проверки комплекта документов
class DocumentCheckInfo(BaseModel):
    id: str
    name: str
    status: str # например, "Предоставлен (данные из OCR)", "Предоставлен (подтверждено пользователем)", "Не предоставлен (критично)", "Не предоставлен"
    description: Optional[str] = None
    condition_text: Optional[str] = None
    is_critical: bool
    ocr_data: Optional[Dict[str, Any]] = None

class DocumentSetCheckResponse(BaseModel):
    pension_type_key: str
    pension_display_name: str
    pension_description: str
    overall_status: str # например, "Комплект предварительно полный", "Требуются критичные документы", "Требуются дополнительные документы"
    checked_documents: List[DocumentCheckInfo]
    missing_critical_documents: List[str]
    missing_other_documents: List[str]

# --- Вспомогательная функция для форматирования описания дела --- 
def format_case_description_for_rag(case_data: CaseDataInput) -> str:
    parts = []
    # Персональные данные
    # <<< Используем новые поля last_name, first_name, middle_name >>>
    pd = case_data.personal_data
    full_name_parts = [pd.last_name, pd.first_name, pd.middle_name]
    full_name = " ".join(filter(None, full_name_parts))
    # ----------------------------------------------------------
    parts.append(f"Заявитель: {full_name}, Дата рождения: {pd.birth_date.strftime('%d.%m.%Y')}, Пол: {pd.gender}, Гражданство: {pd.citizenship}, Иждивенцы: {pd.dependents}.")
    if pd.name_change_info:
        parts.append(f"Была смена ФИО: Старое ФИО: {pd.name_change_info.old_full_name or 'Не указ.'}, Дата: {pd.name_change_info.date_changed.strftime('%d.%m.%Y') if pd.name_change_info.date_changed else 'Не указ.'}.")

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
    # <<< Добавляем проверку типа на всякий случай >>>
    if not isinstance(rag_text, str):
        print(f"[Compliance Check] ОШИБКА: Ожидался текст от RAG, но получен {type(rag_text)}: {rag_text}")
        return False # Считаем не соответствующим, если тип не строка
        
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

# <<< КОНЕЦ ВОЗВРАЩЕННЫХ ФУНКЦИЙ >>>

# --- API Endpoints --- 

@app.get("/")
async def read_root():
    return {"message": "PFR-AI Backend is running!"}

# <<< НОВАЯ ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ВЫЗОВА RAG >>>
# <<< Добавляем case_data: CaseDataInput в параметры >>>
async def _call_rag_engine(request: Request, case_data: CaseDataInput, case_description: str, pension_type: Optional[str], disability_info: Optional[dict]) -> Tuple[str, float]:
    """Выполняет вызов RAG движка с обработкой ошибок."""
    rag_engine = request.app.state.rag_engine
    if rag_engine is None:
        # Эта ошибка будет перехвачена выше как HTTPException 503, если мы не выбросим здесь
        # Либо можно выбросить HTTPException прямо тут
        print("!!! RAG Engine not available in _call_rag_engine")
        # raise HTTPException(status_code=503, detail="PensionRAG Engine is not available.")
        return "Ошибка: RAG движок недоступен.", 0.0

    try:
        print(f"Calling RAG Engine with pension_type: {pension_type}...")
        # <<< Добавляем передачу case_data в query >>>
        analysis_text, score = rag_engine.query( 
            case_data=case_data, # <<< ПЕРЕДАЕМ case_data
            case_description=case_description, 
            pension_type=pension_type, 
            disability_info=disability_info
        )
        print(f"RAG Engine call successful (Score: {score:.4f}) ")
        return analysis_text, score
    except Exception as e:
        print(f"!!! ERROR during RAG query call in _call_rag_engine: {e}")
        traceback.print_exc() # Используем импортированный traceback
        # Возвращаем стандартизированное сообщение об ошибке и нулевой скор
        return f"Ошибка выполнения RAG анализа: {e}", 0.0
# <<< КОНЕЦ ВСПОМОГАТЕЛЬНОЙ ФУНКЦИИ >>>

# --- ЭНДПОИНТ ДЛЯ RAG АНАЛИЗА (ОБНОВЛЕННЫЙ) --- 
@app.post("/api/v1/analyze_case", response_model=CaseAnalysisResponse)
async def analyze_pension_case(case_data: CaseDataInput, req: Request):
    case_description = format_case_description_for_rag(case_data)
    print(f"Received case analysis request (formatted description): {case_description[:150]}...")
    
    case_data_dict_json_compatible = case_data.model_dump(mode='json')
    # <<< Передаем case_data в _call_rag_engine >>>
    analysis_text, score = await _call_rag_engine(
        request=req,
        case_data=case_data, # <<< Передаем объект
        case_description=case_description,
        pension_type=case_data.pension_type,
        disability_info=case_data_dict_json_compatible.get("disability")
    )
    
    # <<< Проверяем, не вернулась ли ошибка от RAG >>>
    if score == 0.0 and analysis_text.startswith("Ошибка"):
         # Можно вернуть 500 или просто передать текст ошибки дальше
         # В данном случае эндпоинт просто возвращает результат, так что передаем как есть
         print(f"RAG analysis failed: {analysis_text}")
         # Или можно выбросить HTTPException, если хотим четкий статус ошибки
         # raise HTTPException(status_code=500, detail=analysis_text)

    print(f"RAG analysis result for endpoint (score: {score:.4f}, start): {analysis_text[:100]}...")
    return CaseAnalysisResponse(analysis_result=analysis_text, confidence_score=score)

# Эндпоинт /process (ОБНОВЛЕННЫЙ)
@app.post("/process", response_model=ProcessOutput)
async def process_case(request: Request, case_data: CaseDataInput, conn: AsyncConnection = Depends(get_db_connection)):
    # classifier = request.app.state.classifier
    # if classifier is None:
    #     # <<< Используем logger здесь, если он будет инициализирован к этому моменту >>>
    #     # Или можно оставить print, если logger используется только в OCR эндпоинте
    #     logger.error("Error Classifier service is not available.") # Пример
    #     raise HTTPException(status_code=503, detail="Error Classifier service is not available.")

    try:
        # 1. Получаем ошибки от ML классификатора
        case_data_dict_json_compatible = case_data.model_dump(mode='json')
        # ml_errors = classifier.classify_errors(case_data_dict_json_compatible)
        ml_errors_output = []

        # 2. Формируем описание дела для RAG
        case_description_full = format_case_description_for_rag(case_data)
        print("--- RAG Input Description ---")
        print(case_description_full)
        print("---------------------------")

        # 3. Выполняем RAG-анализ с помощью новой функции
        case_data_dict_json_compatible = case_data.model_dump(mode='json') # Перемещаем сюда, если еще не было
        # <<< Передаем case_data в _call_rag_engine >>>
        rag_analysis_text, rag_confidence_score = await _call_rag_engine(
            request=request,
            case_data=case_data, # <<< Передаем объект
            case_description=case_description_full,
            pension_type=case_data.pension_type,
            disability_info=case_data_dict_json_compatible.get("disability")
        )

        # 4. Комбинируем результаты и определяем статус
        final_explanation_parts = []
        has_rejecting_issues = False

        # Добавляем ошибки от ML
        if ml_errors_output:
            has_rejecting_issues = True
            final_explanation_parts.append("**Выявлены следующие потенциальные несоответствия (ML Классификатор):**")
            for error in ml_errors_output:
                final_explanation_parts.append(f"- **{error.code}: {error.description}**")
                final_explanation_parts.append(f"  *Основание:* {error.law}")
                final_explanation_parts.append(f"  *Рекомендация:* {error.recommendation}")
            final_explanation_parts.append("\n") # Добавляем отступ

        # Добавляем результат RAG анализа (текст)
        final_explanation_parts.append("**Анализ соответствия законодательству (RAG):**")
        # <<< Добавляем скор в объяснение, если он не нулевой и нет ошибки >>>
        if rag_confidence_score > 0.0 or not rag_analysis_text.startswith("Ошибка"):
            final_explanation_parts.append(f"(Уверенность RAG: {(rag_confidence_score * 100):.1f}%)\n")
        final_explanation_parts.append(rag_analysis_text)

        # --- Определяем статус на основе ML и RAG --- 
        # <<< Проверяем, что RAG не вернул ошибку перед анализом соответствия >>>
        rag_compliant = False
        if not rag_analysis_text.startswith("Ошибка"):
            # <<< Теперь эта функция снова определена >>>
            rag_compliant = analyze_rag_for_compliance(rag_analysis_text)
        else:
            print("[Compliance Check] Пропуск проверки соответствия из-за ошибки RAG.")
            
        # Отказ если есть ML ошибки ИЛИ RAG НЕ соответствует (или была ошибка RAG)
        has_rejecting_issues = bool(ml_errors_output) or not rag_compliant 
        # ---------------------------------------------
        
        final_status = "rejected" if has_rejecting_issues else "approved"
        final_explanation = "\n".join(final_explanation_parts)

        # 5. Сохранение в базу данных
        # TODO: Адаптировать crud.create_case для сохранения доп. полей
        errors_to_save = [error.model_dump() for error in ml_errors_output]
        
        # <<< ГОТОВИМ personal_data ДЛЯ СОХРАНЕНИЯ: добавляем full_name >>>
        personal_data_to_save = case_data_dict_json_compatible["personal_data"].copy()
        pd_source = case_data.personal_data # Берем из исходного объекта Pydantic
        full_name_parts = [pd_source.last_name, pd_source.first_name, pd_source.middle_name]
        personal_data_to_save['full_name'] = " ".join(filter(None, full_name_parts))
        # ------------------------------------------------------------------
        
        case_id = await crud.create_case(
            conn=conn,
            # <<< Передаем подготовленный словарь >>>
            personal_data=personal_data_to_save, 
            errors=errors_to_save,
            pension_type=case_data.pension_type,
            final_status=final_status,
            final_explanation=final_explanation
        )

        # ... (остальной код вызова crud.create_case и возврата ProcessOutput ...

    except Exception as e:
        # <<< Используем logger здесь >>>
        logger.error(f"Error during processing: {e}", exc_info=True)
        # traceback.print_exc() # Можно убрать, если logger.error с exc_info=True используется
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

# Добавляем эндпоинт для OCR
@app.post("/api/v1/ocr/upload_document", response_model=OCRResponse)
async def upload_ocr_document(
    file: UploadFile = File(...),
    document_type: str = "passport"
):
    """
    Загружает документ и извлекает из него текст и структурированные данные.
    """
    try:
        contents = await file.read() # Чтение файла остается асинхронным
        # Обрабатываем документ СИНХРОННО
        result = process_document(contents, document_type, filename=file.filename)
        
        return OCRResponse(
            extracted_text=result.get("extracted_text", ""), # Используем .get для безопасности
            extracted_fields=result.get("extracted_fields", {}) # Используем .get для безопасности
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке документа (upload_ocr_document): {str(e)}", exc_info=True)
        # Если process_document вернул словарь с ошибкой, его можно передать напрямую
        # Но FastAPI ожидает HTTPException для кодов ошибок, отличных от 200
        # Однако, если ошибка уже отловлена и обернута в process_document, то здесь будет общий Exception
        detail_message = str(e)
        if isinstance(result, dict) and result.get("error"): # Проверяем, не вернул ли process_document свою ошибку
             detail_message = result.get("error")

        raise HTTPException(
            status_code=500, # или 422, если ошибка связана с данными, а не сервером
            detail=detail_message
        )
    # finally:
        # UploadFile в FastAPI обычно закрывается автоматически
        # await file.close() # Не нужно для синхронной обработки, если только чтение не вызвало проблем
        pass 

# --- ЭНДПОИНТ ДЛЯ ПРОВЕРКИ КОМПЛЕКТНОСТИ ДОКУМЕНТОВ ---
@app.post("/api/v1/check_document_set", response_model=DocumentSetCheckResponse)
async def check_document_set_endpoint(
    pension_type_key: str = Form(...),
    uploaded_document_ids: Optional[List[str]] = Form(None), # Список ID документов, "загруженных" пользователем
    passport_file: Optional[UploadFile] = File(None) # Файл паспорта для OCR
):
    logger.info(f"Запрос на проверку комплекта документов для типа пенсии: {pension_type_key}")
    logger.info(f"Предоставленные ID других документов: {uploaded_document_ids}")
    logger.info(f"Файл паспорта: {passport_file.filename if passport_file else 'Не предоставлен'}")

    if pension_type_key not in PENSION_DOCUMENT_REQUIREMENTS:
        raise HTTPException(status_code=404, detail=f"Тип пенсии '{pension_type_key}' не найден.")

    pension_config = PENSION_DOCUMENT_REQUIREMENTS[pension_type_key]
    required_documents_config = pension_config.get("documents", [])
    
    checked_documents_list: List[DocumentCheckInfo] = []
    missing_critical_docs_names: List[str] = []
    missing_other_docs_names: List[str] = []
    
    # Обеспечим, чтобы uploaded_document_ids был списком, даже если пустой
    processed_uploaded_ids = uploaded_document_ids[0].split(',') if uploaded_document_ids and uploaded_document_ids[0] else []
    logger.info(f"Обработанные ID других документов: {processed_uploaded_ids}")

    for doc_req in required_documents_config:
        doc_id = doc_req["id"]
        doc_name = doc_req["name"]
        doc_is_critical = doc_req["is_critical"]
        doc_ocr_type = doc_req.get("ocr_type")
        doc_description = doc_req.get("description")
        doc_condition_text = doc_req.get("condition_text")
        
        status = ""
        ocr_data_for_doc = None
        doc_found = False

        if doc_ocr_type == "passport_rf" and passport_file:
            try:
                logger.info(f"Обработка паспорта ({passport_file.filename}) для документа '{doc_name}'...")
                passport_bytes = await passport_file.read()
                # Перед повторным чтением файла, если это тот же объект файла, нужно "перемотать" его
                # Однако, FastAPI обычно создает новый объект UploadFile для каждого запроса, 
                # или если файл передается один раз, его можно прочитать только один раз.
                # Если бы мы читали passport_file несколько раз в одном запросе, потребовалось бы:
                # await passport_file.seek(0)
                ocr_result = process_document(passport_bytes, document_type="passport", filename=passport_file.filename)
                if ocr_result.get("error"):
                    status = f"Паспорт РФ предоставлен, ошибка OCR: {ocr_result.get('error')}"
                    logger.error(f"Ошибка OCR для паспорта: {ocr_result.get('error')}")
                else:
                    ocr_data_for_doc = ocr_result.get("extracted_fields")
                    status = "Предоставлен (данные из OCR)"
                    logger.info(f"Паспорт РФ обработан, извлечено полей: {len(ocr_data_for_doc) if ocr_data_for_doc else 0}")
                doc_found = True
            except Exception as e:
                logger.error(f"Критическая ошибка при OCR обработке паспорта {passport_file.filename}: {str(e)}", exc_info=True)
                status = "Паспорт РФ предоставлен, ошибка при обработке файла OCR"
                doc_found = True # Файл был, но обработка не удалась
        elif doc_id in processed_uploaded_ids:
            status = "Предоставлен (подтверждено пользователем)"
            doc_found = True

        if not doc_found:
            if doc_is_critical:
                status = "Не предоставлен (критично!)"
                missing_critical_docs_names.append(doc_name)
            else:
                status = "Не предоставлен"
                missing_other_docs_names.append(doc_name)
        
        checked_documents_list.append(DocumentCheckInfo(
            id=doc_id,
            name=doc_name,
            status=status,
            description=doc_description,
            condition_text=doc_condition_text,
            is_critical=doc_is_critical,
            ocr_data=ocr_data_for_doc
        ))

    overall_status_text = ""
    if missing_critical_docs_names:
        overall_status_text = "Требуются критичные документы"
    elif missing_other_docs_names:
        overall_status_text = "Требуются дополнительные документы (не критичные)"
    else:
        overall_status_text = "Комплект предварительно полный"

    logger.info(f"Проверка комплекта завершена. Общий статус: {overall_status_text}")
    logger.info(f"Отсутствуют критичные документы: {missing_critical_docs_names}")
    logger.info(f"Отсутствуют другие документы: {missing_other_docs_names}")

    return DocumentSetCheckResponse(
        pension_type_key=pension_type_key,
        pension_display_name=pension_config.get("display_name", ""),
        pension_description=pension_config.get("description", ""),
        overall_status=overall_status_text,
        checked_documents=checked_documents_list,
        missing_critical_documents=missing_critical_docs_names,
        missing_other_documents=missing_other_docs_names
    )

# --- ЭНДПОИНТ ДЛЯ ПОЛУЧЕНИЯ СПИСКА ТИПОВ ПЕНСИЙ (для фронтенда) ---
@app.get("/api/v1/pension_types")
async def get_pension_types():
    return PENSION_TYPE_CHOICES 