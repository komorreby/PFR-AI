import React, { useState, useEffect, useCallback } from 'react';
import { Typography, message as antdMessage, Space, Divider, Descriptions, Alert } from 'antd';
import { Control, UseFormSetValue, FieldErrors, UseFormTrigger } from 'react-hook-form';
import OcrUploader from '../formInputs/OcrUploader';
import { 
    OcrResultData, 
    PassportData, 
    SnilsData, 
    WorkBookData, 
    DocumentTypeToExtract,
    CaseFormDataTypeForRHF
} from '../../types';
import type { UploadFile } from 'antd/es/upload';

const { Title, Paragraph } = Typography;

type DocumentProcessStatus = {
    attempted: boolean; 
    processing: boolean;
    error: boolean;
    success: boolean;
};

const initialDocStatus: DocumentProcessStatus = {
    attempted: false,
    processing: false,
    error: false,
    success: false,
};

interface DocumentUploadStepProps {
    setValue: UseFormSetValue<CaseFormDataTypeForRHF>;
    control: Control<CaseFormDataTypeForRHF>; 
    errors: FieldErrors<CaseFormDataTypeForRHF>; 
    trigger: UseFormTrigger<CaseFormDataTypeForRHF>;
    onOcrStepNextButtonDisabledStateChange?: (isDisabled: boolean) => void;
}

const DocumentUploadStep: React.FC<DocumentUploadStepProps> = ({ 
    setValue, 
    control, 
    trigger, 
    onOcrStepNextButtonDisabledStateChange 
}) => {
    const [passportData, setPassportData] = useState<PassportData | null>(null);
    const [snilsData, setSnilsData] = useState<SnilsData | null>(null);
    const [ocrGlobalError, setOcrGlobalError] = useState<string | null>(null);

    const [passportStatus, setPassportStatus] = useState<DocumentProcessStatus>(initialDocStatus);
    const [snilsStatus, setSnilsStatus] = useState<DocumentProcessStatus>(initialDocStatus);
    const [workBookStatus, setWorkBookStatus] = useState<DocumentProcessStatus>(initialDocStatus);

    useEffect(() => {
        if (onOcrStepNextButtonDisabledStateChange) {
            let shouldBeDisabled = false;
            const statuses = [passportStatus, snilsStatus, workBookStatus];
            for (const status of statuses) {
                if (status.attempted && (status.processing || status.error)) {
                    shouldBeDisabled = true;
                    break;
                }
            }
            onOcrStepNextButtonDisabledStateChange(shouldBeDisabled);
        }
    }, [passportStatus, snilsStatus, workBookStatus, onOcrStepNextButtonDisabledStateChange]);

    const handleProcessingStart = useCallback((docType: DocumentTypeToExtract, _file?: UploadFile) => {
        setOcrGlobalError(null);
        if (docType === 'passport') {
            setPassportStatus({ attempted: true, processing: true, error: false, success: false });
        } else if (docType === 'snils') {
            setSnilsStatus({ attempted: true, processing: true, error: false, success: false });
        } else if (docType === 'work_book') {
            setWorkBookStatus({ attempted: true, processing: true, error: false, success: false });
        }
    }, []);

    const handleOcrSuccess = (data: OcrResultData, docType: DocumentTypeToExtract, file?: UploadFile) => {
        setOcrGlobalError(null);
        let updateMessage = "";
        let fieldsSetForTrigger = false;

        const capitalizeField = (text: string | null | undefined): string | undefined => {
            if (!text) return undefined;
            return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
        };
        
        const docNameToAdd = 
            docType === 'passport' ? "Паспорт РФ" :
            docType === 'snils' ? "СНИЛС" :
            docType === 'work_book' ? "Трудовая книжка" :
            docType.toString();

        if (docType === 'passport' && data) {
            const passData = data as PassportData;
            setPassportData(passData);
            setPassportStatus({ attempted: true, processing: false, error: false, success: true });
            
            setValue('personal_data.first_name', capitalizeField(passData.first_name), { shouldValidate: true, shouldDirty: true });
            setValue('personal_data.last_name', capitalizeField(passData.last_name), { shouldValidate: true, shouldDirty: true });
            setValue('personal_data.middle_name', capitalizeField(passData.middle_name), { shouldValidate: true, shouldDirty: true });
            setValue('personal_data.birth_date', passData.birth_date || undefined, { shouldValidate: true, shouldDirty: true });
            setValue('personal_data.birth_place', passData.birth_place || undefined, { shouldValidate: true, shouldDirty: true });
            
            const genderFromOcr = passData.sex;
            let mappedGender: 'male' | 'female' | undefined = undefined;
            if (genderFromOcr) {
                if (genderFromOcr.toLowerCase().startsWith('муж')) mappedGender = 'male';
                else if (genderFromOcr.toLowerCase().startsWith('жен')) mappedGender = 'female';
            }
            setValue('personal_data.gender', mappedGender, { shouldValidate: true, shouldDirty: true });

            setValue('personal_data.passport_series', passData.passport_series || undefined, { shouldValidate: true, shouldDirty: true });
            setValue('personal_data.passport_number', passData.passport_number || undefined, { shouldValidate: true, shouldDirty: true });
            setValue('personal_data.passport_issue_date', passData.issue_date || undefined, { shouldValidate: true, shouldDirty: true });
            setValue('personal_data.issuing_authority', passData.issuing_authority || undefined, { shouldValidate: true, shouldDirty: true });
            setValue('personal_data.department_code', passData.department_code || undefined, { shouldValidate: true, shouldDirty: true });
            
            updateMessage = `Данные из ${file?.name || 'паспорта'} обновлены.`;
            fieldsSetForTrigger = true;
        } else if (docType === 'snils' && data) {
            const snlsData = data as SnilsData;
            setSnilsData(snlsData);
            setSnilsStatus({ attempted: true, processing: false, error: false, success: true });
            setValue('personal_data.snils', snlsData.snils_number || undefined, { shouldValidate: true, shouldDirty: true });
            updateMessage = `Данные из ${file?.name || 'СНИЛС'} обновлены.`;
            fieldsSetForTrigger = true;
        } else if (docType === 'work_book' && data) {
            const wbData = data as WorkBookData;
            
            // Получаем текущие данные из формы
            const currentRecords = control._getWatch('work_experience.records') || [];
            const currentEvents = control._getWatch('work_experience.raw_events') || [];

            // Добавляем новые записи о периодах, инициализируя special_conditions
            if (wbData.records && wbData.records.length > 0) {
                const newMappedRecords = wbData.records.map(ocrRecord => ({
                    ...ocrRecord,
                    special_conditions: false, // OCR не определяет это, пользователь может указать позже
                }));
                setValue('work_experience.records', [...currentRecords, ...newMappedRecords], { shouldValidate: true, shouldDirty: true });
            }

            // Добавляем новые сырые события
            if (wbData.raw_events && wbData.raw_events.length > 0) {
                setValue('work_experience.raw_events', [...currentEvents, ...wbData.raw_events], { shouldDirty: true });
            }
            
            // Обновляем общий стаж. Это значение будет перезаписано каждым новым файлом,
            // что является известным ограничением. Пользователь сможет скорректировать его на следующем шаге.
            if (wbData.calculated_total_years !== null && wbData.calculated_total_years !== undefined) {
                setValue('work_experience.total_years', wbData.calculated_total_years, { shouldValidate: true, shouldDirty: true });
            }
            trigger('work_experience.records');
            trigger('work_experience.total_years');

            updateMessage = `Данные из файла трудовой книжки ${file?.name || ''.trim()} добавлены в форму.`;
        }

        if (fieldsSetForTrigger) { 
            trigger('personal_data.first_name');
            trigger('personal_data.last_name');
            trigger('personal_data.birth_date');
            trigger('personal_data.snils');
        }
        
        const currentDocsString = control._getWatch('documents') || '';
        const currentDocuments = currentDocsString.split(',').map((s: string) => s.trim()).filter(Boolean);
        
        if (!currentDocuments.includes(docNameToAdd)) {
            currentDocuments.push(docNameToAdd);
            setValue('documents', currentDocuments.join(', '), { shouldDirty: true });
            trigger('documents'); 
        }
        antdMessage.success(updateMessage || "Документ обработан.");
    };

    const handleOcrError = (message: string, docType: DocumentTypeToExtract, file?: UploadFile) => {
        const errorMsg = `Ошибка OCR (${docType}${file ? ", "+file.name : ''}): ${message}`;
        setOcrGlobalError(errorMsg);
        antdMessage.error(errorMsg);
        if (docType === 'passport') {
            setPassportData(null);
            setPassportStatus({ attempted: true, processing: false, error: true, success: false });
        } else if (docType === 'snils') {
            setSnilsData(null);
            setSnilsStatus({ attempted: true, processing: false, error: true, success: false });
        } else if (docType === 'work_book') {
        }
    };
    
    const handleWorkBookBatchFinished = (docType: DocumentTypeToExtract, errorsInBatch: boolean) => {
        if (docType === 'work_book') {
            setWorkBookStatus({
                attempted: true,
                processing: false,
                error: errorsInBatch,
                success: !errorsInBatch, // Consider batch successful if no errors occurred
            });
            if (errorsInBatch) {
                antdMessage.warning('При обработке файлов трудовой книжки возникли ошибки. Проверьте данные.');
            } else {
                antdMessage.info('Все файлы трудовой книжки обработаны.');
            }
        }
    };

    const renderPassportData = (data: PassportData) => (
        <Descriptions bordered column={1} size="small" title="Данные паспорта (предпросмотр)">
            <Descriptions.Item label="ФИО">{`${data.last_name || ''} ${data.first_name || ''} ${data.middle_name || ''}`.trim()}</Descriptions.Item>
            <Descriptions.Item label="Дата рождения">{data.birth_date}</Descriptions.Item>
            <Descriptions.Item label="Пол">{data.sex}</Descriptions.Item>
            <Descriptions.Item label="Серия">{data.passport_series}</Descriptions.Item>
            <Descriptions.Item label="Номер">{data.passport_number}</Descriptions.Item>
            {data.issue_date && <Descriptions.Item label="Дата выдачи">{data.issue_date}</Descriptions.Item>}
            {data.issuing_authority && <Descriptions.Item label="Кем выдан">{data.issuing_authority}</Descriptions.Item>}
            {data.department_code && <Descriptions.Item label="Код подразделения">{data.department_code}</Descriptions.Item>}
            {data.birth_place && <Descriptions.Item label="Место рождения">{data.birth_place}</Descriptions.Item>}
        </Descriptions>
    );

    const renderSnilsData = (data: SnilsData) => (
        <Descriptions bordered column={1} size="small" title="Данные СНИЛС (предпросмотр)">
            <Descriptions.Item label="Номер СНИЛС">{data.snils_number}</Descriptions.Item>
        </Descriptions>
    );


    return (
        <div style={{ maxWidth: '700px', margin: '0 auto' }}>
            <Title level={4} style={{ marginBottom: '16px', textAlign: 'center' }}>Загрузка основных документов</Title>
            <Paragraph type="secondary" style={{ textAlign: 'center', marginBottom: '24px' }}>
                Загрузите сканы паспорта, СНИЛС и трудовой книжки. Данные будут автоматически извлечены. 
                Кнопка "Далее" станет активна, когда все успешно загруженные документы будут обработаны или если вы не загружали документы.
            </Paragraph>

            {ocrGlobalError && <Alert message={ocrGlobalError} type="error" showIcon style={{ marginBottom: '16px' }} />}

            <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <OcrUploader
                    documentType="passport"
                    onOcrSuccess={handleOcrSuccess}
                    onOcrError={handleOcrError}
                    onProcessingStart={handleProcessingStart}
                    uploaderTitle="Загрузить скан паспорта (разворот с фото)"
                    allowMultipleFiles={false} // Паспорт - один файл
                />
                {passportStatus.success && passportData && renderPassportData(passportData)}
                {passportStatus.error && <Alert message="Ошибка обработки паспорта. Попробуйте загрузить другой файл." type="warning" showIcon />}

                <Divider />

                <OcrUploader
                    documentType="snils"
                    onOcrSuccess={handleOcrSuccess}
                    onOcrError={handleOcrError}
                    onProcessingStart={handleProcessingStart}
                    uploaderTitle="Загрузить скан СНИЛС"
                    allowMultipleFiles={false} // СНИЛС - один файл
                />
                {snilsStatus.success && snilsData && renderSnilsData(snilsData)}
                {snilsStatus.error && <Alert message="Ошибка обработки СНИЛС. Попробуйте загрузить другой файл." type="warning" showIcon />}

                <Divider />

                <OcrUploader
                    documentType="work_book"
                    onOcrSuccess={handleOcrSuccess} // individual file success
                    onOcrError={handleOcrError}     // individual file error
                    onProcessingStart={handleProcessingStart} // batch processing start
                    onBatchFinished={handleWorkBookBatchFinished} // batch finished
                    uploaderTitle="Загрузить сканы трудовой книжки (все страницы)"
                    allowMultipleFiles={true} // Трудовая может быть из нескольких файлов
                />
                {/* Предпросмотр для трудовой теперь не отображается здесь, т.к. данные агрегируются в форму */}
                {workBookStatus.attempted && workBookStatus.error && 
                    <Alert message="При обработке файлов трудовой книжки возникли ошибки. Проверьте данные на следующем шаге." type="warning" showIcon />
                }
                 {workBookStatus.attempted && !workBookStatus.error && workBookStatus.success && 
                    <Alert message="Все файлы трудовой книжки успешно обработаны и данные добавлены в форму." type="success" showIcon />
                }
            </Space>
        </div>
    );
};

export default DocumentUploadStep; 