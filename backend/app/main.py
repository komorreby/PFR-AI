from fastapi import FastAPI, HTTPException, Depends, Request, File, UploadFile, Form, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from app.rag_core.engine import PensionRAG
from .models import CaseDataInput, ProcessOutput, CaseHistoryEntry, DocumentFormat, DisabilityInfo, PersonalData, PassportData, SnilsData, DocumentTypeToExtract, OtherDocumentData

from .database import create_db_and_tables, get_db_connection, async_engine, cases_table
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from sqlalchemy.sql import select, insert, text # Добавляем text для сырых запросов, если нужно
from . import crud
from . import services
from typing import List, Optional, Tuple, Dict, Any, Union, Set
import traceback
import json
from . import vision_services
import logging # Добавляем импорт
from datetime import datetime # Убираем date, так как CaseHistoryEntry будет использовать datetime
from app.document_requirements import PENSION_DOCUMENT_REQUIREMENTS, PENSION_TYPE_CHOICES

logger = logging.getLogger(__name__) # Инициализируем логгер

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag_engine = None
    print("Starting up...")
    print("Creating DB tables if they don't exist...")
    create_db_and_tables()
    
    print("Initializing PensionRAG Engine...")
    try:
        app.state.rag_engine = PensionRAG()
        print("PensionRAG Engine initialized.")
    except Exception as e:
        print(f"!!! ERROR initializing PensionRAG Engine: {e}")
        app.state.rag_engine = None
    print("Startup complete.")
    yield # Приложение работает здесь
    print("Shutting down...")
    # Закрываем соединение с Neo4j, если оно было создано в PensionRAG
    if app.state.rag_engine and hasattr(app.state.rag_engine, 'graph_builder') and app.state.rag_engine.graph_builder:
        try:
            print("Closing Neo4j connection...")
            app.state.rag_engine.graph_builder.close()
            print("Neo4j connection closed.")
        except Exception as e:
            print(f"Error closing Neo4j connection: {e}")
            
    await async_engine.dispose()
    print("Database connection pool closed.")
    print("Shutdown complete.")

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
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CaseAnalysisResponse(BaseModel):
    analysis_result: str
    confidence_score: float = Field(ge=0, le=1)

# Новая модель для представления записи в истории
# class CaseHistoryEntry(BaseModel):
#     id: int
#     created_at: datetime # <--- Изменено на datetime
#     pension_type: str
#     final_status: str
#     final_explanation: Optional[str] = None 

def format_case_description_for_rag(case_data: CaseDataInput) -> str:
    parts = []
    pd = case_data.personal_data
    full_name_parts = [pd.last_name, pd.first_name, pd.middle_name]
    full_name = " ".join(filter(None, full_name_parts))
    parts.append(f"Заявитель: {full_name}, Дата рождения: {pd.birth_date.strftime('%d.%m.%Y')}, Пол: {pd.gender}, Гражданство: {pd.citizenship}, Иждивенцы: {pd.dependents}.")
    if pd.name_change_info:
        parts.append(f"Была смена ФИО: Старое ФИО: {pd.name_change_info.old_full_name or 'Не указ.'}, Дата: {pd.name_change_info.date_changed.strftime('%d.%m.%Y') if pd.name_change_info.date_changed else 'Не указ.'}.")

    from app.rag_core import config as rag_config
    parts.append(f"Запрашиваемый тип пенсии: {rag_config.PENSION_TYPE_MAP.get(case_data.pension_type, case_data.pension_type)}.")

    if case_data.disability:
        dis_info = case_data.disability
        group_text = f"{dis_info.group} группа" if dis_info.group != 'child' else "Ребенок-инвалид"
        parts.append(f"Инвалидность: {group_text}, Дата установления: {dis_info.date.strftime('%d.%m.%Y')}. " +
                     (f"Номер справки МСЭ: {dis_info.cert_number}." if dis_info.cert_number else ""))

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

    if case_data.benefits:
        parts.append(f"Заявленные льготы: {', '.join(case_data.benefits)}.")
    if case_data.documents:
        parts.append(f"Представленные документы: {', '.join(case_data.documents)}.")
    else:
         parts.append("Документы не представлены.")

    if case_data.has_incorrect_document:
        parts.append("Заявлено наличие некорректно оформленных документов.")

    # ДОБАВЛЕНИЕ ДАННЫХ ИЗ OTHER DOCUMENTS
    if case_data.other_documents_extracted_data:
        parts.append("\nСведения из дополнительных загруженных документов:")
        for i, doc_extract in enumerate(case_data.other_documents_extracted_data):
            parts.append(f"  Документ {i+1}:")
            # Добавляем стандартизированный тип, если есть, иначе идентифицированный
            doc_type_display = doc_extract.get("standardized_document_type") or doc_extract.get("identified_document_type") or "Тип не определен"
            parts.append(f"    Тип (по данным OCR): {doc_type_display}")
            
            extracted_fields = doc_extract.get("extracted_fields")
            if extracted_fields and isinstance(extracted_fields, dict) and extracted_fields:
                parts.append("    Извлеченные поля:")
                for key, value in extracted_fields.items():
                    parts.append(f"      - {key}: {value}")
            
            multimodal_assessment = doc_extract.get("multimodal_assessment")
            if multimodal_assessment:
                parts.append(f"    Оценка изображения: {multimodal_assessment}")
            
            # text_llm_reasoning может быть очень длинным, возможно, стоит его сокращать или не включать полностью
            text_llm_reasoning = doc_extract.get("text_llm_reasoning")
            if text_llm_reasoning:
                parts.append(f"    Осмысление текстовой LLM (начало): {text_llm_reasoning[:200]}...") # Пример сокращения

    return "\n".join(parts)

def analyze_rag_for_compliance(rag_text: str) -> bool:
    """ 
    Анализирует текст ответа RAG на наличие явной финальной фразы.
    Возвращает True, если найдена фраза 'ИТОГ: СООТВЕТСТВУЕТ',
    False - если найдена фраза 'ИТОГ: НЕ СООТВЕТСТВУЕТ'.
    Если ни одна фраза не найдена, возвращает False (считаем, что есть проблема).
    """
    if not isinstance(rag_text, str):
        print(f"[Compliance Check] ОШИБКА: Ожидался текст от RAG, но получен {type(rag_text)}: {rag_text}")
        return False
        
    lower_text = rag_text.lower()
    
    if "итог: соответствует" in lower_text.strip():
        print("[Compliance Check] Найдена фраза 'ИТОГ: СООТВЕТСТВУЕТ' -> СООТВЕТСТВУЕТ")
        return True
    elif "итог: не соответствует" in lower_text.strip():
        print("[Compliance Check] Найдена фраза 'ИТОГ: НЕ СООТВЕТСТВУЕТ' -> НЕ СООТВЕТСТВУЕТ")
        return False
    else:
        print("[Compliance Check] Четкая фраза ИТОГ не найдена -> ПРЕДПОЛАГАЕМ НЕ СООТВЕТСТВУЕТ")
        return False

@app.get("/")
async def read_root():
    return {"message": "PFR-AI Backend is running!"}

async def _call_rag_engine(request: Request, case_data: CaseDataInput, case_description: str, pension_type: Optional[str], disability_info: Optional[dict]) -> Tuple[str, float]:
    """Выполняет вызов RAG движка с обработкой ошибок."""
    rag_engine = request.app.state.rag_engine
    if rag_engine is None:
        print("!!! RAG Engine not available in _call_rag_engine")
        return "Ошибка: RAG движок недоступен.", 0.0

    try:
        print(f"Calling RAG Engine with pension_type: {pension_type}...")
        analysis_text, score = rag_engine.query( 
            case_data=case_data,
            case_description=case_description, 
            pension_type=pension_type, 
            disability_info=disability_info
        )
        print(f"RAG Engine call successful (Score: {score:.4f}) ")
        return analysis_text, score
    except Exception as e:
        print(f"!!! ERROR during RAG query call in _call_rag_engine: {e}")
        traceback.print_exc()
        return f"Ошибка выполнения RAG анализа: {e}", 0.0

@app.post("/api/v1/analyze_case", response_model=CaseAnalysisResponse)
async def analyze_pension_case(case_data: CaseDataInput, req: Request):
    case_description = format_case_description_for_rag(case_data)
    print(f"Received case analysis request (formatted description): {case_description[:150]}...")
    
    case_data_dict_json_compatible = case_data.model_dump(mode='json')
    analysis_text, score = await _call_rag_engine(
        request=req,
        case_data=case_data,
        case_description=case_description,
        pension_type=case_data.pension_type,
        disability_info=case_data_dict_json_compatible.get("disability")
    )
    
    if score == 0.0 and analysis_text.startswith("Ошибка"):
         print(f"RAG analysis failed: {analysis_text}")

    print(f"RAG analysis result for endpoint (score: {score:.4f}, start): {analysis_text[:100]}...")
    return CaseAnalysisResponse(analysis_result=analysis_text, confidence_score=score)

@app.post("/process", response_model=ProcessOutput)
async def process_case(request: Request, case_data: CaseDataInput, conn: AsyncConnection = Depends(get_db_connection)):
    try:
        case_description_full = format_case_description_for_rag(case_data)
        print("--- RAG Input Description (for /process) ---")
        print(case_description_full)
        print("--------------------------------------------")

        case_data_dict_json_compatible = case_data.model_dump(mode='json')
        rag_analysis_text, rag_confidence_score = await _call_rag_engine(
            request=request,
            case_data=case_data, 
            case_description=case_description_full,
            pension_type=case_data.pension_type,
            disability_info=case_data_dict_json_compatible.get("disability")
        )

        final_explanation_parts = []
        
        if rag_confidence_score > 0.0 or not rag_analysis_text.startswith("Ошибка"):
            # Если RAG сработал, добавляем его вывод в объяснение
            final_explanation_parts.append(f"Анализ системой RAG (уверенность: {rag_confidence_score*100:.1f}%):\n{rag_analysis_text}")
        else:
            # Если RAG вернул ошибку или нулевую уверенность
            final_explanation_parts.append(f"Анализ системой RAG не дал результата или завершился с ошибкой: {rag_analysis_text}")

        final_status_bool = analyze_rag_for_compliance(rag_analysis_text)
        final_status = "СООТВЕТСТВУЕТ" if final_status_bool else "НЕ СООТВЕТСТВУЕТ"
        final_explanation = "\n\n".join(final_explanation_parts)
        
        # Сохранение PersonalData отдельно, т.к. в crud.create_case оно ожидается как словарь
        personal_data_to_save = case_data_dict_json_compatible.get("personal_data")
        disability_data_for_db = case_data_dict_json_compatible.get("disability") # Для передачи в БД
        
        errors_to_save = [] # Пока что всегда пустой, но оставим для будущих доработок
        # Пример: если RAG вернул ошибку, можно добавить ее сюда
        if rag_analysis_text.startswith("Ошибка"):
            errors_to_save.append({
                "code": "RAG_ERROR",
                "description": rag_analysis_text,
                "law": "N/A",
                "recommendation": "Проверить лог RAG системы."
            })

        # Сохраняем данные в базу
        print(f"Attempting to save case. Final status: {final_status}, Explanation (start): {final_explanation[:100]}...")
        saved_case_id = await crud.create_case(
            conn=conn,
            personal_data=personal_data_to_save, 
            errors=errors_to_save,
            pension_type=case_data.pension_type,
            disability=disability_data_for_db, 
            work_experience=case_data_dict_json_compatible.get("work_experience"),
            pension_points=case_data.pension_points,
            benefits=case_data.benefits,
            documents=case_data.documents,
            has_incorrect_document=case_data.has_incorrect_document,
            final_status=final_status,
            final_explanation=final_explanation,
            rag_confidence=rag_confidence_score,
            other_documents_extracted_data=case_data_dict_json_compatible.get("other_documents_extracted_data")
        )
        print(f"Case with ID {saved_case_id} saved successfully.")

        return ProcessOutput(
            case_id=saved_case_id,
            final_status=final_status,
            explanation=final_explanation,
            confidence_score=rag_confidence_score
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"!!! Unhandled error in /process endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {e}")

@app.get("/history", response_model=List[CaseHistoryEntry])
async def get_history(
    skip: int = Query(0, ge=0), 
    limit: int = Query(10, ge=0, le=100), 
    db_conn: AsyncConnection = Depends(get_db_connection) # Используем AsyncConnection, как и было
):
    query = select(
        cases_table.c.id,
        cases_table.c.created_at, 
        cases_table.c.pension_type,
        cases_table.c.final_status,
        cases_table.c.final_explanation,
        cases_table.c.rag_confidence,
        cases_table.c.personal_data 
    ).select_from(cases_table).offset(skip).limit(limit).order_by(cases_table.c.created_at.desc()) # Сортировка по дате создания
    
    logger.info(f"Executing query for history: {query}")
    try:
        result = await db_conn.execute(query)
        history_records = result.fetchall()
        history_entries = []
        for record in history_records:
            entry_data_map = dict(record._mapping) # Преобразуем Row в dict
            
            # Парсим JSON строку personal_data
            personal_data_json = entry_data_map.get("personal_data")
            if personal_data_json:
                try:
                    # Заменяем строку JSON на объект PersonalData
                    entry_data_map["personal_data"] = PersonalData(**json.loads(personal_data_json))
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding personal_data JSON for case {entry_data_map.get('id')}: {e}")
                    entry_data_map["personal_data"] = None 
                except Exception as e_val:
                    logger.error(f"Error validating PersonalData for case {entry_data_map.get('id')}: {e_val}")
                    entry_data_map["personal_data"] = None
            else:
                entry_data_map["personal_data"] = None
            
            # Убедимся, что created_at это datetime, если оно извлекается как строка (хотя aiosqlite обычно типизирует)
            if isinstance(entry_data_map.get("created_at"), str):
                try:
                    entry_data_map["created_at"] = datetime.fromisoformat(entry_data_map["created_at"])
                except ValueError:
                     logger.error(f"Could not parse created_at string for case {entry_data_map.get('id')}: {entry_data_map.get('created_at')}")
                     # Можно установить в None или пробросить ошибку, если это критично
                     # Пока что, если парсинг не удался, Pydantic сам вызовет ошибку, что нам и нужно для отладки

            history_entries.append(CaseHistoryEntry(**entry_data_map))
        return history_entries
    except Exception as e:
        logger.error(f"Error fetching history endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error while fetching history: {str(e)}")

@app.get("/download_document/{case_id}")
async def download_document(
    case_id: int,
    format: DocumentFormat = DocumentFormat.pdf,
    conn: AsyncConnection = Depends(get_db_connection)
):
    case_data_db = await crud.get_case_by_id(conn, case_id=case_id)
    if case_data_db is None:
        raise HTTPException(status_code=404, detail="Дело не найдено")

    # Преобразуем RowProxy в словарь
    case_data = dict(case_data_db._mapping) if hasattr(case_data_db, '_mapping') else dict(case_data_db)

    # Десериализация JSON полей
    for key in ['personal_data', 'errors', 'disability', 'work_experience', 'benefits', 'documents']:
        if key in case_data and isinstance(case_data[key], str): # <--- Проверка на строку
            try:
                case_data[key] = json.loads(case_data[key])
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON for field '{key}' in case {case_id}. Value: {case_data[key]}") # Используем print, если logger не доступен/не настроен
                # Устанавливаем значение по умолчанию в зависимости от поля
                if key in ['errors', 'benefits', 'documents']:
                    case_data[key] = []
                elif key == 'personal_data': # Убедимся, что personal_data это dict или None
                    case_data[key] = None 
                else: # disability, work_experience
                    case_data[key] = None 
        elif key == 'personal_data' and not isinstance(case_data.get(key), dict) and case_data.get(key) is not None:
            # Если personal_data не строка и не dict, но не None (например, другой тип по ошибке), логируем и ставим None
            print(f"Warning: personal_data for case {case_id} is not a string or dict, setting to None. Type: {type(case_data[key])}")
            case_data[key] = None

    # Проверка наличия обязательных полей после преобразования
    # personal_data теперь может быть None, если парсинг не удался, но generate_document это учтет или вызовет ошибку там
    if not case_data.get("pension_type"): # personal_data может быть None
        raise HTTPException(status_code=500, detail="Недостаточно данных для генерации документа. Отсутствует тип пенсии.")
    
    personal_data_for_doc = case_data.get("personal_data")
    if not personal_data_for_doc: # Если personal_data None после всех попыток
        # Вместо ошибки, передадим пустой словарь, generate_document должен его обработать (например, маскировщик вернет дефолтные значения)
        # или же, если это критично, то здесь можно выдать ошибку.
        # Пока что передаем пустой, т.к. masked_personal_data должен справиться
        print(f"Warning: personal_data for case {case_id} is missing or invalid. Proceeding with empty personal data for document generation.")
        personal_data_for_doc = {}

    try:
        file_buffer, filename, mimetype = services.generate_document(
            personal_data=personal_data_for_doc, 
            pension_type=case_data["pension_type"],
            final_status=case_data["final_status"],
            explanation=case_data["final_explanation"],
            case_id=case_id,
            document_format=format.value, # format это Enum, его значение это строка "pdf" или "docx"
            errors=case_data.get("errors", []) 
        )
        return StreamingResponse(file_buffer, media_type=mimetype, headers={"Content-Disposition": f"attachment; filename={filename}"})
    except ValueError as ve:
        print(f"Value error during document generation: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error generating document for case {case_id}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка генерации документа: {e}")

@app.post("/extract_document_data")
async def extract_document_data_endpoint(
    document_type: DocumentTypeToExtract = Form(...),
    image: UploadFile = File(...)
):
    """
    Извлекает структурированные данные из изображения документа (паспорт РФ или СНИЛС).

    - **document_type**: Тип документа ('passport', 'snils', 'other').
    - **image**: Файл изображения.
    """
    if not image.content_type or not image.content_type.startswith("image/"):
        logger.error(f"Попытка загрузки не-изображения: {image.filename}, тип: {image.content_type}")
        # Возвращаем ошибку в формате, который может ожидать OcrExtractionResponse.error
        return {
            "documentType": "error",
            "message": "Неверный тип файла. Пожалуйста, загрузите изображение.",
            "errorDetails": {"filename": image.filename, "contentType": image.content_type}
        }

    logger.info(f"Получено изображение для извлечения данных ({document_type.value}): {image.filename}, тип: {image.content_type}")
    
    try:
        image_content = await image.read()
        extracted_data_object = await vision_services.extract_document_data_from_image(
            image_bytes=image_content, 
            document_type=document_type,
            filename=image.filename # Передаем filename в vision_services, если он там используется
        )

        # Формируем правильный ответ для фронтенда
        if extracted_data_object:
            logger.info(f"Успешно извлечены данные для {document_type.value}: {image.filename}")
            return {
                "documentType": document_type.value,
                "data": extracted_data_object
            }
        else:
            # Этот случай (когда vision_services возвращает None) должен обрабатываться внутри vision_services
            # и он должен был бы выбросить HTTPException, если не смог извлечь.
            # Если мы дошли сюда и extracted_data_object это None, значит что-то не так в логике vision_services
            # или он может легитимно вернуть None, если документ пустой, но это плохая практика.
            # Для надежности, если такое произошло, вернем ошибку.
            logger.warning(f"Не удалось извлечь данные для {document_type.value} из {image.filename}. Сервис vision_services вернул None.")
            return {
                "documentType": "error",
                "message": f"Не удалось извлечь данные из документа ({document_type.value}). Сервис не вернул данных.",
                "errorDetails": {"filename": image.filename}
            }
            
    except HTTPException as http_exc: # Перехватываем HTTPException из vision_services
        logger.warning(f"HTTPException при обработке {document_type.value} для {image.filename}: {http_exc.detail}")
        return {
            "documentType": "error",
            "message": http_exc.detail, # Сообщение из HTTPException
            "errorDetails": {"status_code": http_exc.status_code, "filename": image.filename}
        }
    except Exception as e:
        logger.error(f"Ошибка в эндпоинте /extract_document_data ({document_type.value}) для {image.filename}: {e}", exc_info=True)
        return {
            "documentType": "error",
            "message": f"Внутренняя ошибка сервера при обработке документа ({document_type.value}).",
            "errorDetails": {"error_type": type(e).__name__, "filename": image.filename}
        }

# --- ЭНДПОИНТ ДЛЯ ПОЛУЧЕНИЯ СПИСКА ТИПОВ ПЕНСИЙ (для фронтенда) ---
@app.get("/api/v1/pension_types")
async def get_pension_types():
    return PENSION_TYPE_CHOICES 