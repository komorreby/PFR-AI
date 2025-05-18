import { useState } from 'react';
import { Routes, Route, Link as RouterLink } from 'react-router-dom';
import CaseForm from './components/CaseForm';
import { DocumentSetCheckResponse } from './components/CaseForm';
import HistoryPage from './pages/HistoryPage';
import DocumentCheckPage from './pages/DocumentCheckPage';

// Импорты Chakra UI
import {
  Box, 
  Container,
  Heading,
  Divider,
  useToast, 
  Link,
  Flex,
  Spacer,
  useColorMode,
  IconButton,
  useColorModeValue
} from '@chakra-ui/react';

// Импорт иконок для переключателя
import { SunIcon, MoonIcon } from '@chakra-ui/icons';

function App() {
  const toast = useToast();
  const { colorMode, toggleColorMode } = useColorMode();

  const handleFormSubmitSuccess = (result: DocumentSetCheckResponse) => {
    console.log("Received document check result from backend:", result);
    toast({ 
        title: "Проверка комплекта документов завершена",
        description: `Общий статус: ${result.overall_status}`,
        status: result.overall_status.toLowerCase().includes("требуются") || result.overall_status.toLowerCase().includes("ошибка") ? "warning" : "success",
        duration: 7000,
        isClosable: true,
    });
  };

  const handleFormSubmitError = (errorMessage: string) => {
    toast({ 
        title: "Ошибка отправки данных",
        description: errorMessage,
        status: "error",
        duration: 9000, 
        isClosable: true,
    });
  };

  return (
    <Container maxW="container.lg" py={8}>
      <Heading as="h1" size="xl" textAlign="center" mb={4} fontWeight="light"> 
        Анализ пенсионных дел (PFR-AI)
      </Heading>

      <Flex mb={6}>
        <Link as={RouterLink} to="/" fontWeight="bold" _hover={{ textDecoration: 'underline' }}>
            Ввод данных
        </Link>
        <Link as={RouterLink} to="/check-documents" fontWeight="bold" _hover={{ textDecoration: 'underline' }} ml={4}>
            Проверка комплекта
        </Link>
        <Spacer />
        <Link as={RouterLink} to="/history" fontWeight="bold" _hover={{ textDecoration: 'underline' }}>
            История
        </Link>
        <IconButton
          ml={4}
          onClick={toggleColorMode}
          icon={colorMode === 'light' ? <MoonIcon /> : <SunIcon />}
          aria-label={`Переключить на ${colorMode === 'light' ? 'темную' : 'светлую'} тему`}
          variant="ghost"
          size="sm"
        />
      </Flex>
      <Divider mb={6}/>

      <Routes>
        <Route path="/" element={
          <Box>
            <Box bg={useColorModeValue('white', 'gray.750')} p={6} borderRadius="md" shadow="md"> 
              <CaseForm 
                onSubmitSuccess={handleFormSubmitSuccess}
                onSubmitError={handleFormSubmitError}
              />
            </Box>
          </Box>
        } />

        <Route path="/history" element={<HistoryPage />} />
        <Route path="/check-documents" element={<DocumentCheckPage />} />
      </Routes>

    </Container>
  );
}

export default App;
