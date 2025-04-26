import { format, isValid, differenceInYears } from 'date-fns';
import { CaseFormDataType, WorkRecordType } from './components/CaseForm';

// Вспомогательная функция для форматирования Date в YYYY-MM-DD
export const formatDateForInput = (date: Date | null | undefined): string => {
  if (!date || !isValid(date)) return '';
  return format(date, 'yyyy-MM-dd');
};

const calculateAge = (birthDateString: string): number | null => {
  const birthDate = new Date(birthDateString);
  return isValid(birthDate) ? differenceInYears(new Date(), birthDate) : null;
};

/**
 * Создает подробное текстовое описание дела для RAG-анализа
 * на основе всех данных формы.
 * @param formData - Данные формы типа CaseFormDataType
 * @returns Строка описания дела.
 */
export const createComprehensiveRagDescription = (formData: CaseFormDataType): string => {
    const lines: string[] = [];
    const { personal_data, work_experience, pension_points, benefits, documents, has_incorrect_document, pension_type, disability } = formData;

    // --- Личные данные ---
    lines.push("--- Личные данные ---");
    const fullName = [
        personal_data.last_name,
        personal_data.first_name,
        personal_data.middle_name
    ].filter(Boolean).join(' ');
    lines.push(`ФИО: ${fullName || 'не указано'}`);
    lines.push(`Дата рождения: ${personal_data.birth_date || 'не указано'}`);
    lines.push(`Возраст: ${calculateAge(personal_data.birth_date) || 'неизвестно'}`);
    lines.push(`СНИЛС: ${personal_data.snils || 'не указано'}`);
    lines.push(`Пол: ${personal_data.gender === 'male' ? 'Мужской' : personal_data.gender === 'female' ? 'Женский' : 'не указан'}`);
    lines.push(`Гражданство: ${personal_data.citizenship || 'не указано'}`);
    lines.push(`Количество иждивенцев: ${personal_data.dependents ?? 0}`);
    if (personal_data.name_change_info) {
        lines.push(`Смена ФИО: Да (Прежн: ${personal_data.name_change_info.old_full_name || '-'}, Дата: ${personal_data.name_change_info.date_changed || '-'})`);
    } else {
        lines.push("Смена ФИО: Нет");
    }
    lines.push(""); // Пустая строка для разделения

    // --- Данные о пенсии ---
    lines.push("--- Данные о пенсии ---");
    const pensionTypeText = pension_type === 'retirement_standard' ? 'страховая по старости' :
                            pension_type === 'disability_social' ? 'социальная по инвалидности' :
                            'тип не указан';
    lines.push(`Запрашиваемый тип пенсии: ${pensionTypeText}`);
    if (pension_type === 'retirement_standard') {
        lines.push(`Пенсионные баллы (ИПК): ${pension_points ?? 'не указано'}`);
    }
    if (disability) {
        lines.push(`Инвалидность: Группа ${disability.group || '-'}, Дата установления: ${disability.date || '-'}${disability.cert_number ? ", Номер справки: " + disability.cert_number : ''}`);
    }
    lines.push(`Льготы: ${benefits || 'нет'}`);
    lines.push("");

    // --- Трудовой стаж ---
    lines.push("--- Трудовой стаж ---");
    lines.push(`Общий стаж (лет, указанный пользователем): ${work_experience.total_years ?? 'не указано'}`);
    if (work_experience.records && work_experience.records.length > 0) {
        lines.push("Записи о работе:");
        work_experience.records.forEach((record: WorkRecordType, index: number) => {
            lines.push(`  ${index + 1}. Организация: ${record.organization || '-'}`);
            lines.push(`     Должность: ${record.position || '-'}`);
            lines.push(`     Период: ${record.start_date || '-'} по ${record.end_date || '-'}`);
            lines.push(`     Особые условия: ${record.special_conditions ? 'Да' : 'Нет'}`);
        });
    } else {
        lines.push("Записи о работе: отсутствуют");
    }
    lines.push("");

    // --- Документы ---
    lines.push("--- Документы ---");
    lines.push(`Представленные документы: ${documents || 'нет'}`);
    lines.push(`Наличие некорректных документов: ${has_incorrect_document ? 'Да' : 'Нет'}`);

    // Собираем все строки в одну
    return lines.join('\n');
}; 