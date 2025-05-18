import React from 'react';
import { Control, Controller, FieldErrors, UseFormRegister, UseFormWatch, UseFormSetValue } from 'react-hook-form';
import DatePicker from "react-datepicker";
import { parse } from 'date-fns';
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
import { CaseFormDataTypeForRHF, PersonalData, NameChangeInfo } from '../../types'; // Новый импорт
import CustomDateInput from '../formInputs/CustomDateInput';
import { formatDateForInput } from '../../utils';

// <<< Список стран СНГ
const cisCountries = [
    "Россия",
    "Армения",
    "Азербайджан",
    "Беларусь",
    "Казахстан",
    "Кыргызстан",
    "Молдова",
    "Таджикистан",
    "Узбекистан"
];

// Уточняем тип для getErrorMessage для полей PersonalData
type PersonalDataFieldName = `personal_data.${keyof PersonalData}` | `personal_data.name_change_info.${keyof NameChangeInfo}`;

interface PersonalDataStepProps {
    control: Control<CaseFormDataTypeForRHF>;
    register: UseFormRegister<CaseFormDataTypeForRHF>;
    errors: FieldErrors<PersonalData>;
    watch: UseFormWatch<CaseFormDataTypeForRHF>;
    setValue: UseFormSetValue<CaseFormDataTypeForRHF>;
    getErrorMessage: (name: PersonalDataFieldName) => string | undefined;
}

const PersonalDataStep: React.FC<PersonalDataStepProps> = ({ 
    control, register, errors, watch, setValue, getErrorMessage 
}) => {
    const watchHasNameChangeInfo = !!watch("personal_data.name_change_info");

    return (
        <VStack spacing={4} align="stretch">
            <Heading size="md" mb={4}>Личные данные</Heading>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                <FormControl isInvalid={!!getErrorMessage('personal_data.last_name') || !!errors.last_name}>
                    <FormLabel htmlFor="last_name">Фамилия</FormLabel>
                    <Input id="last_name" {...register("personal_data.last_name", { required: "Фамилия обязательна" })} />
                    <FormErrorMessage>{getErrorMessage('personal_data.last_name') || errors.last_name?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!getErrorMessage('personal_data.first_name') || !!errors.first_name}>
                    <FormLabel htmlFor="first_name">Имя</FormLabel>
                    <Input id="first_name" {...register("personal_data.first_name", { required: "Имя обязательно" })} />
                    <FormErrorMessage>{getErrorMessage('personal_data.first_name') || errors.first_name?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!getErrorMessage('personal_data.middle_name') || !!errors.middle_name}>
                    <FormLabel htmlFor="middle_name">Отчество (при наличии)</FormLabel>
                    <Input id="middle_name" {...register("personal_data.middle_name")} />
                    <FormErrorMessage>{getErrorMessage('personal_data.middle_name') || errors.middle_name?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!getErrorMessage('personal_data.birth_date') || !!errors.birth_date}>
                    <FormLabel htmlFor="birth_date">Дата рождения</FormLabel>
                    <Controller
                        name="personal_data.birth_date"
                        control={control}
                        rules={{ required: "Дата рождения обязательна" }}
                        render={({ field }) => (
                            <DatePicker
                                selected={field.value ? parse(field.value, 'yyyy-MM-dd', new Date()) : null}
                                onChange={(date: Date | null) => field.onChange(formatDateForInput(date))}
                                locale="ru"
                                showYearDropdown scrollableYearDropdown yearDropdownItemNumber={100}
                                maxDate={new Date()}
                                customInput={
                                    <CustomDateInput
                                        id={field.name}
                                        fieldOnChange={field.onChange}
                                        maxDate={new Date()}
                                    />
                                }
                                dateFormat="dd.MM.yyyy" placeholderText="ДД.ММ.ГГГГ" autoComplete="off" shouldCloseOnSelect={true}
                            />
                        )}
                    />
                    <FormErrorMessage>{getErrorMessage('personal_data.birth_date') || errors.birth_date?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!getErrorMessage('personal_data.snils') || !!errors.snils}>
                    <FormLabel htmlFor="snils">СНИЛС</FormLabel>
                    <Controller
                        name="personal_data.snils"
                        control={control}
                        rules={{ required: "СНИЛС обязателен", pattern: { value: /^\d{3}-\d{3}-\d{3} \d{2}$/, message: "Неверный формат СНИЛС (XXX-XXX-XXX YY)" } }}
                        render={({ field }) => (
                            <Input as={IMaskInput} mask="000-000-000 00" value={field.value || ''} onAccept={(value: string) => field.onChange(value)} placeholder="XXX-XXX-XXX XX" id="snils" bg="white" borderColor="inherit" _hover={{ borderColor: "gray.300" }} _focus={{ zIndex: 1, borderColor: "primary", boxShadow: `0 0 0 1px var(--chakra-colors-primary)` }} />
                        )}
                    />
                    <FormErrorMessage>{getErrorMessage('personal_data.snils') || errors.snils?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!getErrorMessage('personal_data.gender') || !!errors.gender}>
                    <FormLabel htmlFor="gender">Пол</FormLabel>
                    <Select id="gender" placeholder="Выберите пол" {...register("personal_data.gender", { required: "Пол обязателен" })}>
                        <option value="male">Мужской</option>
                        <option value="female">Женский</option>
                    </Select>
                    <FormErrorMessage>{getErrorMessage('personal_data.gender') || errors.gender?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!getErrorMessage('personal_data.citizenship') || !!errors.citizenship}>
                    <FormLabel htmlFor="citizenship">Гражданство</FormLabel>
                    <Select
                        id="citizenship"
                        placeholder="Выберите страну"
                        {...register("personal_data.citizenship", { required: "Гражданство обязательно" })}
                    >
                        {cisCountries.map(country => (
                            <option key={country} value={country}>{country}</option>
                        ))}
                    </Select>
                    <FormErrorMessage>{getErrorMessage('personal_data.citizenship') || errors.citizenship?.message}</FormErrorMessage>
                </FormControl>

                <FormControl isInvalid={!!getErrorMessage('personal_data.dependents') || !!errors.dependents}>
                    <FormLabel htmlFor="dependents">Количество иждивенцев</FormLabel>
                    <Controller
                        name="personal_data.dependents"
                        control={control}
                        rules={{ min: { value: 0, message: "Должно быть не меньше 0"} }}
                        render={({ field }) => (
                            <NumberInput 
                                id="dependents" 
                                min={0} 
                                defaultValue={0} 
                                value={field.value === undefined || field.value === null ? '' : String(field.value)}
                                onChange={(_valueAsString, valueAsNumber) => field.onChange(valueAsNumber)}
                                onBlur={field.onBlur}
                            >
                                <NumberInputField ref={field.ref} />
                                <NumberInputStepper><NumberIncrementStepper /><NumberDecrementStepper /></NumberInputStepper>
                            </NumberInput>
                        )}
                     />
                    <FormErrorMessage>{getErrorMessage('personal_data.dependents') || errors.dependents?.message}</FormErrorMessage>
                </FormControl>
            </SimpleGrid>

            <Divider my={4} />

            <Checkbox
                isChecked={watchHasNameChangeInfo}
                onChange={(e) => {
                    setValue('personal_data.name_change_info', e.target.checked ? { old_full_name: '', date_changed: '' } : null, { shouldValidate: false });
                }}
            >
                Была смена ФИО?
            </Checkbox>

            {watchHasNameChangeInfo && (
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} mt={4}>
                    <FormControl isInvalid={!!getErrorMessage('personal_data.name_change_info.old_full_name') || !!errors.name_change_info?.old_full_name}>
                        <FormLabel htmlFor="old_full_name">Предыдущее ФИО</FormLabel>
                        <Input id="old_full_name" {...register("personal_data.name_change_info.old_full_name", { required: watchHasNameChangeInfo ? "Предыдущее ФИО обязательно" : false })} />
                        <FormErrorMessage>{getErrorMessage('personal_data.name_change_info.old_full_name') || errors.name_change_info?.old_full_name?.message}</FormErrorMessage>
                    </FormControl>

                    <FormControl isInvalid={!!getErrorMessage('personal_data.name_change_info.date_changed') || !!errors.name_change_info?.date_changed}>
                        <FormLabel htmlFor="date_changed">Дата смены ФИО</FormLabel>
                        <Controller
                            name="personal_data.name_change_info.date_changed"
                            control={control}
                            rules={{ required: watchHasNameChangeInfo ? "Дата смены обязательна" : false }}
                            render={({ field }) => (
                                <DatePicker
                                    selected={field.value ? parse(field.value, 'yyyy-MM-dd', new Date()) : null}
                                    onChange={(date: Date | null) => field.onChange(formatDateForInput(date))}
                                    locale="ru"
                                    showYearDropdown scrollableYearDropdown yearDropdownItemNumber={100}
                                    maxDate={new Date()}
                                    customInput={
                                        <CustomDateInput
                                            id={field.name}
                                            fieldOnChange={field.onChange}
                                            maxDate={new Date()}
                                        />
                                    }
                                    dateFormat="dd.MM.yyyy" placeholderText="ДД.ММ.ГГГГ" autoComplete="off" shouldCloseOnSelect={true}
                                />
                            )}
                        />
                        <FormErrorMessage>{getErrorMessage('personal_data.name_change_info.date_changed') || errors.name_change_info?.date_changed?.message}</FormErrorMessage>
                    </FormControl>
                </SimpleGrid>
            )}
        </VStack>
    );
};

export default PersonalDataStep; 