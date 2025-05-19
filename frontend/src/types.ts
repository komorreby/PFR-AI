// src/types.ts

// На основе backend/app/models.py

export interface NameChangeInfo {
  old_full_name: string;
  date_changed: string; // YYYY-MM-DD
}

export interface PersonalData {
  last_name: string;
  first_name: string;
  middle_name?: string;
  birth_date: string; // YYYY-MM-DD
  snils: string;
  gender: string; // 'male' | 'female'
  citizenship: string;
  name_change_info: NameChangeInfo | null;
  dependents: number; // <-- Оставляем здесь, так как бэкенд ожидает его внутри personal_data

  // Новые необязательные поля из OCR паспорта
  birth_place?: string;
  passport_series?: string;
  passport_number?: string;
  issue_date?: string; // YYYY-MM-DD
  issuing_authority?: string;
  department_code?: string;
}

export interface WorkRecord {
  organization: string;
  start_date: string; // YYYY-MM-DD
  end_date: string; // YYYY-MM-DD
  position: string;
  special_conditions: boolean;
}

export interface WorkExperience {
  total_years: number;
  records: WorkRecord[];
}

export interface DisabilityInfo {
  group: string; // "1", "2", "3", "child"
  date: string; // YYYY-MM-DD
  cert_number?: string;
}

// Интерфейс для одного элемента other_documents_extracted_data
export interface OtherDocumentExtractedBlock {
  standardized_document_type?: string;
  extracted_fields?: Record<string, any>;
  // Можно добавить имя файла или какой-то идентификатор, если нужно будет их связывать с загруженными файлами
  // original_filename?: string; 
}

// Соответствует CaseDataInput с бэкенда
export interface CaseFormData {
  pension_type: string;
  personal_data: PersonalData; // dependents будут здесь при отправке на API
  work_experience: WorkExperience;
  pension_points: number;
  benefits: string[];
  documents: string[];
  has_incorrect_document: boolean;
  disability?: DisabilityInfo;
  other_documents_extracted_data?: OtherDocumentExtractedBlock[]; // НОВОЕ ПОЛЕ
}

// Для формы React Hook Form, где benefits и documents - строки
// И поле dependents вынесено на верхний уровень для UI
export interface CaseFormDataTypeForRHF extends Omit<CaseFormData, 'benefits' | 'documents' | 'personal_data' | 'other_documents_extracted_data'> {
  pension_type: string;
  personal_data: Omit<PersonalData, 'dependents'>; // dependents здесь не будет
  dependents: number; // dependents на верхнем уровне для формы
  work_experience: WorkExperience;
  pension_points: number;
  benefits: string;
  documents: string;
  has_incorrect_document: boolean;
  disability?: DisabilityInfo;
  other_documents_extracted_data?: OtherDocumentExtractedBlock[]; // НОВОЕ ПОЛЕ
}


// Соответствует ProcessOutput с бэкенда
export interface ProcessOutput {
  case_id: number;
  final_status: string; // 'СООТВЕТСТВУЕТ' | 'НЕ СООТВЕТСТВУЕТ' (или другие от бэка)
  explanation: string;
  confidence_score: number;
  // errors?: ApiError[]; // Если ProcessOutput будет возвращать ошибки
}

// Соответствует CaseHistoryEntry с бэкенда (или то, что реально приходит от /history)
export interface HistoryEntry {
  id: number;
  created_at: string; // "YYYY-MM-DD" или полный ISO datetime
  pension_type: string;
  final_status: string;
  final_explanation?: string;
  rag_confidence?: number;
  personal_data?: PersonalData; // Полный PersonalData, а не урезанный
}

// Для ответа от /api/v1/analyze_case
export interface RagAnalysisResponse {
  analysis_result: string;
  confidence_score: number;
}

// Новый тип для стандартизированной ошибки API
export interface ApiErrorDetail {
  message: string;
  status?: number;
  details?: unknown; // Дополнительные детали из ответа бэкенда
}

// --- OCR Types ---

// Соответствует PassportData с бэкенда
export interface OcrPassportData {
  last_name?: string;
  first_name?: string;
  middle_name?: string;
  birth_date?: string; // Ожидаемый формат: YYYY-MM-DD или DD.MM.YYYY (требует обработки)
  sex?: string; // На бэке gender, здесь sex из OCR
  birth_place?: string;
  passport_series?: string;
  passport_number?: string;
  issue_date?: string; // Ожидаемый формат: YYYY-MM-DD или DD.MM.YYYY (требует обработки)
  issuing_authority?: string;
  department_code?: string;
}

// Соответствует SnilsData с бэкенда
export interface OcrSnilsData {
  // Поля из примера ответа OCR СНИЛС
  last_name?: string;
  first_name?: string;
  middle_name?: string;
  gender?: string;
  birth_date?: string;
  birth_place?: string; // Место рождения может быть и в СНИЛС
  snils_number?: string;
}

// Соответствует OtherDocumentData с бэкенда
export interface OcrOtherDocumentData {
  identified_document_type?: string;
  standardized_document_type?: string;
  extracted_fields?: Record<string, any>;
  multimodal_assessment?: string;
  text_llm_reasoning?: string;
}

// Тип ответа от /extract_document_data
export type OcrExtractionResponse =
  | { documentType: 'passport'; data: OcrPassportData }
  | { documentType: 'snils'; data: OcrSnilsData }
  | { documentType: 'other'; data: OcrOtherDocumentData }
  | { documentType: 'error'; message: string; errorDetails?: any };

export type OcrDocumentType = 'passport' | 'snils' | 'other';