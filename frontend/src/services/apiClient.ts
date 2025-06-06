// src/services/apiClient.ts

import {
    ApiError,
    CaseDataInput,
    CaseHistoryEntry,
    DocumentDetail,
    DocumentExtractionParams,
    DocumentFormat,
    FullCaseData,
    HealthCheckResponse,
    OcrTaskStatusResponse,
    OcrTaskSubmitResponse,
    PensionTypeInfo,
    ProcessOutput,
    StandardErrorResponse,
    TasksStatsResponse,
    HttpValidationError,
    TokenResponse,
    User,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentDeleteResponse
} from '../types';

// Используем переменные окружения Vite для API_BASE_URL
// В файле .env или .env.local (в корне проекта) нужно добавить:
// VITE_API_BASE_URL=http://localhost:8000
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// --- Управление токеном --- 
const TOKEN_KEY = 'pfr_ai_auth_token';

export function storeToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
}

export function removeToken(): void {
    localStorage.removeItem(TOKEN_KEY);
}
// --- Конец Управления токеном ---

async function handleApiResponse<T>(response: Response): Promise<T> {
    if (response.status === 204) { // No Content
        return {} as T; // или null, или другое подходящее значение
    }

    const contentType = response.headers.get('content-type');
    let data;

    if (contentType && contentType.includes('application/json')) {
        data = await response.json();
    } else if (contentType && (contentType.includes('application/pdf') || contentType.includes('application/vnd.openxmlformats-officedocument.wordprocessingml.document'))) {
        // Для файлов возвращаем Blob, обработка будет в вызывающей функции
        return response.blob() as Promise<T>; 
    } else {
        // Если контент не JSON и не известный файл, попробуем как текст (для отладки)
        // В реальном приложении здесь может быть более строгая обработка
        // data = { message: await response.text() };
        // Для простоты, если не JSON и не файл, пока считаем, что это может быть ошибка без JSON тела
        if (!response.ok) {
             const errorText = await response.text();
             console.warn("API Response not JSON and not OK:", response.status, errorText);
             throw {
                status: response.status,
                message: errorText || `Ошибка сервера: ${response.status}`,
                rawError: errorText
            } as ApiError;
        }
        return {} as T; // Если response.ok, но нет контента, возвращаем пустой объект
    }

    if (!response.ok) {
        console.error('API Error Response:', data);
        let errorMessage = `Ошибка сервера: ${response.status}`;
        let errorCode: string | undefined;
        let validationDetails: any | undefined;

        if (data && typeof data === 'object') {
            // Проверяем на StandardErrorResponse (новый формат)
            if ('error_code' in data && 'message' in data) {
                const standardError = data as StandardErrorResponse;
                errorMessage = standardError.message;
                errorCode = standardError.error_code;
                if (standardError.error_code === 'VALIDATION_ERROR' && standardError.details) {
                    validationDetails = standardError.details as any; // StandardizedValidationErrorDetail[]
                }
            } 
            // Проверяем на FastAPI HttpValidationError (старый формат)
            else if ('detail' in data && Array.isArray((data as HttpValidationError).detail)) {
                const validationError = data as HttpValidationError;
                errorMessage = 'Ошибка валидации. Проверьте введенные данные.';
                errorCode = 'FASTAPI_VALIDATION_ERROR';
                validationDetails = validationError.detail; // ValidationErrorDetailItem[]
            } 
            // Общий случай для других JSON ошибок
            else if ('detail' in data && typeof data.detail === 'string') {
                errorMessage = data.detail;
            } else if ('message' in data && typeof data.message === 'string') {
                errorMessage = data.message;
            }
        }
        
        throw {
            status: response.status,
            message: errorMessage,
            errorCode: errorCode,
            validationDetails: validationDetails,
            rawError: data
        } as ApiError;
    }
    return data as T;
}

async function request<T>(path: string, options: RequestInit = {}, rawResponse: boolean = false): Promise<T> {
    const token = getToken();
    const headers = new Headers(options.headers || {});
    
    // Не добавляем Content-Type для FormData, браузер сделает это сам с правильным boundary
    if (!(options.body instanceof FormData)) {
        if (!headers.has('Content-Type')) {
             headers.set('Content-Type', 'application/json');
        }
    }

    if (token) {
        headers.set('Authorization', `Bearer ${token}`);
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers,
    });
    if (rawResponse) {
        return response as unknown as T;
    }
    return handleApiResponse<T>(response);
}

// --- Эндпоинты Аутентификации ---
export async function loginUser(usernameValue: string, passwordValue: string): Promise<TokenResponse> {
    const details = {
        username: usernameValue,
        password: passwordValue,
    };
    const formBody = Object.keys(details)
        // @ts-ignore
        .map(key => encodeURIComponent(key) + '=' + encodeURIComponent(details[key]))
        .join('&');

    // Передаем пустой объект вместо `${API_BASE_URL}/auth/token`
    // и устанавливаем Content-Type как application/x-www-form-urlencoded
    const response = await fetch(`${API_BASE_URL}/auth/token`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formBody,
    });
    return handleApiResponse<TokenResponse>(response);
}

export async function getCurrentUser(): Promise<User> {
    return request<User>('/users/me');
}

// --- Конфигурация и Справочники ---

export async function getPensionTypes(): Promise<PensionTypeInfo[]> {
    return request<PensionTypeInfo[]>('/pension_types');
}

export async function getPensionDocuments(pensionTypeId: string): Promise<DocumentDetail[]> {
    return request<DocumentDetail[]>(`/pension_documents/${pensionTypeId}`);
}

export async function getStandardDocumentNames(): Promise<string[]> {
    return request<string[]>('/standard_document_names');
}

// --- Работа с Делами (Cases) ---

export async function createCase(caseData: CaseDataInput): Promise<ProcessOutput> {
    return request<ProcessOutput>('/cases', {
        method: 'POST',
        body: JSON.stringify(caseData),
    });
}

export async function getCaseStatus(caseId: number): Promise<ProcessOutput> {
    return request<ProcessOutput>(`/cases/${caseId}/status`);
}

export async function getFullCaseData(caseId: number): Promise<FullCaseData> {
    return request<FullCaseData>(`/cases/${caseId}`);
}

export async function getCaseHistory(skip: number = 0, limit: number = 10): Promise<CaseHistoryEntry[]> {
    return request<CaseHistoryEntry[]>(`/cases/history?skip=${skip}&limit=${limit}`);
}

export async function downloadCaseDocument(caseId: number, format: DocumentFormat): Promise<Blob> {
    const response = await request<Response>(`/cases/${caseId}/document?format=${format}`, {
        method: 'GET',
    }, true); // Pass true to get raw response
    if (!response.ok) {
        // Try to parse error from body if it's not a success response
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || 'Failed to download document');
    }
    return response.blob();
}

export interface DeleteCaseResponse {
    message: string;
    case_id: number;
}

export async function deleteCase(caseId: number): Promise<DeleteCaseResponse> {
    return request<DeleteCaseResponse>(`/cases/${caseId}`, {
        method: 'DELETE',
    });
}

// --- Извлечение Данных из Документов (OCR/Vision) ---

export async function submitOcrTask(params: DocumentExtractionParams): Promise<OcrTaskSubmitResponse> {
    const formData = new FormData();
    formData.append('image', params.image);
    formData.append('document_type', params.document_type);
    if (params.ttl_hours) {
        formData.append('ttl_hours', params.ttl_hours.toString());
    }

    return request<OcrTaskSubmitResponse>('/document_extractions', {
        method: 'POST',
        body: formData, // Content-Type будет установлен браузером для FormData
    });
}

export async function getOcrTaskStatus(taskId: string): Promise<OcrTaskStatusResponse> {
    return request<OcrTaskStatusResponse>(`/document_extractions/${taskId}`);
}

export async function getOcrTasksStats(): Promise<TasksStatsResponse> {
    return request<TasksStatsResponse>('/tasks/stats');
}

export async function getHealthCheck(): Promise<HealthCheckResponse> {
    return request<HealthCheckResponse>('/health');
}

// Функции для работы с RAG документами (требуют прав администратора)
export async function listRagDocuments(): Promise<DocumentListResponse> {
    return request<DocumentListResponse>('/documents');
}

export async function uploadRagDocument(file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return request<DocumentUploadResponse>('/documents', {
        method: 'POST',
        body: formData,
        // Заголовки Content-Type для FormData устанавливаются браузером автоматически
    });
}

export async function deleteRagDocument(filename: string): Promise<DocumentDeleteResponse> {
    return request<DocumentDeleteResponse>(`/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
    });
}