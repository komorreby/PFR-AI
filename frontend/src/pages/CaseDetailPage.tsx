// src/pages/CaseDetailPage.tsx
import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Typography, Spin, Alert, Descriptions, Tag, Collapse, Button, Space, Modal, message, List, Card, Divider } from 'antd';
import { getFullCaseData, downloadCaseDocument } from '../services/apiClient';
import { FullCaseData, ApiError, WorkExperienceRecord, OtherDocumentData, PersonalData, DisabilityInfo, WorkExperience } from '../types';
import { ArrowLeftOutlined, DownloadOutlined, InfoCircleOutlined, UserOutlined, IdcardOutlined, SolutionOutlined, PaperClipOutlined, WarningOutlined, ExclamationCircleFilled } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;
const { confirm } = Modal;

const CaseDetailPage: React.FC = () => {
  const { caseId } = useParams<{ caseId: string }>();
  const [caseData, setCaseData] = useState<FullCaseData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<{'pdf': boolean, 'docx': boolean}>({ pdf: false, docx: false });

  useEffect(() => {
    if (caseId) {
      const fetchCaseData = async () => {
        setLoading(true);
        try {
          const id = parseInt(caseId, 10);
          if (isNaN(id)) {
            throw new Error('Некорректный ID дела.');
          }
          const data = await getFullCaseData(id);
          setCaseData(data);
          setError(null);
        } catch (err) {
          const apiErr = err as ApiError;
          setError(apiErr.message || `Не удалось загрузить данные дела #${caseId}.`);
          console.error(`Fetch Case Data Error (ID: ${caseId}):`, apiErr);
        }
        setLoading(false);
      };
      fetchCaseData();
    }
  }, [caseId]);

  const handleDownload = async (format: 'pdf' | 'docx') => {
    if (!caseId || !caseData) return;

    confirm({
        title: `Подтвердите загрузку документа`, 
        icon: <ExclamationCircleFilled />, 
        content: `Вы уверены, что хотите скачать документ по делу #${caseId} в формате ${format.toUpperCase()}?`, 
        okText: 'Да, скачать', 
        cancelText: 'Отмена', 
        async onOk() {
            setDownloading(prev => ({ ...prev, [format]: true }));
            try {
              message.loading({ content: `Подготовка ${format.toUpperCase()} документа...`, key: `download-${format}` });
              const blob = await downloadCaseDocument(parseInt(caseId, 10), format);
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `case_${caseId}_document.${format}`;
              document.body.appendChild(a);
              a.click();
              a.remove();
              window.URL.revokeObjectURL(url);
              message.success({ content: `Документ (${format.toUpperCase()}) успешно загружен!`, key: `download-${format}`, duration: 3 });
            } catch (err) {
              const apiErr = err as ApiError;
              console.error("Download error:", apiErr);
              message.error({ content: apiErr.message || `Не удалось скачать документ (${format.toUpperCase()}).`, key: `download-${format}`, duration: 4 });
            } finally {
              setDownloading(prev => ({ ...prev, [format]: false }));
            }
        }
    });
  };

  if (loading) {
    return <div style={{ textAlign: 'center', margin: '20px 0' }}><Spin size="large" tip={`Загрузка данных дела #${caseId}...`} /></div>;
  }

  if (error) {
    return <Alert message="Ошибка загрузки" description={error} type="error" showIcon />;
  }

  if (!caseData) {
    return <Alert message="Данные не найдены" description={`Не удалось найти информацию по делу #${caseId}.`} type="warning" showIcon />;
  }

  const renderStatusTag = (status: string | null) => {
    if (!status) return <Tag color="default">Неизвестно</Tag>;
    switch (status) {
      case 'СООТВЕТСТВУЕТ': case 'COMPLETED': return <Tag color="success">{status}</Tag>;
      case 'НЕ СООТВЕТСТВУЕТ': return <Tag color="warning">{status}</Tag>;
      case 'PROCESSING': return <Tag color="processing">В ОБРАБОТКЕ</Tag>; // AntD 'processing' color
      case 'ERROR_PROCESSING': case 'FAILED': return <Tag color="error">{status}</Tag>;
      default: return <Tag color="blue">{status}</Tag>;
    }
  };

  return (
    <div>
      <Button type="link" icon={<ArrowLeftOutlined />} onClick={() => window.history.back()} style={{ marginBottom: '16px', paddingLeft: 0 }}>
        Назад к истории
      </Button>
      <Title level={2} style={{ marginBottom: '5px' }}>Детали дела <Text type="secondary">#{caseData.id}</Text></Title>
      <Paragraph>
        <Text strong>Тип пенсии:</Text> {caseData.pension_type} <br />
        <Text strong>Статус:</Text> {renderStatusTag(caseData.final_status)} <br />
        <Text strong>Создано:</Text> {new Date(caseData.created_at).toLocaleString()} <br />
        {caseData.updated_at && <><Text strong>Обновлено:</Text> {new Date(caseData.updated_at).toLocaleString()} <br /></>}
        {typeof caseData.rag_confidence === 'number' && <><Text strong>Уверенность RAG:</Text> {(caseData.rag_confidence * 100).toFixed(1)}%</>}
      </Paragraph>

      {caseData.final_explanation && (
        <Collapse defaultActiveKey={['final_explanation_panel']} style={{marginBottom: '20px'}}>
          <Panel header={<><InfoCircleOutlined style={{marginRight: 8}} />Итоговое заключение</>} key="final_explanation_panel">
            {caseData.final_explanation.split(/\n(?=## )/).map((section, index) => {
              let cardTitle = null;
              let cardContent = section;
              const h2Match = section.match(/^## (.*)(?:\n|$)/);

              if (h2Match && h2Match[1]) {
                cardTitle = h2Match[1].trim();
                // Удаляем строку с заголовком H2 из содержимого, 
                // плюс один символ новой строки, если он есть сразу после заголовка.
                // Это предотвратит двойной отступ, если после H2 идет пустая строка.
                cardContent = section.substring(h2Match[0].length);
                if (cardContent.startsWith('\n')) {
                  cardContent = cardContent.substring(1);
                }
              }

              return (
                <Card 
                  key={index} 
                  title={cardTitle} // Используем извлеченный заголовок H2
                  style={{ 
                    marginBottom: '16px', 
                    background: '#fff', 
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.09)'
                  }}
                  bordered={true}
                >
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm, remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                    components={{
                      h2: ({node, ...props}) => (
                        <>
                          <h2 {...props} style={{ marginBottom: '16px' }} />
                          <Divider />
                        </>
                      ),
                      h3: ({node, ...props}) => (
                        <>
                          <h3 {...props} style={{ marginTop: '20px', marginBottom: '12px' }} />
                          <Divider dashed />
                        </>
                      ),
                    }}
                  >
                    {cardContent || ''}
                  </ReactMarkdown>
                </Card>
              );
            })}
          </Panel>
        </Collapse>
      )}

      <Space style={{marginBottom: '20px'}}>
          <Button icon={<DownloadOutlined />} onClick={() => handleDownload('pdf')} loading={downloading.pdf} disabled={downloading.docx}>
              Скачать PDF
          </Button>
          <Button icon={<DownloadOutlined />} onClick={() => handleDownload('docx')} loading={downloading.docx} disabled={downloading.pdf}>
              Скачать DOCX
          </Button>
      </Space>

      <Collapse defaultActiveKey={['personal']} accordion>
        {caseData.personal_data && (
          <Panel header={<Text strong><UserOutlined /> Персональные данные</Text>} key="personal">
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="ФИО">{[caseData.personal_data.last_name, caseData.personal_data.first_name, caseData.personal_data.middle_name].filter(Boolean).join(' ')}</Descriptions.Item>
              <Descriptions.Item label="Дата рождения">{caseData.personal_data.birth_date}</Descriptions.Item>
              <Descriptions.Item label="СНИЛС">{caseData.personal_data.snils}</Descriptions.Item>
              <Descriptions.Item label="Пол">{caseData.personal_data.gender}</Descriptions.Item>
              <Descriptions.Item label="Гражданство">{caseData.personal_data.citizenship}</Descriptions.Item>
              <Descriptions.Item label="Иждивенцы">{caseData.personal_data.dependents ?? '0'}</Descriptions.Item>
              {caseData.personal_data.name_change_info && (
                  <Descriptions.Item label="Смена ФИО">
                      Прежн. ФИО: {caseData.personal_data.name_change_info.old_full_name || '-'}, 
                      Дата: {caseData.personal_data.name_change_info.date_changed || '-'}
                  </Descriptions.Item>
              )}
            </Descriptions>
          </Panel>
        )}

        {caseData.disability && (
          <Panel header={<Text strong><IdcardOutlined /> Информация об инвалидности</Text>} key="disability">
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="Группа">{caseData.disability.group}</Descriptions.Item>
              <Descriptions.Item label="Дата установления">{caseData.disability.date}</Descriptions.Item>
              <Descriptions.Item label="Номер справки МСЭ">{caseData.disability.cert_number || '-'}</Descriptions.Item>
            </Descriptions>
          </Panel>
        )}

        {caseData.work_experience && caseData.work_experience.records && caseData.work_experience.records.length > 0 && (
          <Panel header={<Text strong><SolutionOutlined /> Трудовой стаж</Text>} key="work">
            <Descriptions bordered column={1} size="small" style={{ marginBottom: '16px' }}>
                 <Descriptions.Item label="Общий заявленный стаж (лет)">{caseData.work_experience.total_years ?? '-'}</Descriptions.Item>
            </Descriptions>
            <List
                size="small"
                bordered
                dataSource={caseData.work_experience.records}
                renderItem={(item: WorkExperienceRecord) => (
                    <List.Item>
                        <List.Item.Meta
                            title={`${item.organization} (${item.position})`}
                            description={`Период: ${item.start_date} - ${item.end_date}`}
                        />
                        {item.special_conditions && <Tag color="orange">Особые условия</Tag>}
                    </List.Item>
                )}
            />
          </Panel>
        )}

        <Panel header={<Text strong><PaperClipOutlined /> Дополнительная информация и документы</Text>} key="additional">
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="Пенсионные баллы (ИПК)">{caseData.pension_points ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="Льготы">{caseData.benefits && caseData.benefits.length > 0 ? caseData.benefits.join(', ') : '-'}</Descriptions.Item>
            <Descriptions.Item label="Представленные стандартные документы">{caseData.submitted_documents && caseData.submitted_documents.length > 0 ? caseData.submitted_documents.join(', ') : '-'}</Descriptions.Item>
            <Descriptions.Item label="Наличие некорректных документов">{caseData.has_incorrect_document ? <Tag color="error">Да</Tag> : <Tag color="success">Нет</Tag>}</Descriptions.Item>
          </Descriptions>
          {caseData.other_documents_extracted_data && caseData.other_documents_extracted_data.length > 0 && (
            <>
                <Title level={5} style={{marginTop: '16px', marginBottom: '8px'}}>Данные из прочих загруженных документов:</Title>
                <Collapse ghost>
                    {caseData.other_documents_extracted_data.map((doc, index) => (
                        <Panel header={`Документ ${index + 1}: ${doc.identified_document_type || 'Неизвестный тип'} (станд.: ${doc.standardized_document_type || '-'})`} key={`other_doc_${index}`}>
                            <Descriptions bordered column={1} size="small">
                                {doc.extracted_fields && Object.entries(doc.extracted_fields).map(([key, value]) => (
                                    <Descriptions.Item label={key} key={key}>{String(value)}</Descriptions.Item>
                                ))}
                                <Descriptions.Item label="Оценка LLM (Vision)">{doc.multimodal_assessment || '-'}</Descriptions.Item>
                                <Descriptions.Item label="Анализ LLM (Text)">{doc.text_llm_reasoning || '-'}</Descriptions.Item>
                            </Descriptions>
                        </Panel>
                    ))}
                </Collapse>
            </>
          )}
        </Panel>
        
        {caseData.errors && caseData.errors.length > 0 && (
            <Panel header={<Text strong color="red"><WarningOutlined /> Ошибки обработки</Text>} key="errors_case">
                <List
                    size="small"
                    bordered
                    dataSource={caseData.errors}
                    renderItem={(errorItem: any, index: number) => (
                        <List.Item>
                            <pre style={{whiteSpace: 'pre-wrap', wordBreak: 'break-all'}}>{JSON.stringify(errorItem, null, 2)}</pre>
                        </List.Item>
                    )}
                />
            </Panel>
        )}
      </Collapse>

    </div>
  );
};

export default CaseDetailPage;