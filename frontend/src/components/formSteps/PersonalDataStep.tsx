import React, { useEffect } from 'react';
import { Control, Controller, FieldErrors, UseFormWatch, UseFormSetValue } from 'react-hook-form';
import { IMaskInput } from 'react-imask';
import dayjs from 'dayjs'; // Импортируем dayjs
import {
    Form,
    Input,
    Select,
    Checkbox,
    DatePicker as AntDatePicker, // Используем Ant Design DatePicker
    Row,
    Col,
    Typography,
    Divider as AntDivider, // Используем Ant Design Divider
    InputNumber,
} from 'antd';

import { CaseFormDataTypeForRHF, PersonalData as PersonalDataModel, NameChangeInfo as NameChangeInfoModel } from '../../types'; 
import CustomDateInput from '../formInputs/CustomDateInput'; // Этот компонент уже адаптирован
// import { formatDateForInput } from '../../utils'; // formatDateForInput не нужен, AntD DatePicker возвращает Dayjs объекты

const { Title } = Typography;
const { Option } = Select;

// Список стран СНГ
const cisCountries = [
    "Россия", "Армения", "Азербайджан", "Беларусь", "Казахстан",
    "Кыргызстан", "Молдова", "Таджикистан", "Узбекистан", "Другое"
];

interface PersonalDataStepProps {
    control: Control<CaseFormDataTypeForRHF>;
    watch: UseFormWatch<CaseFormDataTypeForRHF>;
    setValue: UseFormSetValue<CaseFormDataTypeForRHF>;
    form: any; // Экземпляр формы Ant Design для доступа к ошибкам, если потребуется нестандартная логика
    errors: FieldErrors<CaseFormDataTypeForRHF>; // Добавляем errors
    onValidationStateChange?: (isValid: boolean) => void; // Новый коллбэк
}

const PersonalDataStep: React.FC<PersonalDataStepProps> = ({ 
    control, watch, setValue, form, errors, onValidationStateChange
}) => {
    const nameChangeChecked = watch('personal_data.name_change_info_checkbox');

    useEffect(() => {
        if (onValidationStateChange) {
            const personalDataErrors = errors.personal_data || {};
            let isStepValid = Object.keys(personalDataErrors).length === 0;

            if (nameChangeChecked) {
                const nameInfoErrors = errors.personal_data?.name_change_info;
                if (nameInfoErrors && Object.keys(nameInfoErrors).length > 0) {
                    isStepValid = false;
                }
                // Дополнительная проверка на наличие значений, если RHF правила не покрывают это при динамическом отображении
                const nameInfoValues = watch('personal_data.name_change_info');
                if (!nameInfoValues?.old_full_name?.trim() || !nameInfoValues?.date_changed) {
                    // Если правила RHF (required: nameChangeChecked) не срабатывают до первого взаимодействия,
                    // эта проверка может быть нужна. Но обычно RHF должен это отловить.
                    // isStepValid = false; 
                }
            }
            onValidationStateChange(isStepValid);
        }
    }, [errors, nameChangeChecked, onValidationStateChange, watch]);
        
    const today = new Date();

    return (
        <div style={{ maxWidth: '700px', margin: '0 auto' }}>
            <Title level={4} style={{ marginBottom: '24px', textAlign: 'center' }}>Личные данные</Title>
            <Row gutter={[16, 0]}> {/* gutter: [horizontal, vertical] */}
                <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'last_name']}
                        label="Фамилия"
                        validateStatus={errors.personal_data?.last_name ? 'error' : ''}
                        help={errors.personal_data?.last_name?.message as string}
                    >
                        <Controller
                            name="personal_data.last_name"
                            control={control}
                            rules={{ required: "Фамилия обязательна" }}
                            render={({ field }) => <Input {...field} placeholder="Иванов" />}
                        />
                    </Form.Item>
                </Col>

                <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'first_name']}
                        label="Имя"
                        validateStatus={errors.personal_data?.first_name ? 'error' : ''}
                        help={errors.personal_data?.first_name?.message as string}
                    >
                        <Controller
                            name="personal_data.first_name"
                            control={control}
                            rules={{ required: "Имя обязательно" }}
                            render={({ field }) => <Input {...field} placeholder="Иван" />}
                        />
                    </Form.Item>
                </Col>

                <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'middle_name']}
                        label="Отчество (при наличии)"
                        validateStatus={errors.personal_data?.middle_name ? 'error' : ''}
                        help={errors.personal_data?.middle_name?.message as string}
                    >
                        <Controller
                            name="personal_data.middle_name"
                            control={control}
                            render={({ field }) => <Input {...field} placeholder="Иванович" value={field.value === null ? '' : field.value} />}
                        />
                    </Form.Item>
                </Col>

                <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'birth_date']}
                        label="Дата рождения"
                        validateStatus={errors.personal_data?.birth_date ? 'error' : ''}
                        help={errors.personal_data?.birth_date?.message as string}
                    >
                        <Controller
                            name="personal_data.birth_date"
                            control={control}
                            rules={{ required: "Дата рождения обязательна" }}
                            render={({ field }) => (
                                <AntDatePicker
                                    {...field}
                                    style={{ width: '100%' }}
                                    placeholder="ДД.ММ.ГГГГ"
                                    format="DD.MM.YYYY" // Формат отображения
                                    value={field.value && dayjs(field.value, 'YYYY-MM-DD').isValid() ? dayjs(field.value, 'YYYY-MM-DD') : null}
                                    onChange={(date) => {
                                        field.onChange(date ? date.format('YYYY-MM-DD') : null);
                                    }}
                                    disabledDate={(current) => current && current.valueOf() > today.valueOf()}
                                    showToday={false}
                                    inputReadOnly={true}
                                />
                            )}
                        />
                    </Form.Item>
                </Col>
                
                <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'snils']}
                        label="СНИЛС"
                        validateStatus={errors.personal_data?.snils ? 'error' : ''}
                        help={errors.personal_data?.snils?.message as string}
                    >
                        <Controller
                            name="personal_data.snils"
                            control={control}
                            rules={{
                                required: "СНИЛС обязателен",
                                pattern: {
                                    value: /^\d{3}-\d{3}-\d{3}\s\d{2}$/,
                                    message: "Неверный формат СНИЛС (XXX-XXX-XXX YY)"
                                }
                            }}
                            render={({ field: { onChange, onBlur, value, ref } }) => (
                                <IMaskInput
                                    mask="000-000-000 00"
                                    value={value || ''}
                                    onAccept={(acceptedValue: any) => onChange(acceptedValue)}
                                    placeholder="XXX-XXX-XXX XX"
                                    className="ant-input"
                                    inputRef={ref}
                                    onBlur={onBlur}
                                    overwrite={true}
                                />
                            )}
                        />
                    </Form.Item>
                </Col>

                <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'gender']}
                        label="Пол"
                        validateStatus={errors.personal_data?.gender ? 'error' : ''}
                        help={errors.personal_data?.gender?.message as string}
                    >
                        <Controller
                            name="personal_data.gender"
                            control={control}
                            rules={{ required: "Пол обязателен" }}
                            render={({ field }) => (
                                <Select {...field} placeholder="Выберите пол" style={{ width: '100%' }}>
                                    <Option value="male">Мужской</Option>
                                    <Option value="female">Женский</Option>
                                </Select>
                            )}
                        />
                    </Form.Item>
                </Col>
            </Row>

            <Form.Item
                name={['personal_data', 'birth_place']}
                label="Место рождения"
                validateStatus={errors.personal_data?.birth_place ? 'error' : ''}
                help={errors.personal_data?.birth_place?.message as string}
            >
                <Controller
                    name="personal_data.birth_place"
                    control={control}
                    render={({ field }) => <Input.TextArea {...field} placeholder="Например: г. Москва, Российская Федерация" value={field.value === null ? '' : field.value} />}
                />
            </Form.Item>
            
            <Row gutter={[16, 0]} style={{marginTop: '16px'}}>
                 <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'citizenship']}
                        label="Гражданство"
                        validateStatus={errors.personal_data?.citizenship ? 'error' : ''}
                        help={errors.personal_data?.citizenship?.message as string}
                    >
                        <Controller
                            name="personal_data.citizenship"
                            control={control}
                            rules={{ required: "Гражданство обязательно" }}
                            defaultValue="Россия" // TODO: Consider moving to useForm defaultValues
                            render={({ field }) => (
                                <Select {...field} placeholder="Выберите страну" style={{ width: '100%' }}>
                                    {cisCountries.map(country => (
                                        <Option key={country} value={country}>{country}</Option>
                                    ))}
                                </Select>
                            )}
                        />
                    </Form.Item>
                </Col>

                <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'passport_series']}
                        label="Серия паспорта"
                        validateStatus={errors.personal_data?.passport_series ? 'error' : ''}
                        help={errors.personal_data?.passport_series?.message as string}
                    >
                        <Controller
                            name="personal_data.passport_series"
                            control={control}
                            rules={{ pattern: {value: /^\d{4}$/, message: "Серия - 4 цифры"} }}
                            render={({ field: { onChange, onBlur, value, ref } }) => (
                                <IMaskInput
                                    mask="0000"
                                    value={value || ''}
                                    onAccept={(acceptedValue: any) => onChange(acceptedValue)}
                                    placeholder="XXXX"
                                    className="ant-input"
                                    inputRef={ref}
                                    onBlur={onBlur}
                                    overwrite={true}
                                />
                            )}
                        />
                    </Form.Item>
                </Col>

                <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'passport_number']}
                        label="Номер паспорта"
                        validateStatus={errors.personal_data?.passport_number ? 'error' : ''}
                        help={errors.personal_data?.passport_number?.message as string}
                    >
                        <Controller
                            name="personal_data.passport_number"
                            control={control}
                            rules={{ pattern: {value: /^\d{6}$/, message: "Номер - 6 цифр"} }}
                            render={({ field: { onChange, onBlur, value, ref } }) => (
                                <IMaskInput
                                    mask="000000"
                                    value={value || ''}
                                    onAccept={(acceptedValue: any) => onChange(acceptedValue)}
                                    placeholder="XXXXXX"
                                    className="ant-input"
                                    inputRef={ref}
                                    onBlur={onBlur}
                                    overwrite={true}
                                />
                            )}
                        />
                    </Form.Item>
                </Col>
            </Row>

            <Row gutter={[16, 0]} style={{marginTop: '16px'}}>
                 <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'issuing_authority']}
                        label="Кем выдан паспорт"
                        validateStatus={errors.personal_data?.issuing_authority ? 'error' : ''}
                        help={errors.personal_data?.issuing_authority?.message as string}
                    >
                        <Controller
                            name="personal_data.issuing_authority"
                            control={control}
                            render={({ field }) => <Input {...field} value={field.value === null ? '' : field.value} />}
                        />
                    </Form.Item>
                </Col>

                <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'passport_issue_date']}
                        label="Дата выдачи паспорта"
                        validateStatus={errors.personal_data?.passport_issue_date ? 'error' : ''}
                        help={errors.personal_data?.passport_issue_date?.message as string}
                    >
                         <Controller
                            name="personal_data.passport_issue_date"
                            control={control}
                            render={({ field }) => (
                                <AntDatePicker
                                    {...field}
                                    style={{ width: '100%' }}
                                    placeholder="ДД.ММ.ГГГГ"
                                    format="DD.MM.YYYY"
                                    value={field.value && dayjs(field.value, 'YYYY-MM-DD').isValid() ? dayjs(field.value, 'YYYY-MM-DD') : null}
                                    onChange={(date) => {
                                        field.onChange(date ? date.format('YYYY-MM-DD') : null);
                                    }}
                                    disabledDate={(current) => current && current.valueOf() > today.valueOf()}
                                    showToday={false}
                                    inputReadOnly={true} 
                                />
                            )}
                        />
                    </Form.Item>
                </Col>

                <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'department_code']}
                        label="Код подразделения"
                        validateStatus={errors.personal_data?.department_code ? 'error' : ''}
                        help={errors.personal_data?.department_code?.message as string}
                    >
                        <Controller
                            name="personal_data.department_code"
                            control={control}
                            rules={{ pattern: {value: /^\d{3}-\d{3}$/, message: "Код XXX-XXX"} }}
                            render={({ field: { onChange, onBlur, value, ref } }) => (
                                <IMaskInput
                                    mask="000-000"
                                    value={value || ''}
                                    onAccept={(acceptedValue: any) => onChange(acceptedValue)}
                                    placeholder="XXX-XXX"
                                    className="ant-input"
                                    inputRef={ref}
                                    onBlur={onBlur}
                                    overwrite={true}
                                />
                            )}
                        />
                    </Form.Item>
                </Col>
            </Row>

            <Row gutter={[16, 0]} style={{marginTop: '16px'}}>
                <Col xs={24} sm={12} md={8}>
                    <Form.Item
                        name={['personal_data', 'dependents']}
                        label="Количество иждивенцев"
                        validateStatus={errors.personal_data?.dependents ? 'error' : ''}
                        help={errors.personal_data?.dependents?.message as string}
                    >
                        <Controller
                            name="personal_data.dependents"
                            control={control}
                            rules={{
                                required: "Кол-во иждивенцев обязательно",
                                min: { value: 0, message: "Минимум 0 иждивенцев" }
                            }}
                            defaultValue={0} // TODO: Consider moving to useForm defaultValues
                            render={({ field }) => (
                                <InputNumber 
                                    {...field} 
                                    min={0} 
                                    style={{ width: '100%' }} 
                                    placeholder="0"
                                />
                            )}
                        />
                    </Form.Item>
                </Col>
            </Row>

            <AntDivider style={{ margin: '24px 0' }} />

            <Form.Item name={['personal_data', 'name_change_info_checkbox']} valuePropName="checked">
                 <Controller
                    name="personal_data.name_change_info_checkbox" 
                    control={control}
                    defaultValue={false} // TODO: Consider moving to useForm defaultValues
                    render={({ field: { value, onChange, ref }}) => (
                        <Checkbox
                            ref={ref}
                            checked={!!value} 
                            onChange={(e) => {
                                const isChecked = e.target.checked;
                                onChange(isChecked); 
                                setValue('personal_data.name_change_info', isChecked ? { old_full_name: '', date_changed: '' } : null, { shouldValidate: true });
                            }}
                        >
                            Была смена ФИО?
                        </Checkbox>
                    )}
                />
            </Form.Item>


            {nameChangeChecked && ( 
                <Row gutter={[16, 0]} style={{marginTop: '16px'}}>
                    <Col xs={24} md={12}>
                        <Form.Item
                            name={['personal_data', 'name_change_info', 'old_full_name']}
                            label="Предыдущее ФИО"
                            validateStatus={errors.personal_data?.name_change_info?.old_full_name ? 'error' : ''}
                            help={errors.personal_data?.name_change_info?.old_full_name?.message as string}
                        >
                            <Controller
                                name="personal_data.name_change_info.old_full_name"
                                control={control}
                                rules={{ required: nameChangeChecked ? "Предыдущее ФИО обязательно" : false }}
                                render={({ field: { onChange, onBlur, value, ref } }) => (
                                    <Input 
                                        onChange={onChange}
                                        onBlur={onBlur}
                                        value={value === null ? '' : value}
                                        ref={ref}
                                    />
                                )}
                            />
                        </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                        <Form.Item
                            name={['personal_data', 'name_change_info', 'date_changed']}
                            label="Дата смены ФИО"
                            validateStatus={errors.personal_data?.name_change_info?.date_changed ? 'error' : ''}
                            help={errors.personal_data?.name_change_info?.date_changed?.message as string}
                        >
                            <Controller
                                name="personal_data.name_change_info.date_changed"
                                control={control}
                                rules={{ required: nameChangeChecked ? "Дата смены обязательна" : false }}
                                render={({ field: { onChange, onBlur, value, ref } }) => (
                                    <AntDatePicker
                                        onChange={(date) => onChange(date ? date.format('YYYY-MM-DD') : null)}
                                        onBlur={onBlur}
                                        value={value && dayjs(value, 'YYYY-MM-DD').isValid() ? dayjs(value, 'YYYY-MM-DD') : null}
                                        ref={ref} 
                                        style={{ width: '100%' }}
                                        placeholder="ДД.ММ.ГГГГ"
                                        format="DD.MM.YYYY"
                                        disabledDate={(current) => current && current.valueOf() > today.valueOf()}
                                        showToday={false}
                                        inputReadOnly={true} 
                                    />
                                )}
                            />
                        </Form.Item>
                    </Col>
                </Row>
            )}
        </div>
    );
};

export default PersonalDataStep;