import React from 'react';
import { FieldErrors, UseFormRegister, Control, Controller } from 'react-hook-form';
import {
    VStack,
    Heading,
    FormControl,
    FormLabel,
    NumberInput,
    NumberInputField,
    NumberInputStepper,
    NumberIncrementStepper,
    NumberDecrementStepper,
    Checkbox,
    FormErrorMessage
} from '@chakra-ui/react';
import { CaseFormDataType } from '../CaseForm';
import TagInput from '../formInputs/TagInput';

interface AdditionalInfoStepProps {
    register: UseFormRegister<CaseFormDataType>;
    control: Control<CaseFormDataType>;
    errors: FieldErrors<CaseFormDataType>;
    getErrorMessage: (name: string) => string | undefined;
    pensionType: string | null;
}

const AdditionalInfoStep: React.FC<AdditionalInfoStepProps> = ({ register, control, getErrorMessage, pensionType }) => {
    return (
        <VStack spacing={4} align="stretch">
            <Heading size="md" mb={4}>Дополнительная информация</Heading>
            {/* Пенсионные баллы (только для страховой по старости) */}
            {pensionType === 'retirement_standard' && (
                <FormControl isInvalid={!!getErrorMessage('pension_points')}>
                    <FormLabel htmlFor="pension_points">Пенсионные баллы (ИПК)</FormLabel>
                    <NumberInput id="pension_points" min={0} defaultValue={0} precision={2} step={0.1}>
                        <NumberInputField {...register("pension_points", {
                             valueAsNumber: true,
                             required: pensionType === 'retirement_standard' ? "Пенсионные баллы обязательны для этого типа пенсии" : false,
                             min: { value: 0, message: "Баллы не могут быть отрицательными" }
                             })}
                         />
                        <NumberInputStepper><NumberIncrementStepper /><NumberDecrementStepper /></NumberInputStepper>
                    </NumberInput>
                    <FormErrorMessage>{getErrorMessage('pension_points')}</FormErrorMessage>
                </FormControl>
            )}
            {/* Льготы (скрываем для социальной пенсии по инвалидности - пример) */}
            {pensionType !== 'disability_social' && (
                <FormControl isInvalid={!!getErrorMessage('benefits')}>
                    <FormLabel htmlFor="benefits">Льготы</FormLabel>
                    <Controller
                        name="benefits"
                        control={control}
                        render={({ field }) => (
                            <TagInput
                                id={field.name}
                                value={field.value}
                                fieldOnChange={field.onChange}
                                placeholder="Добавьте льготу и нажмите Enter"
                            />
                        )}
                    />
                    <FormErrorMessage>{getErrorMessage('benefits')}</FormErrorMessage>
                </FormControl>
            )}
            {/* Документы */}
            <FormControl isInvalid={!!getErrorMessage('documents')}>
                <FormLabel htmlFor="documents">Представленные документы</FormLabel>
                <Controller
                    name="documents"
                    control={control}
                    render={({ field }) => (
                        <TagInput
                            id={field.name}
                            value={field.value}
                            fieldOnChange={field.onChange}
                            placeholder="Добавьте документ и нажмите Enter"
                        />
                    )}
                />
                <FormErrorMessage>{getErrorMessage('documents')}</FormErrorMessage>
            </FormControl>
            {/* Некорректные документы */}
            <FormControl mt={2}>
                <Checkbox id="has_incorrect_document" {...register("has_incorrect_document")}>Есть некорректно оформленные документы</Checkbox>
            </FormControl>
        </VStack>
    );
};

export default AdditionalInfoStep; 