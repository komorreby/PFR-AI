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

// Тип для персональных данных (упрощенный, берем только нужное для отображения)
type HistoryPersonalDataType = {
    full_name?: string;
    snils?: string;
    // Можно добавить другие поля при необходимости
};

// Тип для одной записи в истории
export type HistoryEntry = {
    id: number;
    personal_data: HistoryPersonalDataType; // Используем упрощенный тип
};

// Пропсы компонента
interface HistoryListProps {
    history: HistoryEntry[];
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
                {currentItems.map((entry) => (
                    // Карточка остается почти без изменений
                    <Card key={entry.id} variant="outline" size="sm" display="flex" flexDirection="column" justifyContent="space-between"> 
                         <Box> {/* Контейнер для хедера и боди */} 
                            <CardHeader pb={2}> 
                                <Heading size='xs' color="primary"> 
                                   Дело ID: {entry.id}
                                </Heading>
                            </CardHeader>
                            <CardBody py={2}> 
                                <VStack align="start" spacing={1}>
                                    <Text fontSize="sm" noOfLines={1}><strong>ФИО:</strong> {entry.personal_data?.full_name || 'N/A'}</Text> {/* Ограничим одной строкой */} 
                                    <Text fontSize="xs" color="textSecondary"><strong>СНИЛС:</strong> {maskSnils(entry.personal_data?.snils)}</Text>
                                </VStack>
                            </CardBody>
                         </Box>
                         <Box> {/* Контейнер для футера */} 
                             <Divider color="border" mt="auto" /> {/* Разделитель внизу */} 
                             <CardFooter pt={2} display="flex" justifyContent="space-between" alignItems="center"> 
                                 <Tag 
                                   size="sm" 
                                   colorScheme={'green'}
                                   variant="solid"
                                 >
                                    Статус: Ок
                                 </Tag>
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
                ))}
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