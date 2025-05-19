import React, { useState, useCallback } from 'react';
import { Box, Heading, Text, VStack, FormControl, FormLabel, CheckboxGroup, Checkbox, Divider } from '@chakra-ui/react';
import DocumentUpload from '../formInputs/DocumentUpload';
import { useDropzone } from 'react-dropzone';
import { parse, isValid, format } from 'date-fns';

export const ALL_POSSIBLE_DOCUMENT_IDS: { id: string, name: string }[] = [
    { id: "application", name: "Заявление о назначении пенсии" },
    { id: "snils", name: "СНИЛС (общий, для пенсии по старости/инвалидности)" },
    { id: "work_book", name: "Трудовая книжка (общая)" },
    { id: "mse_certificate", name: "Справка МСЭ" },
    { id: "birth_certificate_children", name: "Свидетельство о рождении ребенка (детей)"},
    { id: "military_id", name: "Военный билет"},
    { id: "marriage_certificate", name: "Свидетельство о браке/расторжении/смене имени"},
    { id: "salary_certificate_2002", name: "Справка о заработке за 60 месяцев до 01.01.2002"},
    { id: "special_work_conditions_proof", name: "Справка, уточняющая особый характер работы или условий труда"},
    { id: "residence_proof", name: "Документ, подтверждающий постоянное проживание в РФ"},
    { id: "applicant_snils", name: "СНИЛС заявителя (для пенсии по потере кормильца)" },
    { id: "death_certificate", name: "Свидетельство о смерти кормильца" },
    { id: "relationship_proof", name: "Документы, подтверждающие родственные отношения с умершим" },
    { id: "deceased_work_book", name: "Трудовая книжка умершего кормильца" },
    { id: "deceased_snils", name: "СНИЛС умершего кормильца" },
    { id: "dependency_proof", name: "Документы, подтверждающие нахождение на иждивении" },
];

interface DocumentUploadStepProps {
  setValue: (name: string, value: any, options?: { shouldValidate?: boolean, shouldDirty?: boolean }) => void;
  initialPassportFile?: File | null;
  initialSelectedDocs?: string[];
}

const DocumentUploadStep: React.FC<DocumentUploadStepProps> = ({ 
    setValue, 
    initialPassportFile = null,
    initialSelectedDocs = [] 
}) => {

  const [passportFileForCheck, setPassportFileForCheck] = useState<File | null>(initialPassportFile);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>(initialSelectedDocs);

  const handleOcrDocumentProcessed = (data: {
    extracted_text: string;
    extracted_fields: Record<string, string>;
  }) => {
    if (data.extracted_fields) {
      const { last_name, first_name, middle_name, birth_date, snils, gender, passport_series, passport_number, issue_date, issued_by, department_code, birth_place } = data.extracted_fields;
      
      if (last_name) setValue('personal_data.last_name', last_name, {shouldDirty: true});
      if (first_name) setValue('personal_data.first_name', first_name, {shouldDirty: true});
      if (middle_name) setValue('personal_data.middle_name', middle_name, {shouldDirty: true});
      
      if (birth_date) {
        const parsedDate = parse(birth_date, 'dd.MM.yyyy', new Date());
        if (isValid(parsedDate)) {
          setValue('personal_data.birth_date', format(parsedDate, 'yyyy-MM-dd'), {shouldDirty: true});
        } else {
          const parsedDateAlt = parse(birth_date, 'yyyy-MM-dd', new Date());
          if (isValid(parsedDateAlt)){
            setValue('personal_data.birth_date', format(parsedDateAlt, 'yyyy-MM-dd'), {shouldDirty: true});
          } else {
            console.warn(`OCR: Не удалось распознать формат даты рождения: ${birth_date}. Устанавливаем как есть.`);
            setValue('personal_data.birth_date', birth_date, {shouldDirty: true});
          }
        }
      }

      if (snils) setValue('personal_data.snils', snils, {shouldDirty: true});
      if (gender) setValue('personal_data.gender', gender.toLowerCase() === 'муж' ? 'male' : (gender.toLowerCase() === 'жен' ? 'female' : ''), {shouldDirty: true});
    }
  };

  const onPassportFileDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setPassportFileForCheck(file);
      setValue('passport_file_for_check', file, {shouldDirty: true});
    }
  }, [setValue]);

  const { getRootProps: getPassportRootProps, getInputProps: getPassportInputProps, isDragActive: isPassportDragActive } = useDropzone({
    onDrop: onPassportFileDrop,
    accept: {
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
  });

  const handleCheckboxChange = (selectedIds: (string | number)[]) => {
    const stringIds = selectedIds.map(String);
    setSelectedDocumentIds(stringIds);
    setValue('uploaded_document_ids_for_check', stringIds, {shouldDirty: true});
  };

  return (
    <VStack spacing={8} align="stretch">
      <Box>
        <Heading size="md" mb={2}>1. OCR документа для автозаполнения (Паспорт)</Heading>
        <Text color="gray.600" fontSize="sm">
          Загрузите скан паспорта. Данные из него (ФИО, дата рождения и др.) попробуем считать автоматически 
          для предзаполнения полей на следующих шагах. Этот файл НЕ будет отправлен для проверки комплекта.
        </Text>
        <DocumentUpload onDocumentProcessed={handleOcrDocumentProcessed} />
      </Box>

      <Divider />

      <Box>
        <Heading size="md" mb={2}>2. Файл паспорта (для проверки комплекта)</Heading>
        <Text color="gray.600" fontSize="sm">
            Этот файл паспорта будет отправлен на сервер для финальной проверки комплекта документов. 
            Пожалуйста, убедитесь, что это тот же документ, что и для OCR, или актуальный.
        </Text>
        <Box
          {...getPassportRootProps()}
          p={6}
          mt={2}
          border="2px dashed"
          borderColor={isPassportDragActive ? 'blue.400' : 'gray.200'}
          borderRadius="md"
          textAlign="center"
          cursor="pointer"
          _hover={{ borderColor: 'blue.400' }}
        >
          <input {...getPassportInputProps()} />
          {passportFileForCheck ? (
            <Text>Выбран файл: {passportFileForCheck.name}</Text>
          ) : isPassportDragActive ? (
            <Text>Отпустите файл паспорта здесь...</Text>
          ) : (
            <Text>Перетащите файл паспорта сюда или нажмите для выбора (PNG, JPG, PDF)</Text>
          )}
        </Box>
      </Box>
      
      <Divider />

      <Box>
        <Heading size="md" mb={2}>3. Другие предоставленные документы</Heading>
        <Text color="gray.600" fontSize="sm">
            Отметьте другие документы, которые вы предоставляете вместе с заявлением. 
            Паспорт отмечать не нужно, если вы загрузили его в предыдущем пункте.
        </Text>
        <FormControl mt={2}>
            <FormLabel srOnly>Другие предоставленные документы (отметьте)</FormLabel>
            <CheckboxGroup colorScheme="blue" onChange={handleCheckboxChange} value={selectedDocumentIds}>
                <VStack align="start" spacing={1} maxHeight="300px" overflowY="auto" borderWidth="1px" borderRadius="md" p={3}>
                    {ALL_POSSIBLE_DOCUMENT_IDS.map(doc => (
                        <Checkbox key={doc.id} value={doc.id}>{doc.name}</Checkbox>
                    ))}
                </VStack>
            </CheckboxGroup>
        </FormControl>
      </Box>
    </VStack>
  );
};

export default DocumentUploadStep; 