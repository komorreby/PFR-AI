import { FieldErrors, UseFormRegister, Control } from 'react-hook-form';
// import { CaseFormDataType } from '../CaseForm'; // Старый импорт
import { CaseFormDataTypeForRHF, DisabilityInfo } from '../../types'; // Новый импорт
import {
  FormControl,
  FormLabel,
  Input,
  Select,
  FormErrorMessage,
  VStack,
  Heading
} from '@chakra-ui/react';

// Локальный тип DisabilityInfoType УДАЛЕН, используется импортированный DisabilityInfo
// type DisabilityInfoType = {
//     group: string;
//     date: string;
//     cert_number?: string;
// };

interface DisabilityInfoStepProps {
  register: UseFormRegister<CaseFormDataTypeForRHF>;
  // Ошибки теперь для всего объекта disability, доступ через errors.disability?.group
  // Или, если getErrorMessage используется, он должен обрабатывать 'disability.group'
  errors: FieldErrors<CaseFormDataTypeForRHF>; 
  control: Control<CaseFormDataTypeForRHF>; // Обновляем тип Control
  getErrorMessage: (fieldName: keyof DisabilityInfo | `disability.${keyof DisabilityInfo}`) => string | undefined;
}

function DisabilityInfoStep({ register, errors, getErrorMessage }: DisabilityInfoStepProps) {
  return (
    <VStack spacing={4} align="stretch">
        <Heading size="md" mb={2}>Сведения об инвалидности</Heading>

        <FormControl isInvalid={!!getErrorMessage('disability.group') || !!errors.disability?.group}>
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
            <FormErrorMessage>{getErrorMessage('disability.group') || errors.disability?.group?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!getErrorMessage('disability.date') || !!errors.disability?.date}>
            <FormLabel htmlFor='disability.date'>Дата установления инвалидности</FormLabel>
            <Input
                id='disability.date'
                type="date" // Для нативного date picker, IMaskInput не используется здесь
                {...register('disability.date', {
                    required: 'Пожалуйста, укажите дату установления инвалидности'
                    // Можно добавить валидацию, чтобы дата не была в будущем
                })}
            />
            <FormErrorMessage>{getErrorMessage('disability.date') || errors.disability?.date?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!getErrorMessage('disability.cert_number') || !!errors.disability?.cert_number}>
            <FormLabel htmlFor='disability.cert_number'>Номер справки МСЭ (если есть)</FormLabel>
            <Input
                id='disability.cert_number'
                type="text"
                {...register('disability.cert_number')}
            />
            <FormErrorMessage>{getErrorMessage('disability.cert_number') || errors.disability?.cert_number?.message}</FormErrorMessage>
        </FormControl>

    </VStack>
  );
}

export default DisabilityInfoStep; 