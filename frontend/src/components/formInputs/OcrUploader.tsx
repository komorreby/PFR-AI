import React, { useState, useCallback } from 'react';
import { Upload, Button, Typography, Spin, Alert, Image as AntImage, message as antdMessage, Space } from 'antd';
import { UploadOutlined, DeleteOutlined } from '@ant-design/icons';
import type { RcFile, UploadFile, UploadProps } from 'antd/es/upload';
import { submitOcrTask, getOcrTaskStatus } from '../../services/apiClient';
import type { OcrTaskStatusResponse, DocumentTypeToExtract, OcrResultData, OcrTaskSubmitResponse } from '../../types';

const { Text } = Typography;

interface OcrUploaderProps {
  documentType: DocumentTypeToExtract;
  onOcrSuccess: (data: OcrResultData, docType: DocumentTypeToExtract) => void;
  onOcrError: (message: string, docType: DocumentTypeToExtract) => void;
  uploaderTitle?: string;
  onProcessingStart?: (docType: DocumentTypeToExtract) => void;
}

const OcrUploader: React.FC<OcrUploaderProps> = ({
  documentType,
  onOcrSuccess,
  onOcrError,
  uploaderTitle = 'Загрузите документ',
  onProcessingStart,
}) => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollOcrStatus = async (taskId: string, fileName: string) => {
    try {
      const statusResponse = await getOcrTaskStatus(taskId);
      if (statusResponse.status === 'COMPLETED') {
        setIsLoading(false);
        if (statusResponse.data) {
          onOcrSuccess(statusResponse.data, documentType);
          antdMessage.success(`Документ ${fileName} успешно обработан.`);
        } else {
          onOcrError('Данные не были возвращены после завершения обработки.', documentType);
          antdMessage.error('Ошибка: Данные не были возвращены от сервера.');
        }
        setFileList([]);
      } else if (statusResponse.status === 'FAILED') {
        setIsLoading(false);
        const errorMessage = statusResponse.error?.detail || 'Ошибка обработки документа на сервере.';
        onOcrError(errorMessage, documentType);
        antdMessage.error(errorMessage);
        setFileList([]);
      } else {
        setTimeout(() => pollOcrStatus(taskId, fileName), 3000);
      }
    } catch (e: any) {
      setIsLoading(false);
      const errorMessage = e.message || 'Ошибка при проверке статуса обработки документа.';
      onOcrError(errorMessage, documentType);
      antdMessage.error(errorMessage);
      setFileList([]);
    }
  };

  const handleUpload = async () => {
    if (fileList.length === 0 || !fileList[0].originFileObj) {
      setError('Пожалуйста, выберите файл для загрузки.');
      antdMessage.error('Пожалуйста, выберите файл для загрузки.');
      return;
    }
    const fileToUpload = fileList[0].originFileObj as RcFile;
    const fileName = fileToUpload.name;

    setIsLoading(true);
    setError(null);
    try {
      if (onProcessingStart) {
        onProcessingStart(documentType);
      }
      const submitResponse: OcrTaskSubmitResponse = await submitOcrTask({
        image: fileToUpload,
        document_type: documentType,
      });
      
      antdMessage.info(`Документ ${fileName} отправлен на обработку. ID задачи: ${submitResponse.task_id}`);
      pollOcrStatus(submitResponse.task_id, fileName);

    } catch (e: any) {
      setIsLoading(false);
      const errorMessage = e.message || 'Произошла неизвестная ошибка при отправке документа на обработку.';
      console.error('OCR Submit Error:', e);
      onOcrError(errorMessage, documentType);
      antdMessage.error(errorMessage);
    }
  };

  const uploadProps: UploadProps = {
    onRemove: (file) => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
      setError(null);
      return true;
    },
    beforeUpload: (file: RcFile) => {
      const acceptedMimeTypes = ['image/jpeg', 'image/png', 'application/pdf'];
      const fileType = file.type || '';
      if (!acceptedMimeTypes.includes(fileType)) {
        const errorMsg = `Неподдерживаемый тип файла: ${fileType || 'неизвестный'}. Загрузите PNG, JPG или PDF.`;
        setError(errorMsg);
        antdMessage.error(errorMsg);
        return Upload.LIST_IGNORE;
      }
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        const errorMsg = 'Файл должен быть меньше 10MB!';
        setError(errorMsg);
        antdMessage.error(errorMsg);
        return Upload.LIST_IGNORE;
      }

      setError(null);
      const uploadFileObject: UploadFile = {
        uid: file.uid,
        name: file.name,
        status: 'done',
        originFileObj: file,
        type: file.type
      };
      setFileList([uploadFileObject]);
      return false;
    },
    fileList,
    maxCount: 1,
    accept: 'image/png,image/jpeg,application/pdf',
    listType: 'picture',
  };

  return (
    <Spin spinning={isLoading} tip="Обработка документа...">
      <div style={{ border: '1px solid #d9d9d9', borderRadius: '2px', padding: '16px' }}>
        <Text strong style={{ display: 'block', textAlign: 'center', marginBottom: '12px' }}>{uploaderTitle}</Text>
        
        <Upload.Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">Нажмите или перетащите файл</p>
          <p className="ant-upload-hint">PNG, JPG или PDF. Макс. 1 файл, до 10MB.</p>
        </Upload.Dragger>

        {error && !isLoading && (
          <Alert message={error} type="error" showIcon style={{ marginTop: '10px' }} />
        )}

        <Button
          type="primary"
          onClick={handleUpload}
          disabled={fileList.length === 0 || isLoading}
          style={{ marginTop: '16px', width: '100%' }}
        >
          {isLoading ? 'Отправлено...' : 'Распознать и обработать'}
        </Button>
      </div>
    </Spin>
  );
};

export default OcrUploader; 