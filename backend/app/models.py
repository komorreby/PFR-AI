from pydantic import BaseModel, Field, field_validator # Изменяем импорт
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from enum import Enum
import logging

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
    other_documents_extracted_data: Optional[List[Dict[str, Any]]] = Field(None, description="Список извлеченных данных (поля, оценка, осмысление) из дополнительных документов типа 'other'")

    @field_validator('pension_type')
    @classmethod
    def validate_pension_type(cls, v: str):
        from .rag_core import config as rag_config # Импорт здесь, чтобы избежать циклического импорта
        if v not in rag_config.PENSION_TYPE_MAP:
            raise ValueError(f"Недопустимый тип пенсии: {v}. Допустимые: {list(rag_config.PENSION_TYPE_MAP.keys())}")
        return v

class DocumentTypeToExtract(str, Enum):
    PASSPORT = "passport"
    SNILS = "snils"
    OTHER = "other" # Добавляем новый тип

class ProcessOutput(BaseModel):
    case_id: int
    final_status: str
    explanation: str
    confidence_score: float
    department_code: Optional[str] = None # Код подразделения (например, "770-001")

    # Можно добавить валидаторы для форматов серии, номера, кода подразделения, если нужно

class SnilsData(BaseModel):
    snils_number: Optional[str] = None  # Номер СНИЛС (например, "123-456-789 00")

    @field_validator('snils_number')
    @classmethod
    def format_snils(cls, v: Optional[str]):
        if v is None:
            return None
        # Импортируем logger здесь, чтобы избежать проблем на уровне модуля, если он не настроен глобально
        logger = logging.getLogger(__name__) # Используем имя текущего модуля для логгера
        # Удаляем все нецифровые символы
        cleaned = "".join(filter(str.isdigit, v))
        # Проверяем, что осталось 11 цифр
        if len(cleaned) == 11:
            # Форматируем как XXX-XXX-XXX XX
            return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:9]} {cleaned[9:]}"
        logger.warning(f"Номер СНИЛС '{v}' не содержит 11 цифр после очистки. Возвращен без изменений.")
        return v # Возвращаем как есть, если не 11 цифр, или None если изначально был None

class OtherDocumentData(BaseModel):
    identified_document_type: Optional[str] = Field(None, description="Тип документа, определенный мультимодальной моделью (например, 'Свидетельство о рождении', 'Договор').")
    standardized_document_type: Optional[str] = Field(None, description="Стандартизированный тип документа, если он совпадает с известным типом пенсионных документов.")
    extracted_fields: Optional[Dict[str, Any]] = Field(None, description="Извлеченные поля из документа в формате ключ-значение.")
    multimodal_assessment: Optional[str] = Field(None, description="Оценка документа мультимодальной моделью (например, качество, читаемость, полнота).")
    text_llm_reasoning: Optional[str] = Field(None, description="Дополнительный анализ или 'осмысление' от текстовой LLM на основе извлеченных данных.")

# Новая модель для представления записи в истории
class CaseHistoryEntry(BaseModel):
    id: int
    created_at: datetime
    pension_type: str
    final_status: str
    final_explanation: Optional[str] = None 
    rag_confidence: Optional[float] = None
    personal_data: Optional[PersonalData] = None

class PassportData(BaseModel):
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    sex: Optional[str] = None # Пол (например, "МУЖ." или "ЖЕН.")
    birth_place: Optional[str] = None # <--- ДОБАВЛЕНО ПОЛЕ МЕСТО РОЖДЕНИЯ
    passport_series: Optional[str] = None # Серия паспорта (например, "1234")
    passport_number: Optional[str] = None # Номер паспорта (например, "567890")
    issue_date: Optional[date] = None     # Дата выдачи
    issuing_authority: Optional[str] = None # Кем выдан
    department_code: Optional[str] = None # Код подразделения (например, "770-001")

    # Можно добавить валидаторы для форматов серии, номера, кода подразделения, если нужно

PENSION_DOCUMENT_TYPES = [
    "Заявление о назначении пенсии",
    "Трудовая книжка",
    "Трудовой договор", # "Трудовые договоры"
    "Справка от работодателя", # "Справки от работодателей / госорганов"
    "Справка от госоргана", # "Справки от работодателей / госорганов"
    "Военный билет",
    "Свидетельство о рождении ребенка", # "Свидетельства о рождении детей"
    "Документ об уплате взносов", # "Документы об уплате взносов (для ИП, самозанятых)"
    "Справка о зарплате за 60 месяцев до 2002 года",
    "Документ, подтверждающий особые условия труда", # "Документы, подтверждающие особые условия труда (вредность, Север и т.д.)"
    "Документ, подтверждающий педагогический стаж", # "Документы для подтверждения педагогического, медицинского и др. льготного стажа"
    "Документ, подтверждающий медицинский стаж", # "Документы для подтверждения педагогического, медицинского и др. льготного стажа"
    "Документ, подтверждающий льготный стаж", # "Документы для подтверждения педагогического, медицинского и др. льготного стажа"
    "Свидетельство о рождении всех детей", # (для многодетных матерей)
    "Документ об инвалидности ребенка", # (для родителей/опекунов инвалидов с детства)
    "Справка об инвалидности", # (для пенсии по инвалидности)
    "Свидетельство о смерти кормильца",
    "Документ о родстве с умершим",
    "Документ об иждивении",
    "Справка из учебного заведения", # (для детей старше 18 лет)
    "Свидетельство о перемене ФИО",
    "Документ о месте жительства", # "Документы о месте жительства/пребывания"
    "Документ о месте пребывания", # "Документы о месте жительства/пребывания"
    "Справка о составе семьи",
    "Документ, подтверждающий наличие иждивенцев" # (кроме детей)
]