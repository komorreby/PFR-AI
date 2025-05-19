import React, { useState } from 'react';
import { FieldErrors, UseFormRegister, Control, Controller, FieldPath, UseFormGetValues, UseFormSetValue, UseFormTrigger } from 'react-hook-form';
import {
    VStack,
    Heading,
    FormControl,
    FormLabel,
    NumberInput,
    NumberInputField,
    NumberInputStepper,
    NumberIncrementStepper,
    NumberDecrementStepper,
    Checkbox,
    FormErrorMessage,
    Divider,
    Text,
    useToast,
    SimpleGrid,
    Box,
    IconButton
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon } from '@chakra-ui/icons';
import { CaseFormDataTypeForRHF, OcrExtractionResponse, OcrOtherDocumentData, OtherDocumentExtractedBlock } from '../../types';
import TagInput from '../formInputs/TagInput';
import OcrUploader from '../formInputs/OcrUploader';

const BENEFIT_CONFIRMING_DOCUMENT_TYPES = [
    "Военный билет",
    "Документ, подтверждающий особые условия труда",
    "Документ, подтверждающий педагогический стаж",
    "Документ, подтверждающий медицинский стаж",
    "Документ, подтверждающий льготный стаж",
    "Свидетельство о рождении всех детей",
    "Документ об инвалидности ребенка",
    "Справка об инвалидности",
    "Документ об иждивении",
];

type AdditionalInfoFieldName = FieldPath<Pick<CaseFormDataTypeForRHF, 'pension_points' | 'benefits' | 'documents' | 'dependents' | 'other_documents_extracted_data'>>;

interface AdditionalInfoStepProps {
    register: UseFormRegister<CaseFormDataTypeForRHF>;
    control: Control<CaseFormDataTypeForRHF>;
    errors: FieldErrors<CaseFormDataTypeForRHF>;
    getErrorMessage: (name: AdditionalInfoFieldName) => string | undefined;
    pensionType: string | null;
    setValue: UseFormSetValue<CaseFormDataTypeForRHF>;
    getValues: UseFormGetValues<CaseFormDataTypeForRHF>;
    trigger: UseFormTrigger<CaseFormDataTypeForRHF>;
}

const AdditionalInfoStep: React.FC<AdditionalInfoStepProps> = ({
    register,
    control,
    errors,
    getErrorMessage,
    pensionType,
    setValue,
    getValues,
    trigger
}) => {
    const toast = useToast();
    const [displayedOtherDocs, setDisplayedOtherDocs] = useState<OtherDocumentExtractedBlock[]>(
        () => getValues('other_documents_extracted_data') || []
    );

    const handleOtherDocOcrSuccess = (ocrData: OcrExtractionResponse) => {
        if (ocrData.documentType === 'other' && ocrData.data) {
            const ocrResultData = ocrData.data as OcrOtherDocumentData; // Raw OCR data
            const newExtractedBlock: OtherDocumentExtractedBlock = {
                standardized_document_type: ocrResultData.standardized_document_type,
                extracted_fields: ocrResultData.extracted_fields,
            };
            
            const displayType = newExtractedBlock.standardized_document_type || ocrResultData.identified_document_type || "Неизвестный документ";

            const currentOtherDocsData = getValues('other_documents_extracted_data') || [];
            const updatedOtherDocsData = [...currentOtherDocsData, newExtractedBlock];
            setValue('other_documents_extracted_data', updatedOtherDocsData, { shouldDirty: true });
            setDisplayedOtherDocs(updatedOtherDocsData);

            let targetField: 'benefits' | 'documents' = 'documents';
            if (newExtractedBlock.standardized_document_type && BENEFIT_CONFIRMING_DOCUMENT_TYPES.includes(newExtractedBlock.standardized_document_type)) {
                targetField = 'benefits';
            }
            
            const typeToAdd = newExtractedBlock.standardized_document_type || ocrResultData.identified_document_type;
            if (typeToAdd) {
                const currentTagString = getValues(targetField) || '';
                let tagsArray = currentTagString.split(',').map(v => v.trim()).filter(Boolean);
                if (!tagsArray.includes(typeToAdd)) {
                    tagsArray.push(typeToAdd);
                    setValue(targetField, tagsArray.join(', '), { shouldDirty: true });
                    trigger(targetField);
                }
            }

            toast({
                title: "Дополнительный документ обработан",
                description: `Данные из документа "${displayType}" сохранены. Тип добавлен в соответствующее поле.`,
                status: "success",
                duration: 4000,
                isClosable: true,
            });

        } else if (ocrData.documentType === 'error') {
            toast({
                title: "Ошибка OCR",
                description: ocrData.message || "Не удалось обработать документ.",
                status: "error",
                duration: 5000,
                isClosable: true,
            });
        }
    };
    
    const removeOtherDoc = (indexToRemove: number) => {
        const currentOtherDocsData = getValues('other_documents_extracted_data') || [];
        const removedDoc = currentOtherDocsData[indexToRemove];
        const updatedOtherDocsData = currentOtherDocsData.filter((_, index) => index !== indexToRemove);
        setValue('other_documents_extracted_data', updatedOtherDocsData, { shouldDirty: true });
        setDisplayedOtherDocs(updatedOtherDocsData);

        if (removedDoc) {
            const typeToRemoveFromTags = removedDoc.standardized_document_type; // Only use standardized_document_type
            if (typeToRemoveFromTags) {
                (['benefits', 'documents'] as const).forEach(field => {
                    const currentTagString = getValues(field) || '';
                    let tagsArray = currentTagString.split(',').map(v => v.trim()).filter(Boolean);
                    if (tagsArray.includes(typeToRemoveFromTags)) {
                        tagsArray = tagsArray.filter(tag => tag !== typeToRemoveFromTags);
                        setValue(field, tagsArray.join(', '), { shouldDirty: true });
                        trigger(field);
                    }
                });
            }
        }

        toast({
            title: "Данные документа удалены",
            status: "info",
            duration: 3000,
            isClosable: true,
        });
    };
    
    const handleOtherDocOcrError = (message: string) => {
        toast({
            title: "Ошибка загрузки документа",
            description: message,
            status: "error",
            duration: 5000,
            isClosable: true,
        });
    };

    return (
        <VStack spacing={6} align="stretch">
            <Heading size="md" mb={2}>Дополнительная информация</Heading>

            <FormControl isInvalid={!!getErrorMessage('dependents') || !!errors.dependents}>
                <FormLabel htmlFor="dependents">Количество иждивенцев</FormLabel>
                <Controller
                    name="dependents"
                    control={control}
                    defaultValue={0}
                    rules={{ min: { value: 0, message: "Должно быть не меньше 0" } }}
                    render={({ field: { onChange, onBlur, value, ref } }) => (
                        <NumberInput id="dependents" min={0} value={value ?? ''}
                            onChange={(_valueAsString, valueAsNumber) => onChange(isNaN(valueAsNumber) ? 0 : valueAsNumber)}
                            onBlur={onBlur} bg="cardBackground">
                            <NumberInputField ref={ref} />
                            <NumberInputStepper><NumberIncrementStepper /><NumberDecrementStepper /></NumberInputStepper>
                        </NumberInput>
                    )}
                />
                <FormErrorMessage>{getErrorMessage('dependents') || errors.dependents?.message}</FormErrorMessage>
            </FormControl>

            {pensionType === 'retirement_standard' && (
                <FormControl isInvalid={!!getErrorMessage('pension_points') || !!errors.pension_points}>
                    <FormLabel htmlFor="pension_points">Пенсионные баллы (ИПК)</FormLabel>
                    <Controller
                        name="pension_points"
                        control={control}
                        rules={{
                            required: pensionType === 'retirement_standard' ? "Пенсионные баллы обязательны" : false,
                            min: { value: 0, message: "Баллы не могут быть отрицательными" }
                        }}
                        render={({ field }) => (
                            <NumberInput id="pension_points" min={0} precision={2} step={0.1}
                                value={field.value ?? ''}
                                onChange={(_valueAsString, valueAsNumber) => field.onChange(isNaN(valueAsNumber) ? undefined : valueAsNumber)}
                                onBlur={field.onBlur}>
                                <NumberInputField ref={field.ref} />
                                <NumberInputStepper><NumberIncrementStepper /><NumberDecrementStepper /></NumberInputStepper>
                            </NumberInput>
                        )}
                    />
                    <FormErrorMessage>{getErrorMessage('pension_points') || errors.pension_points?.message}</FormErrorMessage>
                </FormControl>
            )}

            <Divider my={2}/>
            
            <Heading size="sm" mt={2} mb={1}>Льготы и Документы</Heading>
            <Text fontSize="xs" color="gray.500" mb={3}>
                Вы можете ввести названия льгот и документов вручную или загрузить скан документа для автоматического добавления его типа и извлеченных данных.
            </Text>

            <SimpleGrid columns={1} spacing={4} mb={4}>
                 <OcrUploader
                    documentType="other"
                    onOcrSuccess={handleOtherDocOcrSuccess}
                    onOcrError={handleOtherDocOcrError}
                    uploaderTitle="Загрузить скан доп. документа / льготы (OCR)"
                />
            </SimpleGrid>

            {displayedOtherDocs.length > 0 && (
                <Box mt={4}>
                    <Heading size="xs" mb={2}>Загруженные дополнительные документы:</Heading>
                    <VStack spacing={2} align="stretch">
                        {displayedOtherDocs.map((doc, index) => (
                            <Box key={index} p={2} borderWidth="1px" borderRadius="md" display="flex" justifyContent="space-between" alignItems="center">
                                <Text fontSize="sm" isTruncated>
                                    {doc.standardized_document_type || `Документ ${index + 1}`}
                                    {doc.extracted_fields && Object.keys(doc.extracted_fields).length > 0 && (
                                        <Text as="span" fontSize="xs" color="gray.500" ml={2}>
                                            (извлечено полей: {Object.keys(doc.extracted_fields).length})
                                        </Text>
                                    )}
                                </Text>
                                <IconButton
                                    aria-label="Удалить данные документа"
                                    icon={<DeleteIcon />}
                                    size="xs"
                                    variant="ghost"
                                    colorScheme="red"
                                    onClick={() => removeOtherDoc(index)}
                                />
                            </Box>
                        ))}
                    </VStack>
                </Box>
            )}
            <Divider my={2}/>

            {pensionType !== 'disability_social' && (
                <FormControl isInvalid={!!getErrorMessage('benefits') || !!errors.benefits}>
                    <FormLabel htmlFor="benefits">Льготы (введите или отметьте авто-добавленные)</FormLabel>
                    <Controller
                        name="benefits"
                        control={control}
                        render={({ field }) => (
                            <TagInput id={field.name} value={field.value} fieldOnChange={field.onChange}
                                placeholder="Добавьте льготу и нажмите Enter" />
                        )}
                    />
                    <FormErrorMessage>{getErrorMessage('benefits') || errors.benefits?.message}</FormErrorMessage>
                </FormControl>
            )}

            <FormControl isInvalid={!!getErrorMessage('documents') || !!errors.documents}>
                <FormLabel htmlFor="documents">Представленные документы (введите или отметьте авто-добавленные)</FormLabel>
                <Controller
                    name="documents"
                    control={control}
                    render={({ field }) => (
                        <TagInput id={field.name} value={field.value} fieldOnChange={field.onChange}
                            placeholder="Добавьте документ и нажмите Enter" />
                    )}
                />
                <FormErrorMessage>{getErrorMessage('documents') || errors.documents?.message}</FormErrorMessage>
            </FormControl>

            <FormControl mt={3}>
                <Checkbox id="has_incorrect_document" {...register("has_incorrect_document")}>
                    Есть некорректно оформленные документы
                </Checkbox>
            </FormControl>
        </VStack>
    );
};

export default AdditionalInfoStep;
