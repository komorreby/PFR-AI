import React, { useState, useCallback, ReactNode } from 'react';
import { Upload, Button, Typography, Spin, Alert, Image as AntImage, message as antdMessage, Space, Tooltip } from 'antd';
import { UploadOutlined, DeleteOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import type { RcFile, UploadFile, UploadProps as AntUploadProps, UploadChangeParam } from 'antd/es/upload';
import type { UploadFileStatus, ItemRender } from 'antd/es/upload/interface';
import { submitOcrTask, getOcrTaskStatus } from '../../services/apiClient';
import type { OcrTaskStatusResponse, DocumentTypeToExtract, OcrResultData, OcrTaskSubmitResponse } from '../../types';

const { Text } = Typography;

interface OcrUploaderProps {
  documentType: DocumentTypeToExtract;
  onOcrSuccess: (data: OcrResultData, docType: DocumentTypeToExtract, file?: UploadFile) => void;
  onOcrError: (message: string, docType: DocumentTypeToExtract, file?: UploadFile) => void;
  uploaderTitle?: string;
  onProcessingStart?: (docType: DocumentTypeToExtract, file?: UploadFile) => void;
  allowMultipleFiles?: boolean;
  onBatchFinished?: (docType: DocumentTypeToExtract, errorsInBatch: boolean) => void;
}

const OcrUploader: React.FC<OcrUploaderProps> = ({
  documentType,
  onOcrSuccess,
  onOcrError,
  uploaderTitle = 'Загрузите документ',
  onProcessingStart,
  allowMultipleFiles = false,
  onBatchFinished,
}) => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentProcessingFileDisplay, setCurrentProcessingFileDisplay] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const moveFile = (uid: string, direction: 'up' | 'down') => {
    setFileList(prevList => {
      const index = prevList.findIndex(file => file.uid === uid);
      if (index === -1) return prevList;

      const newIndex = direction === 'up' ? index - 1 : index + 1;
      if (newIndex < 0 || newIndex >= prevList.length) return prevList;

      const newList = [...prevList];
      const temp = newList[index];
      newList[index] = newList[newIndex];
      newList[newIndex] = temp;
      return newList;
    });
  };

  const pollOcrStatusAsync = useCallback((taskId: string, fileName: string, processingFile: UploadFile): Promise<OcrResultData> => {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const statusResponse = await getOcrTaskStatus(taskId);
          if (statusResponse.status === 'COMPLETED') {
            if (statusResponse.data) {
              onOcrSuccess(statusResponse.data, documentType, processingFile);
              antdMessage.success(`Документ ${fileName} успешно обработан.`);
              resolve(statusResponse.data);
            } else {
              const noDataMsg = 'Данные не были возвращены после завершения обработки.';
              onOcrError(noDataMsg, documentType, processingFile);
              antdMessage.error(`Ошибка: ${noDataMsg} (${fileName})`);
              reject(new Error(noDataMsg));
            }
          } else if (statusResponse.status === 'FAILED') {
            const errorMessage = statusResponse.error?.detail || 'Ошибка обработки документа на сервере.';
            onOcrError(errorMessage, documentType, processingFile);
            antdMessage.error(`${errorMessage} (${fileName})`);
            reject(new Error(errorMessage));
          } else {
            setTimeout(poll, 3000);
          }
        } catch (e: any) {
          const fetchErrorMsg = e.message || 'Ошибка при проверке статуса обработки документа.';
          onOcrError(fetchErrorMsg, documentType, processingFile);
          antdMessage.error(`${fetchErrorMsg} (${fileName})`);
          reject(e);
        }
      };
      poll();
    });
  }, [documentType, onOcrSuccess, onOcrError]);

  const handleUpload = async () => {
    if (fileList.length === 0) {
      setError('Пожалуйста, выберите файл(ы) для загрузки.');
      antdMessage.error('Пожалуйста, выберите файл(ы) для загрузки.');
      return;
    }

    setIsLoading(true);
    setError(null);

    if (onProcessingStart) {
      onProcessingStart(documentType, allowMultipleFiles ? undefined : fileList[0]);
    }

    let batchErrorsOccurred = false;
    const currentUploads = fileList.map(file => ({
      ...file,
      status: 'uploading' as UploadFileStatus,
      percent: 0,
    }));
    setFileList(currentUploads);

    for (let i = 0; i < currentUploads.length; i++) {
      const fileToProcess = currentUploads[i];
      
      if (!fileToProcess.originFileObj) {
        currentUploads[i] = { ...fileToProcess, status: 'error', response: 'Missing originFileObj' };
        setFileList([...currentUploads]);
        batchErrorsOccurred = true;
        continue;
      }

      setCurrentProcessingFileDisplay(fileToProcess.name);
      currentUploads[i] = { ...fileToProcess, percent: 10 };
      setFileList([...currentUploads]);

      try {
        const submitResponse: OcrTaskSubmitResponse = await submitOcrTask({
          image: fileToProcess.originFileObj as RcFile,
          document_type: documentType,
        });
        
        antdMessage.info(`Документ ${fileToProcess.name} отправлен на обработку (ID: ${submitResponse.task_id}). Ожидание результата...`);
        currentUploads[i] = { ...fileToProcess, percent: 50 };
        setFileList([...currentUploads]);

        const ocrResultData = await pollOcrStatusAsync(submitResponse.task_id, fileToProcess.name, fileToProcess);
        currentUploads[i] = { ...fileToProcess, status: 'done', percent: 100, response: ocrResultData };

      } catch (e: any) {
        batchErrorsOccurred = true;
        const errorMessage = e.message || `Произошла неизвестная ошибка при обработке файла ${fileToProcess.name}.`;
        if (!e.message?.includes('Ошибка при проверке статуса') && !e.message?.includes('Ошибка обработки документа') && !e.message?.includes('Данные не были возвращены')) {
            onOcrError(errorMessage, documentType, fileToProcess);
        }
        if (!(e.message && (e.message.includes('успешно обработан') || e.message.includes('Ошибка')))) {
            antdMessage.error(errorMessage);
        }
        currentUploads[i] = { ...fileToProcess, status: 'error', error: e, percent: 100 };
      }
      setFileList([...currentUploads]);
    }
    
    setCurrentProcessingFileDisplay(null);
    setIsLoading(false);

    if (onBatchFinished) {
      onBatchFinished(documentType, batchErrorsOccurred);
    }
  };

  const itemRender: ItemRender<UploadFile> = (originNode, file, currentFileList, actions): ReactNode => {
    const index = fileList.findIndex(f => f.uid === file.uid);
    const isFirst = index === 0;
    const isLast = index === fileList.length - 1;
    const isUploadingOrProcessing = isLoading || file.status === 'uploading' || (currentProcessingFileDisplay === file.name && isLoading) ;

    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }} className="ant-upload-list-item">
        {originNode} 
        {allowMultipleFiles && (
          <Space style={{ marginLeft: 'auto', paddingLeft: '8px' }}>
            <Tooltip title="Переместить вверх">
              <Button 
                icon={<ArrowUpOutlined />} 
                size="small" 
                type="text" 
                onClick={() => moveFile(file.uid, 'up')} 
                disabled={isFirst || isUploadingOrProcessing}
              />
            </Tooltip>
            <Tooltip title="Переместить вниз">
              <Button 
                icon={<ArrowDownOutlined />} 
                size="small" 
                type="text" 
                onClick={() => moveFile(file.uid, 'down')} 
                disabled={isLast || isUploadingOrProcessing}
              />
            </Tooltip>
          </Space>
        )}
      </div>
    );
  };

  const uploadProps: AntUploadProps = {
    onRemove: (removedFile) => {
      const newFileList = fileList.filter(f => f.uid !== removedFile.uid);
      setFileList(newFileList);
      if (newFileList.length === 0) {
        setError(null);
      }
      return true;
    },
    beforeUpload: (file: RcFile) => {
      const acceptedMimeTypes = ['image/jpeg', 'image/png', 'application/pdf'];
      const fileType = file.type || '';
      let errorMsg = '';
      
      if (!acceptedMimeTypes.includes(fileType)) {
        errorMsg = `Неподдерживаемый тип файла: ${fileType || 'неизвестный'}. (${file.name})`;
      }
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        errorMsg = (errorMsg ? errorMsg + " " : "") + `Файл ${file.name} слишком большой (>10MB).`;
      }

      if (errorMsg) {
        antdMessage.error(errorMsg);
        setError(prev => prev ? `${prev}; ${errorMsg}`: errorMsg);
        return Upload.LIST_IGNORE;
      }
      return false; 
    },
    onChange: (info: UploadChangeParam<UploadFile>) => {
        const validatedFileList = info.fileList.filter(f => f.status !== 'error');
        
        if (allowMultipleFiles) {
            setFileList(validatedFileList);
        } else {
            setFileList(validatedFileList.length > 0 ? [validatedFileList[validatedFileList.length - 1]] : []);
        }

        if (info.file.status !== 'error' && !info.fileList.some(f => f.status === 'error')) {
            setError(null);
        } else if (info.file.status === 'error') {
            const fileErrorMsg = typeof info.file.response === 'string' ? info.file.response : `Ошибка валидации файла ${info.file.name}.`;
            setError(prev => prev ? `${prev}; ${fileErrorMsg}`: fileErrorMsg);
        }
    },
    fileList,
    multiple: allowMultipleFiles,
    maxCount: allowMultipleFiles ? undefined : 1,
    accept: 'image/png,image/jpeg,application/pdf',
    listType: 'picture',
    itemRender: allowMultipleFiles ? itemRender : undefined,
  };
  
  const spinTip = isLoading 
    ? (currentProcessingFileDisplay 
        ? `Обработка: ${currentProcessingFileDisplay}...` 
        : (allowMultipleFiles && fileList.length > 0 ? `Подготовка к обработке ${fileList.length} файлов...` : "Обработка документа..."))
    : "Загрузка...";

  return (
    <Spin spinning={isLoading} tip={spinTip}>
      <div style={{ border: '1px solid #d9d9d9', borderRadius: '2px', padding: '16px' }}>
        <Text strong style={{ display: 'block', textAlign: 'center', marginBottom: '12px' }}>{uploaderTitle}</Text>
        
        <Upload.Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">Нажмите или перетащите файл(ы)</p>
          <p className="ant-upload-hint">
            PNG, JPG или PDF. {allowMultipleFiles ? 'Можно несколько файлов.' : '1 файл.'} До 10MB каждый.
          </p>
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
          {isLoading ? (currentProcessingFileDisplay ? 'Обработка...' : 'В процессе...') : 'Распознать и обработать'}
        </Button>
      </div>
    </Spin>
  );
};

export default OcrUploader; 