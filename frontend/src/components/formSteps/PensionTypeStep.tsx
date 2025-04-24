import React from 'react';
import {
  FormControl,
  FormLabel,
  RadioGroup,
  Stack,
  Radio,
  FormErrorMessage,
  Heading
} from '@chakra-ui/react';

interface PensionTypeStepProps {
  selectedValue: string | null;
  onChange: (value: string) => void;
  errorMessage?: string; // Добавляем для отображения ошибки
}

// Определяем доступные типы пенсий
const pensionTypes = [
  { value: 'retirement_standard', label: 'Страховая пенсия по старости (общий случай)' },
  { value: 'disability_social', label: 'Социальная пенсия по инвалидности' },
  // TODO: Добавить другие типы пенсий по мере необходимости
  // { value: 'survivor', label: 'Пенсия по случаю потери кормильца' },
  // { value: 'early_retirement_hazardous', label: 'Досрочная страховая пенсия (вредные условия труда)' },
];

function PensionTypeStep({ selectedValue, onChange, errorMessage }: PensionTypeStepProps) {
  return (
    <FormControl isInvalid={!!errorMessage}>
      <Heading size="md" mb={6}>Выберите тип назначаемой пенсии</Heading>
      <FormLabel>Тип пенсии:</FormLabel>
      <RadioGroup onChange={onChange} value={selectedValue || ''}>
        <Stack direction="column">
          {pensionTypes.map((type) => (
            <Radio key={type.value} value={type.value}>
              {type.label}
            </Radio>
          ))}
        </Stack>
      </RadioGroup>
      {errorMessage && <FormErrorMessage>{errorMessage}</FormErrorMessage>}
    </FormControl>
  );
}

export default PensionTypeStep; 