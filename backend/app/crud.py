import json
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncConnection

from .database import cases_table, async_engine
from .models import CaseDataInput # Нужны для аннотации типов
from typing import List, Dict, Any, Optional

async def create_case(
    conn: AsyncConnection,
    personal_data: Dict[str, Any],
    errors: List[Dict[str, Any]],
    pension_type: str,
    disability: Optional[Dict[str, Any]] = None,
    work_experience: Optional[Dict[str, Any]] = None,
    pension_points: Optional[float] = None,
    benefits: Optional[List[str]] = None,
    documents: Optional[List[str]] = None,
    has_incorrect_document: Optional[bool] = False,
    final_status: Optional[str] = None,
    final_explanation: Optional[str] = None,
    rag_confidence: Optional[float] = None
):
    """Сохраняет данные дела, ошибки, тип пенсии и данные об инвалидности."""
    insert_stmt = insert(cases_table).values(
        personal_data=json.dumps(personal_data),
        errors=json.dumps(errors),
        pension_type=pension_type,
        disability=json.dumps(disability) if disability else None,
        work_experience=json.dumps(work_experience) if work_experience else None,
        pension_points=pension_points,
        benefits=json.dumps(benefits) if benefits else None,
        documents=json.dumps(documents) if documents else None,
        has_incorrect_document=has_incorrect_document,
        final_status=final_status,
        final_explanation=final_explanation,
        rag_confidence=rag_confidence
    )
    result = await conn.execute(insert_stmt)
    await conn.commit() # Явно коммитим транзакцию
    return result.lastrowid # Возвращаем ID вставленной записи

async def get_cases(conn: AsyncConnection, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Получает список дел из базы данных."""
    select_stmt = select(cases_table).offset(skip).limit(limit)
    result = await conn.execute(select_stmt)
    rows = result.fetchall()

    # Десериализуем JSON обратно в словари/списки
    cases = []
    for row in rows:
        # Используем _mapping для доступа к данным по имени колонки
        case_data = row._mapping
        cases.append({
            "id": case_data["id"],
            "personal_data": json.loads(case_data["personal_data"]),
            "errors": json.loads(case_data["errors"]),
            "pension_type": case_data["pension_type"],
            "disability": json.loads(case_data["disability"]) if case_data["disability"] else None,
            "work_experience": json.loads(case_data["work_experience"]) if case_data["work_experience"] else None,
            "pension_points": case_data["pension_points"],
            "benefits": json.loads(case_data["benefits"]) if case_data["benefits"] else None,
            "documents": json.loads(case_data["documents"]) if case_data["documents"] else None,
            "has_incorrect_document": case_data["has_incorrect_document"],
            "final_status": case_data["final_status"],
            "final_explanation": case_data["final_explanation"],
            "rag_confidence": case_data["rag_confidence"]
        })
    return cases

async def get_case_by_id(conn: AsyncConnection, case_id: int) -> Optional[Dict[str, Any]]:
    """Получает одно дело по ID из базы данных."""
    select_stmt = select(cases_table).where(cases_table.c.id == case_id)
    result = await conn.execute(select_stmt)
    row = result.fetchone()

    if row:
        # Используем _mapping для доступа к данным по имени колонки
        case_data = row._mapping
        return {
            "id": case_data["id"],
            "personal_data": json.loads(case_data["personal_data"]),
            "errors": json.loads(case_data["errors"]),
            "pension_type": case_data["pension_type"],
            "disability": json.loads(case_data["disability"]) if case_data["disability"] else None,
            "work_experience": json.loads(case_data["work_experience"]) if case_data["work_experience"] else None,
            "pension_points": case_data["pension_points"],
            "benefits": json.loads(case_data["benefits"]) if case_data["benefits"] else None,
            "documents": json.loads(case_data["documents"]) if case_data["documents"] else None,
            "has_incorrect_document": case_data["has_incorrect_document"],
            "final_status": case_data["final_status"],
            "final_explanation": case_data["final_explanation"],
            "rag_confidence": case_data["rag_confidence"]
        }
    return None