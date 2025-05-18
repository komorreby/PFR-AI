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
// import { ProcessResult } from './CaseForm'; // Старый импорт
import { ProcessOutput as BackendProcessOutput } from '../types'; // Новый импорт

interface ProcessResultDisplayProps {
  result: BackendProcessOutput; // Используем BackendProcessOutput
}

const ProcessResultDisplay: React.FC<ProcessResultDisplayProps> = ({ result }) => {
  // Обновляем деструктуризацию и логику в соответствии с полями BackendProcessOutput
  const { final_status, explanation, confidence_score, case_id } = result;
  const bgColor = useColorModeValue('gray.50', 'gray.700');
  
  // Определяем цвет и иконку на основе final_status
  const isApproved = final_status.toLowerCase().includes('соответствует');
  const statusColorScheme = isApproved ? 'green' : 'red';
  const StatusIcon = isApproved ? CheckCircleIcon : WarningIcon;

  return (
    <VStack spacing={6} align="stretch">
      <Heading size="lg" textAlign="center">Результат обработки дела ID: {case_id}</Heading>

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
          {final_status}
        </StatNumber>
        {confidence_score !== undefined && (
            <Text fontSize="xs" color="gray.500" mt={1}>
                Уверенность: {(confidence_score * 100).toFixed(1)}%
            </Text>
        )}
      </Stat>

      <Accordion allowToggle defaultIndex={[0]}>
        <AccordionItem>
          <h2>
            <AccordionButton>
              <Box flex="1" textAlign="left" fontWeight="semibold">
                Подробное объяснение
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