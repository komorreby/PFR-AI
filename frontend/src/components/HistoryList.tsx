import { useState } from 'react';
import {
    Box, 
    Heading, 
    Text, 
    Button, 
    VStack, // Вертикальный стек для информации
    HStack, // Горизонтальный стек для кнопок
    Card,   // <--- Используем Card
    CardBody,
    CardHeader, 
    CardFooter, 
    Tag,    // <--- Для количества ошибок
    Divider,
    SimpleGrid, // <--- Для сетки карточек
    Flex,       // <--- Для кнопок пагинации
} from '@chakra-ui/react';

// Импортируем типы из центрального файла
import type { HistoryEntry } from '../types'; // Убедитесь, что путь правильный

// Локальные типы HistoryPersonalDataType и HistoryEntry УДАЛЕНЫ
// type HistoryPersonalDataType = { ... };
// export type HistoryEntry = { ... };

// Пропсы компонента
interface HistoryListProps {
    history: HistoryEntry[]; // Используем импортированный HistoryEntry
    onDownload: (caseId: number, format: 'pdf' | 'docx') => void; // Колбэк для скачивания
}

// Функция для маскирования СНИЛС (пример)
const maskSnils = (snils: string | undefined): string => {
    if (!snils) return 'N/A';
    // Простая маска, можно усложнить
    return snils.substring(0, 3) + '-***-*** **'; 
};

// Количество элементов на странице
const ITEMS_PER_PAGE = 6; 

function HistoryList({ history, onDownload }: HistoryListProps) {
    const [currentPage, setCurrentPage] = useState(1);

    // Расчеты для пагинации
    const totalPages = Math.ceil(history.length / ITEMS_PER_PAGE);
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const endIndex = startIndex + ITEMS_PER_PAGE;
    const currentItems = history.slice(startIndex, endIndex);

    const handlePreviousPage = () => {
        setCurrentPage((prev) => Math.max(prev - 1, 1));
    };

    const handleNextPage = () => {
        setCurrentPage((prev) => Math.min(prev + 1, totalPages));
    };

    if (!history || history.length === 0) {
        return <Text textAlign="center" color="gray.500" mt={4}>История обработанных дел пуста.</Text>;
    }

    return (
        <Box> {/* Общий контейнер Box нужен */}
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}> 
                {currentItems.map((entry) => {
                    // Собираем ФИО из отдельных полей
                    const fullName = [
                        entry.personal_data?.last_name, 
                        entry.personal_data?.first_name, 
                        entry.personal_data?.middle_name
                    ].filter(Boolean).join(' ');

                    return (
                        <Card key={entry.id} variant="outline" size="sm" display="flex" flexDirection="column" justifyContent="space-between"> 
                             <Box> {/* Контейнер для хедера и боди */} 
                                <CardHeader pb={2}> 
                                    <Flex justify="space-between" align="center">
                                        <Heading size='xs' color="primary"> 
                                           Дело ID: {entry.id}
                                        </Heading>
                                        {entry.final_status && (
                                            <Tag
                                                size="sm"
                                                // Примерная логика цвета в зависимости от статуса
                                                colorScheme={entry.final_status.toLowerCase().includes('соответствует') ? 'green' : 
                                                             entry.final_status.toLowerCase().includes('не соответствует') ? 'red' : 'gray'}
                                                variant="solid"
                                            >
                                                {entry.final_status}
                                            </Tag>
                                        )}
                                    </Flex>
                                </CardHeader>
                                <CardBody py={2}> 
                                    <VStack align="start" spacing={1}>
                                        <Text fontSize="sm" noOfLines={1}><strong>ФИО:</strong> {fullName || 'N/A'}</Text> 
                                        <Text fontSize="xs" color="textSecondary"><strong>СНИЛС:</strong> {maskSnils(entry.personal_data?.snils)}</Text>
                                        <Text fontSize="xs" color="textSecondary"><strong>Тип пенсии:</strong> {entry.pension_type || 'N/A'}</Text>
                                        {entry.final_explanation && (
                                            <Text fontSize="xs" color="textSecondary" noOfLines={2} title={entry.final_explanation}>
                                                <strong>Пояснение:</strong> {entry.final_explanation}
                                            </Text>
                                        )}
                                        {entry.rag_confidence !== undefined && entry.rag_confidence !== null && (
                                            <Text fontSize="xs" color="textSecondary">
                                                <strong>Уверенность RAG:</strong> {(entry.rag_confidence * 100).toFixed(1)}%
                                            </Text>
                                        )}
                                    </VStack>
                                </CardBody>
                             </Box>
                             <Box> {/* Контейнер для футера */} 
                                 <Divider color="border" mt="auto" /> {/* Разделитель внизу */} 
                                 <CardFooter pt={2} display="flex" justifyContent="flex-end" alignItems="center"> 
                                     {/* Старый тег статуса удален, так как статус теперь в CardHeader */}
                                     <HStack spacing={2}> 
                                        <Button 
                                          colorScheme="danger" 
                                          variant="outline" 
                                          size="xs" 
                                          onClick={() => onDownload(entry.id, 'pdf')}
                                        >
                                            PDF
                                        </Button>
                                        <Button 
                                          colorScheme="primary" 
                                          variant="outline"
                                          size="xs"
                                          onClick={() => onDownload(entry.id, 'docx')}
                                        >
                                            DOCX
                                        </Button>
                                     </HStack>
                                </CardFooter>
                             </Box>
                        </Card>
                    );
                })}
            </SimpleGrid>

             {/* Элементы управления пагинацией */} 
             {totalPages > 1 && (
                <Flex justify="center" align="center" mt={6}> 
                    <Button 
                        onClick={handlePreviousPage} 
                        isDisabled={currentPage === 1}
                        size="sm"
                        variant="outline"
                    >
                       Назад
                    </Button>
                    <Text mx={4} fontSize="sm"> 
                        Страница {currentPage} из {totalPages}
                    </Text>
                    <Button 
                        onClick={handleNextPage} 
                        isDisabled={currentPage === totalPages}
                        size="sm"
                        variant="outline"
                    >
                        Вперед
                    </Button>
                </Flex>
            )}
        </Box>
    );
}

export default HistoryList; 