import React from 'react';
import {
  FormControl,
  FormLabel,
  Stack,
  Button,
  FormErrorMessage,
  Heading,
  Alert,
  AlertIcon
} from '@chakra-ui/react';

interface PensionTypeStepProps {
  selectedValue: string | null;
  onChange: (value: string) => void;
  errorMessage?: string;
  availablePensionTypes: { [key: string]: string };
}

function PensionTypeStep({
  selectedValue,
  onChange,
  errorMessage,
  availablePensionTypes,
}: PensionTypeStepProps) {
  return (
    <FormControl isInvalid={!!errorMessage}>
      <Heading size="md" mb={6}>
        Выберите тип назначаемой пенсии
      </Heading>
      <FormLabel>Тип пенсии:</FormLabel>
      <Stack direction={['column', 'row']} spacing="4" align="stretch" wrap="wrap">
        {Object.entries(availablePensionTypes).map(([key, name]) => (
          <Button
            key={key}
            variant={selectedValue === key ? 'solid' : 'outline'}
            colorScheme="blue"
            onClick={() => onChange(key)}
            size="lg"
            justifyContent="flex-start"
            flex={{ base: "100%", md: "auto" }}
            textAlign="left"
            whiteSpace="normal"
            height="auto"
            py={3}
            minWidth="200px"
          >
            {name}
          </Button>
        ))}
      </Stack>
      {errorMessage && <FormErrorMessage>{errorMessage}</FormErrorMessage>}
      {Object.keys(availablePensionTypes).length === 0 && (
        <Alert status="warning" mt={4}>
            <AlertIcon />
            Нет доступных типов пенсий для выбора.
        </Alert>
      )}
    </FormControl>
  );
}

export default PensionTypeStep; 