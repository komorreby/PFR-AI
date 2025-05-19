import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  VStack,
  Text,
  Button,
  Spinner,
  Alert,
  AlertIcon,
  Image,
} from '@chakra-ui/react';
import { extractDocumentData } from '../../services/client';
import type { OcrExtractionResponse, OcrDocumentType } from '../../types';

interface OcrUploaderProps {
  documentType: OcrDocumentType;
  onOcrSuccess: (data: OcrExtractionResponse, docType: OcrDocumentType) => void;
  onOcrError: (message: string, docType: OcrDocumentType) => void;
  uploaderTitle?: string;
}

const OcrUploader = ({
  documentType,
  onOcrSuccess,
  onOcrError,
  uploaderTitle = 'Загрузите документ'
}: OcrUploaderProps) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      const acceptedMimeTypes = ['image/jpeg', 'image/png', 'application/pdf'];
      if (!acceptedMimeTypes.includes(file.type)) {
        setError(`Неподдерживаемый тип файла: ${file.type}. Пожалуйста, загрузите PNG, JPG или PDF.`);
        setSelectedFile(null);
        setFilePreview(null);
        return;
      }
      setError(null);
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setFilePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    multiple: false,
  });

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Пожалуйста, выберите файл для загрузки.');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const result = await extractDocumentData(selectedFile, documentType);
      console.log(`Raw OCR Result for ${documentType} from backend:`, JSON.stringify(result, null, 2));
      
      if (result.documentType === 'error') {
        const errorMessage = result.message || 'Ошибка OCR: Не удалось обработать документ.';
        console.error('OCR Error from backend:', result.errorDetails || errorMessage);
        setError(errorMessage);
        onOcrError(errorMessage, documentType);
      } else {
        onOcrSuccess(result, documentType);
      }
    } catch (e: any) {
      const errorMessage = e.message || 'Произошла неизвестная ошибка при обработке документа.';
      console.error('OCR Upload Error:', e);
      setError(errorMessage);
      onOcrError(errorMessage, documentType);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setFilePreview(null);
    setError(null);
  };

  return (
    <VStack spacing={3} align="stretch" borderWidth="1px" borderRadius="md" p={4} bg="gray.50" _dark={{bg: "gray.700"}}>
      <Text fontWeight="medium" textAlign="center" mb={2}>{uploaderTitle}</Text>
      
      <Box
        {...getRootProps()}
        p={5}
        border="2px dashed"
        borderColor={isDragActive ? 'blue.400' : (error ? 'red.400' : 'gray.300')}
        borderRadius="md"
        textAlign="center"
        cursor="pointer"
        _hover={{ borderColor: 'blue.300' }}
        bg={isDragActive ? 'blue.50' : 'transparent'}
        minH="120px"
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
      >
        <input {...getInputProps()} />
        {isDragActive ? (
          <Text>Отпустите файл здесь ...</Text>
        ) : selectedFile ? (
          <VStack spacing={1}>
            <Text fontSize="sm">Файл: {selectedFile.name}</Text>
            {filePreview && selectedFile.type.startsWith('image/') && (
              <Image src={filePreview} alt="Предпросмотр" boxSize="80px" objectFit="contain" my={1} />
            )}
            {filePreview && selectedFile.type === 'application/pdf' && (
                <Text fontSize="xs" color="gray.500">(Предпросмотр для PDF не отображается)</Text>
            )}
          </VStack>
        ) : (
          <Text fontSize="sm">Перетащите файл или нажмите для выбора (PNG, JPG, PDF)</Text>
        )}
      </Box>
      
      {selectedFile && !isLoading && (
        <Button onClick={handleRemoveFile} colorScheme="red" variant="outline" size="xs" mt={1}>
          Удалить файл
        </Button>
      )}

      {error && (
        <Alert status="error" mt={2} fontSize="sm">
          <AlertIcon />
          {error}
        </Alert>
      )}

      <Button
        onClick={handleUpload}
        isLoading={isLoading}
        isDisabled={!selectedFile || isLoading}
        colorScheme="primary"
        size="sm"
      >
        {isLoading ? <Spinner size="xs" /> : 'Распознать'}
      </Button>
      
      {isLoading && <Text textAlign="center" fontSize="xs" color="gray.500">Обработка...</Text>}
    </VStack>
  );
};

export default OcrUploader; 