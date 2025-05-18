import React from 'react';
import {
  Box,
  Heading,
  Text,
  useColorModeValue,
  VStack,
  Stat,
  StatLabel,
  StatNumber,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import { ProcessResult } from './CaseForm'; // Импортируем типы

interface ProcessResultDisplayProps {
  result: ProcessResult;
}

const ProcessResultDisplay: React.FC<ProcessResultDisplayProps> = ({ result }) => {
  const { status, explanation } = result;
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

      <Accordion allowMultiple defaultIndex={[0]}>
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
      </Accordion>

    </VStack>
  );
};

export default ProcessResultDisplay; 