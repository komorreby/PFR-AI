// src/types.ts

// 6. Основные Сущности (Модели Данных)

export interface NameChangeInfo {
  old_full_name: string | null;
  date_changed: string | null; // YYYY-MM-DD
}

export interface PersonalData {
  last_name: string;
  first_name: string;
  middle_name: string | null;
  birth_date: string; // YYYY-MM-DD
  snils: string;
  gender: string; // "Мужской", "Женский" - как в API, или предусмотреть маппинг
  citizenship: string;
  name_change_info: NameChangeInfo | null;
  dependents: number;
}

export interface DisabilityInfo {
  group: "1" | "2" | "3" | "child";
  date: string; // YYYY-MM-DD
  cert_number: string | null;
}

export interface WorkExperienceRecord {
  organization: string;
  position: string;
  start_date: string; // YYYY-MM-DD
  end_date: string; // YYYY-MM-DD
  special_conditions: boolean | null;
}

export interface WorkExperience {
  total_years: number;
  records: WorkExperienceRecord[] | null;
}

export interface OtherDocumentData {
  identified_document_type: string | null;
  standardized_document_type: string | null;
  extracted_fields: Record<string, any> | null; // object | null
  multimodal_assessment: string | null;
  text_llm_reasoning: string | null;
}

export interface CaseDataInput {
  personal_data: PersonalData;
  pension_type: string; // ID из /api/v1/pension_types
  disability: DisabilityInfo | null;
  work_experience: WorkExperience | null;
  pension_points: number | null;
  benefits: string[] | null;
  submitted_documents: string[] | null; // ID из /api/v1/pension_documents/{pension_type_id}
  has_incorrect_document: boolean | null;
  other_documents_extracted_data: OtherDocumentData[] | null;
}

export interface ErrorDetail {
  code: string | null;
  message: string | null;
  source: string | null;
  details: Record<string, any> | null; // object | null
}

export interface ProcessOutput {
  case_id: number;
  final_status: string; // "PROCESSING", "COMPLETED", "FAILED", "ERROR_PROCESSING", "СООТВЕТСТВУЕТ", "НЕ СООТВЕТСТВУЕТ", "UNKNOWN"
  explanation: string | null;
  confidence_score: number | null;
  department_code: string | null;
  error_info: ErrorDetail | null;
}

export interface CaseHistoryEntry {
  id: number;
  created_at: string; // datetime, ISO 8601
  pension_type: string;
  final_status: string;
  final_explanation: string | null;
  rag_confidence: number | null;
  personal_data: PersonalData | null;
}

export interface FullCaseData extends CaseDataInput {
  id: number;
  created_at: string; // datetime, ISO 8601
  updated_at: string | null; // datetime, ISO 8601
  errors: Record<string, any>[] | null; // Array<object>
  final_status: string | null;
  final_explanation: string | null;
  rag_confidence: number | null;
  // Поля из CaseDataInput здесь уже есть через extends,
  // они могут быть null, если данные не были предоставлены или ошибки парсинга
}

export interface PassportData {
  last_name: string | null;
  first_name: string | null;
  middle_name: string | null;
  birth_date: string | null; // YYYY-MM-DD
  sex: string | null; // "МУЖ.", "ЖЕН."
  birth_place: string | null;
  passport_series: string | null;
  passport_number: string | null;
  issue_date: string | null; // YYYY-MM-DD
  issuing_authority: string | null;
  department_code: string | null;
}

export interface SnilsData {
  snils_number: string | null;
  last_name: string | null;
  first_name: string | null;
  middle_name: string | null;
  gender: string | null;
  birth_date: string | null; // YYYY-MM-DD
  birth_place: string | null;
}

export interface WorkBookRecordEntry {
  date_in: string | null; // YYYY-MM-DD
  date_out: string | null; // YYYY-MM-DD
  organization: string | null;
  position: string | null;
}

export interface WorkBookData {
  records: WorkBookRecordEntry[]; // По умолчанию пустой массив []
  calculated_total_years: number | null;
}

export interface OcrTaskSubmitResponse {
  task_id: string; // UUID
  status: "PROCESSING";
  message: string;
}

export type OcrTaskStatus = "PROCESSING" | "COMPLETED" | "FAILED";

export type OcrResultData = PassportData | SnilsData | WorkBookData | OtherDocumentData;

export interface OcrTaskStatusResponse {
  task_id: string;
  status: OcrTaskStatus;
  data: OcrResultData | null; // Структура зависит от document_type при создании задачи
  error: {
    detail: string;
    type: string; // ИмяОшибки
  } | null;
}

export interface TasksStatsResponse {
  total: number;
  pending: number;
  expired_processing: number;
  status_specific_counts: {
    PROCESSING: number;
    COMPLETED: number;
    FAILED: number;
    [key: string]: number; // Для возможных других статусов
  };
}

export interface DocumentDetail {
  id: string;
  name: string;
  description: string;
  is_critical: boolean;
  condition_text: string | null;
  ocr_type: "passport" | "snils" | "work_book" | "other" | null;
}

export interface DependencyStatus {
  name: string; // "database", "Ollama_LLM", "Ollama_Vision", "neo4j"
  status: "ok" | "error" | "skipped";
  message: string | null;
}

export interface HealthCheckResponse {
  overall_status: "healthy" | "unhealthy";
  timestamp: string; // datetime, ISO 8601
  dependencies: DependencyStatus[];
}

// Типы для эндпоинтов конфигурации

export interface PensionTypeInfo {
  id: string;
  display_name: string;
  description: string;
}

// Типы для пользователя, согласно API документации
export interface User {
  id: number;
  username: string;
  role: "admin" | "manager";
  is_active: boolean;
}

// Тип для ответа от эндпоинта /token, согласно API документации
export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

// Типы для параметров запросов и тел

// Для POST /api/v1/document_extractions
export type DocumentTypeToExtract = "passport" | "snils" | "work_book" | "other";

export interface DocumentExtractionParams {
  document_type: DocumentTypeToExtract;
  image: File;
  ttl_hours?: number; // 1-168
}

// Для GET /api/v1/cases/{case_id}/document
export type DocumentFormat = "pdf" | "docx";

// Стандартизированный формат ошибки (из раздела 5)
export interface StandardErrorResponse {
    error_code: string;
    message: string;
    details?: any; // Может быть объектом или массивом
}

// Детали ошибки валидации (из раздела 5)
export interface ValidationErrorDetailItem {
    loc: (string | number)[];
    msg: string;
    type: string;
}
export interface HttpValidationError {
    detail: ValidationErrorDetailItem[];
}

// Для стандартизированных ошибок (новый формат)
export interface StandardizedValidationErrorDetail {
    field: string; // "body.personal_data.snils"
    message: string;
    type: string; // "value_error"
}
export interface StandardizedValidationErrorResponse {
    error_code: "VALIDATION_ERROR";
    message: string;
    details: StandardizedValidationErrorDetail[];
}

// Общий тип для ошибки API, который будет использоваться в API клиенте
export interface ApiError {
  status: number;
  message: string; // Человекочитаемое сообщение
  errorCode?: string; // Код ошибки из StandardErrorResponse
  validationDetails?: StandardizedValidationErrorDetail[] | ValidationErrorDetailItem[]; // Детали валидации
  rawError?: any; // Исходный объект ошибки от сервера
}

// Тип для данных формы React Hook Form (RHF)
// Основан на CaseDataInput, но с учетом того, что поля могут быть частично заполнены
// или иметь немного другую структуру на стороне UI перед отправкой.
export interface CaseFormDataTypeForRHF {
  pension_type?: string; // ID из /api/v1/pension_types
  personal_data?: Partial<PersonalData> & { 
    name_change_info_checkbox?: boolean; // Вспомогательное поле для UI
    // Поля паспорта, которые могут быть отдельными в UI, но часть PersonalData в API
    passport_series?: string;
    passport_number?: string;
    passport_issue_date?: string; 
    issuing_authority?: string;
    department_code?: string;
    birth_place?: string;
  };
  disability?: Partial<DisabilityInfo> | null;
  work_experience?: Partial<WorkExperience> & {
    // Если есть специфичные для UI поля в work_experience, добавляем сюда
  };
  pension_points?: number | null;
  benefits?: string; // В RHF может храниться как строка тегов
  submitted_documents?: string; // В RHF может храниться как строка тегов
  has_incorrect_document?: boolean;
  other_documents_extracted_data?: Partial<OtherDocumentData>[]; // Массив частично заполненных данных
  
  // Могут быть и другие поля, специфичные для UI или временные
  [key: string]: any; // Для гибкости, если есть другие поля в RHF
}