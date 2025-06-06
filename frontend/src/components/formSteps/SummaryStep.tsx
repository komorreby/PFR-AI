import React from 'react';
import {
    Typography,
    Divider,
    List as AntList,
    Badge as AntBadge,
    Row,
    Col,
    Collapse,
    Space,
    Descriptions
} from 'antd';
import { CheckCircleOutlined, WarningOutlined, ProfileOutlined, BookOutlined, SolutionOutlined, FileTextOutlined, UserOutlined, AuditOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { CaseFormDataTypeForRHF, OtherDocumentData } from '../../types';
import SummaryInsights from '../SummaryInsights';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

interface SummaryStepProps {
  formData: CaseFormDataTypeForRHF;
  onEditStep?: (stepIndex: number) => void; 
}

// Вспомогательная функция для отображения списков тегов или простых элементов
const renderSimpleList = (itemsString: string | undefined | null, title: string) => {
  const items = itemsString?.split(',').map(s => s.trim()).filter(Boolean);
  if (!items || items.length === 0) {
    return <Descriptions.Item label={title}>Нет</Descriptions.Item>;
  }
  return (
    <Descriptions.Item label={title} span={2}>
      <Space direction="vertical" size="small">
        {items.map((item, index) => (
          <Text key={index}>{item}</Text>
        ))}
      </Space>
    </Descriptions.Item>
  );
};

const SummaryStep: React.FC<SummaryStepProps> = ({ formData, onEditStep }) => {
  const { 
    personal_data = {}, 
    work_experience = { total_years: 0, records: [], raw_events: [] },
    pension_points,
    benefits,
    // documents, // Это поле, вероятно, было для старой структуры. В CaseFormDataTypeForRHF есть submitted_documents
    submitted_documents,
    has_incorrect_document,
    disability,
    pension_type,
    other_documents_extracted_data = []
  } = formData;

  const pensionTypeLabel = 
    pension_type === 'retirement_standard' ? 'Страховая по старости' :
    pension_type === 'disability_social' ? 'Социальная по инвалидности' :
    'Тип пенсии не выбран';

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Title level={3} style={{ textAlign: 'center' }}>Сводка данных дела</Title>
      <Text style={{ textAlign: 'center', fontSize: '18px'}}>
        Тип пенсии: <Text strong style={{color: '#1890ff'}}>{pensionTypeLabel}</Text>
      </Text>
      <Divider />

      <Descriptions bordered column={{ xxl: 2, xl: 2, lg: 1, md: 1, sm: 1, xs: 1 }} title={<><UserOutlined style={{marginRight: 8}}/>Персональные данные</>}>
        <Descriptions.Item label="ФИО">
          {[personal_data.last_name, personal_data.first_name, personal_data.middle_name].filter(Boolean).join(' ') || 'Не указано'}
        </Descriptions.Item>
        <Descriptions.Item label="Дата рождения">{personal_data.birth_date || 'Не указано'}</Descriptions.Item>
        <Descriptions.Item label="СНИЛС">{personal_data.snils || 'Не указано'}</Descriptions.Item>
        <Descriptions.Item label="Пол">{personal_data.gender === 'male' ? 'Мужской' : personal_data.gender === 'female' ? 'Женский' : 'Не указан'}</Descriptions.Item>
        <Descriptions.Item label="Гражданство">{personal_data.citizenship || 'Не указано'}</Descriptions.Item>
        <Descriptions.Item label="Место рождения">{personal_data.birth_place || 'Не указано'}</Descriptions.Item>
        <Descriptions.Item label="Серия паспорта">{personal_data.passport_series || 'Не указано'}</Descriptions.Item>
        <Descriptions.Item label="Номер паспорта">{personal_data.passport_number || 'Не указано'}</Descriptions.Item>
        <Descriptions.Item label="Кем выдан">{personal_data.issuing_authority || 'Не указано'}</Descriptions.Item>
        <Descriptions.Item label="Дата выдачи">{personal_data.passport_issue_date || 'Не указано'}</Descriptions.Item>
        <Descriptions.Item label="Код подразделения">{personal_data.department_code || 'Не указано'}</Descriptions.Item>
        {personal_data.name_change_info && (
          <>
            <Descriptions.Item label="Смена ФИО" span={2}><Text strong>Да</Text></Descriptions.Item>
            <Descriptions.Item label="Прежнее ФИО">{personal_data.name_change_info.old_full_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="Дата смены">{personal_data.name_change_info.date_changed || '-'}</Descriptions.Item>
          </>
        )}
      </Descriptions>

      {pension_type === 'retirement_standard' && (
        <>
          <Divider />
          <Descriptions bordered column={1} title={<><ProfileOutlined style={{marginRight: 8}}/>Трудовой стаж</>}>
            <Descriptions.Item label="Заявленный общий стаж">
              {work_experience.total_years !== null && work_experience.total_years !== undefined ? `${work_experience.total_years} лет` : 'Не указан'}
            </Descriptions.Item>
            {work_experience.records && work_experience.records.length > 0 ? (
              <Descriptions.Item label="Записи о стаже" span={1}>
                <AntList
                  size="small"
                  bordered
                  dataSource={work_experience.records}
                  renderItem={(record, index) => (
                    <AntList.Item>
                      <AntList.Item.Meta
                        title={<Text strong>{index + 1}. {record.organization}</Text>}
                        description={`Период: ${record.date_in || '-'} - ${record.date_out || '-'}, Должность: ${record.position || '-'}`}
                      />
                      {record.special_conditions && <AntBadge status="warning" text="Особые условия" />}
                    </AntList.Item>
                  )}
                />
              </Descriptions.Item>
            ) : (
              <Descriptions.Item label="Записи о стаже">Отсутствуют</Descriptions.Item>
            )}
          </Descriptions>
        </>
      )}

      {pension_type === 'disability_social' && disability && (
        <>
          <Divider />
          <Descriptions bordered column={1} title={<><AuditOutlined style={{marginRight: 8}}/>Сведения об инвалидности</>}>
            <Descriptions.Item label="Группа">
              {disability.group === 'child' ? 'Ребенок-инвалид' : disability.group ? `${disability.group} группа` : 'Не указана'}
            </Descriptions.Item>
            <Descriptions.Item label="Дата установления">{disability.date || 'Не указана'}</Descriptions.Item>
            <Descriptions.Item label="Номер справки МСЭ">{disability.cert_number || 'Не указан'}</Descriptions.Item>
          </Descriptions>
        </>
      )}
      
      <Divider />
      <Descriptions bordered column={{ xxl: 2, xl: 2, lg: 1, md: 1, sm: 1, xs: 1 }} title={<><InfoCircleOutlined style={{marginRight: 8}}/>Дополнительная информация</>}>
        <Descriptions.Item label="Количество иждивенцев">
            {personal_data.dependents !== null && personal_data.dependents !== undefined ? personal_data.dependents : 'Не указано'}
        </Descriptions.Item>
        {pension_type === 'retirement_standard' && (
            <Descriptions.Item label="Пенсионные баллы (ИПК)">
                {pension_points !== null && pension_points !== undefined ? pension_points : 'Не указано'}
            </Descriptions.Item>
        )}
        {renderSimpleList(benefits, 'Льготы')}
        {renderSimpleList(submitted_documents, 'Представленные документы')}
        <Descriptions.Item label="Корректность оформления документов" span={2}>
          {has_incorrect_document ? 
            <Text type="danger"><WarningOutlined style={{marginRight: 4}} /> Указано наличие некорректно оформленных документов</Text> :
            <Text type="success"><CheckCircleOutlined style={{marginRight: 4}} /> Проблем не указано</Text>
          }
        </Descriptions.Item>
      </Descriptions>

      {other_documents_extracted_data && other_documents_extracted_data.length > 0 && (
        <>
          <Divider />
          <Title level={4} style={{marginBottom: 16}}><FileTextOutlined style={{marginRight: 8}} />Данные из загруженных дополнительных документов</Title>
          <Collapse accordion>
            {other_documents_extracted_data.map((docData: Partial<OtherDocumentData>, index: number) => (
              <Panel header={`Документ ${index + 1}: ${docData.standardized_document_type || "Тип не определен"}`} key={index.toString()}>
                {docData.extracted_fields && Object.keys(docData.extracted_fields).length > 0 ? (
                  <Descriptions bordered size="small" column={1}>
                    {Object.entries(docData.extracted_fields).map(([key, value]) => (
                      <Descriptions.Item label={key} key={key}>
                        {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                      </Descriptions.Item>
                    ))}
                  </Descriptions>
                ) : (
                  <Text italic>Дополнительные извлеченные данные по этому документу отсутствуют.</Text>
                )}
                {docData.multimodal_assessment && (
                    <Descriptions bordered size="small" column={1} style={{marginTop: 10}}>
                        <Descriptions.Item label="Мультимодальная оценка">{docData.multimodal_assessment}</Descriptions.Item>
                    </Descriptions>
                )}
                 {docData.text_llm_reasoning && (
                    <Descriptions bordered size="small" column={1} style={{marginTop: 10}}>
                        <Descriptions.Item label="Обоснование LLM (текст)">
                            <Paragraph copyable={{ tooltips: ['Копировать', 'Скопировано!'] }} style={{whiteSpace: "pre-wrap"}}>
                                {docData.text_llm_reasoning}
                            </Paragraph>
                        </Descriptions.Item>
                    </Descriptions>
                )}
              </Panel>
            ))}
          </Collapse>
        </>
      )}

      <Divider />
      <SummaryInsights formData={formData} onEditStep={onEditStep} />

      <Paragraph style={{ textAlign: 'center', fontWeight: 'bold', color: 'rgba(0, 0, 0, 0.65)' }}>
        Пожалуйста, проверьте все данные перед отправкой.
      </Paragraph>
    </Space>
  );
}

export default SummaryStep;