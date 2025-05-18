import React from 'react';
import { Control, Controller, FieldErrors, UseFormRegister, UseFormWatch, UseFormSetValue } from 'react-hook-form';
import DatePicker from "react-datepicker";
import { parse, isValid, format } from 'date-fns';
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
import { CaseFormDataType } from '../CaseForm'; // Импортируем основной тип
import CustomDateInput from '../formInputs/CustomDateInput'; // Импортируем кастомный инпут
import { formatDateForInput } from '../../utils'; // <--- Исправляем путь

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

interface PersonalDataStepProps {
    control: Control<CaseFormDataType>;
    register: UseFormRegister<CaseFormDataType>;
    errors: FieldErrors<CaseFormDataType>;
    watch: UseFormWatch<CaseFormDataType>;
    setValue: UseFormSetValue<CaseFormDataType>;
    getErrorMessage: (name: string) => string | undefined;
}

const PersonalDataStep: React.FC<PersonalDataStepProps> = ({ 
    control, register, watch, setValue, getErrorMessage 
}) => {
    const watchHasNameChangeInfo = watch("personal_data.name_change_info");

    return (
        <VStack spacing={4} align="stretch">
            <Heading size="md" mb={4}>Личные данные</Heading>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                {/* Фамилия */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.last_name')}>
                    <FormLabel htmlFor="last_name">Фамилия</FormLabel>
                    <Input id="last_name" {...register("personal_data.last_name", { required: "Фамилия обязательна" })} />
                    <FormErrorMessage>{getErrorMessage('personal_data.last_name')}</FormErrorMessage>
                </FormControl>

                {/* Имя */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.first_name')}>
                    <FormLabel htmlFor="first_name">Имя</FormLabel>
                    <Input id="first_name" {...register("personal_data.first_name", { required: "Имя обязательно" })} />
                    <FormErrorMessage>{getErrorMessage('personal_data.first_name')}</FormErrorMessage>
                </FormControl>

                {/* Отчество */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.middle_name')}>
                    <FormLabel htmlFor="middle_name">Отчество (при наличии)</FormLabel>
                    <Input id="middle_name" {...register("personal_data.middle_name")} />
                    <FormErrorMessage>{getErrorMessage('personal_data.middle_name')}</FormErrorMessage>
                </FormControl>

                {/* Дата рождения */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.birth_date')}>
                    <FormLabel htmlFor="birth_date">Дата рождения</FormLabel>
                    <Controller
                        name="personal_data.birth_date"
                        control={control}
                        rules={{ required: "Дата рождения обязательна" }}
                        render={({ field }) => {
                            const valueForParse = field.value;
                            let dateForSelected = null;
                            if (valueForParse && valueForParse.trim() !== '') {
                                // Ожидаем, что field.value уже в формате yyyy-MM-dd благодаря DocumentUploadStep
                                const parsed = parse(valueForParse, 'yyyy-MM-dd', new Date());
                                console.log(
                                    'DatePicker (birth_date): field.value =',
                                    valueForParse,
                                    '; Parsed = ', parsed,
                                    '; IsValid = ', isValid(parsed)
                                );
                                if (isValid(parsed)) {
                                    dateForSelected = parsed;
                                } else {
                                    // Дополнительная попытка распарсить как dd.MM.yyyy, если вдруг значение пришло в таком формате
                                    const parsedAlt = parse(valueForParse, 'dd.MM.yyyy', new Date());
                                    if (isValid(parsedAlt)) {
                                        dateForSelected = parsedAlt;
                                        // Важно: если мы успешно распарсили "dd.MM.yyyy",
                                        // немедленно обновим значение в react-hook-form на правильный формат "yyyy-MM-dd"
                                        // чтобы при следующем рендере оно уже было корректным.
                                        // Это особенно актуально, если CustomDateInput не используется.
                                        field.onChange(format(parsedAlt, 'yyyy-MM-dd'));
                                    } else {
                                        console.error(
                                            'DatePicker (birth_date): parse returned Invalid Date for value (tried yyyy-MM-dd and dd.MM.yyyy):',
                                            valueForParse
                                        );
                                    }
                                }
                            } else {
                                console.log(
                                    'DatePicker (birth_date): field.value (',
                                    valueForParse,
                                    ') is null or empty, selected = null'
                                );
                            }

                            return (
                                <DatePicker
                                    selected={dateForSelected} // selected ожидает объект Date или null
                                    onChange={(date: Date | null) => {
                                        // field.onChange ожидает строку в формате 'yyyy-MM-dd' или пустую строку
                                        field.onChange(date && isValid(date) ? format(date, 'yyyy-MM-dd') : '');
                                    }}
                                    customInput={ // Добавляем CustomDateInput
                                        <CustomDateInput
                                            id={field.name}
                                            fieldOnChange={(value: string) => field.onChange(value)} // CustomDateInput уже возвращает 'yyyy-MM-dd'
                                            maxDate={new Date()}
                                        />
                                    }
                                    locale="ru"
                                    showYearDropdown scrollableYearDropdown yearDropdownItemNumber={100}
                                    maxDate={new Date()} // Этот maxDate для DatePicker, CustomDateInput имеет свой
                                    dateFormat="dd.MM.yyyy" // Этот dateFormat для отображения в DatePicker, если CustomInput не используется активно
                                    placeholderText="ДД.ММ.ГГГГ" 
                                    autoComplete="off" 
                                    shouldCloseOnSelect={true}
                                />
                            );
                        }}
                    />
                    <FormErrorMessage>{getErrorMessage('personal_data.birth_date')}</FormErrorMessage>
                </FormControl>

                {/* СНИЛС */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.snils')}>
                    <FormLabel htmlFor="snils">СНИЛС</FormLabel>
                    <Controller
                        name="personal_data.snils"
                        control={control}
                        rules={{ required: "СНИЛС обязателен", pattern: { value: /^\d{3}-\d{3}-\d{3} \d{2}$/, message: "Неверный формат СНИЛС (XXX-XXX-XXX YY)" } }}
                        render={({ field }) => (
                            <Input as={IMaskInput} mask="000-000-000 00" value={field.value || ''} onAccept={(value: string) => field.onChange(value)} placeholder="XXX-XXX-XXX XX" id="snils" bg="white" borderColor="inherit" _hover={{ borderColor: "gray.300" }} _focus={{ zIndex: 1, borderColor: "primary", boxShadow: `0 0 0 1px var(--chakra-colors-primary)` }} />
                        )}
                    />
                    <FormErrorMessage>{getErrorMessage('personal_data.snils')}</FormErrorMessage>
                </FormControl>

                {/* Пол */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.gender')}>
                    <FormLabel htmlFor="gender">Пол</FormLabel>
                    <Select id="gender" placeholder="Выберите пол" {...register("personal_data.gender", { required: "Пол обязателен" })}>
                        <option value="male">Мужской</option>
                        <option value="female">Женский</option>
                    </Select>
                    <FormErrorMessage>{getErrorMessage('personal_data.gender')}</FormErrorMessage>
                </FormControl>

                {/* Гражданство */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.citizenship')}>
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
                    <FormErrorMessage>{getErrorMessage('personal_data.citizenship')}</FormErrorMessage>
                </FormControl>

                {/* Иждивенцы */}
                <FormControl isInvalid={!!getErrorMessage('personal_data.dependents')}>
                    <FormLabel htmlFor="dependents">Количество иждивенцев</FormLabel>
                    <NumberInput id="dependents" min={0} defaultValue={0}>
                        <NumberInputField {...register("personal_data.dependents", { valueAsNumber: true, min: { value: 0, message: "Должно быть не меньше 0"} })} />
                        <NumberInputStepper><NumberIncrementStepper /><NumberDecrementStepper /></NumberInputStepper>
                    </NumberInput>
                    <FormErrorMessage>{getErrorMessage('personal_data.dependents')}</FormErrorMessage>
                </FormControl>
            </SimpleGrid>

            <Divider my={4} />

            {/* Чекбокс смены ФИО */}
            <Checkbox
                isChecked={!!watchHasNameChangeInfo}
                onChange={(e) => {
                    setValue('personal_data.name_change_info', e.target.checked ? { old_full_name: '', date_changed: null } : null, { shouldValidate: false });
                }}
            >
                Была смена ФИО?
            </Checkbox>

            {/* Поля смены ФИО */}
            {watchHasNameChangeInfo && (
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} mt={4}>
                    <FormControl isInvalid={!!getErrorMessage('personal_data.name_change_info.old_full_name')}>
                        <FormLabel htmlFor="old_full_name">Предыдущее ФИО</FormLabel>
                        <Input id="old_full_name" {...register("personal_data.name_change_info.old_full_name", { required: watchHasNameChangeInfo ? "Предыдущее ФИО обязательно" : false })} />
                        <FormErrorMessage>{getErrorMessage('personal_data.name_change_info.old_full_name')}</FormErrorMessage>
                    </FormControl>

                    <FormControl isInvalid={!!getErrorMessage('personal_data.name_change_info.date_changed')}>
                        <FormLabel htmlFor="date_changed">Дата смены ФИО</FormLabel>
                        <Controller
                            name="personal_data.name_change_info.date_changed"
                            control={control}
                            rules={{ required: watchHasNameChangeInfo ? "Дата смены обязательна" : false }}
                            render={({ field }) => (
                                <DatePicker
                                    selected={field.value && field.value.trim() !== '' ? parse(field.value, 'yyyy-MM-dd', new Date()) : null}
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
                        <FormErrorMessage>{getErrorMessage('personal_data.name_change_info.date_changed')}</FormErrorMessage>
                    </FormControl>
                </SimpleGrid>
            )}
        </VStack>
    );
};

export default PersonalDataStep; 