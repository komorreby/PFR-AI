import React from 'react';
import { Control, Controller, FieldErrors, UseFormRegister, UseFormWatch, UseFormSetValue } from 'react-hook-form';
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
    NumberInput,
    NumberInputField,
    NumberInputStepper,
    NumberIncrementStepper,
    NumberDecrementStepper,
    Divider,
    Checkbox
} from '@chakra-ui/react';
// Используем типы из центрального файла
import { CaseFormDataTypeForRHF, PersonalData, NameChangeInfo } from '../../types'; 
import CustomDateInput from '../formInputs/CustomDateInput';
import { formatDateForInput } from '../../utils';

// Список стран СНГ
const cisCountries = [
    "Россия", "Армения", "Азербайджан", "Беларусь", "Казахстан",
    "Кыргызстан", "Молдова", "Таджикистан", "Узбекистан"
];

// Уточняем тип для getErrorMessage для полей PersonalData
type PersonalDataFieldName = `personal_data.${keyof PersonalData}` | `personal_data.name_change_info.${keyof NameChangeInfo}` | `personal_data.${string}`;


interface PersonalDataStepProps {
    control: Control<CaseFormDataTypeForRHF>;
    register: UseFormRegister<CaseFormDataTypeForRHF>;
    // errors теперь типизируется более конкретно, если это поле из PersonalData
    errors: FieldErrors<CaseFormDataTypeForRHF['personal_data']>; 
    watch: UseFormWatch<CaseFormDataTypeForRHF>;
    setValue: UseFormSetValue<CaseFormDataTypeForRHF>;
    getErrorMessage: (name: PersonalDataFieldName) => string | undefined;
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
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
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

                {/* Гражданство */}
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

                {/* Иждивенцы */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.dependents') || !!errors?.dependents}>
                    <FormLabel htmlFor="personal_data.dependents">Количество иждивенцев</FormLabel>
                    <Controller
                        name="personal_data.dependents"
                        control={control}
                        defaultValue={0} // Установка defaultValue здесь
                        rules={{ 
                            min: { value: 0, message: "Должно быть не меньше 0"}
                        }}
                        render={({ field: { onChange, onBlur, value, ref } }) => ( // Явно деструктурируем field
                            <NumberInput 
                                id="personal_data.dependents" 
                                min={0}
                                value={value ?? ''} // Если value undefined/null, передаем '' в NumberInput
                                onChange={(_valueAsString, valueAsNumber) => onChange(isNaN(valueAsNumber) ? 0 : valueAsNumber)} // Передаем 0 если NaN
                                onBlur={onBlur}
                                bg="cardBackground"
                            >
                                <NumberInputField ref={ref} />
                                <NumberInputStepper><NumberIncrementStepper /><NumberDecrementStepper /></NumberInputStepper>
                            </NumberInput>
                        )}
                     />
                    <FormErrorMessage>{getErrorMessage('personal_data.dependents') || errors?.dependents?.message}</FormErrorMessage>
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