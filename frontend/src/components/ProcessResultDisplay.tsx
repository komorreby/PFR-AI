import React from 'react';
import {
  Box,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Heading,
  Text,
  Divider,
  Code,
  useColorModeValue,
  VStack,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import { ProcessResult } from './CaseForm'; // Импортируем тип

interface ProcessResultDisplayProps {
  result: ProcessResult;
}

const ProcessResultDisplay: React.FC<ProcessResultDisplayProps> = ({ result }) => {
  const { status, explanation, errors } = result;
  const bgColor = useColorModeValue('gray.50', 'gray.700');

  return (
    <VStack spacing={4} align="stretch">
      <Heading size="lg" textAlign="center">Результат обработки</Heading>
      <Alert 
        status={status === 'approved' ? 'success' : 'error'}
        variant="subtle"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        textAlign="center"
        p={4}
        borderRadius="md"
      >
        <AlertIcon boxSize="40px" mr={0} />
        <AlertTitle mt={4} mb={1} fontSize="xl">
          Статус: {status === 'approved' ? 'Одобрено' : 'Отказано'}
        </AlertTitle>
      </Alert>

      <Box p={5} borderWidth="1px" borderRadius="lg" bg={bgColor}>
        <Heading size="md" mb={3}>Детальное объяснение:</Heading>
        {/* Используем pre-wrap для сохранения переносов строк из бэкенда */} 
        <Text whiteSpace="pre-wrap" fontFamily="monospace">{explanation || "Объяснение отсутствует."}</Text>
      </Box>

      {/* Опционально: Можно дополнительно показать ML ошибки отдельно, если нужно */} 
      {/* {errors && errors.length > 0 && (
        <Box p={4} borderWidth="1px" borderRadius="lg">
          <Heading size="sm" mb={2}>Список выявленных типовых ошибок:</Heading>
          <List spacing={3}>
            {errors.map((error, index) => (
              <ListItem key={index}>
                <ListIcon as={WarningIcon} color="orange.500" />
                <strong>{error.code}:</strong> {error.description} (<i>Рекомендация: {error.recommendation}, Закон: {error.law}</i>)
              </ListItem>
            ))}
          </List>
        </Box>
      )} */}
    </VStack>
  );
};

export default ProcessResultDisplay; 