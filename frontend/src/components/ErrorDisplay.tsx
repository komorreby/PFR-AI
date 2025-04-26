import { ApiError } from './CaseForm'; // Тип для ошибки

import { 
    Alert, 
    AlertIcon, 
    AlertTitle, 
    AlertDescription, 
    List, 
    ListItem,
} from '@chakra-ui/react';

interface ErrorDisplayProps {
    errors: ApiError[] | null;
}

function ErrorDisplay({ errors }: ErrorDisplayProps) {
    if (!errors || errors.length === 0) {
        return null;
    }

    return (
        <Alert 
            status="error" 
            variant="subtle" // Или "solid", "left-accent", "top-accent"
            flexDirection="column"
            alignItems="start" 
            width="100%"
            borderRadius="md" // Закругленные углы
            mt={4} // Отступ сверху
        >
            <AlertIcon />
            <AlertTitle mt={1} mb={1} fontSize="lg">
                Обнаружены ошибки при обработке:
            </AlertTitle>
            <AlertDescription maxWidth="100%">
                <List spacing={1} mt={2} styleType="none"> {/* Убираем маркеры по умолчанию */} 
                    {errors.map((error, index) => (
                        <ListItem key={index} fontSize="sm">
                           {/* Можно использовать кастомную иконку */} 
                           {/* <ListIcon as={MdError} color="red.500" /> */}
                           {/* Отображаем description вместо field и message */}
                           {error.description}
                           {/* Можно добавить код закона и рекомендацию, если нужно */}
                           {/* {error.code && <Code ml={2}>{error.code}</Code>} */}
                           {/* {error.law && <Text fontSize="xs" color="gray.600">Закон: {error.law}</Text>} */}
                           {/* {error.recommendation && <Text fontSize="xs" color="blue.600">Рекомендация: {error.recommendation}</Text>} */}
                        </ListItem>
                    ))}
                </List>
            </AlertDescription>
        </Alert>
    );
}

export default ErrorDisplay; 