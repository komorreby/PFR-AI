import React from 'react';
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
import { UseFormSetValue, UseFormTrigger, Control, FieldPath, UseFormGetValues } from 'react-hook-form';
import OcrUploader from '../formInputs/OcrUploader';
import type { CaseFormDataTypeForRHF, OcrExtractionResponse, OcrDocumentType, OcrPassportData, OcrSnilsData } from '../../types';
import { formatDateForInput } from '../../utils'; // Для форматирования дат
import { isValid, parse as parseDate } from 'date-fns'; // Для парсинга дат

interface OcrStepComponentProps {
  setValue: UseFormSetValue<CaseFormDataTypeForRHF>;
  trigger: UseFormTrigger<CaseFormDataTypeForRHF>;
  getValues: UseFormGetValues<CaseFormDataTypeForRHF>;
  control?: Control<CaseFormDataTypeForRHF>;
  onOcrErrorProp?: (error: any, docType: OcrDocumentType) => void; // Переименовал, чтобы не конфликтовать
}

const OcrStepComponent: React.FC<OcrStepComponentProps> = ({
  setValue,
  trigger,
  getValues,
  onOcrErrorProp, 
}) => {
  const toast = useToast(); // toast объявлен здесь

  // Обработчик ошибок по умолчанию или переданный
  const handleOcrError = onOcrErrorProp || ((error, docType) => {
    console.error(`Error processing ${docType}:`, error);
    toast({
        title: `Ошибка обработки ${docType}`,
        description: error.message || "Произошла неизвестная ошибка",
        status: "error",
        duration: 5000,
        isClosable: true,
    });
  });

  const handleOcrSuccess = async (ocrData: OcrExtractionResponse, docType: OcrDocumentType) => {
    let fieldsUpdated: FieldPath<CaseFormDataTypeForRHF>[] = [];
    let mainMessage = 'Данные не распознаны или документ не поддерживается для автозаполнения.';
    let toastStatus: "success" | "info" | "warning" = 'info';

    if (ocrData.documentType === 'passport' && ocrData.data) {
      const data = ocrData.data as OcrPassportData;
      mainMessage = 'Паспортные данные частично распознаны!';
      if (data.last_name) { setValue('personal_data.last_name', data.last_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.last_name'); }
      if (data.first_name) { setValue('personal_data.first_name', data.first_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.first_name'); }
      if (data.middle_name) { setValue('personal_data.middle_name', data.middle_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.middle_name'); }
      
      if (data.birth_date) {
        let parsedBDate = parseDate(data.birth_date, 'dd.MM.yyyy', new Date());
        if (!isValid(parsedBDate)) {
          parsedBDate = parseDate(data.birth_date, 'yyyy-MM-dd', new Date());
        }
        if (isValid(parsedBDate)) {
          setValue('personal_data.birth_date', formatDateForInput(parsedBDate), { shouldDirty: true });
          fieldsUpdated.push('personal_data.birth_date');
        } else {
          console.warn(`OCR Passport: Не удалось распознать формат даты рождения: ${data.birth_date}`);
        }
      }

      if (data.sex) { 
        const gender = data.sex.toLowerCase().startsWith('муж') ? 'male' : (data.sex.toLowerCase().startsWith('жен') ? 'female' : '');
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
        let parsedIssueDate = parseDate(data.issue_date, 'dd.MM.yyyy', new Date());
        if (!isValid(parsedIssueDate)) {
          parsedIssueDate = parseDate(data.issue_date, 'yyyy-MM-dd', new Date());
        }
        if (isValid(parsedIssueDate)) {
          setValue('personal_data.issue_date', formatDateForInput(parsedIssueDate), { shouldDirty: true });
          fieldsUpdated.push('personal_data.issue_date');
        } else {
          console.warn(`OCR Passport: Не удалось распознать формат даты выдачи: ${data.issue_date}`);
        }
      }

      // Добавляем "паспорт" в поле documents
      const currentDocsStringPassport = getValues('documents') || '';
      let docsArrayPassport = currentDocsStringPassport.split(',').map(d => d.trim()).filter(Boolean);
      if (!docsArrayPassport.includes('паспорт')) {
        docsArrayPassport.push('паспорт');
        setValue('documents', docsArrayPassport.join(', '), { shouldDirty: true });
      }

    } else if (ocrData.documentType === 'snils' && ocrData.data) {
      const data = ocrData.data as OcrSnilsData;
      mainMessage = 'Данные СНИЛС частично распознаны!';
      if (data.snils_number) { 
        setValue('personal_data.snils', data.snils_number, { shouldDirty: true }); 
        fieldsUpdated.push('personal_data.snils'); 
      }
      if (data.last_name && !getValues('personal_data.last_name')) { setValue('personal_data.last_name', data.last_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.last_name'); }
      if (data.first_name && !getValues('personal_data.first_name')) { setValue('personal_data.first_name', data.first_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.first_name'); }
      if (data.middle_name && !getValues('personal_data.middle_name')) { setValue('personal_data.middle_name', data.middle_name, { shouldDirty: true }); fieldsUpdated.push('personal_data.middle_name'); }
      if (data.birth_date && !getValues('personal_data.birth_date')) {
        let parsedBDateSnils = parseDate(data.birth_date, 'dd.MM.yyyy', new Date());
        if (!isValid(parsedBDateSnils)) {
          parsedBDateSnils = parseDate(data.birth_date, 'yyyy-MM-dd', new Date());
        }
        if (isValid(parsedBDateSnils)) {
          setValue('personal_data.birth_date', formatDateForInput(parsedBDateSnils), { shouldDirty: true });
          fieldsUpdated.push('personal_data.birth_date');
        } else {
           console.warn(`OCR SNILS: Не удалось распознать формат даты рождения: ${data.birth_date}`);
        }
      }
       if (data.gender && !getValues('personal_data.gender')) {
        const gender = data.gender.toLowerCase().startsWith('муж') ? 'male' : (data.gender.toLowerCase().startsWith('жен') ? 'female' : '');
        if (gender) { setValue('personal_data.gender', gender, { shouldDirty: true }); fieldsUpdated.push('personal_data.gender'); }
      }

      // Добавляем "снилс" в поле documents
      const currentDocsStringSnils = getValues('documents') || '';
      let docsArraySnils = currentDocsStringSnils.split(',').map(d => d.trim()).filter(Boolean);
      if (!docsArraySnils.includes('снилс')) {
        docsArraySnils.push('снилс');
        setValue('documents', docsArraySnils.join(', '), { shouldDirty: true });
      }

    } else if (ocrData.documentType === 'other' && ocrData.data) {
      mainMessage = `Документ типа '${ocrData.data.identified_document_type || 'Другой'}' обработан. Автозаполнение для этого типа не настроено.`;
      console.log('OCR Other Document Data:', ocrData.data);
      toastStatus = 'info';
    } else if (ocrData.documentType === 'error') {
      mainMessage = ocrData.message || 'Произошла ошибка при обработке документа.';
      console.error('OCR Error (structured):', ocrData.errorDetails);
      toastStatus = 'warning';
      handleOcrError(ocrData.errorDetails || new Error(mainMessage), docType); // Используем общий обработчик
    }

    if (fieldsUpdated.length > 0) {
      toastStatus = 'success';
      toast({
        title: 'Автозаполнение успешно',
        description: `${mainMessage} Пожалуйста, проверьте и при необходимости дополните данные. Обновлено полей: ${fieldsUpdated.length}.`,
        status: toastStatus,
        duration: 7000,
        isClosable: true,
      });
      if (fieldsUpdated.length > 0) {
        trigger(fieldsUpdated as FieldPath<CaseFormDataTypeForRHF>[]);
      }
    } else {
      if (ocrData.documentType === 'error' || toastStatus !== 'info') {
        toast({
            title: ocrData.documentType === 'error' ? 'Ошибка OCR' : 'Результат OCR',
            description: mainMessage,
            status: toastStatus,
            duration: 5000,
            isClosable: true,
        });
      }
    }
  };

  return (
    <VStack spacing={6} align="stretch">
      <Heading size="md" mb={0}>Шаг 2: Автозаполнение данных (OCR)</Heading>
      <Text color="gray.600" fontSize="sm" mt={0} mb={4}>
        Загрузите сканы паспорта и СНИЛС. Система попытается автоматически считать данные для предзаполнения.
      </Text>
      
      <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
        <OcrUploader 
          documentType="passport" 
          onOcrSuccess={handleOcrSuccess} 
          onOcrError={(err) => handleOcrError(err, 'passport')} 
          uploaderTitle="Загрузить Паспорт РФ"
        />
        <OcrUploader 
          documentType="snils" 
          onOcrSuccess={handleOcrSuccess} 
          onOcrError={(err) => handleOcrError(err, 'snils')} 
          uploaderTitle="Загрузить СНИЛС"
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