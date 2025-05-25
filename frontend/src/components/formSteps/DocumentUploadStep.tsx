import React, { useState, useEffect, useCallback } from 'react';
import { Typography, Button, List, message as antdMessage, Space, Divider, Descriptions, Alert } from 'antd';
import { Control, UseFormSetValue, FieldErrors, UseFormTrigger } from 'react-hook-form';
import OcrUploader from '../formInputs/OcrUploader';
import { 
    OcrResultData, 
    PassportData, 
    SnilsData, 
    WorkBookData, 
    DocumentTypeToExtract,
    WorkBookRecordEntry,
    CaseFormDataTypeForRHF
} from '../../types';

const { Title, Text, Paragraph } = Typography;

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
    const [workBookData, setWorkBookData] = useState<WorkBookData | null>(null);
    const [ocrGlobalError, setOcrGlobalError] = useState<string | null>(null);

    const [passportStatus, setPassportStatus] = useState<DocumentProcessStatus>(initialDocStatus);
    const [snilsStatus, setSnilsStatus] = useState<DocumentProcessStatus>(initialDocStatus);
    const [workBookStatus, setWorkBookStatus] = useState<DocumentProcessStatus>(initialDocStatus);

    useEffect(() => {
        if (onOcrStepNextButtonDisabledStateChange) {
            const statuses = [passportStatus, snilsStatus, workBookStatus];
            let shouldBeDisabled = false;

            for (const status of statuses) {
                if (status.attempted && (status.processing || status.error)) {
                    shouldBeDisabled = true;
                    break;
                }
            }
            onOcrStepNextButtonDisabledStateChange(shouldBeDisabled);
        }
    }, [passportStatus, snilsStatus, workBookStatus, onOcrStepNextButtonDisabledStateChange]);

    const handleProcessingStart = useCallback((docType: DocumentTypeToExtract) => {
        setOcrGlobalError(null);
        if (docType === 'passport') {
            setPassportStatus({ attempted: true, processing: true, error: false, success: false });
        } else if (docType === 'snils') {
            setSnilsStatus({ attempted: true, processing: true, error: false, success: false });
        } else if (docType === 'work_book') {
            setWorkBookStatus({ attempted: true, processing: true, error: false, success: false });
        }
    }, []);

    const handleOcrSuccess = (data: OcrResultData, docType: DocumentTypeToExtract) => {
        setOcrGlobalError(null);
        let updateMessage = "";
        let fieldsSet = false;

        const capitalizeField = (text: string | null | undefined): string | undefined => {
            if (!text) return undefined;
            return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
        };

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
            
            updateMessage = "Данные паспорта обновлены.";
            fieldsSet = true;
        } else if (docType === 'snils' && data) {
            const snlsData = data as SnilsData;
            setSnilsData(snlsData);
            setSnilsStatus({ attempted: true, processing: false, error: false, success: true });
            setValue('personal_data.snils', snlsData.snils_number || undefined, { shouldValidate: true, shouldDirty: true });
            updateMessage = "Номер СНИЛС обновлен.";
            fieldsSet = true;
        } else if (docType === 'work_book' && data) {
            const wbData = data as WorkBookData;
            setWorkBookData(wbData);
            setWorkBookStatus({ attempted: true, processing: false, error: false, success: true });
            
            if (wbData.records && wbData.records.length > 0) {
                const mappedRecords = wbData.records.map(ocrRecord => ({
                    organization: ocrRecord.organization || 'Не указано',
                    position: ocrRecord.position || 'Не указано',
                    start_date: ocrRecord.date_in || '',
                    end_date: ocrRecord.date_out || '',
                    special_conditions: null,
                }));
                setValue('work_experience.records', mappedRecords, { shouldValidate: true, shouldDirty: true });
            }
            if (wbData.calculated_total_years !== null && wbData.calculated_total_years !== undefined) {
                setValue('work_experience.total_years', wbData.calculated_total_years, { shouldValidate: true, shouldDirty: true });
            }
            trigger('work_experience.records');
            trigger('work_experience.total_years');

            updateMessage = "Данные трудовой книжки обновлены и добавлены в форму.";
        }

        if (fieldsSet) { 
            trigger('personal_data.first_name');
            trigger('personal_data.last_name');
            trigger('personal_data.birth_date');
            trigger('personal_data.snils');
        }

        const docTypeRussian: Record<string, string> = {
            passport: "Паспорт РФ",
            snils: "СНИЛС",
            work_book: "Трудовая книжка",
            other: "Другой документ"
        };
        const docNameToAdd = docTypeRussian[docType] || docType.toString();
        
        const currentDocsString = control._getWatch('documents') || '';
        const currentDocuments = currentDocsString.split(',').map((s: string) => s.trim()).filter(Boolean);
        
        if (!currentDocuments.includes(docNameToAdd)) {
            currentDocuments.push(docNameToAdd);
            setValue('documents', currentDocuments.join(', '), { shouldDirty: true });
            trigger('documents'); 
        }
        antdMessage.success(updateMessage || "Документ обработан.");
    };

    const handleOcrError = (message: string, docType: DocumentTypeToExtract) => {
        setOcrGlobalError(`Ошибка OCR (${docType}): ${message}`);
        antdMessage.error(`Ошибка OCR (${docType}): ${message}`);
        if (docType === 'passport') {
            setPassportData(null);
            setPassportStatus({ attempted: true, processing: false, error: true, success: false });
        } else if (docType === 'snils') {
            setSnilsData(null);
            setSnilsStatus({ attempted: true, processing: false, error: true, success: false });
        } else if (docType === 'work_book') {
            setWorkBookData(null);
            setWorkBookStatus({ attempted: true, processing: false, error: true, success: false });
        }
    };

    const renderPassportData = (data: PassportData) => (
        <Descriptions bordered column={1} size="small" title="Данные паспорта">
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
        <Descriptions bordered column={1} size="small" title="Данные СНИЛС">
            <Descriptions.Item label="Номер СНИЛС">{data.snils_number}</Descriptions.Item>
        </Descriptions>
    );

    const renderWorkBookData = (data: WorkBookData) => (
        <Descriptions bordered column={1} size="small" title="Данные трудовой книжки">
            {data.calculated_total_years !== null && <Descriptions.Item label="Рассчитанный стаж (лет)">{data.calculated_total_years}</Descriptions.Item>}
            <Descriptions.Item label="Записи">
                {data.records && data.records.length > 0 ? (
                    <List
                        size="small"
                        bordered
                        dataSource={data.records}
                        renderItem={(item: WorkBookRecordEntry, index: number) => (
                            <List.Item>
                                <Text strong>{`Запись ${index + 1}:`}</Text> {item.organization} (c {item.date_in} по {item.date_out || 'н.в.'}) - {item.position}
                            </List.Item>
                        )}
                    />
                ) : <Text type="secondary">Записи отсутствуют</Text>}
            </Descriptions.Item>
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
                />
                {snilsStatus.success && snilsData && renderSnilsData(snilsData)}
                {snilsStatus.error && <Alert message="Ошибка обработки СНИЛС. Попробуйте загрузить другой файл." type="warning" showIcon />}

                <Divider />

                <OcrUploader
                    documentType="work_book"
                    onOcrSuccess={handleOcrSuccess}
                    onOcrError={handleOcrError}
                    onProcessingStart={handleProcessingStart}
                    uploaderTitle="Загрузить скан трудовой книжки (все страницы)"
                />
                {workBookStatus.success && workBookData && renderWorkBookData(workBookData)}
                {workBookStatus.error && <Alert message="Ошибка обработки трудовой книжки. Попробуйте загрузить другой файл." type="warning" showIcon />}
            </Space>
        </div>
    );
};

export default DocumentUploadStep; 