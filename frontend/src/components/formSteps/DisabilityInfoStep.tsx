import React from 'react';
import { useFormContext, Controller, FieldErrors, UseFormRegister, Control } from 'react-hook-form';
import {
  FormControl,
  FormLabel,
  Input,
  Select,
  FormErrorMessage,
  VStack,
  Heading
} from '@chakra-ui/react';

// Предполагаем, что DisabilityInfoType экспортируется из CaseForm или определен глобально
// Если нет, его нужно определить здесь:
type DisabilityInfoType = {
    group: string;
    date: string;
    cert_number?: string;
};

// Примерный интерфейс для пропсов, может потребоваться доработка
interface DisabilityInfoStepProps {
  register: UseFormRegister<any>; // Можно уточнить, если известен полный тип формы
  errors: FieldErrors<DisabilityInfoType>; // <<< Используем FieldErrors<DisabilityInfoType>
  control: Control<any>; // Можно уточнить
  getErrorMessage: (fieldName: string) => string | undefined;
}

function DisabilityInfoStep({ register, errors, control, getErrorMessage }: DisabilityInfoStepProps) {
  return (
    <VStack spacing={4} align="stretch">
        <Heading size="md" mb={2}>Сведения об инвалидности</Heading>

        {/* Группа инвалидности */}
        <FormControl isInvalid={!!errors.group}>
            <FormLabel htmlFor='disability.group'>Группа инвалидности</FormLabel>
            <Select
                id='disability.group'
                placeholder="Выберите группу"
                {...register('disability.group', {
                    required: 'Пожалуйста, выберите группу инвалидности'
                })}
            >
                <option value="1">I группа</option>
                <option value="2">II группа</option>
                <option value="3">III группа</option>
                <option value="child">Ребенок-инвалид</option>
            </Select>
            <FormErrorMessage>{errors.group?.message}</FormErrorMessage>
        </FormControl>

        {/* Дата установления инвалидности */}
        <FormControl isInvalid={!!errors.date}>
            <FormLabel htmlFor='disability.date'>Дата установления инвалидности</FormLabel>
            <Input
                id='disability.date'
                type="date"
                {...register('disability.date', {
                    required: 'Пожалуйста, укажите дату установления инвалидности'
                })}
            />
            <FormErrorMessage>{errors.date?.message}</FormErrorMessage>
        </FormControl>

        {/* Номер справки МСЭ (опционально) */}
        <FormControl isInvalid={!!errors.cert_number}>
            <FormLabel htmlFor='disability.cert_number'>Номер справки МСЭ (если есть)</FormLabel>
            <Input
                id='disability.cert_number'
                type="text"
                {...register('disability.cert_number')}
            />
            <FormErrorMessage>{errors.cert_number?.message}</FormErrorMessage>
        </FormControl>

    </VStack>
  );
}

export default DisabilityInfoStep; 