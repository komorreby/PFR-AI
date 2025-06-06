import React from 'react';
import { Control, Controller, FieldErrors, UseFormRegister, UseFormGetValues, UseFieldArrayAppend, UseFieldArrayRemove, FieldArrayWithId } from 'react-hook-form';
import dayjs from 'dayjs';
import {
    Form,
    Input,
    InputNumber,
    DatePicker as AntDatePicker,
    Checkbox,
    Button,
    Row,
    Col,
    Typography,
    Divider as AntDivider,
    Space,
    Card
} from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { CaseFormDataTypeForRHF, WorkBookRecordEntry } from '../../types';

const { Title, Text } = Typography;

interface WorkExperienceStepProps {
    control: Control<CaseFormDataTypeForRHF>;
    errors: FieldErrors<CaseFormDataTypeForRHF>;
    fields: FieldArrayWithId<CaseFormDataTypeForRHF, "work_experience.records", "id">[];
    append: UseFieldArrayAppend<CaseFormDataTypeForRHF, "work_experience.records">;
    remove: UseFieldArrayRemove;
    getValues: UseFormGetValues<CaseFormDataTypeForRHF>;
    form: any;
}

const WorkExperienceStep: React.FC<WorkExperienceStepProps> = ({ 
    control, fields, append, remove, getValues, form
}) => {
    const today = new Date();

    return (
        <div style={{ maxWidth: '700px', margin: '0 auto' }}>
            <Title level={4} style={{ marginBottom: '24px', textAlign: 'center' }}>Трудовой стаж</Title>
            <Form.Item
                label="Общий подтвержденный стаж (лет)"
                name={["work_experience", "total_years"]}
                rules={[
                    { required: true, message: "Общий стаж обязателен" },
                    { type: 'number', min: 0, message: "Стаж не может быть отрицательным" },
                ]}
            >
                <Controller
                    name="work_experience.total_years"
                    control={control}
                    render={({ field }) => (
                        <InputNumber 
                            {...field}
                            min={0} 
                            precision={1} 
                            step={0.5}
                            style={{ width: '100%' }}
                            onChange={(value) => field.onChange(value)}
                        />
                    )}
                />
            </Form.Item>

            <AntDivider style={{ margin: '24px 0' }}/>
            <Title level={5} style={{ marginBottom: '16px' }}>Записи о трудовой деятельности</Title>

            {fields.map((item, index) => (
                <Card key={item.id} style={{ marginBottom: '16px' }} bodyStyle={{padding: '16px'}}>
                    <Title level={5} style={{marginTop: 0, marginBottom: '12px'}}>
                        Место работы #{index + 1}
                        <Button 
                            type="text" 
                            danger 
                            icon={<DeleteOutlined />} 
                            onClick={() => remove(index)} 
                            style={{ float: 'right'}}
                            size="small"
                        />
                    </Title>
                    <Row gutter={[16,0]}>
                        <Col xs={24} md={12}>
                            <Form.Item
                                label="Организация"
                                name={[`work_experience`, `records`, index, `organization`]}
                                rules={[{ required: true, message: "Организация обязательна" }]}
                            >
                                <Controller
                                    name={`work_experience.records.${index}.organization` as const}
                                    control={control}
                                    render={({ field }) => <Input {...field} value={field.value ?? ''} />}
                                />
                            </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                            <Form.Item
                                label="Должность"
                                name={[`work_experience`, `records`, index, `position`]}
                                rules={[{ required: true, message: "Должность обязательна" }]}
                            >
                                <Controller
                                    name={`work_experience.records.${index}.position` as const}
                                    control={control}
                                    render={({ field }) => <Input {...field} value={field.value ?? ''} />}
                                />
                            </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                            <Form.Item
                                label="Дата начала"
                                name={[`work_experience`, `records`, index, `date_in`]}
                                rules={[{ required: true, message: "Дата начала обязательна" }]}
                            >
                                <Controller
                                    name={`work_experience.records.${index}.date_in` as const}
                                    control={control}
                                    render={({ field }) => (
                                        <AntDatePicker
                                            {...field}
                                            style={{ width: '100%' }}
                                            placeholder="ДД.ММ.ГГГГ"
                                            format="DD.MM.YYYY"
                                            value={field.value && dayjs(field.value, 'YYYY-MM-DD').isValid() ? dayjs(field.value, 'YYYY-MM-DD') : null}
                                            onChange={(date) => field.onChange(date ? date.format('YYYY-MM-DD') : null)}
                                            disabledDate={(current) => current && current.valueOf() > today.valueOf()}
                                            showToday={false}
                                        />
                                    )}
                                />
                            </Form.Item>
                        </Col>
                        <Col xs={24} md={12}>
                            <Form.Item
                                label="Дата окончания"
                                name={[`work_experience`, `records`, index, `date_out`]}
                                rules={[
                                    { required: true, message: "Дата окончания обязательна" },
                                    {
                                        validator: async (_, value) => {
                                            const startDateStr = getValues(`work_experience.records.${index}.date_in`);
                                            if (startDateStr && value) {
                                                const startDate = dayjs(startDateStr, 'YYYY-MM-DD');
                                                const endDate = dayjs(value, 'YYYY-MM-DD');
                                                if (startDate.isValid() && endDate.isValid() && endDate.isBefore(startDate)) {
                                                    return Promise.reject(new Error("Дата окончания не может быть раньше даты начала"));
                                                }
                                            }
                                            return Promise.resolve();
                                        }
                                    }
                                ]}
                            >
                                <Controller
                                    name={`work_experience.records.${index}.date_out` as const}
                                    control={control}
                                    render={({ field }) => (
                                        <AntDatePicker
                                            {...field}
                                            style={{ width: '100%' }}
                                            placeholder="ДД.ММ.ГГГГ"
                                            format="DD.MM.YYYY"
                                            value={field.value && dayjs(field.value, 'YYYY-MM-DD').isValid() ? dayjs(field.value, 'YYYY-MM-DD') : null}
                                            onChange={(date) => field.onChange(date ? date.format('YYYY-MM-DD') : null)}
                                            disabledDate={(current) => {
                                                const startDateStr = getValues(`work_experience.records.${index}.date_in`);
                                                const startDate = startDateStr && dayjs(startDateStr, 'YYYY-MM-DD').isValid() 
                                                                  ? dayjs(startDateStr, 'YYYY-MM-DD') 
                                                                  : null;
                                                if (startDate && current && current.valueOf() < startDate.valueOf()) return true;
                                                return current && current.valueOf() > today.valueOf();
                                            }}
                                            showToday={false}
                                        />
                                    )}
                                />
                            </Form.Item>
                        </Col>
                    </Row>
                    <Form.Item 
                        name={[`work_experience`, `records`, index, `special_conditions`]} 
                        valuePropName="checked"
                        style={{marginBottom: 0, marginTop: '8px'}}
                    >
                        <Controller
                             name={`work_experience.records.${index}.special_conditions` as const}
                             control={control}
                             defaultValue={false}
                             render={({ field }) => (
                                <Checkbox {...field} checked={!!field.value}>
                                    Особые условия труда
                                </Checkbox>
                             )}
                        />
                    </Form.Item>
                </Card>
            ))}

            <Button
                type="dashed"
                onClick={() => append({ organization: '', position: '', date_in: null, date_out: null, special_conditions: false })}
                icon={<PlusOutlined />}
                style={{ width: '100%', marginTop: fields.length > 0 ? '0px' : '16px'}}
            >
               Добавить место работы
            </Button>
        </div>
    );
};

export default WorkExperienceStep; 