from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from enum import Enum

# Enum для формата документа
class DocumentFormat(str, Enum):
    pdf = "pdf"
    docx = "docx"

class NameChangeInfo(BaseModel):
    old_full_name: Optional[str] = None
    date_changed: Optional[date] = None

class PersonalData(BaseModel):
    full_name: str
    birth_date: date
    snils: str # TODO: Add validation for SNILS format
    gender: str # TODO: Use Enum? (e.g., 'male', 'female')
    citizenship: str
    name_change_info: Optional[NameChangeInfo] = None
    dependents: int = Field(ge=0) # ge=0 means greater than or equal to 0

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
    personal_data: PersonalData
    work_experience: WorkExperience
    pension_points: float = Field(ge=0)
    benefits: List[str] = []
    documents: List[str] = []
    has_incorrect_document: bool = False
    # Note: This model expects structured JSON input, not form data like the Flask app.
    # The React frontend will need to send data in this JSON format.

class ErrorOutput(BaseModel):
    code: str
    description: str
    law: str
    recommendation: str

class ProcessOutput(BaseModel):
    errors: List[ErrorOutput]

# Новая модель для представления записи в истории
class CaseHistoryEntry(BaseModel):
    id: int
    personal_data: dict # Оставляем как dict, т.к. структура уже определена в PersonalData
    errors: List[ErrorOutput] # Используем ErrorOutput для согласованности 