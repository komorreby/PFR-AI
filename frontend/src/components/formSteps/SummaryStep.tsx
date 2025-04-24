import React from 'react';
import {
  Box,
  Heading,
  Text,
  Divider,
  List,
  ListItem,
  ListIcon,
  Badge,
  SimpleGrid,
  VStack
} from '@chakra-ui/react';
import { CheckCircleIcon, WarningIcon } from '@chakra-ui/icons';
import { CaseFormDataType } from '../CaseForm'; // Импортируем тип

interface SummaryStepProps {
  formData: CaseFormDataType;
}

// Вспомогательная функция для отображения списков
const renderList = (items: string[] | undefined, title: string) => {
  if (!items || items.length === 0) {
    return <Text><em>{title}: нет</em></Text>;
  }
  return (
    <Box mb={3}>
      <Text fontWeight="bold">{title}:</Text>
      <List spacing={1} pl={4}>
        {items.map((item, index) => (
          <ListItem key={index}>{item}</ListItem>
        ))}
      </List>
    </Box>
  );
};

function SummaryStep({ formData }: SummaryStepProps) {
  const { personal_data, work_experience, pension_points, benefits, documents, has_incorrect_document, disability, pension_type } = formData;

  const pensionTypeLabel = pension_type === 'retirement_standard' ? 'Страховая по старости' :
                            pension_type === 'disability_social' ? 'Социальная по инвалидности' :
                            'Неизвестный тип';

  return (
    <VStack spacing={6} align="stretch">
      <Heading size="lg" textAlign="center">Сводка данных дела</Heading>
      <Text textAlign="center" fontSize="lg" color="blue.600">Тип пенсии: <strong>{pensionTypeLabel}</strong></Text>
      <Divider />

      {/* Персональные данные */}
      <Box>
        <Heading size="md" mb={3}>Персональные данные</Heading>
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={2}>
          <Text><strong>ФИО:</strong> {personal_data.full_name}</Text>
          <Text><strong>Дата рождения:</strong> {personal_data.birth_date}</Text>
          <Text><strong>СНИЛС:</strong> {personal_data.snils}</Text>
          <Text><strong>Пол:</strong> {personal_data.gender === 'male' ? 'Мужской' : personal_data.gender === 'female' ? 'Женский' : 'Не указан'}</Text>
          <Text><strong>Гражданство:</strong> {personal_data.citizenship}</Text>
          <Text><strong>Иждивенцы:</strong> {personal_data.dependents}</Text>
        </SimpleGrid>
        {personal_data.name_change_info && (
          <Box mt={2} p={2} bg="gray.50" borderRadius="md">
            <Text><strong>Смена ФИО:</strong> Да</Text>
            <Text><em>Прежн. ФИО:</em> {personal_data.name_change_info.old_full_name}</Text>
            <Text><em>Дата смены:</em> {personal_data.name_change_info.date_changed}</Text>
          </Box>
        )}
      </Box>
      <Divider />

      {/* Трудовой стаж (только для retirement_standard) */}
      {pension_type === 'retirement_standard' && (
        <Box>
          <Heading size="md" mb={3}>Трудовой стаж</Heading>
          <Text mb={2}><strong>Заявленный общий стаж:</strong> {work_experience.total_years} лет</Text>
          {work_experience.records.length > 0 ? (
            <List spacing={3}>
              {work_experience.records.map((record, index) => (
                <ListItem key={index} p={2} borderWidth="1px" borderRadius="md">
                  <Text><strong>{index + 1}. Организация:</strong> {record.organization}</Text>
                  <Text><em>Период:</em> {record.start_date} - {record.end_date}</Text>
                  <Text><em>Должность:</em> {record.position}</Text>
                  {record.special_conditions && <Badge colorScheme="orange" ml={2}>Особые условия</Badge>}
                </ListItem>
              ))}
            </List>
          ) : (
            <Text><em>Записи о стаже отсутствуют.</em></Text>
          )}
        </Box>
      )}

      {/* Сведения об инвалидности (только для disability_social) */}
      {pension_type === 'disability_social' && disability && (
        <Box>
          <Heading size="md" mb={3}>Сведения об инвалидности</Heading>
          <Text><strong>Группа:</strong> {disability.group === 'child' ? 'Ребенок-инвалид' : `${disability.group} группа`}</Text>
          <Text><strong>Дата установления:</strong> {disability.date}</Text>
          {disability.cert_number && <Text><strong>Номер справки МСЭ:</strong> {disability.cert_number}</Text>}
        </Box>
      )}

      {/* Разделитель, если были предыдущие секции */} 
      {(pension_type === 'retirement_standard' || (pension_type === 'disability_social' && disability)) && <Divider />}

      {/* Дополнительная информация */}
      <Box>
        <Heading size="md" mb={3}>Дополнительная информация</Heading>
        {pension_type === 'retirement_standard' && (
            <Text mb={2}><strong>Пенсионные баллы (ИПК):</strong> {pension_points}</Text>
        )}
        {renderList(benefits?.split(',').map(s => s.trim()).filter(Boolean), 'Льготы')}
        {renderList(documents?.split(',').map(s => s.trim()).filter(Boolean), 'Представленные документы')}
        <Text mt={2}>
          <strong>Корректность оформления документов:</strong> {has_incorrect_document ? 
            <><WarningIcon color="red.500" mr={1}/> Указано наличие некорректно оформленных документов</> :
            <><CheckCircleIcon color="green.500" mr={1}/> Проблем не указано</>
          }
        </Text>
      </Box>

      <Divider />
      <Text textAlign="center" fontWeight="bold" color="gray.600">Пожалуйста, проверьте все данные перед отправкой.</Text>

    </VStack>
  );
}

export default SummaryStep; 