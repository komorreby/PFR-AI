import { format, isValid } from 'date-fns';
// import { CaseFormDataType, WorkRecordType } from './components/CaseForm'; // Будет заменено на импорт из ../types
import { CaseFormDataTypeForRHF, CaseFormData, PersonalData, OtherDocumentExtractedBlock } from './types'; // Импорт из нового файла

// Вспомогательная функция для форматирования Date в YYYY-MM-DD
export const formatDateForInput = (date: Date | null | undefined): string => {
  if (!date || !isValid(date)) return '';
  return format(date, 'yyyy-MM-dd');
};

export const prepareDataForApi = (formData: CaseFormDataTypeForRHF): CaseFormData => {
  // Создаем объект personal_data для API, включая dependents
  const apiPersonalData: PersonalData = {
    ...formData.personal_data, // Берем все поля из personal_data формы
    dependents: formData.dependents, // Добавляем dependents с верхнего уровня формы
    name_change_info: (formData.personal_data.name_change_info?.old_full_name || formData.personal_data.name_change_info?.date_changed)
            ? formData.personal_data.name_change_info
            : null,
  };

  // Очищаем other_documents_extracted_data, оставляя только нужные поля
  const sanitizedOtherDocumentsData = formData.other_documents_extracted_data?.map(doc => {
    const newDoc: OtherDocumentExtractedBlock = {};
    if (doc.standardized_document_type) {
      newDoc.standardized_document_type = doc.standardized_document_type;
    }
    if (doc.extracted_fields) {
      newDoc.extracted_fields = doc.extracted_fields;
    }
    return newDoc;
  });

  const dataToSend: CaseFormData = {
    pension_type: formData.pension_type, // Явно указываем поля, чтобы избежать лишних
    personal_data: apiPersonalData,
    work_experience: formData.work_experience,
    pension_points: formData.pension_points,
    benefits: (formData.benefits || '').split(',').map((s: string) => s.trim()).filter(Boolean),
    documents: (formData.documents || '').split(',').map((s: string) => s.trim()).filter(Boolean),
    has_incorrect_document: formData.has_incorrect_document,
    disability: formData.disability,
    other_documents_extracted_data: sanitizedOtherDocumentsData
  };
  // Удаляем dependents с верхнего уровня, если он там случайно оказался после spread (...)
  // Этого не должно быть из-за типизации, но для безопасности:
  // delete (dataToSend as any).dependents; 

  return dataToSend;
}; 