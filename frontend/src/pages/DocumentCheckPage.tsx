import React, { useState, useEffect, ChangeEvent, FormEvent } from 'react';
import { 
    Box, 
    Heading, 
    Select, 
    Button, 
    VStack, 
    FormControl, 
    FormLabel, 
    Input, 
    CheckboxGroup, 
    Checkbox, 
    Text, 
    Alert, 
    AlertIcon,
    Spinner,
    Code,
    useToast
} from '@chakra-ui/react';

// Типы данных, которые мы ожидаем от бэкенда
interface PensionType {
    [key: string]: string; 
}

interface OcrData {
    [key: string]: any;
}

interface CheckedDocumentInfo {
    id: string;
    name: string;
    status: string;
    description?: string | null;
    condition_text?: string | null;
    is_critical: boolean;
    ocr_data?: OcrData | null;
}

interface DocumentSetCheckResponse {
    pension_type_key: string;
    pension_display_name: string;
    pension_description: string;
    overall_status: string;
    checked_documents: CheckedDocumentInfo[];
    missing_critical_documents: string[];
    missing_other_documents: string[];
}

// Предполагаем, что у нас есть список всех возможных документов для чекбоксов
// В идеале, его тоже можно было бы получать с бэка или генерировать на основе PENSION_DOCUMENT_REQUIREMENTS
// Пока для простоты сделаем небольшой статический список, вам нужно будет его расширить или сделать динамическим
// Это должны быть ID документов, как в PENSION_DOCUMENT_REQUIREMENTS
const ALL_POSSIBLE_DOCUMENT_IDS: { id: string, name: string }[] = [
    // Общие документы, которые могут встречаться в разных типах пенсий
    { id: "application", name: "Заявление о назначении пенсии" },
    { id: "snils", name: "СНИЛС (общий, для пенсии по старости/инвалидности)" }, // Оставляем для других типов пенсий
    { id: "work_book", name: "Трудовая книжка (общая)" }, // Общая трудовая, если не указано чья
    { id: "mse_certificate", name: "Справка МСЭ" },
    { id: "birth_certificate_children", name: "Свидетельство о рождении ребенка (детей)"},
    { id: "military_id", name: "Военный билет"},
    { id: "marriage_certificate", name: "Свидетельство о браке/расторжении/смене имени"},
    { id: "salary_certificate_2002", name: "Справка о заработке за 60 месяцев до 01.01.2002"},
    { id: "special_work_conditions_proof", name: "Справка, уточняющая особый характер работы или условий труда"},
    { id: "residence_proof", name: "Документ, подтверждающий постоянное проживание в РФ"},
    
    // Специфичные документы для "Пенсии по случаю потери кормильца"
    // (Паспорт заявителя - applicant_passport_rf - обрабатывается через загрузку файла, поэтому его нет в чекбоксах)
    { id: "applicant_snils", name: "СНИЛС заявителя (для пенсии по потере кормильца)" },
    { id: "death_certificate", name: "Свидетельство о смерти кормильца" },
    { id: "relationship_proof", name: "Документы, подтверждающие родственные отношения с умершим" },
    { id: "deceased_work_book", name: "Трудовая книжка умершего кормильца" },
    { id: "deceased_snils", name: "СНИЛС умершего кормильца" },
    { id: "dependency_proof", name: "Документы, подтверждающие нахождение на иждивении" },

    // Добавьте сюда другие ID и названия документов, если они нужны для других типов пенсий
    // и должны выбираться чекбосом
];

const DocumentCheckPage: React.FC = () => {
    const [pensionTypes, setPensionTypes] = useState<PensionType>({});
    const [selectedPensionType, setSelectedPensionType] = useState<string>('');
    const [passportFile, setPassportFile] = useState<File | null>(null);
    const [uploadedDocumentIds, setUploadedDocumentIds] = useState<string[]>([]);
    
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [checkResult, setCheckResult] = useState<DocumentSetCheckResponse | null>(null);

    const toast = useToast();

    // Загрузка типов пенсий при монтировании компонента
    useEffect(() => {
        const fetchPensionTypes = async () => {
            try {
                // Убедитесь, что ваш FastAPI сервер запущен и доступен по этому адресу
                const response = await fetch('http://127.0.0.1:8000/api/v1/pension_types');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data: PensionType = await response.json();
                setPensionTypes(data);
                // Установить первый тип пенсии как выбранный по умолчанию, если список не пуст
                if (Object.keys(data).length > 0) {
                    setSelectedPensionType(Object.keys(data)[0]);
                }
            } catch (err) {
                console.error("Ошибка загрузки типов пенсий:", err);
                setError("Не удалось загрузить типы пенсий. Проверьте консоль для деталей.");
                toast({
                    title: "Ошибка загрузки",
                    description: "Не удалось загрузить справочник типов пенсий.",
                    status: "error",
                    duration: 5000,
                    isClosable: true,
                });
            }
        };
        fetchPensionTypes();
    }, [toast]);

    const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files[0]) {
            setPassportFile(event.target.files[0]);
        }
    };

    const handleCheckboxChange = (selectedIds: (string | number)[]) => {
        setUploadedDocumentIds(selectedIds as string[]);
    };

    const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!selectedPensionType) {
            toast({ title: "Ошибка", description: "Пожалуйста, выберите тип пенсии.", status: "warning", duration: 3000, isClosable: true });
            return;
        }

        setIsLoading(true);
        setError(null);
        setCheckResult(null);

        const formData = new FormData();
        formData.append('pension_type_key', selectedPensionType);
        if (passportFile) {
            formData.append('passport_file', passportFile);
        }
        // Собираем ID документов в строку, разделенную запятыми
        // Важно: имя параметра должно точно совпадать с тем, что ожидает FastAPI (uploaded_document_ids)
        if (uploadedDocumentIds.length > 0) {
             formData.append('uploaded_document_ids', uploadedDocumentIds.join(','));
        }
       

        try {
            const response = await fetch('http://127.0.0.1:8000/api/v1/check_document_set', {
                method: 'POST',
                body: formData, // FormData автоматически устанавливает Content-Type: multipart/form-data
            });

            const responseData = await response.json(); // Сначала получаем JSON

            if (!response.ok) {
                // Если есть detail в ошибке от FastAPI, используем его
                const errorMsg = responseData.detail || `HTTP error! status: ${response.status}`;
                throw new Error(errorMsg);
            }
            
            setCheckResult(responseData as DocumentSetCheckResponse);
            toast({
                title: "Проверка завершена",
                status: "success",
                duration: 3000,
                isClosable: true,
            });

        } catch (err: any) {
            console.error("Ошибка при проверке комплекта документов:", err);
            setError(err.message || "Произошла ошибка при отправке данных.");
            toast({
                title: "Ошибка проверки",
                description: err.message || "Не удалось проверить комплект документов.",
                status: "error",
                duration: 5000,
                isClosable: true,
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Box>
            <Heading as="h2" size="lg" mb={6} textAlign="center">Проверка комплектности документов</Heading>
            <form onSubmit={handleSubmit}>
                <VStack spacing={4} align="stretch">
                    <FormControl isRequired>
                        <FormLabel htmlFor="pensionType">Тип пенсии</FormLabel>
                        <Select 
                            id="pensionType" 
                            placeholder="Выберите тип пенсии" 
                            value={selectedPensionType}
                            onChange={(e) => setSelectedPensionType(e.target.value)}
                        >
                            {Object.entries(pensionTypes).map(([key, name]) => (
                                <option key={key} value={key}>{name}</option>
                            ))}
                        </Select>
                    </FormControl>

                    <FormControl>
                        <FormLabel htmlFor="passportFile">Файл паспорта (для OCR)</FormLabel>
                        <Input id="passportFile" type="file" onChange={handleFileChange} accept=".png,.jpg,.jpeg,.pdf" p={1} />
                    </FormControl>

                    <FormControl>
                        <FormLabel>Другие предоставленные документы (отметьте)</FormLabel>
                        <CheckboxGroup colorScheme="blue" onChange={handleCheckboxChange} value={uploadedDocumentIds}>
                            <VStack align="start" spacing={1}>
                                {ALL_POSSIBLE_DOCUMENT_IDS.map(doc => (
                                    <Checkbox key={doc.id} value={doc.id}>{doc.name}</Checkbox>
                                ))}
                            </VStack>
                        </CheckboxGroup>
                    </FormControl>

                    <Button type="submit" colorScheme="blue" isLoading={isLoading} loadingText="Проверка...">
                        Проверить комплект
                    </Button>
                </VStack>
            </form>

            {isLoading && <Spinner mt={4} />}
            
            {error && (
                <Alert status="error" mt={4}>
                    <AlertIcon />
                    {error}
                </Alert>
            )}

            {checkResult && (
                <Box mt={6} p={4} borderWidth="1px" borderRadius="md">
                    <Heading as="h3" size="md" mb={3}>Результат проверки</Heading>
                    <Text><strong>Тип пенсии:</strong> {checkResult.pension_display_name}</Text>
                    <Text><strong>Общий статус:</strong> {checkResult.overall_status}</Text>
                    
                    <Heading as="h4" size="sm" mt={4} mb={2}>Детали по документам:</Heading>
                    {checkResult.checked_documents.map(doc => (
                        <Box key={doc.id} mb={3} p={3} borderWidth="1px" borderRadius="sm">
                            <Text><strong>{doc.name}</strong> (ID: {doc.id})</Text>
                            <Text>Статус: {doc.status}</Text>
                            {doc.description && <Text fontSize="sm">Описание: {doc.description}</Text>}
                            {doc.condition_text && <Text fontSize="sm" color="gray.500">Условие: {doc.condition_text}</Text>}
                            <Text>Критичность: {doc.is_critical ? "Да" : "Нет"}</Text>
                            {doc.ocr_data && (
                                <Box mt={2}>
                                    <Text fontWeight="bold">Данные из OCR:</Text>
                                    <Code display="block" whiteSpace="pre" p={2} overflowX="auto">
                                        {JSON.stringify(doc.ocr_data, null, 2)}
                                    </Code>
                                </Box>
                            )}
                        </Box>
                    ))}

                    {checkResult.missing_critical_documents.length > 0 && (
                        <Box mt={3}>
                            <Text fontWeight="bold" color="red.500">Отсутствуют критичные документы:</Text>
                            <ul>
                                {checkResult.missing_critical_documents.map(name => <li key={name}>{name}</li>)}
                            </ul>
                        </Box>
                    )}
                     {checkResult.missing_other_documents.length > 0 && (
                        <Box mt={3}>
                            <Text fontWeight="bold" color="orange.500">Отсутствуют другие документы:</Text>
                            <ul>
                                {checkResult.missing_other_documents.map(name => <li key={name}>{name}</li>)}
                            </ul>
                        </Box>
                    )}
                </Box>
            )}
        </Box>
    );
};

export default DocumentCheckPage; 