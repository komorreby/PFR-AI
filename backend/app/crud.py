import json
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncConnection # Import AsyncConnection

from .database import cases_table, async_engine # Используем async_engine для прямого выполнения
from .models import CaseDataInput, ErrorOutput # Нужны для аннотации типов
from typing import List, Dict, Any, Optional

async def create_case(
    conn: AsyncConnection,
    personal_data: Dict[str, Any],
    errors: List[Dict[str, Any]],
    pension_type: str,
    disability: Optional[Dict[str, Any]] = None
):
    """Сохраняет данные дела, ошибки, тип пенсии и данные об инвалидности."""
    insert_stmt = insert(cases_table).values(
        personal_data=json.dumps(personal_data),
        errors=json.dumps(errors),
        pension_type=pension_type,
        disability=json.dumps(disability) if disability else None
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
            "disability": json.loads(case_data["disability"]) if case_data["disability"] else None
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
            "disability": json.loads(case_data["disability"]) if case_data["disability"] else None
        }
    return None

# Альтернативный подход с использованием движка напрямую (менее предпочтителен для запросов)
# async def create_case_engine(personal_data: Dict[str, Any], errors: List[Dict[str, Any]]):
#     async with async_engine.connect() as conn:
#         async with conn.begin(): # Начинаем транзакцию
#             insert_stmt = insert(cases_table).values(
#                 personal_data=json.dumps(personal_data),
#                 errors=json.dumps(errors)
#             )
#             result = await conn.execute(insert_stmt)
#             return result.lastrowid
#
# async def get_cases_engine(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
#     async with async_engine.connect() as conn:
#         select_stmt = select(cases_table).offset(skip).limit(limit)
#         result = await conn.execute(select_stmt)
#         rows = result.fetchall()
#         # ... десериализация ...
#         return cases 