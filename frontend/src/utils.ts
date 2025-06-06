import { format, isValid } from 'date-fns';
// import { CaseFormDataType, WorkRecordType } from './components/CaseForm'; // Будет заменено на импорт из ../types
import { CaseFormDataTypeForRHF, CaseDataInput, PersonalData, OtherDocumentData } from './types'; // Импорт из нового файла

// Вспомогательная функция для форматирования Date в YYYY-MM-DD
export const formatDateForInput = (date: Date | null | undefined): string => {
  if (!date || !isValid(date)) return '';
  return format(date, 'yyyy-MM-dd');
};

export const prepareDataForApi = (formData: CaseFormDataTypeForRHF): CaseDataInput => {
  // Создаем объект personal_data для API, включая dependents
  const apiPersonalData: PersonalData = {
    last_name: formData.personal_data?.last_name || '',
    first_name: formData.personal_data?.first_name || '',
    middle_name: formData.personal_data?.middle_name || null,
    birth_date: formData.personal_data?.birth_date || '',
    snils: formData.personal_data?.snils || '',
    gender: formData.personal_data?.gender || '',
    citizenship: formData.personal_data?.citizenship || '',
    dependents: typeof formData.dependents === 'number' ? formData.dependents : 0, // Обеспечиваем тип number
    name_change_info: (formData.personal_data?.name_change_info?.old_full_name || formData.personal_data?.name_change_info?.date_changed) && formData.personal_data?.name_change_info
            ? {
                old_full_name: formData.personal_data.name_change_info.old_full_name,
                date_changed: formData.personal_data.name_change_info.date_changed
              }
            : null,
  };

  // Очищаем other_documents_extracted_data, оставляя только нужные поля
  const sanitizedOtherDocumentsData = formData.other_documents_extracted_data?.map(doc => {
    const newDoc: Partial<OtherDocumentData> = {}; // Используем Partial т.к. можем не все поля заполнять
    if (doc.standardized_document_type) {
      newDoc.standardized_document_type = doc.standardized_document_type;
    }
    if (doc.extracted_fields) {
      newDoc.extracted_fields = doc.extracted_fields;
    }
    // Можно добавить и другие поля из OtherDocumentData при необходимости
    return newDoc as OtherDocumentData; // Приводим к OtherDocumentData, если уверены в структуре
  }).filter(Boolean) as OtherDocumentData[] | undefined; // Фильтруем null/undefined и приводим тип

  const dataToSend: CaseDataInput = {
    pension_type: formData.pension_type || '', // Обеспечиваем наличие значения
    personal_data: apiPersonalData,
    work_experience: formData.work_experience 
        ? { // Обеспечиваем структуру WorkExperience
            total_years: formData.work_experience.total_years || 0,
            records: formData.work_experience.records || null
          } 
        : null,
    pension_points: formData.pension_points || null,
    benefits: (formData.benefits || '').split(',').map((s: string) => s.trim()).filter(Boolean),
    // Для submitted_documents теперь используется submitted_documents, а не documents
    submitted_documents: (formData.submitted_documents || '').split(',').map((s: string) => s.trim()).filter(Boolean),
    has_incorrect_document: formData.has_incorrect_document || null,
    disability: formData.disability 
        ? { // Обеспечиваем структуру DisabilityInfo
            group: formData.disability.group || "1", // Пример значения по умолчанию
            date: formData.disability.date || '',
            cert_number: formData.disability.cert_number || null
          }
        : null,
    other_documents_extracted_data: sanitizedOtherDocumentsData || null
  };
  // Удаляем dependents с верхнего уровня, если он там случайно оказался после spread (...)
  // Этого не должно быть из-за типизации, но для безопасности:
  // delete (dataToSend as any).dependents; 

  return dataToSend;
}; 