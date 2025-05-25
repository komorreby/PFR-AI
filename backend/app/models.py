from pydantic import BaseModel, Field, field_validator, HttpUrl, ValidationInfo
from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime, timezone
from enum import Enum
import logging
import re
import json

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
    
    @field_validator('birth_date')
    @classmethod
    def birth_date_not_in_future(cls, v: date):
        if v > date.today():
            raise ValueError('Дата рождения не может быть в будущем')
        return v
    
    @field_validator('snils')
    @classmethod
    def validate_snils_format(cls, v: str) -> str:
        # Удаляем все нецифровые символы, кроме пробелов и дефисов, которые могут быть частью форматирования
        cleaned = re.sub(r'[^-0-9\s]', '', v)
        # Удаляем пробелы и дефисы для подсчета цифр
        digits_only = re.sub(r'[^0-9]', '', cleaned)
        if len(digits_only) != 11:
            raise ValueError("Номер СНИЛС должен содержать 11 цифр")
        # Можно добавить более строгую проверку формата XXX-XXX-XXX XX, если требуется
        # Например, с помощью re.match(r'^\d{3}-\d{3}-\d{3}\s\d{2}$', cleaned)
        # Но для базовой валидации достаточно количества цифр
        return v # Возвращаем исходное значение, если прошло проверку, или можно вернуть cleaned

class WorkRecord(BaseModel):
    organization: str
    start_date: date
    end_date: date
    position: str
    special_conditions: bool = False

    @field_validator('end_date')
    @classmethod
    def check_dates_order(cls, v: date, info: ValidationInfo): # Используем info для доступа к values
        if 'start_date' in info.data and info.data['start_date'] and v < info.data['start_date']:
            raise ValueError('Дата окончания не может быть раньше даты начала')
        return v

class WorkExperienceRecord(BaseModel):
    organization: str
    position: str
    start_date: date
    end_date: date
    special_conditions: Optional[bool] = False

class WorkExperience(BaseModel):
    total_years: int = Field(ge=0)
    records: Optional[List[WorkExperienceRecord]] = None

class OtherDocumentData(BaseModel):
    identified_document_type: Optional[str] = Field(None, description="Тип документа, определенный мультимодальной моделью (например, 'Свидетельство о рождении', 'Договор').")
    standardized_document_type: Optional[str] = Field(None, description="Стандартизированный тип документа, если он совпадает с известным типом пенсионных документов.")
    extracted_fields: Optional[Dict[str, Any]] = Field(None, description="Извлеченные поля из документа в формате ключ-значение.")
    multimodal_assessment: Optional[str] = Field(None, description="Оценка документа мультимодальной моделью (например, качество, читаемость, полнота).")
    text_llm_reasoning: Optional[str] = Field(None, description="Дополнительный анализ или 'осмысление' от текстовой LLM на основе извлеченных данных.")

class CaseDataInput(BaseModel):
    personal_data: PersonalData
    pension_type: str # Например, 'retirement_standard', 'disability', 'survivor'
    disability: Optional[DisabilityInfo] = None
    work_experience: Optional[WorkExperience] = None
    pension_points: Optional[float] = None
    benefits: Optional[List[str]] = None # Список кодов льгот или их описаний
    submitted_documents: Optional[List[str]] = None # Список ID представленных документов
    has_incorrect_document: Optional[bool] = False
    # Поле для хранения извлеченных данных из дополнительных документов (OCR)
    other_documents_extracted_data: Optional[List[OtherDocumentData]] = Field(default_factory=list)

    @field_validator('pension_type')
    @classmethod
    def validate_pension_type(cls, v: str, info: ValidationInfo) -> str:
        """Валидатор для поля pension_type

        Проверяет, что тип пенсии находится в списке доступных типов.
        Проверка происходит в контроллере при наличии app.state.pension_types_config.
        """
        # Валидация будет происходить в контроллере
        return v

class DocumentTypeToExtract(str, Enum):
    PASSPORT = "passport"
    SNILS = "snils"
    WORK_BOOK = "work_book" # Добавляем новый тип
    OTHER = "other" # Добавляем новый тип

class ErrorDetail(BaseModel): # Новая модель для детализации ошибки
    code: Optional[str] = None # Код ошибки (например, RAG_ERROR, VALIDATION_ERROR)
    message: Optional[str] = None # Человекочитаемое сообщение
    source: Optional[str] = None # Источник ошибки (например, RAG, OCR, DB)
    details: Optional[Dict[str, Any]] = None # Дополнительные детали, специфичные для ошибки

class ProcessOutput(BaseModel):
    case_id: int
    final_status: str # Например: PROCESSING, COMPLETED, FAILED, ERROR_PROCESSING, СООТВЕТСТВУЕТ, НЕ СООТВЕТСТВУЕТ
    explanation: Optional[str] = None # Сделаем опциональным, т.к. при PROCESSING его может не быть
    confidence_score: Optional[float] = None # Сделаем опциональным
    department_code: Optional[str] = None
    error_info: Optional[ErrorDetail] = None # Новое поле для информации об ошибке

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

# Новая модель для представления записи в истории
class CaseHistoryEntry(BaseModel):
    id: int
    created_at: datetime 
    pension_type: str
    final_status: str
    final_explanation: Optional[str] = None
    rag_confidence: Optional[float] = None
    personal_data: Optional[PersonalData] = None # Добавлено поле для персональных данных в истории

    @field_validator('created_at', mode='before')
    def ensure_datetime(cls, value):
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                # Попытка парсинга другого распространенного формата, если предыдущий не удался
                try:
                    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f') # Пример формата SQLite
                except ValueError:
                     raise ValueError(f"Invalid datetime format: {value}")
        elif not isinstance(value, datetime):
            raise TypeError(f"created_at must be a datetime object or valid ISO string, got {type(value)}")
        return value

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

class WorkBookRecordEntry(BaseModel):
    """Одна запись (период работы) из трудовой книжки."""
    date_in: Optional[date] = Field(None, description="Дата приема на работу")
    date_out: Optional[date] = Field(None, description="Дата увольнения с работы (если есть)")
    organization: Optional[str] = Field(None, description="Наименование организации")
    position: Optional[str] = Field(None, description="Должность (1-2 слова)")
    # basis_document_raw: Optional[str] = Field(None, description="Необработанный текст из колонки 'На основании чего внесена запись'") # Опционально, если нужно извлекать

class WorkBookData(BaseModel):
    """Структурированные данные, извлеченные из трудовой книжки."""
    records: List[WorkBookRecordEntry] = Field(default_factory=list, description="Список записей о трудовой деятельности")
    calculated_total_years: Optional[float] = Field(None, description="Общий стаж, рассчитанный на основе извлеченных записей (в годах).")

class FullCaseData(BaseModel):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    pension_type: str
    personal_data: Optional[PersonalData] = None # Сделаем PersonalData опциональным на случай ошибок парсинга
    disability: Optional[DisabilityInfo] = None
    work_experience: Optional[WorkExperience] = None
    pension_points: Optional[float] = None
    benefits: Optional[List[str]] = None
    submitted_documents: Optional[List[str]] = None
    has_incorrect_document: Optional[bool] = None
    other_documents_extracted_data: Optional[List[Dict[str, Any]]] = None
    errors: Optional[List[Dict[str, Any]]] = None # Ошибки, сохраненные с делом
    final_status: Optional[str] = None
    final_explanation: Optional[str] = None
    rag_confidence: Optional[float] = None

    @field_validator('personal_data', 'disability', 'work_experience', 'errors', 'benefits', 'submitted_documents', 'other_documents_extracted_data', mode='before')
    @classmethod
    def parse_json_fields(cls, value: Any, info: ValidationInfo) -> Optional[Union[Dict, List]]:
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # logger.error(f"Could not decode JSON for field '{info.field_name}': {value}")
                # Вместо прямого логирования здесь, можно выбросить ValueError или вернуть специальный маркер,
                # чтобы обработать в вызывающем коде или положиться на стандартную обработку Pydantic.
                # Пока что просто вернем None, как в примере.
                # print(f"Warning: Could not decode JSON for field '{info.field_name}'. Value: '{value[:100]}...'") # Отладочный принт
                logger.warning(f"Could not decode JSON for field '{info.field_name}' in FullCaseData. Value starts with: '{value[:100]}...'")
                return None 
        return value

class StandardErrorResponse(BaseModel):
    error_code: Optional[str] = None # Уникальный код ошибки для программной обработки
    message: str # Человекочитаемое сообщение об ошибке
    details: Optional[Any] = None # Дополнительные детали (например, поля с ошибками валидации)

PENSION_DOCUMENT_TYPES = [
    # Общие и часто встречающиеся
    "Заявление о назначении страховой пенсии по старости", # Из retirement_standard
    "Заявление о назначении досрочной страховой пенсии по старости", # Из retirement_early
    "Заявление о назначении страховой пенсии по инвалидности", # Из disability_insurance
    "Заявление о назначении страховой пенсии по случаю потери кормильца", # Из survivors_insurance
    "Заявление о назначении пенсии за выслугу лет", # Общее для service_pension_...
    "Заявление о назначении государственной пенсии по инвалидности", # Может быть общее для state_pension_disability_...
    "Заявление о назначении государственной пенсии по старости", # Может быть общее для state_pension_old_age_...
    "Заявление о назначении социальной пенсии по инвалидности", # Из social_pension_disability
    "Заявление о назначении социальной пенсии по старости", # Из social_pension_old_age (если детализировано)
    "Заявление о назначении социальной пенсии по случаю потери кормильца", # Если детализировано
    "Заявление о назначении социальной пенсии детям, оба родителя которых неизвестны", # Если детализировано
    # Если используется одно общее заявление:
    "Заявление о назначении пенсии", # Общее, если конкретные формы не выделяются

    "Паспорт гражданина РФ",
    "Паспорт РФ заявителя (получателя пенсии)", # Для survivor
    "СНИЛС",
    "СНИЛС заявителя (получателя пенсии)", # Для survivor
    "СНИЛС умершего кормильца", # Для survivor

    "Трудовая книжка и/или сведения о трудовой деятельности (форма СТД-Р/СТД-ПФР)",
    "Трудовая книжка и/или сведения о трудовой деятельности", # Более короткий вариант
    "Трудовая книжка и/или сведения о трудовой деятельности (при наличии)", # Вариант для disability_insurance
    "Трудовая книжка умершего кормильца и/или сведения о его трудовой деятельности", # Для survivor
    "Трудовая книжка и/или сведения о трудовой деятельности с подтверждением стажа госслужбы", # Для service_pension_civil_servant

    "Справка о среднемесячном заработке за любые 60 месяцев подряд до 01.01.2002",
    "Справка о среднемесячном заработке федерального госслужащего", # Для service_pension_civil_servant

    "Документы о смене фамилии, имени, отчества", # Общее название
    # Более конкретные, если нужно, но общее покрывает:
    # "Свидетельство о браке",
    # "Свидетельство о расторжении брака",
    # "Свидетельство о перемене имени",

    "Свидетельства о рождении детей",
    "Свидетельство о рождении иждивенца", # Для survivor

    "Военный билет",
    "Военный билет (для проходивших службу по призыву)", # Для state_pension_disability_military_conscript

    # Документы для льготного стажа и особых условий
    "Документы, подтверждающие стаж на соответствующих видах работ (льготный стаж)", # Для retirement_early

    # Документы по инвалидности
    "Справка медико-социальной экспертизы (МСЭ)", # Общее
    "Справка МСЭ об установлении инвалидности", # Вариант
    "Справка МСЭ (для гос. пенсии)", # Из disability_state в вашем JSON
    "Справка МСЭ с указанием причины инвалидности (военная травма или заболевание в период службы)", # Для state_pension_disability_military_conscript
    "Справка МСЭ об установлении инвалидности (с указанием причины, если это важно для гос. пенсии).", # Оригинал из вашего JSON для disability_state
    "Справка МСЭ об установлении инвалидности (с указанием категории 'ребенок-инвалид')", # Пример для детализации, если нужно

    # Документы по потере кормильца
    "Свидетельство о смерти кормильца",
    "Документы, подтверждающие родственные отношения с умершим кормильцем",
    "Документы, подтверждающие нахождение на иждивении умершего кормильца",
    "Справка об очном обучении для иждивенца старше 18 лет",

    # Документы для государственных пенсий (специфичные)
    "Справка (выписка из приказа) об основании и дате увольнения с госслужбы", # Для service_pension_civil_servant
    "Документы, подтверждающие выслугу лет в качестве космонавта", # Для service_pension_cosmonaut
    "Удостоверение пострадавшего от радиационной/техногенной катастрофы", # Для old_age_state (пострадавшим от радиации)
    "Документ, подтверждающий статус гражданина, пострадавшего в результате радиационных или техногенных катастроф.", # Оригинал из вашего JSON

    # Документы для социальных пенсий
    "Документ, подтверждающий отсутствие права на страховую пенсию", # Из вашего JSON для social_pension
    "Документ, подтверждающий постоянное проживание в РФ", # Для social_pension_disability
    "Документ, подтверждающий принадлежность к малочисленным народам Севера", # Для social_pension_old_age (народы Севера)
    "Документ, подтверждающий постоянное проживание в районах проживания малочисленных народов Севера" # Для social_pension_old_age (народы Севера)
]

# --- Модели для аутентификации и пользователей ---
class UserBase(BaseModel):
    username: str
    role: str = Field(description="Роль пользователя: 'admin' или 'manager'")
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserInDBBase(UserBase):
    id: int
    
    class Config: # В старых версиях Pydantic orm_mode = True
        from_attributes = True # Для Pydantic v2

class UserInDB(UserInDBBase):
    hashed_password: str

class User(UserInDBBase): # Модель для возврата клиенту (без пароля)
    pass

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel): # Для типизации данных в токене, если нужно
    sub: Optional[str] = None # username
    role: Optional[str] = None
    user_id: Optional[int] = None