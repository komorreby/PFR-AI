import { useState, useEffect, useMemo, useCallback } from 'react';
import {
    Box,
    Container,
    Heading,
    Spinner,
    useToast,
    Input,
    InputGroup,
    InputLeftElement
} from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import HistoryList from '../components/HistoryList';
import { HistoryEntry } from '../components/HistoryList';
import { getHistory, downloadDocument } from '../api/client';

function HistoryPage() {
    const [historyData, setHistoryData] = useState<HistoryEntry[]>([]);
    const [historyLoading, setHistoryLoading] = useState<boolean>(true);
    const [searchTerm, setSearchTerm] = useState('');
    const toast = useToast();

    const fetchHistory = useCallback(async () => {
        setHistoryLoading(true);
        try {
            const data = await getHistory();
            setHistoryData(data);
        } catch (error) {
            toast({ 
                title: "Ошибка загрузки истории",
                description: `${error instanceof Error ? error.message : String(error)}`,
                status: "error",
                duration: 5000,
                isClosable: true,
            });
        } finally {
            setHistoryLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        fetchHistory();
    }, [fetchHistory]);

    const handleDownload = async (caseId: number, format: 'pdf' | 'docx') => {
        const toastId = toast({ 
            title: `Загрузка ${format.toUpperCase()}...`,
            description: `Запрос файла для дела #${caseId}`,
            status: "info",
            duration: null, 
            isClosable: false,
        });
        console.log(`Requesting download for case ${caseId}, format: ${format}`);
        try {
            const response = await downloadDocument(caseId, format);

            if (response.ok) {
                const disposition = response.headers.get('content-disposition');
                let filename = `pension_decision_${caseId}.${format}`;
                if (disposition && disposition.includes('attachment')) {
                    const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    const matches = filenameRegex.exec(disposition);
                    if (matches?.[1]) {
                        filename = matches[1].replace(/['"]/g, '');
                    }
                }
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', filename);
                document.body.appendChild(link);
                link.click();
                link.parentNode?.removeChild(link);
                window.URL.revokeObjectURL(url);
                if (toastId) {
                    toast.update(toastId, { 
                        title: "Файл скачан",
                        description: `Файл ${filename} успешно загружен.`, 
                        status: "success", 
                        duration: 3000, 
                        isClosable: true 
                    });
                }
            } else {
                const errorData = await response.json().catch(() => null);
                const errorDetail = errorData?.detail || `Ошибка ${response.status}`;
                if (toastId) {
                    toast.update(toastId, { 
                        title: "Ошибка скачивания", 
                        description: `Не удалось скачать файл: ${errorDetail}`, 
                        status: "error", 
                        duration: 5000, 
                        isClosable: true 
                    });
                }
                console.error("Download error:", response.status, response.statusText);
            }
        } catch (error) {
            if (toastId) {
                toast.update(toastId, { 
                    title: "Ошибка скачивания", 
                    description: `Не удалось скачать файл: ${error instanceof Error ? error.message : String(error)}`, 
                    status: "error", 
                    duration: 5000, 
                    isClosable: true 
                });
            }
            console.error("Download network error:", error);
        }
    };

    const filteredHistory = useMemo(() => {
        if (!searchTerm) {
            return historyData;
        }
        const lowerCaseSearchTerm = searchTerm.toLowerCase();
        return historyData.filter(entry => 
            entry.id.toString().includes(lowerCaseSearchTerm) ||
            entry.personal_data?.full_name?.toLowerCase().includes(lowerCaseSearchTerm)
        );
    }, [historyData, searchTerm]);

    return (
        <Container maxW="container.lg" py={8}>
            <Heading as="h2" size="lg" textAlign="center" mb={6} fontWeight="normal" color="gray.600">
                История обработанных дел
            </Heading>
            <InputGroup mb={6}>
                <InputLeftElement pointerEvents="none">
                     <SearchIcon color="gray.300" />
                </InputLeftElement>
                <Input 
                    placeholder="Поиск по ID или ФИО..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    bg="cardBackground"
                />
            </InputGroup>
            {historyLoading && (
                <Box textAlign="center" p={5}>
                    <Spinner size="xl" color="blue.500" />
                </Box>
            )}
            {!historyLoading && (
                <HistoryList history={filteredHistory} onDownload={handleDownload} />
            )}
        </Container>
    );
}

export default HistoryPage; 