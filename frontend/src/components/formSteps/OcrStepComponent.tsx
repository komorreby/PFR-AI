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
import { UseFormSetValue, UseFormTrigger, Control } from 'react-hook-form';
import OcrUploader from '../formInputs/OcrUploader';
import type { CaseFormDataTypeForRHF, OcrExtractionResponse, OcrDocumentType, OcrPassportData, OcrSnilsData } from '../../types';
import { formatDateForInput } from '../../utils'; // Для форматирования дат
import { isValid, parse as parseDate } from 'date-fns'; // Для парсинга дат

interface OcrStepComponentProps {
  setValue: UseFormSetValue<CaseFormDataTypeForRHF>;
  trigger: UseFormTrigger<CaseFormDataTypeForRHF>;
  control: Control<CaseFormDataTypeForRHF>; // Пока не используется, но может понадобиться
  // Можно добавить проп для управления видимостью кнопки "Пропустить", если она нужна
  // showSkipButton?: boolean;
  // onSkip?: () => void;
}

const OcrStepComponent: React.FC<OcrStepComponentProps> = ({
  setValue,
  trigger,
  // control, // Пока не используется
  // onStepComplete, // Пока не используется
}) => {
  const toast = useToast();

  const handleOcrSuccess = async (ocrData: OcrExtractionResponse, docType: OcrDocumentType) => {
    let fieldsUpdated: (keyof CaseFormDataTypeForRHF['personal_data'])[] = [];
    let mainMessage = 'Данные не распознаны или документ не поддерживается для автозаполнения.';
    let toastStatus: "success" | "info" | "warning" = 'info';

    if (ocrData.documentType === 'passport' && ocrData.data) {
      const data = ocrData.data as OcrPassportData;
      mainMessage = 'Паспортные данные частично распознаны!';
      if (data.last_name) { setValue('personal_data.last_name', data.last_name, { shouldDirty: true }); fieldsUpdated.push('last_name'); }
      if (data.first_name) { setValue('personal_data.first_name', data.first_name, { shouldDirty: true }); fieldsUpdated.push('first_name'); }
      if (data.middle_name) { setValue('personal_data.middle_name', data.middle_name, { shouldDirty: true }); fieldsUpdated.push('middle_name'); }
      if (data.birth_date) {
        // Пытаемся распарсить дату из DD.MM.YYYY или YYYY-MM-DD
        let parsedDate = parseDate(data.birth_date, 'dd.MM.yyyy', new Date());
        if (!isValid(parsedDate)) {
          parsedDate = parseDate(data.birth_date, 'yyyy-MM-dd', new Date());
        }
        if (isValid(parsedDate)) {
          setValue('personal_data.birth_date', formatDateForInput(parsedDate), { shouldDirty: true });
          fieldsUpdated.push('birth_date');
        } else {
          console.warn(`OCR: Не удалось распознать формат даты рождения из паспорта: ${data.birth_date}`);
        }
      }
      if (data.sex) {
        const gender = data.sex.toLowerCase().startsWith('муж') ? 'male' : (data.sex.toLowerCase().startsWith('жен') ? 'female' : '');
        if (gender) { setValue('personal_data.gender', gender, { shouldDirty: true }); fieldsUpdated.push('gender'); }
      }
      // TODO: Добавить маппинг для других полей паспорта, если они есть в PersonalData (passport_series, number, issue_date etc.)
      // например, если есть snils в паспорте, а не отдельным документом
      // if (data.snils) { setValue('personal_data.snils', data.snils, { shouldDirty: true }); fieldsUpdated.push('snils'); }
    } else if (ocrData.documentType === 'snils' && ocrData.data) {
      const data = ocrData.data as OcrSnilsData;
      mainMessage = 'Номер СНИЛС распознан!';
      if (data.snils_number) { setValue('personal_data.snils', data.snils_number, { shouldDirty: true }); fieldsUpdated.push('snils'); }
    } else if (ocrData.documentType === 'other' && ocrData.data) {
      // Логика для других типов документов, если она нужна для предзаполнения
      mainMessage = `Документ типа '${ocrData.data.identified_document_type || 'Другой'}' обработан. Автозаполнение для этого типа не настроено.`;
      console.log('OCR Other Document Data:', ocrData.data);
      toastStatus = 'info';
    } else if (ocrData.documentType === 'error') {
      mainMessage = ocrData.message || 'Произошла ошибка при обработке документа.';
      console.error('OCR Error (structured):', ocrData.errorDetails);
      toastStatus = 'warning';
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
      // Запускаем валидацию для обновленных полей
      // Важно: trigger может принимать массив строк, соответствующих именам полей в react-hook-form
      const fieldsToTrigger = fieldsUpdated.map(f => `personal_data.${f}` as const);
      if (fieldsToTrigger.length > 0) {
        trigger(fieldsToTrigger);
      }
    } else {
      toast({
        title: ocrData.documentType === 'error' ? 'Ошибка OCR' : 'Результат OCR',
        description: mainMessage,
        status: toastStatus, // уже установлено в 'info' или 'warning'
        duration: 5000,
        isClosable: true,
      });
    }
    
    // Если есть колбэк для завершения шага (например, для автоматического перехода)
    // onStepComplete?.();
  };

  const handleOcrError = (message: string, docType: OcrDocumentType) => {
    toast({
      title: `Критическая ошибка OCR (${docType})`,
      description: message,
      status: 'error',
      duration: 7000,
      isClosable: true,
    });
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
          onOcrError={handleOcrError} 
          uploaderTitle="Загрузить Паспорт РФ"
        />
        <OcrUploader 
          documentType="snils" 
          onOcrSuccess={handleOcrSuccess} 
          onOcrError={handleOcrError} 
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