import React, { useState } from 'react';
import { Upload, Button, Select, Typography, Spin, message as antdMessage, Form } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import type { UploadProps, RcFile } from 'antd/es/upload';

const { Text } = Typography;
const { Option } = Select;

interface DocumentUploadProps {
  onDocumentProcessed: (data: {
    extracted_text: string;
    extracted_fields: Record<string, string>;
  }) => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ onDocumentProcessed }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [documentType, setDocumentType] = useState('passport');

  const props: UploadProps = {
    name: 'file',
    multiple: false,
    action: 'http://localhost:8000/api/v1/ocr/upload_document',
    data: { document_type: documentType },
    beforeUpload: (file: RcFile) => {
      const isImage = file.type.startsWith('image/');
      if (!isImage) {
        antdMessage.error('Вы можете загружать только изображения!');
      }
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        antdMessage.error('Изображение должно быть меньше 10MB!');
      }
      return isImage && isLt10M;
    },
    onChange: (info) => {
      if (info.file.status === 'uploading') {
        setIsLoading(true);
        return;
      }
      if (info.file.status === 'done') {
        setIsLoading(false);
        antdMessage.success(`${info.file.name} успешно загружен и обработан.`);
        onDocumentProcessed(info.file.response);
      } else if (info.file.status === 'error') {
        setIsLoading(false);
        antdMessage.error(`Ошибка загрузки ${info.file.name}.`);
        console.error("Upload Error Response:", info.file.response);
      }
    },
    showUploadList: true,
    maxCount: 1,
  };

  return (
    <Spin spinning={isLoading} tip="Обработка документа...">
      <Form layout="vertical">
        <Form.Item label="Тип документа">
          <Select
            value={documentType}
            onChange={(value) => setDocumentType(value)}
            style={{ width: '100%' }}
          >
            <Option value="passport">Паспорт</Option>
          </Select>
        </Form.Item>
        
        <Form.Item>
          <Upload.Dragger {...props}>
            <p className="ant-upload-drag-icon">
              <UploadOutlined />
            </p>
            <p className="ant-upload-text">Нажмите или перетащите файл в эту область для загрузки</p>
            <p className="ant-upload-hint">
              Поддерживаются изображения (PNG, JPG, TIFF). Максимальный размер: 10MB.
            </p>
          </Upload.Dragger>
        </Form.Item>
      </Form>
    </Spin>
  );
};

export default DocumentUpload; 