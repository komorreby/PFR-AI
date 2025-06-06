from fastapi import FastAPI, HTTPException, Depends, Request, File, UploadFile, Form, Query, BackgroundTasks, status, Path
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from app.rag_core.engine import PensionRAG, KnowledgeGraphBuilder
from .models import (
    CaseDataInput, ProcessOutput, CaseHistoryEntry, DocumentFormat, DisabilityInfo, 
    PersonalData, DocumentTypeToExtract, OtherDocumentData,
    ErrorDetail, FullCaseData, StandardErrorResponse
)
from .config_models.config_models import DocumentDetail, PensionTypeInfo, PensionTypeDocuments
from .config_loader import load_configuration, get_standard_document_names_from_config

from .database import create_db_and_tables, get_db_connection, async_engine, cases_table
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql import select, text, delete
from sqlalchemy.exc import SQLAlchemyError
from . import crud
from . import services
from typing import List, Optional, Tuple, Dict, Any, Union
import traceback
import json
from . import vision_services
import logging
from datetime import datetime, timedelta
import asyncio
import uuid
import time
import httpx
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordRequestForm
from . import auth, models
import os

logger = logging.getLogger(__name__)
logger_bg = logging.getLogger(__name__ + ".background")

async def validate_pension_type_dependency(
    request: Request,
    case_data: CaseDataInput
):
    logger.debug(f"Запуск зависимости validate_pension_type_dependency для типа: {case_data.pension_type}")
    if not hasattr(request.app.state, 'pension_types_config') or not request.app.state.pension_types_config:
        logger.error("Конфигурация типов пенсий не загружена в validate_pension_type_dependency.")
        raise HTTPException(status_code=503, detail="Сервис временно недоступен: конфигурация типов пенсий не загружена.")
    
    valid_pension_type_ids = {pt.id for pt in request.app.state.pension_types_config}
    if case_data.pension_type not in valid_pension_type_ids:
        logger.warning(f"Недопустимый тип пенсии '{case_data.pension_type}' получен в запросе. Допустимые: {valid_pension_type_ids}")
        raise HTTPException(
            status_code=422,
            detail=f"Недопустимый тип пенсии: '{case_data.pension_type}'. Допустимые типы: {', '.join(valid_pension_type_ids)}."
        )
    logger.debug(f"Тип пенсии '{case_data.pension_type}' прошел валидацию в зависимости.")
    return case_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag_engine = None
    logger.info("Starting up...")
    logger.info("Creating DB tables if they don't exist...")
    await asyncio.to_thread(create_db_and_tables)
    
    logger.info("Loading pension configurations...")
    try:
        app.state.pension_types_config, app.state.document_requirements_config = await asyncio.to_thread(load_configuration)
        logger.info(f"Loaded {len(app.state.pension_types_config)} pension types and requirements for {len(app.state.document_requirements_config)} types.")
        
        app.state.standard_document_names = get_standard_document_names_from_config(
            app.state.document_requirements_config
        )
        logger.info(f"Loaded {len(app.state.standard_document_names)} standard document names.")
        logger.info(f"Standard document names loaded: {app.state.standard_document_names}")

    except Exception as e:
        logger.error(f"!!! ERROR loading pension configurations or standard doc names: {e}", exc_info=True)
        app.state.pension_types_config = []
        app.state.document_requirements_config = {}
        app.state.standard_document_names = []
    
    logger.info("Initializing PensionRAG Engine...")
    try:
        app.state.rag_engine = PensionRAG()
        await app.state.rag_engine.async_init(
            pension_types_config=app.state.pension_types_config,
            document_requirements_config=app.state.document_requirements_config
        )
        logger.info("PensionRAG Engine initialized with async_init.")
    except Exception as e_rag_init:
        logger.error(f"!!! ERROR initializing PensionRAG Engine (async_init): {e_rag_init}", exc_info=True)
        traceback.print_exc()
        app.state.rag_engine = None
    logger.info("Startup complete.")
    yield
    logger.info("Shutting down...")
    if app.state.rag_engine and hasattr(app.state.rag_engine, 'graph_builder') and app.state.rag_engine.graph_builder:
        try:
            logger.info("Closing Neo4j connection in graph_builder...")
            await asyncio.to_thread(app.state.rag_engine.graph_builder.close)
            logger.info("Neo4j connection in graph_builder closed.")
        except Exception as e:
            logger.error(f"Error closing Neo4j connection in graph_builder: {e}", exc_info=True)
            
    await async_engine.dispose()
    logger.info("Database connection pool closed.")
    logger.info("Shutdown complete.")

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def format_case_description_for_rag_background(
    case_data: CaseDataInput,
    pension_types_config: List[PensionTypeInfo],
    document_requirements_config: Dict[str, PensionTypeDocuments]
    ) -> str:
    parts = []
    pd = case_data.personal_data
    full_name = " ".join(filter(None, [pd.last_name, pd.first_name, pd.middle_name]))
    parts.append(f"Заявитель: {full_name}, Дата рождения: {pd.birth_date.strftime('%d.%m.%Y')}, Пол: {pd.gender}, Гражданство: {pd.citizenship}, Иждивенцы: {pd.dependents}.")
    if pd.name_change_info:
        parts.append(f"Была смена ФИО: Старое ФИО: {pd.name_change_info.old_full_name or 'Не указ.'}, Дата: {pd.name_change_info.date_changed.strftime('%d.%m.%Y') if pd.name_change_info.date_changed else 'Не указ.'}.")

    pension_type_info = next((pt for pt in pension_types_config if pt.id == case_data.pension_type), None)
    pension_type_display_name = pension_type_info.display_name if pension_type_info else case_data.pension_type
    parts.append(f"Запрашиваемый тип пенсии: {pension_type_display_name}.")

    if case_data.disability:
        dis_info = case_data.disability
        group_text = f"{dis_info.group} группа" if dis_info.group != 'child' else "Ребенок-инвалид"
        parts.append(f"Инвалидность: {group_text}, Дата установления: {dis_info.date.strftime('%d.%m.%Y')}. " +
                        (f"Номер справки МСЭ: {dis_info.cert_number}." if dis_info.cert_number else ""))

    if case_data.pension_type == 'retirement_standard' and case_data.work_experience:
        we = case_data.work_experience
        parts.append(f"Общий страховой стаж: {we.calculated_total_years or 0.0} лет.")
        parts.append(f"Пенсионные баллы (ИПК): {case_data.pension_points or 'Не указаны'}.")
        
        if we.records:
            parts.append("Записи о стаже (обработанные периоды):")
            for i, r in enumerate(we.records):
                start_date_str = r.date_in.strftime('%d.%m.%Y') if r.date_in else '?'
                end_date_str = r.date_out.strftime('%d.%m.%Y') if r.date_out else 'н.в.'
                period_str = f"{start_date_str} - {end_date_str}"
                
                org_info = r.organization or "Организация не указана"
                pos_info = r.position or "Должность не указана"
                
                parts.append(f"  {i+1}. {org_info}, Должность: {pos_info} ({period_str}).")
        else:
            parts.append("Записи о стаже отсутствуют.")
    
    if case_data.benefits:
        parts.append(f"Заявленные льготы: {', '.join(case_data.benefits)}.")
    
    if case_data.submitted_documents:
        doc_details_map = {}
        for pt_id_cfg, pension_reqs_cfg in document_requirements_config.items():
            for doc_cfg in pension_reqs_cfg.documents:
                doc_details_map[doc_cfg.id] = doc_cfg
        
        doc_ids = ", ".join(case_data.submitted_documents)
        doc_names_list = []
        for doc_id_submitted in case_data.submitted_documents:
            doc_detail_obj = doc_details_map.get(doc_id_submitted)
            if doc_detail_obj:
                doc_names_list.append(doc_detail_obj.name)
            else:
                doc_names_list.append(f"Неизвестный документ ({doc_id_submitted})")
        doc_names = ", ".join(doc_names_list)

        parts.append(f"Представленные документы (ID): {doc_ids}.")
        parts.append(f"Представленные документы (названия): {doc_names}.")
    else:
        parts.append("Документы не представлены.")

    if case_data.has_incorrect_document:
        parts.append("Заявлено наличие некорректно оформленных документов.")

    if case_data.other_documents_extracted_data:
        parts.append("\nСведения из дополнительных загруженных документов:")
        for i, doc_extract in enumerate(case_data.other_documents_extracted_data):
            parts.append(f"  Документ {i+1}:")
            doc_type_display = doc_extract.get("standardized_document_type") or doc_extract.get("identified_document_type") or "Тип не определен"
            parts.append(f"    Тип (по данным OCR): {doc_type_display}")
            extracted_fields = doc_extract.get("extracted_fields")
            if extracted_fields and isinstance(extracted_fields, dict) and extracted_fields:
                parts.append("    Извлеченные поля:")
                for key_val, val_val in extracted_fields.items():
                    parts.append(f"      - {key_val}: {val_val}")
            multimodal_assessment = doc_extract.get("multimodal_assessment")
            if multimodal_assessment:
                parts.append(f"    Оценка изображения: {multimodal_assessment}")
            text_llm_reasoning = doc_extract.get("text_llm_reasoning")
            if text_llm_reasoning:
                parts.append(f"    Осмысление текстовой LLM (начало): {text_llm_reasoning[:200]}...")
    return "\n".join(parts)

def analyze_rag_for_compliance(rag_text: str) -> bool:
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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error['loc']) if error['loc'] else "body"
        error_details.append({
            "field": field,
            "message": error['msg'],
            "type": error['type']
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=StandardErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Ошибка валидации входных данных.",
            details=error_details
        ).model_dump(exclude_none=True)
    )

@app.get(
    "/api/v1/cases/history", 
    response_model=List[CaseHistoryEntry],
    summary="Получить историю дел",
    description="Возвращает список всех дел с возможностью пагинации.",
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Внутренняя ошибка сервера при получении истории дел"}
    },
    dependencies=[Depends(auth.require_manager_role)]
)
async def get_history(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(10, ge=0, le=100, description="Максимальное количество записей для возврата"),
    db_conn: AsyncConnection = Depends(get_db_connection),
    current_user_with_role: Dict[str, Any] = Depends(auth.require_manager_role)
):
    logger.info(f"User '{current_user_with_role['username']}' (role: {current_user_with_role['role']}) accessed case history.")
    query = select(
        cases_table.c.id,
        cases_table.c.created_at, 
        cases_table.c.pension_type,
        cases_table.c.final_status,
        cases_table.c.final_explanation,
        cases_table.c.rag_confidence,
        cases_table.c.personal_data 
    ).select_from(cases_table).offset(skip).limit(limit).order_by(cases_table.c.created_at.desc())
    
    logger.debug(f"Executing query for history: {query}")
    try:
        result = await db_conn.execute(query)
        history_records = result.fetchall()
        history_entries = []
        for record in history_records:
            entry_data_map = dict(record._mapping)
            
            personal_data_json = entry_data_map.get("personal_data")
            if personal_data_json:
                try:
                    entry_data_map["personal_data"] = PersonalData(**json.loads(personal_data_json))
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding personal_data JSON for case {entry_data_map.get('id')}: {e}")
                    entry_data_map["personal_data"] = None 
                except Exception as e_val:
                    logger.error(f"Error validating PersonalData for case {entry_data_map.get('id')}: {e_val}")
                    entry_data_map["personal_data"] = None
            else:
                entry_data_map["personal_data"] = None
            
            if isinstance(entry_data_map.get("created_at"), str):
                try:
                    entry_data_map["created_at"] = datetime.fromisoformat(entry_data_map["created_at"])
                except ValueError:
                     logger.error(f"Could not parse created_at string for case {entry_data_map.get('id')}: {entry_data_map.get('created_at')}")

            history_entries.append(CaseHistoryEntry(**entry_data_map))
        return history_entries
    except Exception as e:
        logger.error(f"Error fetching history endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error while fetching history: {str(e)}")

@app.get(
    "/api/v1/cases/{case_id}/document",
    summary="Скачать документ по делу",
    description="Позволяет скачать сгенерированный документ для указанного дела в формате PDF или DOCX.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Дело с указанным ID не найдено или документ для него не готов"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Внутренняя ошибка сервера при генерации или скачивании документа"}
    },
    dependencies=[Depends(auth.require_manager_role)]
)
async def download_document(
    request: Request,
    case_id: int = Path(..., description="Уникальный идентификатор дела"),
    format: DocumentFormat = Query(..., description="Формат документа: pdf или docx"),
    conn: AsyncConnection = Depends(get_db_connection),
    current_user_with_role: Dict[str, Any] = Depends(auth.require_manager_role)
):
    logger.info(f"User '{current_user_with_role['username']}' (role: {current_user_with_role['role']}) requested document for case {case_id} in format {format.value}.")
    case_data_db = await crud.get_case_by_id(conn, case_id=case_id)
    if case_data_db is None:
        logger.warning(f"Case {case_id} not found for document generation.")
        raise HTTPException(status_code=404, detail="Дело не найдено")

    # Преобразуем RowProxy в словарь, если это необходимо
    # и десериализуем JSON поля.
    # Важно: теперь мы ожидаем, что case_data_db уже содержит ВСЕ необходимые поля
    # для детализированного документа. Если crud.get_case_by_id не возвращает все,
    # его нужно будет доработать.
    try:
        # Попытка создать словарь из db_case_row, если это объект Row или похожий
        case_data_dict = dict(case_data_db._mapping if hasattr(case_data_db, '_mapping') else case_data_db)
        
        # Десериализация JSON полей (этот код уже был, но теперь он более критичен)
        for key in ['personal_data', 'errors', 'disability', 'work_experience', 'benefits', 'submitted_documents', 'other_documents_extracted_data']:
            if key in case_data_dict and isinstance(case_data_dict[key], str):
                try:
                    case_data_dict[key] = json.loads(case_data_dict[key])
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode JSON for field '{key}' in case {case_id}. Value: {case_data_dict[key]}")
                    # Устанавливаем значения по умолчанию, если парсинг не удался, чтобы избежать ошибок далее
                    if key in ['errors', 'benefits', 'submitted_documents', 'other_documents_extracted_data']:
                        case_data_dict[key] = [] if key not in ['other_documents_extracted_data'] else None # Для other_documents_extracted_data может быть None
                    elif key == 'personal_data':
                         case_data_dict[key] = {} # Пустой словарь для персональных данных
                    else:
                        case_data_dict[key] = None 
            elif key == 'personal_data' and not isinstance(case_data_dict.get(key), dict) and case_data_dict.get(key) is not None:
                logger.warning(f"personal_data for case {case_id} is not a string or dict, setting to empty dict. Type: {type(case_data_dict[key])}")
                case_data_dict[key] = {}
            elif key == 'personal_data' and case_data_dict.get(key) is None: # Если personal_data отсутствует вообще
                logger.warning(f"personal_data is missing for case {case_id}. Setting to empty dict.")
                case_data_dict[key] = {} 

        # Проверка наличия конфигураций в app.state
        if not hasattr(request.app.state, 'pension_types_config') or not request.app.state.pension_types_config:
            logger.error("Pension types configuration not found in app.state for document generation.")
            raise HTTPException(status_code=503, detail="Ошибка конфигурации сервера: типы пенсий не загружены.")
        
        if not hasattr(request.app.state, 'document_requirements_config') or not request.app.state.document_requirements_config:
            logger.error("Document requirements configuration not found in app.state for document generation.")
            raise HTTPException(status_code=503, detail="Ошибка конфигурации сервера: требования к документам не загружены.")

        pension_types_list_config = request.app.state.pension_types_config
        doc_requirements_config = request.app.state.document_requirements_config

    except Exception as e_prepare:
        logger.error(f"Error preparing data for document generation for case {case_id}: {e_prepare}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка подготовки данных для документа: {e_prepare}")

    if not case_data_dict.get("pension_type"):
        logger.error(f"Missing pension_type in case data for case_id {case_id} during document generation.")
        raise HTTPException(status_code=500, detail="Недостаточно данных для генерации документа (отсутствует тип пенсии).")
    
    try:
        file_buffer, filename, mimetype = await services.generate_document(
            case_details=case_data_dict, # Передаем весь словарь с данными дела
            pension_types_list_config=pension_types_list_config, # Передаем конфигурацию типов пенсий
            doc_requirements_config=doc_requirements_config, # Передаем конфигурацию требований к документам
            document_format=format,
        )
        logger.info(f"Document {filename} (type: {mimetype}) generated successfully for case {case_id}.")
        return StreamingResponse(file_buffer, media_type=mimetype, headers={"Content-Disposition": f"attachment; filename={filename}"})
    except ValueError as ve:
        logger.error(f"Value error during document generation for case {case_id}: {ve}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error generating document for case {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка генерации документа: {e}")

class OcrTaskSubmitResponse(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "PROCESSING"
    message: str = "Документ принят на обработку. Проверьте статус позже."

class OcrTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class TasksStatsResponse(BaseModel):
    total: int
    pending: int
    expired_processing: int
    status_specific_counts: Dict[str, int] 

async def cleanup_expired_tasks():
    while True:
        try:
            async with async_engine.connect() as conn:
                deleted_count = await crud.delete_expired_ocr_tasks(conn)
                if deleted_count > 0:
                    logger.info(f"Удалено {deleted_count} просроченных OCR задач")
            await asyncio.sleep(3600)
        except Exception as e:
            logger.error(f"Ошибка при очистке просроченных OCR задач: {e}", exc_info=True)
            await asyncio.sleep(300)

from typing import Dict, Optional, Callable, Any
import time

class TTLCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        
    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
            
        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl_seconds:
            del self.cache[key]
            return None
            
        return value
        
    def set(self, key: str, value: Any):
        self.cache[key] = (value, time.time())
        
    def remove_expired(self):
        now = time.time()
        expired_keys = [k for k, (_, ts) in self.cache.items() if now - ts > self.ttl_seconds]
        for key in expired_keys:
            del self.cache[key]

ocr_results_cache = TTLCache(ttl_seconds=1800)

async def extract_data_in_background(
    task_id: str,
    image_bytes: bytes,
    document_type: DocumentTypeToExtract,
    filename: Optional[str],
    standard_document_names_from_state: List[str]
):
    try:
        extracted_data_object = await vision_services.extract_document_data_from_image(
            image_bytes=image_bytes,
            document_type=document_type,
            filename=filename,
            standard_document_names=standard_document_names_from_state
        )
        
        data_to_store = extracted_data_object.model_dump(mode='json') if extracted_data_object else None

        async with async_engine.connect() as conn:
            async with conn.begin():
                success = await crud.update_ocr_task_result(
                    conn=conn,
                    task_id=task_id,
                    status="COMPLETED",
                    data=data_to_store 
                )
            
            if success and data_to_store:
                ocr_results_cache.set(task_id, {
                    "status": "COMPLETED",
                    "data": data_to_store,
                    "error": None
                })
                
        logger_bg.info(f"Фоновая задача извлечения данных для task_id {task_id} успешно выполнена")
        
    except HTTPException as he:
        error_data = {"detail": he.detail, "status_code": he.status_code}
        async with async_engine.connect() as conn:
            async with conn.begin():
                await crud.update_ocr_task_result(
                    conn=conn,
                    task_id=task_id,
                    status="FAILED",
                    error=error_data
                )
            ocr_results_cache.set(task_id, {"status": "FAILED", "data": None, "error": error_data})
            logger_bg.warning(f"HTTPException в фоновой задаче OCR для task_id {task_id}: {he.detail}")
        
    except Exception as e:
        logger_bg.error(f"Ошибка в фоновой задаче OCR extract_data_in_background для task_id {task_id}: {e}", exc_info=True)
        error_data = {"detail": str(e), "type": type(e).__name__}
        async with async_engine.connect() as conn:
            async with conn.begin():
                await crud.update_ocr_task_result(
                    conn=conn,
                    task_id=task_id,
                    status="FAILED",
                    error=error_data
                )
            ocr_results_cache.set(task_id, {"status": "FAILED", "data": None, "error": error_data})

@app.post(
    "/api/v1/document_extractions", 
    response_model=OcrTaskSubmitResponse, 
    status_code=202,
    dependencies=[Depends(auth.require_manager_role)]
)
async def submit_document_for_extraction(
    request: Request,
    background_tasks: BackgroundTasks,
    document_type: DocumentTypeToExtract = Form(...),
    image: UploadFile = File(...),
    ttl_hours: Optional[int] = Query(24, description="Время жизни задачи в часах", ge=1, le=168),
    conn: AsyncConnection = Depends(get_db_connection),
    current_user_with_role: Dict[str, Any] = Depends(auth.require_manager_role)
):
    logger.info(f"User '{current_user_with_role['username']}' (role: {current_user_with_role['role']}) submitted document for extraction: {document_type.value}, file: {image.filename}, TTL: {ttl_hours}ч")
    
    if not image.content_type or image.content_type not in ALLOWED_IMAGE_MIME_TYPES:
        logger.warning(f"Попытка загрузки файла с недопустимым MIME-типом для OCR: {image.filename}, тип: {image.content_type}. Разрешенные: {ALLOWED_IMAGE_MIME_TYPES}")
        raise HTTPException(
            status_code=400, 
            detail=f"Неверный тип файла: {image.content_type}. Пожалуйста, загрузите изображение одного из следующих форматов: {', '.join(ALLOWED_IMAGE_MIME_TYPES)}."
        )

    image_bytes = await image.read()

    if len(image_bytes) > MAX_FILE_SIZE_BYTES:
        logger.warning(f"Попытка загрузки слишком большого файла для OCR: {image.filename}, размер: {len(image_bytes)} байт. Максимум: {MAX_FILE_SIZE_BYTES} байт.")
        raise HTTPException(
            status_code=413, 
            detail=f"Размер файла {image.filename} ({len(image_bytes)/(1024*1024):.2f} МБ) превышает максимально допустимый ({MAX_FILE_SIZE_MB} МБ)."
        )
    
    task_id = str(uuid.uuid4()) 

    try:
        async with conn.begin():
            await crud.create_ocr_task(
                conn=conn,
                task_id=task_id,
                document_type=document_type.value,
                filename=image.filename,
                ttl_hours=ttl_hours
            )
    except ValueError as e:
        logger.error(f"Ошибка при создании OCR задачи в БД: {e}")
        raise HTTPException(status_code=500, detail=f"Не удалось создать задачу для обработки документа: {e}")
    
    logger.debug(f"Создана задача OCR с task_id: {task_id} в БД, начальный статус PROCESSING.")

    background_tasks.add_task(
        extract_data_in_background,
        task_id=task_id,
        image_bytes=image_bytes, 
        document_type=document_type,
        filename=image.filename,
        standard_document_names_from_state=request.app.state.standard_document_names
    )
    logger.info(f"Запущена фоновая задача OCR для task_id: {task_id}")

    return OcrTaskSubmitResponse(task_id=task_id)

@app.get(
    "/api/v1/document_extractions/{task_id}", 
    response_model=OcrTaskStatusResponse,
    dependencies=[Depends(auth.require_manager_role)]
)
async def get_document_extraction_status(
    task_id: str,
    conn: AsyncConnection = Depends(get_db_connection),
    current_user_with_role: Dict[str, Any] = Depends(auth.require_manager_role)
):
    logger.info(f"User '{current_user_with_role['username']}' (role: {current_user_with_role['role']}) requested status for OCR task {task_id}.")
    cached_result = ocr_results_cache.get(task_id)
    if cached_result:
        logger.debug(f"Результат для задачи OCR task_id: {task_id} найден в кеше.")
        return OcrTaskStatusResponse(task_id=task_id, **cached_result)
    
    logger.debug(f"Результат для задачи OCR task_id: {task_id} не найден в кеше, обращаемся к БД.")
    task_db_result = await crud.get_ocr_task(conn, task_id)
    if not task_db_result:
        logger.warning(f"Задача OCR с task_id: {task_id} не найдена в БД.")
        raise HTTPException(status_code=404, detail="Задача извлечения не найдена.")
    
    response_data = {
        "status": task_db_result["status"],
        "data": task_db_result.get("data"),
        "error": task_db_result.get("error")
    }
    
    if task_db_result["status"] in ["COMPLETED", "FAILED"]:
        ocr_results_cache.set(task_id, response_data)
        logger.debug(f"Результат для задачи OCR task_id: {task_id} (статус: {task_db_result['status']}) сохранен в кеш.")
    
    return OcrTaskStatusResponse(task_id=task_id, **response_data)

@app.get(
    "/api/v1/tasks/stats", 
    response_model=TasksStatsResponse,
    dependencies=[Depends(auth.require_manager_role)]
)
async def get_tasks_stats(
    conn: AsyncConnection = Depends(get_db_connection),
    current_user_with_role: Dict[str, Any] = Depends(auth.require_manager_role)
):
    logger.info(f"User '{current_user_with_role['username']}' (role: {current_user_with_role['role']}) requested OCR tasks statistics.")
    try:
        stats_from_crud = await crud.get_ocr_tasks_stats(conn)
        
        response_data = {
            "total": stats_from_crud.get("total", 0),
            "pending": stats_from_crud.get("pending", 0),
            "expired_processing": stats_from_crud.get("expired_processing", 0),
            "status_specific_counts": {
                status: count for status, count in stats_from_crud.items()
                if status not in ["total", "pending", "expired_processing"]
            }
        }
        return TasksStatsResponse(**response_data)
    except Exception as e:
        logger.error(f"Ошибка при получении статистики по OCR задачам: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статистики: {str(e)}")

@app.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(cleanup_expired_tasks())
    logger.info("Запущена фоновая задача очистки просроченных OCR задач")

@app.get(
    "/api/v1/pension_types",
    summary="Получить список типов пенсий",
    description="Возвращает список всех доступных для выбора типов пенсий с их идентификаторами и отображаемыми именами.",
    response_model=List[Dict[str, str]],
    dependencies=[Depends(auth.get_current_user_data)]
)
async def get_pension_types(
    request: Request,
    current_user: Dict[str, Any] = Depends(auth.get_current_user_data)
):
    logger.info(f"User '{current_user['username']}' requested pension types.")
    if not request.app.state.pension_types_config:
        raise HTTPException(status_code=503, detail="Конфигурация типов пенсий не загружена.")
    return [{"id": pt.id, "display_name": pt.display_name, "description": pt.description} 
            for pt in request.app.state.pension_types_config]

@app.get(
    "/api/v1/pension_documents/{pension_type_id}", 
    response_model=List[DocumentDetail],
    dependencies=[Depends(auth.get_current_user_data)]
)
async def get_pension_type_documents(
    pension_type_id: str, 
    request: Request,
    current_user: Dict[str, Any] = Depends(auth.get_current_user_data)
):
    logger.info(f"User '{current_user['username']}' requested documents for pension type {pension_type_id}.")
    if not request.app.state.document_requirements_config:
        raise HTTPException(status_code=503, detail="Конфигурация требований к документам не загружена.")
    
    requirements = request.app.state.document_requirements_config.get(pension_type_id)
    if not requirements:
        raise HTTPException(status_code=404, detail=f"Требования для типа пенсии '{pension_type_id}' не найдены.")
    return requirements.documents 

rag_results_cache = TTLCache(ttl_seconds=3600)

async def process_case_in_background(
    case_id: int,
    case_data_dict: dict,
    rag_engine: PensionRAG,
    pension_types_config: List[PensionTypeInfo],
    document_requirements_config: Dict[str, PensionTypeDocuments]
):
    logger_bg.info(f"Начало фоновой обработки для case_id: {case_id}")
    try:
        cache_key = f"rag_case_{case_data_dict.get('pension_type')}_{hash(str(case_data_dict))}"
        cached_result = rag_results_cache.get(cache_key)
        
        if cached_result:
            logger_bg.info(f"Найдены кешированные результаты RAG анализа для дела #{case_id} (кеш-ключ: {cache_key[:20]}...)")
            final_status, final_explanation, rag_confidence_score = cached_result
            
            async with async_engine.connect() as conn:
                async with conn.begin():
                    updated = await crud.update_case_results(
                        conn=conn,
                        case_id=case_id,
                        final_status=final_status,
                        final_explanation=f"{final_explanation}\n\n(Результат получен из кеша)",
                        rag_confidence=rag_confidence_score
                    )
                if updated:
                    logger_bg.info(f"Дело #{case_id} обновлено из кеша успешно")
                else:
                    logger_bg.warning(f"Дело #{case_id} не удалось обновить из кеша")
                    
            return
        
        case_data_for_rag = CaseDataInput(**case_data_dict)
        
        case_description_full = format_case_description_for_rag_background(
            case_data_for_rag, 
            pension_types_config,
            document_requirements_config
        )
        
        logger_bg.info(f"Начало фонового RAG анализа для дела #{case_id}")
        logger_bg.debug(f"--- RAG Input Description (background for case_id {case_id}) ---")
        logger_bg.debug(case_description_full[:500] + "...")
        
        start_time = time.time()
        
        rag_analysis_text, rag_confidence_score = await rag_engine.query(
            case_data=case_data_for_rag,
            case_description=case_description_full,
            pension_type=case_data_for_rag.pension_type,
            disability_info=case_data_dict.get("disability")
        )
        
        execution_time = time.time() - start_time
        logger_bg.info(f"RAG анализ для дела #{case_id} завершен за {execution_time:.2f} сек с уверенностью {rag_confidence_score:.4f}")
        
        final_status_bool = analyze_rag_for_compliance(rag_analysis_text)
        final_status = "СООТВЕТСТВУЕТ" if final_status_bool else "НЕ СООТВЕТСТВУЕТ"
        if rag_analysis_text.startswith("Ошибка"):
            final_explanation = rag_analysis_text
        else:
            final_explanation = f"Анализ системой RAG (уверенность: {rag_confidence_score*100:.1f}%):\n{rag_analysis_text}"

        
        rag_results_cache.set(cache_key, (final_status, final_explanation, rag_confidence_score))
        
        async with async_engine.connect() as conn:
            async with conn.begin():
                updated = await crud.update_case_results(
                    conn=conn,
                    case_id=case_id,
                    final_status=final_status,
                    final_explanation=final_explanation,
                    rag_confidence=rag_confidence_score
                )
            if updated:
                logger_bg.info(f"Фоновая обработка для дела #{case_id} завершена успешно, обновление БД выполнено.")
            else:
                logger_bg.warning(f"Фоновая обработка для дела #{case_id} завершена, но запись в БД не была обновлена.")
        
    except Exception as e:
        logger_bg.error(f"Ошибка в фоновой задаче process_case_in_background для дела #{case_id}: {e}", exc_info=True)
        error_message = f"Внутренняя ошибка при обработке дела: {str(e)}"
        try:
            async with async_engine.connect() as conn:
                async with conn.begin():
                    await crud.update_case_status_and_error(
                        conn, case_id, "ERROR_PROCESSING", error_message
                    )
            logger_bg.info(f"Фоновая обработка для case_id {case_id} завершена с ошибкой.")
        except Exception as update_error:
            logger_bg.error(f"Не удалось обновить статус на ERROR_PROCESSING для дела #{case_id}: {update_error}", exc_info=True)

@app.post("/api/v1/cases", response_model=ProcessOutput, status_code=202)
async def submit_case_for_processing(
    request: Request,
    background_tasks: BackgroundTasks,
    case_data: CaseDataInput = Depends(validate_pension_type_dependency), 
    conn: AsyncConnection = Depends(get_db_connection),
    current_user_with_role: Dict[str, Any] = Depends(auth.require_manager_role)
):
    logger.info(f"User '{current_user_with_role['username']}' (role: {current_user_with_role['role']}) submitted case for processing: type {case_data.pension_type}")
    logger.info(f"Получен запрос на создание и обработку дела для типа пенсии: {case_data.pension_type}")
    personal_data_dict = case_data.personal_data.model_dump(mode='json')
    disability_dict = case_data.disability.model_dump(mode='json') if case_data.disability else None
    work_experience_dict = case_data.work_experience.model_dump(mode='json') if case_data.work_experience else {}
    
    other_docs_data = case_data.other_documents_extracted_data

    async with conn.begin(): 
        case_id = await crud.create_case(
            conn=conn,
            personal_data=personal_data_dict,
            errors=[], 
            pension_type=case_data.pension_type,
            disability=disability_dict,
            work_experience=work_experience_dict,
            pension_points=case_data.pension_points,
            benefits=case_data.benefits,
            submitted_documents=case_data.submitted_documents,
            has_incorrect_document=case_data.has_incorrect_document,
            final_status="PROCESSING",
            final_explanation="Дело принято и находится в процессе автоматической обработки.",
            rag_confidence=None, 
            other_documents_extracted_data=other_docs_data
        )
    logger.info(f"Создана начальная запись для дела case_id: {case_id} со статусом PROCESSING")

    background_tasks.add_task(
        process_case_in_background,
        case_id=case_id,
        case_data_dict=case_data.model_dump(mode='json'), 
        rag_engine=request.app.state.rag_engine,
        pension_types_config=request.app.state.pension_types_config, 
        document_requirements_config=request.app.state.document_requirements_config 
    )
    logger.info(f"Запущена фоновая задача для обработки case_id: {case_id}")

    return ProcessOutput(
        case_id=case_id,
        final_status="PROCESSING",
        explanation="Дело принято в обработку. Результаты будут доступны позже."
    )

@app.get(
    "/api/v1/cases/{case_id}/status", 
    response_model=ProcessOutput,
    summary="Получить статус и результаты обработки дела",
    description="Возвращает текущий статус обработки дела и, если обработка завершена, результаты.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Дело с указанным ID не найдено"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Внутренняя ошибка сервера при получении статуса дела"}
    },
    dependencies=[Depends(auth.require_manager_role)]
)
async def get_case_status_and_results(
    case_id: int = Path(..., description="Уникальный идентификатор дела"),
    conn: AsyncConnection = Depends(get_db_connection),
    current_user_with_role: Dict[str, Any] = Depends(auth.require_manager_role)
):
    logger.info(f"User '{current_user_with_role['username']}' (role: {current_user_with_role['role']}) requested status for case {case_id}.")
    db_case = await crud.get_case_by_id(conn, case_id) 
    if not db_case:
        logger.warning(f"Дело с case_id: {case_id} не найдено при запросе статуса.")
        raise HTTPException(status_code=404, detail="Дело не найдено")

    final_status = db_case.get("final_status") 
    explanation = db_case.get("final_explanation")
    confidence_score = db_case.get("rag_confidence")
    error_info_data = None

    if final_status is None:
        final_status = "UNKNOWN"
        explanation = explanation or "Статус дела неизвестен или обработка еще не завершена."
    
    if final_status == "ERROR_PROCESSING" or final_status == "FAILED":
        error_info_data = ErrorDetail(
            code=final_status, 
            message=explanation or "Детали ошибки не указаны.",
            source="BackgroundProcessing" 
        )
        if final_status == "FAILED" and not explanation:
             error_info_data.message = "Обработка завершилась с ошибкой без детального объяснения."

    confidence_score_val = confidence_score if confidence_score is not None else 0.0

    logger.info(f"Возврат статуса для case_id: {case_id}. Статус: {final_status}, Уверенность: {confidence_score_val}")
    return ProcessOutput(
        case_id=db_case["id"],
        final_status=final_status,
        explanation=explanation or "Объяснение отсутствует.",
        confidence_score=confidence_score_val,
        error_info=error_info_data
    )

@app.get(
    "/api/v1/cases/{case_id}",
    response_model=FullCaseData,
    summary="Получить полную информацию о деле",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Дело с указанным ID не найдено"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Внутренняя ошибка сервера при обработке данных дела"}
    },
    dependencies=[Depends(auth.require_manager_role)]
)
async def get_full_case_details(
    case_id: int = Path(..., description="Уникальный идентификатор дела"), 
    conn: AsyncConnection = Depends(get_db_connection),
    current_user_with_role: Dict[str, Any] = Depends(auth.require_manager_role)
):
    logger.info(f"User '{current_user_with_role['username']}' (role: {current_user_with_role['role']}) requested full details for case {case_id}.")
    db_case_row = await crud.get_case_by_id(conn, case_id)
    if not db_case_row:
        logger.warning(f"Дело с case_id: {case_id} не найдено при запросе полной информации.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail={ 
                "error_code": "CASE_NOT_FOUND",
                "message": "Дело не найдено",
                "details": {"case_id": case_id}
            }
        )

    try:
        case_data_dict = dict(db_case_row)
        full_case_data = FullCaseData(**case_data_dict)
    except Exception as e:
        logger.error(f"Ошибка валидации FullCaseData для case_id {case_id}: {e}", exc_info=True)
        logger.debug(f"Данные, вызвавшие ошибку: {db_case_row}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при обработке данных дела.")
        
    logger.info(f"Возвращена полная информация для case_id: {case_id}")
    return full_case_data

@app.get(
    "/api/v1/standard_document_names", 
    response_model=List[str],
    dependencies=[Depends(auth.get_current_user_data)]
)
async def get_standard_document_names_api(
    request: Request,
    current_user: Dict[str, Any] = Depends(auth.get_current_user_data)
):
    logger.info(f"User '{current_user['username']}' requested standard document names.")
    if not hasattr(request.app.state, 'standard_document_names') or request.app.state.standard_document_names is None:
        logger.error("Список стандартных имен документов не загружен в app.state.")
        raise HTTPException(status_code=503, detail="Сервис временно недоступен: конфигурация стандартных документов не загружена.")
    
    logger.info(f"Возвращен список из {len(request.app.state.standard_document_names)} стандартных имен документов.")
    return request.app.state.standard_document_names

class HealthStatus(BaseModel):
    status: str 
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class DependencyStatus(BaseModel):
    name: str
    status: str 
    message: Optional[str] = None

class HealthCheckResponse(BaseModel):
    overall_status: str 
    timestamp: datetime = Field(default_factory=datetime.now)
    dependencies: List[DependencyStatus]

async def check_database_health(conn: AsyncConnection) -> DependencyStatus:
    try:
        await conn.execute(text("SELECT 1"))
        return DependencyStatus(name="database", status="ok", message="Соединение с БД успешно.")
    except SQLAlchemyError as e:
        logger.error(f"Ошибка проверки здоровья БД: {e}", exc_info=True)
        return DependencyStatus(name="database", status="error", message=f"Ошибка соединения с БД: {str(e)[:100]}")
    except Exception as e: 
        logger.error(f"Неожиданная ошибка проверки здоровья БД: {e}", exc_info=True)
        return DependencyStatus(name="database", status="error", message=f"Неожиданная ошибка БД: {str(e)[:100]}")

async def check_ollama_health(ollama_base_url: str, model_name: str, service_name: str) -> DependencyStatus:
    try:
        async with httpx.AsyncClient(base_url=ollama_base_url, timeout=5.0) as client:
            response = await client.get("/") 
            response.raise_for_status() 
        return DependencyStatus(name=service_name, status="ok", message=f"Сервис {service_name} (модель {model_name}) доступен.")
    except httpx.TimeoutException:
        logger.warning(f"Таймаут при проверке здоровья {service_name} ({ollama_base_url})")
        return DependencyStatus(name=service_name, status="error", message=f"Таймаут соединения с {service_name}.")
    except httpx.HTTPStatusError as e:
        logger.warning(f"Ошибка HTTP при проверке здоровья {service_name}: {e.response.status_code} - {e.response.text[:100]}")
        return DependencyStatus(name=service_name, status="error", message=f"Ошибка HTTP {e.response.status_code} от {service_name}.")
    except httpx.RequestError as e:
        logger.warning(f"Ошибка запроса при проверке здоровья {service_name}: {e}")
        return DependencyStatus(name=service_name, status="error", message=f"Ошибка соединения с {service_name}.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка проверки здоровья {service_name}: {e}", exc_info=True)
        return DependencyStatus(name=service_name, status="error", message=f"Неожиданная ошибка {service_name}: {str(e)[:100]}")

async def check_neo4j_health(graph_builder: Optional[KnowledgeGraphBuilder]) -> DependencyStatus:
    if not graph_builder or not hasattr(graph_builder, '_driver'):
        return DependencyStatus(name="neo4j", status="error", message="GraphBuilder не инициализирован.")
    try:
        await asyncio.to_thread(graph_builder._driver.verify_connectivity)
        return DependencyStatus(name="neo4j", status="ok", message="Соединение с Neo4j успешно.")
    except Exception as e:
        logger.warning(f"Ошибка проверки здоровья Neo4j: {e}", exc_info=True)
        return DependencyStatus(name="neo4j", status="error", message=f"Ошибка соединения с Neo4j: {str(e)[:100]}")

@app.get("/api/v1/health", response_model=HealthCheckResponse)
async def health_check(request: Request, conn: AsyncConnection = Depends(get_db_connection)):
    dependencies_statuses = []

    db_status = await check_database_health(conn)
    dependencies_statuses.append(db_status)

    ollama_llm_config = request.app.state.rag_engine.config if request.app.state.rag_engine else None
    if ollama_llm_config:
        llm_status = await check_ollama_health(
            ollama_llm_config.OLLAMA_BASE_URL,
            ollama_llm_config.OLLAMA_LLM_MODEL_NAME,
            "Ollama_LLM"
        )
        dependencies_statuses.append(llm_status)
    else:
        dependencies_statuses.append(DependencyStatus(name="Ollama_LLM", status="skipped", message="Конфигурация RAG не загружена."))

    vision_config = request.app.state.rag_engine.config if request.app.state.rag_engine else None 
    if vision_config:
        vision_model_name = getattr(vision_config, 'OLLAMA_MULTIMODAL_LLM_MODEL_NAME', 'qwen-vl:latest') 
        vision_status = await check_ollama_health(
            vision_config.OLLAMA_BASE_URL, 
            vision_model_name,
            "Ollama_Vision"
        )
        dependencies_statuses.append(vision_status)
    else:
         dependencies_statuses.append(DependencyStatus(name="Ollama_Vision", status="skipped", message="Конфигурация RAG/Vision не загружена."))

    graph_builder_instance = request.app.state.rag_engine.graph_builder if request.app.state.rag_engine else None
    neo4j_status = await check_neo4j_health(graph_builder_instance)
    dependencies_statuses.append(neo4j_status)
    
    overall_healthy = all(dep.status == "ok" for dep in dependencies_statuses if dep.status != "skipped")

    return HealthCheckResponse(
        overall_status="healthy" if overall_healthy else "unhealthy",
        dependencies=dependencies_statuses
    )

# --- Эндпоинты для аутентификации ---
@app.post("/api/v1/auth/token", response_model=models.Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    conn: AsyncConnection = Depends(get_db_connection)
):
    user_dict = await crud.get_user_by_username(conn, username=form_data.username)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_in_db = models.UserInDB(**user_dict)

    if not user_in_db.is_active:
        logger.warning(f"Попытка входа неактивного пользователя: {form_data.username}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        
    if not auth.verify_password(form_data.password, user_in_db.hashed_password):
        logger.warning(f"Неудачная попытка входа для пользователя: {form_data.username} (неверный пароль)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user_in_db.username, "role": user_in_db.role, "user_id": user_in_db.id},
        expires_delta=access_token_expires
    )
    logger.info(f"Пользователь '{user_in_db.username}' успешно аутентифицирован.")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/v1/users/me", response_model=models.User, tags=["Users"])
async def read_users_me(current_user_data: Dict[str, Any] = Depends(auth.get_current_user_data)):
    logger.info(f"Запрос данных для текущего пользователя: {current_user_data.get('username')}")
    return models.User(
        id=current_user_data["user_id"],
        username=current_user_data["username"],
        role=current_user_data["role"],
        is_active=current_user_data.get("is_active", True) # Берем is_active из токена (если есть) или по умолчанию True
    )
# --- Конец эндпоинтов для аутентификации ---

MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_IMAGE_MIME_TYPES = ["image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp"]
ALLOWED_DOCUMENT_MIME_TYPES = ["application/pdf"]

# --- Эндпоинты для управления документами RAG --- 
class DocumentListResponse(BaseModel):
    filenames: List[str]

class DocumentUploadResponse(BaseModel):
    filename: str
    message: str

class DocumentDeleteResponse(BaseModel):
    filename: str
    message: str

@app.post("/api/v1/documents", response_model=DocumentUploadResponse, tags=["RAG Documents"], status_code=status.HTTP_201_CREATED)
async def upload_rag_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Файл PDF для загрузки в RAG."),
    current_user: Dict[str, Any] = Depends(auth.require_admin_role) # Только админ может загружать
):
    logger.info(f"User '{current_user['username']}' (role: {current_user['role']}) attempting to upload RAG document: {file.filename}")
    
    if file.content_type not in ALLOWED_DOCUMENT_MIME_TYPES:
        logger.warning(f"Disallowed MIME type for RAG document: {file.filename}, type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый тип файла: {file.content_type}. Разрешенные типы: {', '.join(ALLOWED_DOCUMENT_MIME_TYPES)}"
        )

    # Путь к директории документов из конфигурации RAG
    docs_dir = app.state.rag_engine.config.DOCUMENTS_DIR
    os.makedirs(docs_dir, exist_ok=True) # Убедимся, что директория существует
    
    file_path = os.path.join(docs_dir, file.filename)

    if os.path.exists(file_path):
        logger.warning(f"File {file.filename} already exists in RAG documents directory. Overwriting.")
        # Можно добавить логику для предотвращения перезаписи или версионирования

    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        logger.info(f"RAG document '{file.filename}' saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving uploaded RAG document {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ошибка при сохранении файла: {e}")

    # Запускаем переиндексацию в фоне
    async def run_reindex(rag_engine_instance):
        try:
            logger_bg.info(f"Background task: Starting forced reindex after uploading {file.filename}")
            await rag_engine_instance.force_rebuild_index_async()
            logger_bg.info(f"Background task: Forced reindex completed after uploading {file.filename}")
        except Exception as e_reindex:
            logger_bg.error(f"Background task: Error during forced reindex after uploading {file.filename}: {e_reindex}", exc_info=True)
    
    if request.app.state.rag_engine:
        background_tasks.add_task(run_reindex, request.app.state.rag_engine)
        logger.info(f"Background task for RAG index rebuild scheduled after upload of {file.filename}")
    else:
        logger.error("RAG engine not available, cannot schedule reindex task.")
        # В этом случае файл сохранен, но индекс не будет обновлен автоматически.
        # Можно вернуть ошибку или предупреждение клиенту.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Сервис RAG недоступен для переиндексации.")

    return DocumentUploadResponse(filename=file.filename, message="Документ успешно загружен. Переиндексация запущена в фоновом режиме.")

@app.get("/api/v1/documents", response_model=DocumentListResponse, tags=["RAG Documents"])
async def list_rag_documents(
    request: Request,
    current_user: Dict[str, Any] = Depends(auth.require_manager_role) # Менеджер может просматривать
):
    logger.info(f"User '{current_user['username']}' (role: {current_user['role']}) requested list of RAG documents.")
    docs_dir = app.state.rag_engine.config.DOCUMENTS_DIR
    if not os.path.exists(docs_dir) or not os.path.isdir(docs_dir):
        logger.warning(f"RAG documents directory {docs_dir} not found.")
        return DocumentListResponse(filenames=[])
    
    try:
        filenames = [f for f in os.listdir(docs_dir) if os.path.isfile(os.path.join(docs_dir, f)) and f.lower().endswith(".pdf")]
        logger.info(f"Found {len(filenames)} PDF RAG documents in {docs_dir}.")
        return DocumentListResponse(filenames=filenames)
    except Exception as e:
        logger.error(f"Error listing RAG documents in {docs_dir}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка при получении списка документов.")

@app.delete("/api/v1/documents/{filename}", response_model=DocumentDeleteResponse, tags=["RAG Documents"])
async def delete_rag_document(
    request: Request,
    filename: str,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(auth.require_admin_role) # Только админ может удалять
):
    logger.info(f"User '{current_user['username']}' (role: {current_user['role']}) attempting to delete RAG document: {filename}")
    docs_dir = app.state.rag_engine.config.DOCUMENTS_DIR
    file_path = os.path.join(docs_dir, filename)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        logger.warning(f"RAG document {filename} not found for deletion in {docs_dir}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден.")

    try:
        os.remove(file_path)
        logger.info(f"RAG document '{filename}' deleted from {file_path}")
    except Exception as e:
        logger.error(f"Error deleting RAG document {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ошибка при удалении файла: {e}")

    # Запускаем переиндексацию в фоне
    async def run_reindex_after_delete(rag_engine_instance):
        try:
            logger_bg.info(f"Background task: Starting forced reindex after deleting {filename}")
            await rag_engine_instance.force_rebuild_index_async()
            logger_bg.info(f"Background task: Forced reindex completed after deleting {filename}")
        except Exception as e_reindex:
            logger_bg.error(f"Background task: Error during forced reindex after deleting {filename}: {e_reindex}", exc_info=True)
    
    if request.app.state.rag_engine:
        background_tasks.add_task(run_reindex_after_delete, request.app.state.rag_engine)
        logger.info(f"Background task for RAG index rebuild scheduled after deletion of {filename}")
    else:
        logger.error("RAG engine not available, cannot schedule reindex task after deletion.")
        # Файл удален, но индекс не будет обновлен. Это может привести к проблемам.
        # Возможно, стоит вернуть ошибку, если RAG движок недоступен для такой критической операции.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Сервис RAG недоступен для переиндексации после удаления.")

    return DocumentDeleteResponse(filename=filename, message="Документ успешно удален. Переиндексация запущена в фоновом режиме.")

# --- Конец эндпоинтов для управления документами RAG --- 

@app.delete(
    "/api/v1/cases/{case_id}",
    status_code=status.HTTP_200_OK,
    summary="Удалить дело по ID",
    description="Удаляет запись о деле из базы данных по его уникальному идентификатору.",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Дело с указанным ID не найдено"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Внутренняя ошибка сервера при удалении дела"}
    },
    dependencies=[Depends(auth.require_manager_role)]
)
async def delete_case(
    case_id: int = Path(..., description="Уникальный идентификатор дела для удаления"),
    db_conn: AsyncConnection = Depends(get_db_connection),
    current_user_with_role: Dict[str, Any] = Depends(auth.require_manager_role)
):
    """
    Удаляет дело из базы данных. Доступно администраторам и менеджерам.
    """
    logger.info(f"User '{current_user_with_role['username']}' (role: {current_user_with_role['role']}) is attempting to delete case ID: {case_id}.")

    # Сначала проверим, существует ли дело
    check_query = select(cases_table.c.id).where(cases_table.c.id == case_id)
    existing_case = await db_conn.execute(check_query)
    if existing_case.scalar_one_or_none() is None:
        logger.warning(f"Attempted to delete non-existent case with ID: {case_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Дело с ID {case_id} не найдено.")

    # Если существует, удаляем
    delete_query = delete(cases_table).where(cases_table.c.id == case_id)
    try:
        result = await db_conn.execute(delete_query)
        await db_conn.commit()
        if result.rowcount == 0:
            # Эта ситуация маловероятна из-за проверки выше, но для надежности
            logger.error(f"Failed to delete case with ID: {case_id} after existence check.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Не удалось удалить дело с ID {case_id}. Возможно, оно было удалено другим процессом.")
        
        logger.info(f"Successfully deleted case with ID: {case_id}")
        return {"message": "Дело успешно удалено", "case_id": case_id}
    except Exception as e:
        await db_conn.rollback()
        logger.error(f"Error deleting case with ID {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Внутренняя ошибка сервера при удалении дела: {e}")