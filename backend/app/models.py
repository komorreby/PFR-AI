from pydantic import BaseModel, Field, field_validator # Изменяем импорт
from typing import List, Optional
from datetime import date
from enum import Enum

# Enum для формата документа
class DocumentFormat(str, Enum):
    pdf = "pdf"
    docx = "docx"

class DisabilityInfo(BaseModel):
    group: str # Значения "1", "2", "3", "child"
    date: date # Дата установления
    cert_number: Optional[str] = None # Номер справки МСЭ (опционально)

    @field_validator('group') # Обновляем декоратор
    @classmethod # Добавляем classmethod
    def check_group_value(cls, v: str): # Можно добавить тип для v
        allowed_groups = {"1", "2", "3", "child"}
        if v not in allowed_groups:
            raise ValueError(f'Недопустимое значение группы инвалидности: {v}. Допустимые: {allowed_groups}')
        return v

class NameChangeInfo(BaseModel):
    old_full_name: Optional[str] = None
    date_changed: Optional[date] = None

class PersonalData(BaseModel):
    last_name: str
    first_name: str
    middle_name: Optional[str] = None # Отчество опционально
    birth_date: date
    snils: str
    gender: str
    citizenship: str
    name_change_info: Optional[NameChangeInfo] = None
    dependents: int = Field(ge=0)
    

class WorkRecord(BaseModel):
    organization: str
    start_date: date
    end_date: date
    position: str
    special_conditions: bool = False

class WorkExperience(BaseModel):
    total_years: float = Field(ge=0)
    records: List[WorkRecord] = []

class CaseDataInput(BaseModel):
    pension_type: str # TODO: Возможно, тоже Enum
    personal_data: PersonalData
    work_experience: WorkExperience
    pension_points: float = Field(ge=0)
    benefits: List[str] = []
    documents: List[str] = []
    has_incorrect_document: bool = False
    disability: Optional[DisabilityInfo] = None

    @field_validator('pension_type')
    @classmethod
    def validate_pension_type(cls, v: str):
        from .rag_core import config as rag_config # Импорт здесь, чтобы избежать циклического импорта
        if v not in rag_config.PENSION_TYPE_MAP:
            raise ValueError(f"Недопустимый тип пенсии: {v}. Допустимые: {list(rag_config.PENSION_TYPE_MAP.keys())}")
        return v

class ProcessOutput(BaseModel):
    case_id: int
    final_status: str # <--- Переименовано c status
    explanation: str
    confidence_score: float # <--- Добавлено

# Новая модель для представления записи в истории
class CaseHistoryEntry(BaseModel):
    id: int
    created_at: date # Или datetime, если время тоже важно. Пока оставим date.
    pension_type: str
    final_status: str
    final_explanation: Optional[str] = None 
    rag_confidence: Optional[float] = None
    personal_data: Optional[PersonalData] = None