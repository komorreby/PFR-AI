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
  dependents: number;
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

// Соответствует CaseDataInput с бэкенда
export interface CaseFormData {
  pension_type: string;
  personal_data: PersonalData;
  work_experience: WorkExperience;
  pension_points: number;
  benefits: string[];
  documents: string[];
  has_incorrect_document: boolean;
  disability?: DisabilityInfo;
}

// Для формы React Hook Form, где benefits и documents - строки
export interface CaseFormDataTypeForRHF extends Omit<CaseFormData, 'benefits' | 'documents'> {
  benefits: string;
  documents: string;
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

// Пример структуры ApiError для поля errors в ProcessOutput (если понадобится)
// export interface ApiError {
//   code?: string;
//   description: string;
//   law?: string;
//   recommendation?: string;
//   field?: string; // Для ошибок валидации полей
// } 