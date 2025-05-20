import React, { useState, useCallback } from 'react';
import {
  Box,
  Heading,
  Text,
  VStack,
  // Button, // Если кнопка "Пропустить" не нужна здесь
  useToast,
  Divider,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  SimpleGrid, // Для размещения двух загрузчиков
} from '@chakra-ui/react';
import { UseFormSetValue, UseFormTrigger, Control, FieldPath, UseFormGetValues, UseFieldArrayAppend } from 'react-hook-form';
import OcrUploader from '../formInputs/OcrUploader';
import type { CaseFormDataTypeForRHF, OcrExtractionResponse, OcrDocumentType, OcrPassportData, OcrSnilsData, OcrOtherDocumentData, WorkRecord, OcrWorkBookData, OcrWorkBookRecordEntry } from '../../types';
import { formatDateForInput } from '../../utils'; // Для форматирования дат
import { isValid, parse as parseDateFns, format as formatDateFns } from 'date-fns'; // Для парсинга дат

interface OcrStepComponentProps {
  setValue: UseFormSetValue<CaseFormDataTypeForRHF>;
  trigger: UseFormTrigger<CaseFormDataTypeForRHF>;
  getValues: UseFormGetValues<CaseFormDataTypeForRHF>;
  control?: Control<CaseFormDataTypeForRHF>;
  appendWorkRecord?: UseFieldArrayAppend<CaseFormDataTypeForRHF, "work_experience.records">;
}

const OcrStepComponent: React.FC<OcrStepComponentProps> = ({
  setValue,
  trigger,
  getValues,
  appendWorkRecord,
}) => {
  const toast = useToast(); // toast объявлен здесь

  // Новый обработчик для успешного OCR из OcrUploader
  const handleOcrSuccess = useCallback((
    ocrData: OcrExtractionResponse,
    documentType: OcrDocumentType // OcrUploader передает и тип документа
  ) => {
    let mainMessage = 'Данные обработаны.';
    let status: 'info' | 'success' | 'error' | 'warning' = 'info'; // Статус по умолчанию
    const fieldsUpdated: FieldPath<CaseFormDataTypeForRHF>[] = [];

    if (ocrData.documentType === 'error') {
      mainMessage = ocrData.message || 'Ошибка распознавания документа.';
      status = 'error';
      console.error("OCR Error (reported by OcrUploader):", ocrData.errorDetails);
    } else {
      status = 'success'; // По умолчанию success, если не ошибка
      if (ocrData.documentType === 'passport' && ocrData.data) {
        mainMessage = 'Данные из Паспорта частично распознаны!';
        const data = ocrData.data as OcrPassportData; // Уточняем тип
        if (data.last_name) { setValue('personal_data.last_name', data.last_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.last_name'); }
        if (data.first_name) { setValue('personal_data.first_name', data.first_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.first_name'); }
        if (data.middle_name) { setValue('personal_data.middle_name', data.middle_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.middle_name'); }
        if (data.birth_date) {
          let parsedDate = parseDateFns(data.birth_date, 'dd.MM.yyyy', new Date());
          if (!isValid(parsedDate)) parsedDate = parseDateFns(data.birth_date, 'yyyy-MM-dd', new Date());
          if (isValid(parsedDate)) {setValue('personal_data.birth_date', formatDateForInput(parsedDate), { shouldDirty: true }); fieldsUpdated.push('personal_data.birth_date');}
        }
        // Используем data.sex и конвертируем в gender
        if (data.sex) {
          const gender = data.sex.toLowerCase().startsWith('м') || data.sex.toLowerCase().startsWith('m') ? 'male' : (data.sex.toLowerCase().startsWith('ж') || data.sex.toLowerCase().startsWith('f') ? 'female' : '');
          if (gender) { setValue('personal_data.gender', gender, { shouldDirty: true }); fieldsUpdated.push('personal_data.gender'); }
        }
        if (data.birth_place) {
          setValue('personal_data.birth_place', data.birth_place, { shouldDirty: true });
          fieldsUpdated.push('personal_data.birth_place');
          if (data.birth_place.toLowerCase().includes('российская федерация') || data.birth_place.toLowerCase().includes('россия')) {
            setValue('personal_data.citizenship', 'Россия', { shouldDirty: true });
            fieldsUpdated.push('personal_data.citizenship');
          }
        }
        if (data.passport_series) { setValue('personal_data.passport_series', data.passport_series, { shouldDirty: true }); fieldsUpdated.push('personal_data.passport_series'); }
        if (data.passport_number) { setValue('personal_data.passport_number', data.passport_number, { shouldDirty: true }); fieldsUpdated.push('personal_data.passport_number'); }
        if (data.issuing_authority) { setValue('personal_data.issuing_authority', data.issuing_authority, { shouldDirty: true }); fieldsUpdated.push('personal_data.issuing_authority'); }
        if (data.department_code) { setValue('personal_data.department_code', data.department_code, { shouldDirty: true }); fieldsUpdated.push('personal_data.department_code'); }
        if (data.issue_date) {
          let parsedIssueDate = parseDateFns(data.issue_date, 'dd.MM.yyyy', new Date());
          if (!isValid(parsedIssueDate)) {
            parsedIssueDate = parseDateFns(data.issue_date, 'yyyy-MM-dd', new Date());
          }
          if (isValid(parsedIssueDate)) {
            setValue('personal_data.issue_date', formatDateForInput(parsedIssueDate), { shouldDirty: true });
            fieldsUpdated.push('personal_data.issue_date');
          } else {
            console.warn(`OCR Passport (${documentType}): Не удалось распознать формат даты выдачи: ${data.issue_date}`);
          }
        }
      } else if (ocrData.documentType === 'snils' && ocrData.data) {
        mainMessage = 'Данные из СНИЛС частично распознаны!';
        const data = ocrData.data as OcrSnilsData; // Уточняем тип
        if (data.snils_number) {
          setValue('personal_data.snils', data.snils_number, { shouldDirty: true });
          fieldsUpdated.push('personal_data.snils');
        }
        if (data.last_name && !getValues('personal_data.last_name')) { setValue('personal_data.last_name', data.last_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.last_name'); }
        if (data.first_name && !getValues('personal_data.first_name')) { setValue('personal_data.first_name', data.first_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.first_name'); }
        if (data.middle_name && !getValues('personal_data.middle_name')) { setValue('personal_data.middle_name', data.middle_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.middle_name'); }
        if (data.birth_date && !getValues('personal_data.birth_date')) {
          let parsedBDateSnils = parseDateFns(data.birth_date, 'dd.MM.yyyy', new Date());
          if (!isValid(parsedBDateSnils)) {
            parsedBDateSnils = parseDateFns(data.birth_date, 'yyyy-MM-dd', new Date());
          }
          if (isValid(parsedBDateSnils)) {
            setValue('personal_data.birth_date', formatDateForInput(parsedBDateSnils), { shouldDirty: true });
            fieldsUpdated.push('personal_data.birth_date');
          } else {
             console.warn(`OCR SNILS (${documentType}): Не удалось распознать формат даты рождения: ${data.birth_date}`);
          }
        }
         if (data.gender && !getValues('personal_data.gender')) { // data.gender здесь из OcrSnilsData
          const gender = data.gender.toLowerCase().startsWith('муж') ? 'male' : (data.gender.toLowerCase().startsWith('жен') ? 'female' : '');
          if (gender) { setValue('personal_data.gender', gender, { shouldDirty: true }); fieldsUpdated.push('personal_data.gender'); }
        }
      } else if (ocrData.documentType === 'work_book' && ocrData.data) {
        const data = ocrData.data as OcrWorkBookData;
        mainMessage = 'Данные из Трудовой книжки обработаны.';
        let recordsAddedCount = 0;
        if (data.records && data.records.length > 0) {
          data.records.forEach(ocrRecord => {
            const newRecord: WorkRecord = {
              organization: ocrRecord.organization || '',
              position: ocrRecord.position || '',
              start_date: '',
              end_date: '',
              special_conditions: false
            };

            if (ocrRecord.date_in) {
              let parsedDateIn = parseDateFns(ocrRecord.date_in, 'dd.MM.yyyy', new Date());
              if (!isValid(parsedDateIn)) parsedDateIn = parseDateFns(ocrRecord.date_in, 'yyyy-MM-dd', new Date());
              if (!isValid(parsedDateIn)) parsedDateIn = parseDateFns(ocrRecord.date_in, 'yyyy.MM.dd', new Date()); 
              if (isValid(parsedDateIn)) newRecord.start_date = formatDateForInput(parsedDateIn);
            }

            if (ocrRecord.date_out) {
              let parsedDateOut = parseDateFns(ocrRecord.date_out, 'dd.MM.yyyy', new Date());
              if (!isValid(parsedDateOut)) parsedDateOut = parseDateFns(ocrRecord.date_out, 'yyyy-MM-dd', new Date());
              if (!isValid(parsedDateOut)) parsedDateOut = parseDateFns(ocrRecord.date_out, 'yyyy.MM.dd', new Date()); 
              if (isValid(parsedDateOut)) newRecord.end_date = formatDateForInput(parsedDateOut);
            } else {
              newRecord.end_date = ''; 
            }
            
            if (appendWorkRecord) {
              appendWorkRecord(newRecord);
              recordsAddedCount++;
            } else {
              const currentRecords = getValues('work_experience.records') || [];
              setValue('work_experience.records', [...currentRecords, newRecord], { shouldDirty: true, shouldValidate: true });
              recordsAddedCount++; 
            }
          });
        }
        // Обновляем сообщение и total_years на основе calculated_total_years
        if (typeof data.calculated_total_years === 'number') {
            setValue('work_experience.total_years', data.calculated_total_years, { shouldDirty: true, shouldValidate: true });
            fieldsUpdated.push('work_experience.total_years' as FieldPath<CaseFormDataTypeForRHF>);
            if (recordsAddedCount > 0) {
                mainMessage = `Добавлено ${recordsAddedCount} записей из трудовой книжки. Общий стаж автоматически рассчитан: ${data.calculated_total_years.toFixed(1)} лет.`;
            } else {
                mainMessage = `Записи о стаже не извлечены, но общий стаж рассчитан: ${data.calculated_total_years.toFixed(1)} лет. Проверьте корректность!`;
                status = 'warning'; // Так как записи не извлечены, но стаж как-то посчитан
            }
        } else if (recordsAddedCount > 0) {
            mainMessage = `Добавлено ${recordsAddedCount} записей из трудовой книжки. Автоматический расчет общего стажа не выполнен OCR.`;
            // Статус не меняем, если записи добавлены успешно, это просто доп. информация
            // status = 'warning'; 
        } else if (data.records && data.records.length === 0) { // Это условие уже было
          mainMessage = "В трудовой книжке не найдено записей о стаже или они не были распознаны.";
          status = 'warning';
        } else {
          mainMessage = "Не удалось извлечь записи о стаже из трудовой книжки: неверный формат ответа от OCR или отсутствуют записи.";
          status = 'warning';
        }
        // Добавляем work_experience.records в fieldsUpdated, если были добавлены записи, чтобы сработал trigger для массива
        if (recordsAddedCount > 0) {
            fieldsUpdated.push('work_experience.records' as FieldPath<CaseFormDataTypeForRHF>); 
        }
      } else if (ocrData.documentType === 'other' && ocrData.data) {
        mainMessage = 'Данные из Дополнительного документа частично распознаны!';
        const existingOtherData = getValues('other_documents_extracted_data') || [];
        setValue('other_documents_extracted_data', [...existingOtherData, ocrData.data as OcrOtherDocumentData], { shouldDirty: true });
        fieldsUpdated.push('other_documents_extracted_data'  as FieldPath<CaseFormDataTypeForRHF>);
      }
    }
    
    // Показываем toast в зависимости от результата
    if (fieldsUpdated.length > 0 && status === 'success') {
      toast({
        title: 'Автозаполнение успешно',
        description: `${mainMessage} Пожалуйста, проверьте и при необходимости дополните данные. Обновлено полей: ${fieldsUpdated.length}.`,
        status: 'success', // Явно success
        duration: 7000,
        isClosable: true,
      });
      trigger(fieldsUpdated as FieldPath<CaseFormDataTypeForRHF>[]); // Валидируем обновленные поля
    } else {
      // Показываем toast, если статус 'error', 'warning', 
      // или если это 'success' но без обновленных полей (например, пустая трудовая книжка).
      // Не показываем toast для начального 'info' статуса, если ничего не произошло.
      if (status === 'error' || status === 'warning' || (status === 'success' && fieldsUpdated.length === 0)) {
         toast({
            title: status === 'error' ? `Ошибка OCR: ${documentType.toUpperCase()}` : `Результат OCR: ${documentType.toUpperCase()}`,
            description: mainMessage,
            status: status, 
            duration: (status === 'error' || status === 'warning') ? 7000 : 5000,
            isClosable: true,
        });
      }
    }
  }, [setValue, getValues, trigger, toast, appendWorkRecord]);

  // Новый обработчик для ошибок OCR из OcrUploader
  const handleOcrFailure = useCallback((
    errorMessage: string,
    documentType: OcrDocumentType
  ) => {
    toast({
      title: `Ошибка обработки ${documentType.toUpperCase()}`,
      description: errorMessage || "Произошла неизвестная ошибка при распознавании.",
      status: "error",
      duration: 7000,
      isClosable: true,
    });
    // Здесь можно добавить дополнительную логику, если нужно, например, сброс каких-то полей
  }, [toast]);

  return (
    <VStack spacing={6} align="stretch">
      <Heading size="md" mb={0}>Шаг 2: Автозаполнение данных (OCR)</Heading>
      <Text color="gray.600" fontSize="sm" mt={0} mb={4}>
        Загрузите сканы паспорта, СНИЛС и трудовой книжки. Система попытается автоматически считать данные для предзаполнения.
      </Text>
      
      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
        <OcrUploader 
          documentType="passport" 
          onOcrSuccess={handleOcrSuccess} 
          onOcrError={handleOcrFailure}
          uploaderTitle="Загрузить Паспорт РФ"
        />
        <OcrUploader 
          documentType="snils" 
          onOcrSuccess={handleOcrSuccess}
          onOcrError={handleOcrFailure}
          uploaderTitle="Загрузить СНИЛС"
        />
        <OcrUploader
          documentType="work_book"
          onOcrSuccess={handleOcrSuccess}
          onOcrError={handleOcrFailure}
          uploaderTitle="Загрузить Трудовую книжку"
        />
      </SimpleGrid>

      <Divider my={6}/>

      <Alert status='info' variant='subtle'>
        <AlertIcon />
        <Box flex="1">
          <AlertTitle>Как это работает?</AlertTitle>
          <AlertDescription display='block'>
            - Загрузите изображения или PDF-файлы ваших документов в соответствующие поля.<br/>
            - После успешного распознавания, поля на следующем шаге ("Личные данные") будут автоматически заполнены.<br/>
            - Вы всегда сможете проверить и отредактировать предзаполненные данные.<br/>
            - Этот шаг не обязателен, вы можете пропустить его, нажав "Далее".
          </AlertDescription>
        </Box>
      </Alert>
      
      {/* 
        Кнопка "Пропустить" может быть добавлена сюда или управляться из CaseForm 
        в зависимости от общей логики навигации по шагам 
      */}
      {/* {onStepComplete && (
        <Button onClick={onStepComplete} colorScheme='gray' variant='outline' mt={4}>
          Пропустить и заполнить вручную
        </Button>
      )} */}

    </VStack>
  );
};

export default OcrStepComponent; 