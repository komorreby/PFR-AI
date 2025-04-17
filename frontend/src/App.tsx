import { useState } from 'react';
import { Routes, Route, Link as RouterLink } from 'react-router-dom';
import CaseForm from './components/CaseForm';
import { ApiError } from './components/CaseForm'; 
import ErrorDisplay from './components/ErrorDisplay'; 
import HistoryPage from './pages/HistoryPage';

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
  Spacer
} from '@chakra-ui/react';

const API_BASE_URL = 'http://127.0.0.1:8000'; 

function App() {
  const [analysisErrors, setAnalysisErrors] = useState<ApiError[]>([]);
  const [formSubmittedSuccessfully, setFormSubmittedSuccessfully] = useState<boolean>(false);

  const toast = useToast();

  const handleFormSubmitSuccess = (errors: ApiError[]) => {
    console.log("Received errors from backend:", errors);
    setAnalysisErrors(errors);
    setFormSubmittedSuccessfully(true); 
    toast({ 
        title: "Анализ завершен",
        description: errors.length === 0 ? "Ошибок не найдено." : `Найдено ошибок: ${errors.length}`,
        status: errors.length === 0 ? "success" : "warning",
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
    setAnalysisErrors([]); 
    setFormSubmittedSuccessfully(false); 
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
      </Flex>
      <Divider mb={6}/>

      <Routes>
        <Route path="/" element={
          <Box>
            <Box bg="white" p={6} borderRadius="md" shadow="md"> 
              <CaseForm 
                onSubmitSuccess={handleFormSubmitSuccess}
                onSubmitError={handleFormSubmitError}
              />
            </Box>

            {formSubmittedSuccessfully && (
              <Box mt={6}>
                <ErrorDisplay errors={analysisErrors} />
              </Box>
            )}
            
            {formSubmittedSuccessfully && analysisErrors.length === 0 && (
                 <Alert status="success" variant="subtle" mt={6} borderRadius="md">
                     <AlertIcon />
                     <AlertDescription>Ошибок не найдено. Пенсия может быть предоставлена.</AlertDescription>
                 </Alert>
            )}
          </Box>
        } />

        <Route path="/history" element={<HistoryPage />} />
      </Routes>

    </Container>
  );
}

export default App;
