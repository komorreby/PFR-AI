import React from 'react';
import { Control, Controller, FieldErrors, UseFormRegister, UseFormWatch, UseFormSetValue, FieldPath } from 'react-hook-form';
import DatePicker from "react-datepicker";
import { parse, isValid } from 'date-fns'; // format здесь не нужен, если formatDateForInput используется
import { IMaskInput } from 'react-imask';
import {
    VStack,
    Heading,
    SimpleGrid,
    FormControl,
    FormLabel,
    Input,
    FormErrorMessage,
    Select,
    NumberInput, // Оставим, т.к. может быть нужен в других частях или после рефакторинга
    NumberInputField,
    NumberInputStepper,
    NumberIncrementStepper,
    NumberDecrementStepper,
    Divider,
    Checkbox,
    Textarea
} from '@chakra-ui/react';
// Используем типы из центрального файла
import { CaseFormDataTypeForRHF, PersonalData as PersonalDataModel, NameChangeInfo as NameChangeInfoModel } from '../../types'; 
import CustomDateInput from '../formInputs/CustomDateInput';
import { formatDateForInput } from '../../utils';

// Список стран СНГ
const cisCountries = [
    "Россия", "Армения", "Азербайджан", "Беларусь", "Казахстан",
    "Кыргызстан", "Молдова", "Таджикистан", "Узбекистан", "Другое"
];

// Обновляем тип для getErrorMessage, используя PersonalDataModel и NameChangeInfoModel для большей точности
type PersonalDataStepFieldName = 
  | `personal_data.${keyof Omit<PersonalDataModel, 'name_change_info' | 'dependents'>}` 
  | `personal_data.name_change_info.${keyof NameChangeInfoModel}`;


interface PersonalDataStepProps {
    control: Control<CaseFormDataTypeForRHF>;
    register: UseFormRegister<CaseFormDataTypeForRHF>;
    errors: FieldErrors<CaseFormDataTypeForRHF['personal_data']>;
    watch: UseFormWatch<CaseFormDataTypeForRHF>;
    setValue: UseFormSetValue<CaseFormDataTypeForRHF>;
    getErrorMessage: (name: PersonalDataStepFieldName) => string | undefined;
}

const PersonalDataStep: React.FC<PersonalDataStepProps> = ({ 
    control, register, errors, watch, setValue, getErrorMessage 
}) => {
    // watchHasNameChangeInfo теперь смотрит на personal_data.name_change_info
    // !! приведение к boolean, если name_change_info может быть null/undefined
    const watchHasNameChangeInfo = !!watch("personal_data.name_change_info");

    return (
        <VStack spacing={4} align="stretch">
            <Heading size="md" mb={4}>Личные данные</Heading>
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
                {/* Фамилия */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.last_name') || !!errors?.last_name}>
                    <FormLabel htmlFor="personal_data.last_name">Фамилия</FormLabel>
                    <Input id="personal_data.last_name" {...register("personal_data.last_name", { required: "Фамилия обязательна" })} />
                    <FormErrorMessage>{getErrorMessage('personal_data.last_name') || errors?.last_name?.message}</FormErrorMessage>
                </FormControl>

                {/* Имя */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.first_name') || !!errors?.first_name}>
                    <FormLabel htmlFor="personal_data.first_name">Имя</FormLabel>
                    <Input id="personal_data.first_name" {...register("personal_data.first_name", { required: "Имя обязательно" })} />
                    <FormErrorMessage>{getErrorMessage('personal_data.first_name') || errors?.first_name?.message}</FormErrorMessage>
                </FormControl>

                {/* Отчество */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.middle_name') || !!errors?.middle_name}>
                    <FormLabel htmlFor="personal_data.middle_name">Отчество (при наличии)</FormLabel>
                    <Input id="personal_data.middle_name" {...register("personal_data.middle_name")} />
                    <FormErrorMessage>{getErrorMessage('personal_data.middle_name') || errors?.middle_name?.message}</FormErrorMessage>
                </FormControl>

                {/* Дата рождения */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.birth_date') || !!errors?.birth_date}>
                    <FormLabel htmlFor="personal_data.birth_date">Дата рождения</FormLabel>
                    <Controller
                        name="personal_data.birth_date"
                        control={control}
                        rules={{ required: "Дата рождения обязательна" }}
                        render={({ field }) => (
                            <DatePicker
                                selected={field.value && isValid(parse(field.value, 'yyyy-MM-dd', new Date())) ? parse(field.value, 'yyyy-MM-dd', new Date()) : null}
                                onChange={(date: Date | null) => field.onChange(formatDateForInput(date))}
                                customInput={
                                    <CustomDateInput
                                        id={field.name} // field.name будет "personal_data.birth_date"
                                        fieldOnChange={field.onChange} // CustomDateInput вернет 'yyyy-MM-dd'
                                        maxDate={new Date()}
                                    />
                                }
                                locale="ru"
                                showYearDropdown scrollableYearDropdown yearDropdownItemNumber={100}
                                maxDate={new Date()}
                                dateFormat="dd.MM.yyyy" 
                                placeholderText="ДД.ММ.ГГГГ" 
                                autoComplete="off" 
                                shouldCloseOnSelect={true}
                            />
                        )}
                    />
                    <FormErrorMessage>{getErrorMessage('personal_data.birth_date') || errors?.birth_date?.message}</FormErrorMessage>
                </FormControl>

                {/* СНИЛС */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.snils') || !!errors?.snils}>
                    <FormLabel htmlFor="personal_data.snils">СНИЛС</FormLabel>
                    <Controller
                        name="personal_data.snils"
                        control={control}
                        rules={{ 
                            required: "СНИЛС обязателен", 
                            pattern: { 
                                value: /^\d{3}-\d{3}-\d{3}\s\d{2}$/,  // Пробел теперь \s
                                message: "Неверный формат СНИЛС (XXX-XXX-XXX YY)" 
                            } 
                        }}
                        render={({ field }) => (
                            <Input 
                                as={IMaskInput} 
                                mask="000-000-000 00" 
                                value={field.value || ''} 
                                onAccept={(value: string) => field.onChange(value)} 
                                placeholder="XXX-XXX-XXX XX" 
                                id="personal_data.snils" // Соответствует field.name
                                bg="cardBackground" // Используем семантический токен
                                borderColor="inherit" 
                                _hover={{ borderColor: "gray.300" }} 
                                _focus={{ zIndex: 1, borderColor: "primary", boxShadow: `0 0 0 1px var(--chakra-colors-primary)` }} 
                            />
                        )}
                    />
                    <FormErrorMessage>{getErrorMessage('personal_data.snils') || errors?.snils?.message}</FormErrorMessage>
                </FormControl>

                {/* Пол */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.gender') || !!errors?.gender}>
                    <FormLabel htmlFor="personal_data.gender">Пол</FormLabel>
                    <Select 
                        id="personal_data.gender" 
                        placeholder="Выберите пол" 
                        {...register("personal_data.gender", { required: "Пол обязателен" })}
                        bg="cardBackground"
                    >
                        <option value="male">Мужской</option>
                        <option value="female">Женский</option>
                    </Select>
                    <FormErrorMessage>{getErrorMessage('personal_data.gender') || errors?.gender?.message}</FormErrorMessage>
                </FormControl>
            </SimpleGrid>

            <FormControl isInvalid={!!getErrorMessage('personal_data.birth_place') || !!errors?.birth_place}>
                <FormLabel htmlFor="personal_data.birth_place">Место рождения</FormLabel>
                <Textarea id="personal_data.birth_place" {...register("personal_data.birth_place")} placeholder="Например: г. Москва, Российская Федерация" />
                <FormErrorMessage>{getErrorMessage('personal_data.birth_place') || errors?.birth_place?.message}</FormErrorMessage>
            </FormControl>
            
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mt={4}>
                 <FormControl isInvalid={!!getErrorMessage('personal_data.citizenship') || !!errors?.citizenship}>
                    <FormLabel htmlFor="personal_data.citizenship">Гражданство</FormLabel>
                    <Select
                        id="personal_data.citizenship"
                        placeholder="Выберите страну"
                        {...register("personal_data.citizenship", { required: "Гражданство обязательно" })}
                        bg="cardBackground"
                    >
                        {cisCountries.map(country => (
                            <option key={country} value={country}>{country}</option>
                        ))}
                    </Select>
                    <FormErrorMessage>{getErrorMessage('personal_data.citizenship') || errors?.citizenship?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!getErrorMessage('personal_data.passport_series') || !!errors?.passport_series}>
                    <FormLabel htmlFor="personal_data.passport_series">Серия паспорта</FormLabel>
                    <Input id="personal_data.passport_series" {...register("personal_data.passport_series")} placeholder="XXXX"/>
                    <FormErrorMessage>{getErrorMessage('personal_data.passport_series') || errors?.passport_series?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!getErrorMessage('personal_data.passport_number') || !!errors?.passport_number}>
                    <FormLabel htmlFor="personal_data.passport_number">Номер паспорта</FormLabel>
                    <Input id="personal_data.passport_number" {...register("personal_data.passport_number")} placeholder="XXXXXX"/>
                    <FormErrorMessage>{getErrorMessage('personal_data.passport_number') || errors?.passport_number?.message}</FormErrorMessage>
                </FormControl>
            </SimpleGrid>

            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mt={4}>
                 <FormControl isInvalid={!!getErrorMessage('personal_data.issuing_authority') || !!errors?.issuing_authority}>
                    <FormLabel htmlFor="personal_data.issuing_authority">Кем выдан паспорт</FormLabel>
                    <Input id="personal_data.issuing_authority" {...register("personal_data.issuing_authority")} />
                    <FormErrorMessage>{getErrorMessage('personal_data.issuing_authority') || errors?.issuing_authority?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!getErrorMessage('personal_data.issue_date') || !!errors?.issue_date}>
                    <FormLabel htmlFor="personal_data.issue_date">Дата выдачи паспорта</FormLabel>
                     <Controller
                        name="personal_data.issue_date"
                        control={control}
                        render={({ field }) => (
                            <DatePicker
                                selected={field.value && isValid(parse(field.value, 'yyyy-MM-dd', new Date())) ? parse(field.value, 'yyyy-MM-dd', new Date()) : null}
                                onChange={(date: Date | null) => field.onChange(formatDateForInput(date))}
                                customInput={<CustomDateInput id={field.name} fieldOnChange={field.onChange} maxDate={new Date()} />}
                                locale="ru" showYearDropdown scrollableYearDropdown yearDropdownItemNumber={100}
                                maxDate={new Date()} dateFormat="dd.MM.yyyy" placeholderText="ДД.ММ.ГГГГ"
                                autoComplete="off" shouldCloseOnSelect={true}
                            />
                        )}
                    />
                    <FormErrorMessage>{getErrorMessage('personal_data.issue_date') || errors?.issue_date?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!getErrorMessage('personal_data.department_code') || !!errors?.department_code}>
                    <FormLabel htmlFor="personal_data.department_code">Код подразделения</FormLabel>
                    <Input id="personal_data.department_code" {...register("personal_data.department_code")} placeholder="XXX-XXX"/>
                    <FormErrorMessage>{getErrorMessage('personal_data.department_code') || errors?.department_code?.message}</FormErrorMessage>
                </FormControl>
            </SimpleGrid>

            <Divider my={4} />

            <Checkbox
                isChecked={watchHasNameChangeInfo}
                onChange={(e) => {
                    setValue('personal_data.name_change_info', e.target.checked ? { old_full_name: '', date_changed: '' } : null, { shouldValidate: false });
                }}
                id="hasNameChangeInfoCheckbox" // Добавил id для лучшей практики
            >
                Была смена ФИО?
            </Checkbox>

            {watchHasNameChangeInfo && (
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} mt={4}>
                    <FormControl isInvalid={!!getErrorMessage('personal_data.name_change_info.old_full_name') || !!errors?.name_change_info?.old_full_name}>
                        <FormLabel htmlFor="personal_data.name_change_info.old_full_name">Предыдущее ФИО</FormLabel>
                        <Input 
                            id="personal_data.name_change_info.old_full_name" 
                            {...register("personal_data.name_change_info.old_full_name", { 
                                required: watchHasNameChangeInfo ? "Предыдущее ФИО обязательно" : false 
                            })} 
                        />
                        <FormErrorMessage>{getErrorMessage('personal_data.name_change_info.old_full_name') || errors?.name_change_info?.old_full_name?.message}</FormErrorMessage>
                    </FormControl>

                    <FormControl isInvalid={!!getErrorMessage('personal_data.name_change_info.date_changed') || !!errors?.name_change_info?.date_changed}>
                        <FormLabel htmlFor="personal_data.name_change_info.date_changed">Дата смены ФИО</FormLabel>
                        <Controller
                            name="personal_data.name_change_info.date_changed"
                            control={control}
                            rules={{ required: watchHasNameChangeInfo ? "Дата смены обязательна" : false }}
                            render={({ field }) => (
                                <DatePicker
                                    selected={field.value && isValid(parse(field.value, 'yyyy-MM-dd', new Date())) ? parse(field.value, 'yyyy-MM-dd', new Date()) : null}
                                    onChange={(date: Date | null) => field.onChange(formatDateForInput(date))}
                                    customInput={
                                        <CustomDateInput
                                            id={field.name}
                                            fieldOnChange={field.onChange}
                                            maxDate={new Date()}
                                        />
                                    }
                                    locale="ru"
                                    showYearDropdown scrollableYearDropdown yearDropdownItemNumber={100}
                                    maxDate={new Date()}
                                    dateFormat="dd.MM.yyyy" 
                                    placeholderText="ДД.ММ.ГГГГ" 
                                    autoComplete="off" 
                                    shouldCloseOnSelect={true}
                                />
                            )}
                        />
                        <FormErrorMessage>{getErrorMessage('personal_data.name_change_info.date_changed') || errors?.name_change_info?.date_changed?.message}</FormErrorMessage>
                    </FormControl>
                </SimpleGrid>
            )}
        </VStack>
    );
};

export default PersonalDataStep;