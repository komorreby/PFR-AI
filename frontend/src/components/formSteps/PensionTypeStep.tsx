import React, { useState, useEffect } from 'react';
import {
  FormControl,
  FormLabel,
  Stack,
  Button,
  FormErrorMessage,
  Heading,
  Spinner,
  Alert,
  AlertIcon,
  Text
} from '@chakra-ui/react';
import { getPensionTypes, PensionTypeChoice } from '../../services/client';

interface PensionTypeStepProps {
  selectedValue: string | null;
  onChange: (value: string) => void;
  errorMessage?: string;
}

function PensionTypeStep({
  selectedValue,
  onChange,
  errorMessage: propErrorMessage,
}: PensionTypeStepProps) {
  const [availablePensionTypes, setAvailablePensionTypes] = useState<PensionTypeChoice | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTypes = async () => {
      try {
        setLoading(true);
        setError(null);
        const types = await getPensionTypes();
        setAvailablePensionTypes(types);
      } catch (err) {
        console.error("Failed to fetch pension types:", err);
        setError(err instanceof Error ? err.message : "Не удалось загрузить типы пенсий.");
      } finally {
        setLoading(false);
      }
    };
    fetchTypes();
  }, []);

  if (loading) {
    return <Spinner />;
  }

  if (error) {
    return (
      <Alert status="error">
        <AlertIcon />
        {error}
      </Alert>
    );
  }

  if (!availablePensionTypes || Object.keys(availablePensionTypes).length === 0) {
    return <Text>Типы пенсий не найдены или не загружены.</Text>;
  }

  return (
    <FormControl isInvalid={!!propErrorMessage}>
      <Heading size="md" mb={6}>
        Выберите тип назначаемой пенсии
      </Heading>
      <FormLabel htmlFor="pensionTypeSelect">Тип пенсии:</FormLabel>
      <Stack direction={['column', 'row']} spacing="4" align="stretch" wrap="wrap">
        {Object.entries(availablePensionTypes).map(([typeKey, typeLabel]) => (
          <Button
            key={typeKey}
            variant={selectedValue === typeKey ? 'solid' : 'outline'}
            colorScheme="blue"
            onClick={() => onChange(typeKey)}
            size="lg"
            justifyContent="flex-start"
            flex={{ base: "1 1 100%", md: "0 1 auto" }}
            minWidth="200px"
            textAlign="left"
            whiteSpace="normal"
            height="auto"
            py={3}
            px={4}
          >
            {typeLabel}
          </Button>
        ))}
      </Stack>
      {propErrorMessage && <FormErrorMessage>{propErrorMessage}</FormErrorMessage>}
    </FormControl>
  );
}

export default PensionTypeStep; 