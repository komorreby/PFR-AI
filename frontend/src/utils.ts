import { format, isValid } from 'date-fns';
// import { CaseFormDataType, WorkRecordType } from './components/CaseForm'; // Будет заменено на импорт из ../types
import { CaseFormDataTypeForRHF, CaseFormData } from './types'; // Импорт из нового файла

// Вспомогательная функция для форматирования Date в YYYY-MM-DD
export const formatDateForInput = (date: Date | null | undefined): string => {
  if (!date || !isValid(date)) return '';
  return format(date, 'yyyy-MM-dd');
};

export const prepareDataForApi = (formData: CaseFormDataTypeForRHF): CaseFormData => {
  const dataToSend: CaseFormData = {
    ...formData,
    personal_data: { 
        ...formData.personal_data,
        name_change_info: (formData.personal_data.name_change_info?.old_full_name || formData.personal_data.name_change_info?.date_changed)
            ? formData.personal_data.name_change_info
            : null,
    },
    benefits: (formData.benefits || '').split(',').map((s: string) => s.trim()).filter(Boolean),
    documents: (formData.documents || '').split(',').map((s: string) => s.trim()).filter(Boolean),
  };
  return dataToSend;
}; 