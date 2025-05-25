import React, { useState } from 'react';
import { Typography, Button, Space, Alert, Descriptions, List, message as antdMessage } from 'antd';
import OcrUploader from '../formInputs/OcrUploader';
import { 
    OcrResultData, 
    DocumentTypeToExtract, 
    PassportData, 
    SnilsData, 
    WorkBookData, 
    OtherDocumentData,
    WorkBookRecordEntry
} from '../../types';

const { Title, Text } = Typography;

interface OcrStepComponentProps {
  documentType: DocumentTypeToExtract;
  uploaderTitle: string;
  onOcrComplete: (data: OcrResultData, docType: DocumentTypeToExtract) => void; 
}

const OcrStepComponent: React.FC<OcrStepComponentProps> = ({ 
    documentType, 
    uploaderTitle, 
    onOcrComplete 
}) => {
  const [ocrData, setOcrData] = useState<OcrResultData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false); 

  const handleOcrSuccess = (data: OcrResultData, docType: DocumentTypeToExtract) => {
    setOcrData(data);
    setError(null);
    antdMessage.success(`Документ "${docType}" успешно обработан и данные извлечены.`);
    setIsProcessing(false);
  };

  const handleOcrError = (message: string, docType: DocumentTypeToExtract) => {
    setOcrData(null);
    setError(`Ошибка OCR (${docType}): ${message}`);
    antdMessage.error(`Ошибка OCR (${docType}): ${message}`);
    setIsProcessing(false);
  };
  
  // OcrUploader должен сам вызывать setIsProcessing(true) в начале загрузки 
  // и setIsProcessing(false) по завершению (успех/ошибка) через эти коллбэки.
  // Для этого OcrUploader должен был бы принимать setIsProcessing как проп,
  // или мы упрощаем и считаем, что isProcessing - это состояние между кликом на upload и результатом.
  // Здесь я предполагаю, что OcrUploader сам управляет индикацией загрузки файла, 
  // а isProcessing здесь - это больше про состояние "ожидаем результат от бэкенда".
  // Чтобы это работало точнее, OcrUploader должен иметь проп onUploadStart/onProcessingStart.
  // Пока что isProcessing будет активироваться только в этих коллбэках, что не идеально для UI.
  // Либо OcrUploader сам должен вызывать setIsProcessing перед фактической отправкой файла
  // через проп вроде `onProcessingStart: () => void;` 
  // Для упрощения, пока что setIsProcessing(true) можно поставить в начале этих обработчиков.

  const handleConfirmAndProceed = () => {
    if (ocrData) {
      onOcrComplete(ocrData, documentType);
      antdMessage.info('Данные подтверждены.');
    } else {
      antdMessage.warning('Нет данных для подтверждения. Пожалуйста, загрузите и обработайте документ.');
    }
  };

  const renderOcrDataPreview = (data: OcrResultData, docType: DocumentTypeToExtract) => {
    if (!data) return <Text type="secondary">Нет данных для предпросмотра.</Text>;

    switch (docType) {
      case 'passport':
        const passData = data as PassportData;
        return (
          <Descriptions bordered column={1} size="small" title="Предпросмотр: Паспорт">
            <Descriptions.Item label="ФИО">{`${passData.last_name || ''} ${passData.first_name || ''} ${passData.middle_name || ''}`.trim()}</Descriptions.Item>
            <Descriptions.Item label="Дата рождения">{passData.birth_date}</Descriptions.Item>
            {/* <Descriptions.Item label="Пол">{passData.gender}</Descriptions.Item> */}
            <Descriptions.Item label="Серия">{passData.passport_series}</Descriptions.Item>
            <Descriptions.Item label="Номер">{passData.passport_number}</Descriptions.Item>
            {/* {passData.issue_date && <Descriptions.Item label="Дата выдачи">{passData.issue_date}</Descriptions.Item>} */}
            {/* {passData.issued_by && <Descriptions.Item label="Кем выдан">{passData.issued_by}</Descriptions.Item>} */}
          </Descriptions>
        );
      case 'snils':
        const snilsData = data as SnilsData;
        return (
          <Descriptions bordered column={1} size="small" title="Предпросмотр: СНИЛС">
            <Descriptions.Item label="Номер СНИЛС">{snilsData.snils_number}</Descriptions.Item>
          </Descriptions>
        );
      case 'work_book':
        const wbData = data as WorkBookData;
        return (
          <Descriptions bordered column={1} size="small" title="Предпросмотр: Трудовая книжка">
            {/* <Descriptions.Item label="ФИО Владельца">{`${wbData.owner_surname || ''} ${wbData.owner_name || ''} ${wbData.owner_patronymic || ''}`.trim()}</Descriptions.Item> */}
            {/* <Descriptions.Item label="Дата рождения владельца">{wbData.owner_birth_date}</Descriptions.Item> */}
            <Descriptions.Item label="Записи">
              {wbData.records && wbData.records.length > 0 ? (
                <List
                  size="small"
                  bordered
                  dataSource={wbData.records}
                  renderItem={(item: WorkBookRecordEntry, index) => (
                    <List.Item>
                      <Text strong>{`Запись ${index + 1}:`}</Text> {item.organization} 
                      {/* (c {item.start_date} по {item.end_date || 'н.в.'}) */}
                       - {item.position}
                    </List.Item>
                  )}
                />
              ) : <Text type="secondary">Записи отсутствуют</Text>}
            </Descriptions.Item>
          </Descriptions>
        );
      case 'other':
        const otherData = data as OtherDocumentData;
        return (
            <Descriptions bordered column={1} size="small" title={`Предпросмотр: ${otherData.identified_document_type || 'Доп. документ'}`}>
                {otherData.standardized_document_type && 
                    <Descriptions.Item label="Стандартный тип">{otherData.standardized_document_type}</Descriptions.Item>}
                {Object.entries(otherData.extracted_fields || {}).map(([key, value]) => (
                    <Descriptions.Item key={key} label={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}>
                        {String(value)}
                    </Descriptions.Item>
                ))}
                 {(!otherData.extracted_fields || Object.keys(otherData.extracted_fields).length === 0) && 
                    <Descriptions.Item label="Извлеченные поля">Отсутствуют</Descriptions.Item>}
            </Descriptions>
        );
      default:
        const exhaustiveCheck: never = docType;
        return <Text type="warning">Предпросмотр для типа документа "{exhaustiveCheck}" не настроен.</Text>;
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', padding: '20px', border: '1px solid #f0f0f0', borderRadius: '8px' }}>
      <Title level={4} style={{ textAlign: 'center', marginBottom: 0 }}>{uploaderTitle}</Title>
      
      <OcrUploader
        documentType={documentType}
        onOcrSuccess={(data, docType) => { setIsProcessing(true); handleOcrSuccess(data, docType); }}
        onOcrError={(message, docType) => { setIsProcessing(true); handleOcrError(message, docType); }}
        // onUploadInitiated НЕ ИСПОЛЬЗУЕТСЯ, т.к. его нет в OcrUploaderProps и это вызывает ошибку
        uploaderTitle={`Перетащите или выберите файл для "${documentType}"`}
      />

      {isProcessing && !ocrData && !error && <Text type="secondary" style={{textAlign: 'center'}}>Обработка документа...</Text>}
      {error && !isProcessing && <Alert message={error} type="error" showIcon style={{ marginTop: '16px' }}/>}

      {ocrData && !isProcessing &&
        <div style={{ marginTop: '16px' }}>
            <Title level={5} style={{marginBottom: '12px'}}>Предпросмотр извлеченных данных:</Title>
            {renderOcrDataPreview(ocrData, documentType)}
        </div>
      }
      
      <Button 
        type="primary" 
        onClick={handleConfirmAndProceed}
        disabled={!ocrData || isProcessing} // Дизейблим, если нет данных или пока идет обработка ответа
        loading={isProcessing} // Показываем состояние загрузки на кнопке
        style={{ marginTop: '20px', width: '100%' }}
      >
        Подтвердить и использовать эти данные
      </Button>
    </Space>
  );
};

export default OcrStepComponent; 