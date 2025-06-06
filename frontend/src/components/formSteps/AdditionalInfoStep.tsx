import React, { useState, useEffect } from 'react';
import { Control, Controller, FieldErrors, UseFormGetValues, UseFormSetValue, UseFormTrigger, useWatch } from 'react-hook-form';
import { Form, InputNumber, Checkbox, Divider, Typography, message as antdMessage, Row, Col, Button } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import type { 
    CaseFormDataTypeForRHF, // Глобальный тип для формы RHF
    OtherDocumentData, // Для данных из OCR
    DocumentTypeToExtract, 
    OcrResultData,
    DocumentDetail
} from '../../types';
import type { UploadFile } from 'antd/es/upload'; // Ensure UploadFile is imported

import TagInput from '../formInputs/TagInput';
import OcrUploader from '../formInputs/OcrUploader';

const { Title, Text, Paragraph } = Typography;

const BENEFIT_CONFIRMING_DOCUMENT_TYPES = [
    "Военный билет",
    "Документ, подтверждающий особые условия труда",
    "Документ, подтверждающий педагогический стаж",
    "Документ, подтверждающий медицинский стаж",
    "Документ, подтверждающий льготный стаж",
    "Свидетельство о рождении всех детей",
    "Документ об инвалидности ребенка",
    "Справка об инвалидности",
    "Справка МСЭ об установлении инвалидности",
    "Документ об иждивении",
    "Справка медико-социальной экспертизы (МСЭ)",
    "Справка МСЭ (для гос. пенсии)",
];

interface AdditionalInfoStepProps {
    control: Control<CaseFormDataTypeForRHF>;
    errors: FieldErrors<CaseFormDataTypeForRHF>;
    pensionType: string | null;
    setValue: UseFormSetValue<CaseFormDataTypeForRHF>;
    getValues: UseFormGetValues<CaseFormDataTypeForRHF>;
    trigger: UseFormTrigger<CaseFormDataTypeForRHF>;
    standardDocNames?: string[];
    requiredDocsForType?: DocumentDetail[];
}

const AdditionalInfoStep: React.FC<AdditionalInfoStepProps> = ({
    control,
    errors,
    pensionType,
    setValue,
    getValues,
    trigger,
    standardDocNames,
    requiredDocsForType
}) => {
    const watchedOtherDocs = useWatch<CaseFormDataTypeForRHF, 'other_documents_extracted_data'>({ 
        control,
        name: 'other_documents_extracted_data',
        defaultValue: [] 
    });
    const [displayedOtherDocs, setDisplayedOtherDocs] = useState<Partial<OtherDocumentData>[]>(watchedOtherDocs || []);

    // State to track if the batch of 'other' documents is currently processing
    const [isOtherDocsBatchProcessing, setIsOtherDocsBatchProcessing] = useState(false);

    useEffect(() => {
        setDisplayedOtherDocs(watchedOtherDocs || []);
    }, [watchedOtherDocs]);

    const handleOtherDocOcrSuccess = (ocrData: OcrResultData, docType: DocumentTypeToExtract, file?: UploadFile) => {
        if (docType === 'other' && ocrData) {
            const ocrResultDataAsOther = ocrData as OtherDocumentData; 
            const newExtractedBlock: Partial<OtherDocumentData> = {
                standardized_document_type: ocrResultDataAsOther.standardized_document_type,
                extracted_fields: ocrResultDataAsOther.extracted_fields,
                identified_document_type: ocrResultDataAsOther.identified_document_type, 
                multimodal_assessment: ocrResultDataAsOther.multimodal_assessment,
                text_llm_reasoning: ocrResultDataAsOther.text_llm_reasoning
            };
            
            const displayType = newExtractedBlock.standardized_document_type || newExtractedBlock.identified_document_type || (file ? file.name : "Неизвестный документ");

            const currentOtherDocsDataInForm = getValues('other_documents_extracted_data') || [];
            const updatedOtherDocsData = [...currentOtherDocsDataInForm, newExtractedBlock];
            setValue('other_documents_extracted_data', updatedOtherDocsData, { shouldDirty: true, shouldValidate: true });

            let targetField: 'benefits' | 'documents' = 'documents';
            if (newExtractedBlock.standardized_document_type && BENEFIT_CONFIRMING_DOCUMENT_TYPES.includes(newExtractedBlock.standardized_document_type)) {
                targetField = 'benefits';
            }
            
            const typeToAdd = newExtractedBlock.standardized_document_type || newExtractedBlock.identified_document_type;
            if (typeToAdd) {
                const currentTagString = getValues(targetField) || '';
                const tagsArray = currentTagString.split(',').map((v: string) => v.trim()).filter(Boolean);
                if (!tagsArray.includes(typeToAdd)) {
                    tagsArray.push(typeToAdd);
                    setValue(targetField, tagsArray.join(', '), { shouldDirty: true });
                    trigger(targetField as string); 
                }
            }
            antdMessage.success(`Данные из документа "${displayType}" сохранены и добавлены в форму.`);
        } 
    };
    
    const removeOtherDoc = (indexToRemove: number) => {
        const currentOtherDocsDataInForm = getValues('other_documents_extracted_data') || [];
        const updatedOtherDocsData = currentOtherDocsDataInForm.filter((_: Partial<OtherDocumentData>, index: number) => index !== indexToRemove);
        setValue('other_documents_extracted_data', updatedOtherDocsData, { shouldDirty: true, shouldValidate: true });

        const removedDocData = currentOtherDocsDataInForm[indexToRemove];
        if (removedDocData && removedDocData.standardized_document_type) {
            const typeToRemoveFromTags = removedDocData.standardized_document_type;
            (['benefits', 'documents'] as const).forEach(field => {
                const currentTagString = getValues(field) || '';
                let tagsArray = currentTagString.split(',').map((v: string) => v.trim()).filter(Boolean);
                if (tagsArray.includes(typeToRemoveFromTags)) {
                    tagsArray = tagsArray.filter((tag: string) => tag !== typeToRemoveFromTags);
                    setValue(field, tagsArray.join(', '), { shouldDirty: true });
                    trigger(field as string); 
                }
            });
        }
        antdMessage.info("Данные документа удалены из формы.");
    };
    
    const handleOtherDocOcrError = (message: string, docType: DocumentTypeToExtract, file?: UploadFile) => {
        antdMessage.error(`Ошибка загрузки документа ${file ? `(${file.name})` : ''} (${docType}): ${message}`);
    };

    const handleOtherDocBatchFinished = (docType: DocumentTypeToExtract, errorsInBatch: boolean) => {
        setIsOtherDocsBatchProcessing(false);
        if (errorsInBatch) {
            antdMessage.warning('При обработке некоторых дополнительных документов возникли ошибки.');
        } else {
            antdMessage.info('Все дополнительные документы были обработаны.');
        }
    };

    const handleOtherDocProcessingStart = (docType: DocumentTypeToExtract, file?: UploadFile) => {
        // If file is undefined, it means a batch is starting
        if (docType === 'other' && file === undefined) { 
            setIsOtherDocsBatchProcessing(true);
        }
        // If file is defined, it means a single file upload (which should not happen if allowMultipleFiles is true and used for batch)
        // or it could be the first file in a batch, depending on OcrUploader's onProcessingStart logic.
        // For now, we primarily use this to set batch processing state.
    };

    return (
        <div style={{ maxWidth: '700px', margin: '0 auto' }}>
            <Title level={4} style={{ marginBottom: '20px', textAlign: 'center' }}>Дополнительная информация</Title>

            {pensionType === 'retirement_standard' && (
                <Form.Item
                    label="Пенсионные баллы (ИПК)"
                    name="pension_points"
                    validateStatus={errors.pension_points ? 'error' : ''}
                    help={errors.pension_points?.message as string | undefined}
                    rules={[
                        { required: pensionType === 'retirement_standard', message: "Пенсионные баллы обязательны" },
                    ]}
                >
                    <Controller
                        name="pension_points"
                        control={control}
                        rules={{ min: {value: 0, message: "Баллы не могут быть отрицательными"}}} 
                        render={({ field }) => (
                            <InputNumber 
                                {...field} 
                                value={typeof field.value === 'number' ? field.value : undefined}
                                min={0} 
                                precision={2} 
                                step={0.1} 
                                style={{ width: '100%' }} 
                            />
                        )}
                    />
                </Form.Item>
            )}

            <Divider style={{ margin: '24px 0' }}/>
            
            <Title level={5} style={{ marginTop: '20px', marginBottom: '8px' }}>Льготы и Документы</Title>
            <Paragraph type="secondary" style={{ marginBottom: '16px' }}>
                Вы можете ввести названия льгот и документов вручную или загрузить скан документа для автоматического добавления его типа и извлеченных данных.
            </Paragraph>

            <Form.Item label="Загрузить скан доп. документа / льготы (OCR)">
                <OcrUploader
                    documentType="other"
                    onOcrSuccess={handleOtherDocOcrSuccess}
                    onOcrError={handleOtherDocOcrError}
                    uploaderTitle="Перетащите или выберите файл(ы) для доп. документов"
                    allowMultipleFiles={true} // Разрешаем несколько файлов
                    onBatchFinished={handleOtherDocBatchFinished} // Обрабатываем завершение пачки
                    onProcessingStart={handleOtherDocProcessingStart} // Обрабатываем начало обработки (пачки)
                />
            </Form.Item>

            {displayedOtherDocs.length > 0 && (
                <div style={{ marginTop: '20px' }}>
                    <Text strong>Загруженные и распознанные доп. документы:</Text>
                    {displayedOtherDocs.map((doc, index) => (
                        <div key={index} style={{ padding: '8px', border: '1px solid #e8e8e8', borderRadius: '2px', marginTop: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <Text >{doc.standardized_document_type || doc.identified_document_type || `Документ ${index + 1}`}</Text>
                                {doc.extracted_fields && Object.keys(doc.extracted_fields).length > 0 && (
                                    <Text type="secondary" style={{ fontSize: '0.85em', marginLeft: '8px' }}>
                                        (извлечено полей: {Object.keys(doc.extracted_fields).length})
                                    </Text>
                                )}
                            </div>
                            <Button
                                type="text"
                                danger
                                icon={<DeleteOutlined />}
                                onClick={() => removeOtherDoc(index)}
                                size="small"
                            />
                        </div>
                    ))}
                </div>
            )}
            <Divider style={{ margin: '24px 0' }}/>

            {pensionType !== 'disability_social' && (
                <Form.Item
                    label="Льготы (введите или будут добавлены автоматически после OCR)"
                    name="benefits"
                    validateStatus={errors.benefits ? 'error' : ''}
                    help={errors.benefits?.message as string | undefined}
                >
                    <Controller
                        name="benefits"
                        control={control}
                        render={({ field }) => (
                            <TagInput 
                                fieldOnChange={field.onChange} 
                                value={field.value}
                                placeholder="Добавить льготу и нажать Enter"
                            />
                        )}
                    />
                </Form.Item>
            )}

            <Form.Item
                label="Представленные стандартные документы (введите или будут добавлены автоматически после OCR)"
                name="documents"
                validateStatus={errors.documents ? 'error' : ''}
                help={errors.documents?.message as string | undefined}
            >
                <Controller
                    name="documents"
                    control={control}
                    render={({ field }) => (
                        <TagInput 
                            fieldOnChange={field.onChange} 
                            value={field.value}
                            placeholder="Добавить документ и нажать Enter"
                        />
                    )}
                />
            </Form.Item>

            <Form.Item name="has_incorrect_document" valuePropName="checked">
                 <Controller
                    name="has_incorrect_document"
                    control={control}
                    defaultValue={false} 
                    render={({ field: {onChange, value, ref} }) => (
                        <Checkbox 
                            onChange={onChange} 
                            checked={!!value}
                            ref={ref}
                        >
                            Есть некорректно оформленные документы
                        </Checkbox>
                    )}
                />
            </Form.Item>
        </div>
    );
};

export default AdditionalInfoStep;
