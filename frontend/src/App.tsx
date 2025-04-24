import { useState } from 'react';
import { Routes, Route, Link as RouterLink } from 'react-router-dom';
import CaseForm from './components/CaseForm';
import { ProcessResult, ApiError } from './components/CaseForm'; 
import ErrorDisplay from './components/ErrorDisplay'; 
import HistoryPage from './pages/HistoryPage';
import ProcessResultDisplay from './components/ProcessResultDisplay';

// Импорты Chakra UI
import {
  Box, 
  Container,
  Heading,
  Divider,
  useToast, 
  Alert,
  AlertIcon,
  AlertDescription,
  Link,
  Flex,
  Spacer,
  useColorMode,
  IconButton
} from '@chakra-ui/react';

// Импорт иконок для переключателя
import { SunIcon, MoonIcon } from '@chakra-ui/icons';

const API_BASE_URL = 'http://127.0.0.1:8000'; 

function App() {
  const [processResult, setProcessResult] = useState<ProcessResult | null>(null);

  const toast = useToast();
  const { colorMode, toggleColorMode } = useColorMode();

  const handleFormSubmitSuccess = (result: ProcessResult) => {
    console.log("Received result from backend:", result);
    setProcessResult(result);
    toast({ 
        title: "Анализ завершен",
        description: `Статус: ${result.status === 'approved' ? 'Одобрено' : 'Отказано'}`,
        status: result.status === 'approved' ? "success" : "error",
        duration: 5000,
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
    setProcessResult(null);
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
            <Box bg="cardBackground" p={6} borderRadius="md" shadow="md"> 
              <CaseForm 
                onSubmitSuccess={handleFormSubmitSuccess}
                onSubmitError={handleFormSubmitError}
              />
            </Box>

            {processResult && (
              <Box mt={6}>
                 <ProcessResultDisplay result={processResult} />
              </Box>
            )}
          </Box>
        } />

        <Route path="/history" element={<HistoryPage />} />
      </Routes>

    </Container>
  );
}

export default App;
