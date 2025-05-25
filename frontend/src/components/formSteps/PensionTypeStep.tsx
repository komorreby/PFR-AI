// src/components/caseFormSteps/PensionTypeStep.tsx
import React from 'react';
// import { Form, Select, Spin, Alert, Typography, Empty } from 'antd'; // Старый импорт
import { Form, Spin, Alert, Typography, Empty, Card, Row, Col } from 'antd'; // Новый импорт с Card, Row, Col
import type { FormInstance } from 'antd/es/form';
import type { CaseDataInput, PensionTypeInfo } from '../../types';

const { Paragraph, Text } = Typography;

interface PensionTypeStepProps {
  form: FormInstance<CaseDataInput>; // Экземпляр формы Ant Design
  pensionTypes: PensionTypeInfo[];
  loadingPensionTypes: boolean;
  // Добавим пропсы для RHF, если они понадобятся для обновления значения
  // или если управление значением будет через Controller RHF прямо здесь.
  // Пока что предполагаем, что HomePage следит за полем 'pension_type' в форме AntD.
  // Если мы будем использовать Controller от RHF, то form и Form.Item будут не нужны.
  // Для данного изменения, будем считать, что HomePage продолжает следить за полем формы AntD.
  // Позже можно будет рефакторить на полный контроль через RHF.
  currentValue?: string; // Текущее выбранное значение для подсветки карточки
  onChange?: (value: string) => void; // Функция для обновления значения в форме
}

const PensionTypeStep: React.FC<PensionTypeStepProps> = ({
  form, // form все еще нужен, если HomePage использует Form.useWatch('pension_type', form)
  pensionTypes,
  loadingPensionTypes,
  currentValue, // Текущее выбранное значение для подсветки
  onChange,     // Функция для установки значения
}) => {
  if (loadingPensionTypes) {
    return (
      <div style={{ textAlign: 'center', padding: '30px' }}>
        <Spin tip="Загрузка типов пенсий..." />
      </div>
    );
  }

  if (!loadingPensionTypes && pensionTypes.length === 0) {
    return <Empty description="Типы пенсий не найдены или не загружены." />;
  }

  const handleCardClick = (pensionTypeId: string) => {
    if (onChange) {
      onChange(pensionTypeId);
    }
    // Если HomePage следит за FormInstance AntD, то это должно обновить значение
    // form.setFieldsValue({ pension_type: pensionTypeId });
    // Однако, если используется RHF Controller в HomePage для этого поля,
    // то onChange должен вызывать field.onChange от RHF.
    // На данном этапе, мы передаем onChange и currentValue из HomePage,
    // который будет обернут в RHF Controller.
  };

  return (
    <>
      <Paragraph style={{ marginBottom: '20px', textAlign: 'center' }}>
        Пожалуйста, выберите тип пенсии, на назначение которой подается заявление.
        От выбранного типа будет зависеть дальнейший набор шагов и необходимых документов.
      </Paragraph>
      {/* Form.Item все еще нужен, чтобы RHF Controller в HomePage мог корректно работать с полем pension_type */}
      <Form.Item
        // name="pension_type" // Имя уже будет в Controller в HomePage
        // label="Тип назначаемой пенсии" // Можно убрать, т.к. заголовок карточек будет служить лейблом
        rules={[{ required: true, message: 'Пожалуйста, выберите тип пенсии!' }]}
        // help="Выберите один из доступных вариантов."
      >
        <Row gutter={[16, 16]}>
          {pensionTypes.map((pt) => (
            <Col xs={24} sm={12} md={8} key={pt.id}>
              <Card
                hoverable
                onClick={() => handleCardClick(pt.id)}
                style={{
                  height: '100%',
                  border: currentValue === pt.id ? '2px solid #1890ff' : '1px solid #d9d9d9',
                  boxShadow: currentValue === pt.id ? '0 0 0 2px rgba(24, 144, 255, 0.2)' : 'none'
                }}
                bodyStyle={{ padding: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' }}
              >
                <div>
                  <Text strong style={{ display: 'block', marginBottom: '8px', fontSize: '1.1em' }}>{pt.display_name}</Text>
                  <Paragraph type="secondary" style={{ fontSize: '0.9em', marginBottom: 0, flexGrow: 1 }}>
                    {pt.description}
                  </Paragraph>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      </Form.Item>
      {/* 
        Информация о выбранном типе пенсии (описание) может отображаться здесь, 
        если получать значение из form.getFieldValue('pension_type') или через Form.useWatch в этом компоненте,
        или же это можно оставить на усмотрение HomePage, если она уже как-то отображает эту информацию.
        Пример:
        const currentPensionTypeId = Form.useWatch('pension_type', form);
        const selectedTypeInfo = pensionTypes.find(pt => pt.id === currentPensionTypeId);
        ... и затем отобразить selectedTypeInfo.description ...
      */}
    </>
  );
};

export default PensionTypeStep;