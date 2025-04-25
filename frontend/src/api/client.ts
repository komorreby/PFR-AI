// Типы данных, импортированные для ясности. В реальном проекте их лучше вынести
// в отдельный файл `types.ts` или использовать генерацию типов из OpenAPI схемы бэкенда.
import type { CaseFormDataType, ProcessResult, ApiError } from '../components/CaseForm';
import type { HistoryEntry } from '../components/HistoryList';

// <<< Определяем новый тип для ответа RAG-анализа
export interface RagAnalysisResponse {
    analysis_result: string;
    confidence_score: number;
}

// <<< Пока оставляем URL здесь как константу
const API_BASE_URL = 'http://127.0.0.1:8000';

// --- Вспомогательная функция для обработки ответа --- 
async function handleResponse<T>(response: Response): Promise<T> {
    if (response.ok) {
        // Обрабатываем случай пустого ответа (например, для скачивания файла)
        if (response.headers.get('content-length') === '0' || response.status === 204) {
            return {} as T; // Возвращаем пустой объект или другое подходящее значение
        }
        // Пытаемся распарсить JSON
        try {
            const data = await response.json();
            return data as T;
        } catch (error) {
            // Если парсинг не удался, но статус ОК (маловероятно, но возможно)
            console.error("Failed to parse JSON response:", error);
            throw new Error(`Не удалось обработать ответ сервера (статус ${response.status})`);
        }
    } else {
        // Пытаемся получить детали ошибки из тела
        let errorDetail = `Ошибка ${response.status}: ${response.statusText}`;
        try {
            const errorData = await response.json();
            errorDetail = errorData.detail || JSON.stringify(errorData);
        } catch (jsonError) { /* ignore */ }
        console.error("API Error:", errorDetail);
        throw new Error(errorDetail); // Бросаем ошибку с деталями
    }
}

// --- Функции API --- 

/**
 * Отправляет данные формы для базовой обработки и анализа ошибок.
 * @param caseData Данные формы
 * @returns Результат обработки (статус, объяснение, ошибки)
 */
export async function processCase(caseData: CaseFormDataType): Promise<ProcessResult> {
    const response = await fetch(`${API_BASE_URL}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(caseData),
    });
    return handleResponse<ProcessResult>(response);
}

/**
 * Отправляет описание дела для RAG-анализа.
 * @param caseDescription Текстовое описание дела
 * @returns Результат RAG-анализа с скором уверенности
 */
export async function analyzeCase(caseDescription: string): Promise<RagAnalysisResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/analyze_case`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ case_description: caseDescription }),
    });
    return handleResponse<RagAnalysisResponse>(response);
}

/**
 * Загружает историю обработанных дел.
 * @param limit Максимальное количество записей
 * @param skip Смещение (для пагинации)
 * @returns Массив записей истории
 */
export async function getHistory(limit: number = 50, skip: number = 0): Promise<HistoryEntry[]> {
    // TODO: Добавить параметры поиска, когда бэкенд будет их поддерживать
    const response = await fetch(`${API_BASE_URL}/history?limit=${limit}&skip=${skip}`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
    });
    return handleResponse<HistoryEntry[]>(response);
}

/**
 * Запрашивает скачивание файла отчета для указанного дела.
 * Важно: Эта функция возвращает сам объект Response, так как нам нужен доступ
 * к заголовкам (content-disposition) и телу как Blob для скачивания файла.
 * Обработка вынесена в вызывающий компонент (HistoryPage).
 * @param caseId ID дела
 * @param format Формат файла ('pdf' или 'docx')
 * @returns Объект Response
 */
export async function downloadDocument(caseId: number, format: 'pdf' | 'docx'): Promise<Response> {
    const response = await fetch(`${API_BASE_URL}/download_document/${caseId}?format=${format}`, {
        method: 'GET',
        // Не указываем Accept: 'application/json', так как ожидаем файл
    });
    if (!response.ok) {
        // Если ошибка, пытаемся получить детали
        let errorDetail = `Ошибка ${response.status}: ${response.statusText}`;
        try {
            const errorData = await response.json();
            errorDetail = errorData.detail || JSON.stringify(errorData);
        } catch (jsonError) { /* ignore */ }
        console.error("API Download Error:", errorDetail);
        throw new Error(errorDetail);
    }
    // Возвращаем полный Response для дальнейшей обработки в компоненте
    return response;
} 