import type { CaseFormData, ProcessOutput, HistoryEntry, RagAnalysisResponse, ApiErrorDetail } from '../types';

// Используем переменные окружения Vite для API_BASE_URL
// В файле .env.local (или других .env.* файлах) фронтенда нужно добавить:
// VITE_API_BASE_URL=http://127.0.0.1:8000
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function handleJsonResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      // Для 204 No Content или пустого ответа, если ожидается T, это может быть проблемой.
      // Для большинства GET/POST/PUT, которые возвращают данные, это будет ошибкой.
      // Если есть эндпоинты, которые легитимно возвращают 204 и их тип T = void, то это ОК.
      // Пока что, если мы ожидаем JSON, пустой ответ будет проблемой.
      // Уточнение: если тип T это что-то вроде { success: boolean }, то пустой ответ может быть {} as T, 
      // но если это массив или сложный объект, то это ошибка.
      // Для данного проекта большинство ответов ожидают данные, поэтому выбросим ошибку.
      console.warn(`Получен пустой успешный ответ (статус ${response.status}), но ожидались данные.`);
      // В зависимости от требований, можно вернуть `undefined as T` или `{}` 
      // если вызывающий код это корректно обработает. Пока бросаем ошибку.
      throw new Error(`Получен пустой успешный ответ (статус ${response.status}), но ожидались данные.`);
    }
    try {
      const data = await response.json();
      return data as T;
    } catch (error) {
      console.error("API Error: Failed to parse JSON response:", error);
      throw new Error(`Не удалось обработать JSON ответ сервера (статус ${response.status})`);
    }
  } else {
    let errorDetailMessage = `Ошибка ${response.status}: ${response.statusText}`;
    let errorDetailsFromServer: unknown = null;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        if (Array.isArray(errorData.detail)) {
            errorDetailMessage = errorData.detail.map((d: unknown) => (typeof d === 'object' && d && 'msg' in d ? (d as {msg: string}).msg : JSON.stringify(d))).join(', ');
        } else if (typeof errorData.detail === 'string') {
            errorDetailMessage = errorData.detail;
        } else {
            errorDetailMessage = JSON.stringify(errorData.detail);
        }
      } else if (errorData.message) { // Проверка на случай, если ошибка приходит в поле message
        errorDetailMessage = errorData.message;
      }
      errorDetailsFromServer = errorData;
    } catch (_jsonError) { /* ignore if error response is not JSON */ }
    
    console.error("API Error:", errorDetailMessage, "Status:", response.status, "Details from server:", errorDetailsFromServer);
    // Создаем ошибку, совместимую с ApiErrorDetail, но остающуюся экземпляром Error
    const error = new Error(errorDetailMessage) as Error & Partial<ApiErrorDetail>; 
    error.details = errorDetailsFromServer;
    error.status = response.status;
    throw error;
  }
}

export async function processCase(caseData: CaseFormData): Promise<ProcessOutput> {
  const response = await fetch(`${API_BASE_URL}/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(caseData),
  });
  return handleJsonResponse<ProcessOutput>(response);
}

export async function analyzeCase(caseData: CaseFormData): Promise<RagAnalysisResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analyze_case`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(caseData),
  });
  return handleJsonResponse<RagAnalysisResponse>(response);
}

export async function getHistory(limit: number = 50, skip: number = 0): Promise<HistoryEntry[]> {
  const response = await fetch(`${API_BASE_URL}/history?limit=${limit}&skip=${skip}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  return handleJsonResponse<HistoryEntry[]>(response);
}

export async function downloadDocument(caseId: number, format: 'pdf' | 'docx'): Promise<Response> {
  const response = await fetch(`${API_BASE_URL}/download_document/${caseId}?format=${format}`);
  if (!response.ok) {
    let errorDetailMessage = `Ошибка ${response.status}: ${response.statusText}`;
    let errorDetailsFromServer: unknown = null;
    try {
        const errorData = await response.json();
        if (errorData.detail) {
            if (Array.isArray(errorData.detail)) {
                errorDetailMessage = errorData.detail.map((d: unknown) => (typeof d === 'object' && d && 'msg' in d ? (d as {msg: string}).msg : JSON.stringify(d))).join(', ');
            } else if (typeof errorData.detail === 'string') {
                errorDetailMessage = errorData.detail;
            } else {
                errorDetailMessage = JSON.stringify(errorData.detail);
            }
        } else if (errorData.message) {
            errorDetailMessage = errorData.message;
        }
        errorDetailsFromServer = errorData;
    } catch (_e) { /* если ответ не JSON, используем статус */ }

    console.error("API Error (downloadDocument):", errorDetailMessage, "Status:", response.status, "Details from server:", errorDetailsFromServer);
    const error = new Error(errorDetailMessage) as Error & Partial<ApiErrorDetail>;
    error.details = errorDetailsFromServer;
    error.status = response.status;
    throw error;
  }
  return response;
} 