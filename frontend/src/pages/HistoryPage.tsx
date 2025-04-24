import React, { useState, useEffect, useMemo } from 'react';
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

const API_BASE_URL = 'http://127.0.0.1:8000';

function HistoryPage() {
    const [historyData, setHistoryData] = useState<HistoryEntry[]>([]);
    const [historyLoading, setHistoryLoading] = useState<boolean>(true);
    const [searchTerm, setSearchTerm] = useState('');
    const toast = useToast();

    const fetchHistory = async () => {
        setHistoryLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/history?limit=50`);
            if (response.ok) {
                const data: HistoryEntry[] = await response.json();
                setHistoryData(data);
            } else {
                toast({ 
                    title: "Ошибка загрузки истории",
                    description: `${response.status} ${response.statusText}`,
                    status: "error",
                    duration: 5000,
                    isClosable: true,
                });
            }
        } catch (error) {
            toast({ 
                title: "Сетевая ошибка",
                description: `Не удалось загрузить историю: ${error instanceof Error ? error.message : String(error)}`,
                status: "error",
                duration: 5000,
                isClosable: true,
            });
        } finally {
            setHistoryLoading(false);
        }
    };

    useEffect(() => {
        fetchHistory();
    }, []);

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
            const response = await fetch(`${API_BASE_URL}/download_document/${caseId}?format=${format}`);

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
                    title: "Сетевая ошибка", 
                    description: `Ошибка при скачивании файла: ${error instanceof Error ? error.message : String(error)}`, 
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
                    bg="white"
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