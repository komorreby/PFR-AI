import React from 'react';
import { Control, Controller, FieldErrors } from 'react-hook-form';
import { Form, Select, DatePicker, Typography, Input } from 'antd';
import { CaseFormDataTypeForRHF } from '../../types';
import dayjs from 'dayjs';

const { Title } = Typography;
const { Option } = Select;

interface DisabilityInfoStepProps {
  control: Control<CaseFormDataTypeForRHF>;
  errors: FieldErrors<CaseFormDataTypeForRHF>;
}

const disabilityGroups = [
    { id: '1', name: '1 группа' },
    { id: '2', name: '2 группа' },
    { id: '3', name: '3 группа' },
    { id: 'child', name: 'Ребенок-инвалид' },
];

const DisabilityInfoStep: React.FC<DisabilityInfoStepProps> = ({ control, errors }) => {
  return (
    <div style={{ maxWidth: '500px', margin: '0 auto' }}>
      <Title level={4} style={{ marginBottom: '24px', textAlign: 'center' }}>
        Сведения об инвалидности
      </Title>

      <Form.Item
        label="Группа инвалидности"
        name={['disability', 'group']}
        validateStatus={errors.disability?.group ? 'error' : ''}
        help={errors.disability?.group?.message as string | undefined}
      >
        <Controller
          name="disability.group"
          control={control}
          rules={{ required: 'Пожалуйста, выберите группу инвалидности!'}}
          render={({ field }) => (
            <Select {...field} placeholder="Выберите группу" style={{ width: '100%' }}>
              {disabilityGroups.map(group => (
                <Option key={group.id} value={group.id}>
                  {group.name}
                </Option>
              ))}
            </Select>
          )}
        />
      </Form.Item>

      <Form.Item
        label="Дата установления инвалидности"
        name={['disability', 'date']} 
        validateStatus={errors.disability?.date ? 'error' : ''}
        help={errors.disability?.date?.message as string | undefined}
      >
        <Controller
          name="disability.date"
          control={control}
          rules={{ required: 'Пожалуйста, укажите дату установления инвалидности!'}}
          render={({ field }) => (
            <DatePicker 
              {...field}
              style={{ width: '100%' }}
              placeholder="Выберите дату"
              format="DD.MM.YYYY"
              value={field.value ? dayjs(field.value, 'YYYY-MM-DD') : null}
              onChange={(date, _dateString) => {
                field.onChange(date ? date.format('YYYY-MM-DD') : null);
              }}
            />
          )}
        />
      </Form.Item>

      <Form.Item
        label="Номер справки МСЭ (БМСЭ) (необязательно)"
        name={['disability', 'cert_number']}
        validateStatus={errors.disability?.cert_number ? 'error' : ''}
        help={errors.disability?.cert_number?.message as string | undefined}
      >
        <Controller
            name="disability.cert_number"
            control={control}
            render={({field}) => (
                <Input 
                    {...field} 
                    value={field.value === null ? '' : field.value}
                    placeholder="Введите номер справки" 
                />
            )}
        />
      </Form.Item>
    </div>
  );
};

export default DisabilityInfoStep; 