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
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  List,
  ListItem,
  ListIcon,
  Tag
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon, InfoIcon } from '@chakra-ui/icons';
import { ProcessResult, ApiError } from './CaseForm'; // Импортируем типы

interface ProcessResultDisplayProps {
  result: ProcessResult;
}

const ProcessResultDisplay: React.FC<ProcessResultDisplayProps> = ({ result }) => {
  const { status, explanation, errors } = result;
  const bgColor = useColorModeValue('gray.50', 'gray.700');
  const statusColorScheme = status === 'approved' ? 'green' : 'red';
  const StatusIcon = status === 'approved' ? CheckCircleIcon : WarningIcon;

  return (
    <VStack spacing={6} align="stretch">
      <Heading size="lg" textAlign="center">Результат обработки</Heading>

      <Stat
        p={4}
        borderWidth="1px"
        borderRadius="lg"
        borderColor={`${statusColorScheme}.200`}
        bg={`${statusColorScheme}.50`}
        _dark={{
            bg: `${statusColorScheme}.900`,
            borderColor: `${statusColorScheme}.700`
        }}
      >
        <StatLabel display="flex" alignItems="center">
          <StatusIcon mr={2} color={`${statusColorScheme}.500`} />
          Итоговый статус
        </StatLabel>
        <StatNumber color={`${statusColorScheme}.600`} _dark={{ color: `${statusColorScheme}.300` }}>
          {status === 'approved' ? 'Одобрено' : 'Отказано'}
        </StatNumber>
      </Stat>

      <Accordion allowMultiple defaultIndex={[0, 1]}>
        <AccordionItem>
          <h2>
            <AccordionButton>
              <Box flex="1" textAlign="left" fontWeight="semibold">
                Объяснение
              </Box>
              <AccordionIcon />
            </AccordionButton>
          </h2>
          <AccordionPanel pb={4} bg={bgColor} borderBottomRadius="md">
            <Text whiteSpace="pre-wrap" fontFamily="monospace" fontSize="sm">
                {explanation || "Объяснение отсутствует."}
            </Text>
          </AccordionPanel>
        </AccordionItem>

        {errors && errors.length > 0 && (
            <AccordionItem>
            <h2>
                <AccordionButton>
                <Box flex="1" textAlign="left" fontWeight="semibold">
                    Выявленные ошибки ({errors.length})
                </Box>
                <AccordionIcon />
                </AccordionButton>
            </h2>
            <AccordionPanel pb={4} bg={bgColor} borderBottomRadius="md">
                <List spacing={4}>
                    {errors.map((error: ApiError, index: number) => (
                    <ListItem key={index}>
                        <VStack align="start" spacing={1}>
                            <Heading size="sm" display="flex" alignItems="center">
                                <ListIcon as={WarningIcon} color="orange.500" mr={2} />
                                {error.code || `Ошибка ${index + 1}`}
                            </Heading>
                            <Text fontSize="md">{error.description}</Text>
                            <Text fontSize="xs" color="textSecondary">
                                Рекомендация: {error.recommendation || '-'}
                            </Text>
                            <Text fontSize="xs" color="textSecondary">
                                Основание: {error.law || '-'}
                            </Text>
                        </VStack>
                    </ListItem>
                    ))}
                </List>
            </AccordionPanel>
            </AccordionItem>
        )}
      </Accordion>

    </VStack>
  );
};

export default ProcessResultDisplay; 