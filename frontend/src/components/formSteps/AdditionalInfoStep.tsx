import React from 'react';
import { FieldErrors, UseFormRegister } from 'react-hook-form';
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
    Textarea,
    Checkbox,
    FormErrorMessage
} from '@chakra-ui/react';
import { CaseFormDataType } from '../CaseForm';

interface AdditionalInfoStepProps {
    register: UseFormRegister<CaseFormDataType>;
    errors: FieldErrors<CaseFormDataType>;
    getErrorMessage: (name: string) => string | undefined;
}

const AdditionalInfoStep: React.FC<AdditionalInfoStepProps> = ({ register, errors, getErrorMessage }) => {
    return (
        <VStack spacing={4} align="stretch">
            <Heading size="md" mb={4}>Дополнительная информация</Heading>
            {/* Пенсионные баллы */}
            <FormControl isInvalid={!!getErrorMessage('pension_points')}>
                <FormLabel htmlFor="pension_points">Пенсионные баллы</FormLabel>
                <NumberInput id="pension_points" min={0} defaultValue={0} precision={2} step={0.1}>
                    <NumberInputField {...register("pension_points", { valueAsNumber: true, required: "Пенсионные баллы обязательны", min: { value: 0, message: "Баллы не могут быть отрицательными" } })} />
                    <NumberInputStepper><NumberIncrementStepper /><NumberDecrementStepper /></NumberInputStepper>
                </NumberInput>
                <FormErrorMessage>{getErrorMessage('pension_points')}</FormErrorMessage>
            </FormControl>
            {/* Льготы */}
            <FormControl isInvalid={!!getErrorMessage('benefits')}>
                <FormLabel htmlFor="benefits">Льготы</FormLabel>
                <Textarea id="benefits" placeholder="Перечислите льготы через запятую" {...register("benefits")} />
                <FormErrorMessage>{getErrorMessage('benefits')}</FormErrorMessage>
            </FormControl>
            {/* Документы */}
            <FormControl isInvalid={!!getErrorMessage('documents')}>
                <FormLabel htmlFor="documents">Представленные документы</FormLabel>
                <Textarea id="documents" placeholder="Перечислите документы через запятую" {...register("documents")} />
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