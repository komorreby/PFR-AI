import React from 'react';
import {
    Typography,
    Collapse,
    Space,
    Statistic,
    Row,
    Col,
    Descriptions
} from 'antd';
import { CheckCircleOutlined, WarningOutlined } from '@ant-design/icons';
import { ProcessOutput as BackendProcessOutput } from '../types';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css'; // Import Katex CSS

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface ProcessResultDisplayProps {
  result: BackendProcessOutput;
}

const ProcessResultDisplay: React.FC<ProcessResultDisplayProps> = ({ result }) => {
  const { final_status, explanation, confidence_score, case_id, error_info } = result;
  
  const isApproved = final_status?.toLowerCase().includes('соответствует') ?? false;
  const isErrorStatus = final_status?.toLowerCase().includes('error') || final_status?.toLowerCase().includes('failed');
  
  let statusTagColor: string;
  let StatusIconComponent: React.FC<any> = CheckCircleOutlined; // По умолчанию

  if (isApproved) {
    statusTagColor = 'success';
    StatusIconComponent = CheckCircleOutlined;
  } else if (isErrorStatus) {
    statusTagColor = 'error';
    StatusIconComponent = WarningOutlined;
  } else {
    statusTagColor = 'warning'; // Для статусов типа "PROCESSING" или "UNKNOWN"
    StatusIconComponent = WarningOutlined;
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Title level={3} style={{ textAlign: 'center' }}>Результат обработки дела ID: {case_id}</Title>

      <Row justify="center">
        <Col>
          <Statistic 
            title={
              <Space>
                <StatusIconComponent style={{color: statusTagColor === 'success' ? '#52c41a' : statusTagColor === 'error' ? '#ff4d4f' : '#faad14'}}/>
                Итоговый статус
              </Space>
            }
            value={final_status || "Неизвестен"}
            valueStyle={{ color: statusTagColor === 'success' ? '#52c41a' : statusTagColor === 'error' ? '#ff4d4f' : '#faad14' }}
          />
          {confidence_score !== null && confidence_score !== undefined && (
            <Text type="secondary" style={{ display:'block', textAlign: 'center'}}>
                Уверенность: {(confidence_score * 100).toFixed(1)}%
            </Text>
          )}
        </Col>
      </Row>

      <Collapse defaultActiveKey={['explanation']} bordered={false} style={{backgroundColor: 'transparent'}}>
        <Panel header={<Text strong>Подробное объяснение</Text>} key="explanation">
          <div style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
            <ReactMarkdown
              children={explanation || "Объяснение отсутствует."}
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                table: ({node, ...props}) => <table style={{ borderCollapse: 'collapse', width: '100%' }} {...props} />,
                th: ({node, ...props}) => <th style={{ border: '1px solid #ddd', padding: '8px', backgroundColor: '#f0f0f0' }} {...props} />,
                td: ({node, ...props}) => <td style={{ border: '1px solid #ddd', padding: '8px' }} {...props} />,
              }}
            />
          </div>
        </Panel>
        {error_info && (
            <Panel header={<Text strong style={{color: '#ff4d4f'}}>Информация об ошибке</Text>} key="error_info">
                 <Descriptions bordered column={1} size="small">
                    {error_info.code && <Descriptions.Item label="Код ошибки">{error_info.code}</Descriptions.Item>}
                    {error_info.message && <Descriptions.Item label="Сообщение">{error_info.message}</Descriptions.Item>}
                    {error_info.source && <Descriptions.Item label="Источник">{error_info.source}</Descriptions.Item>}
                    {error_info.details && (
                        <Descriptions.Item label="Детали">
                            <pre style={{whiteSpace: 'pre-wrap', wordBreak: 'break-all'}}>
                                {JSON.stringify(error_info.details, null, 2)}
                            </pre>
                        </Descriptions.Item>
                    )}
                </Descriptions>
            </Panel>
        )}
      </Collapse>
    </Space>
  );
};

export default ProcessResultDisplay; 