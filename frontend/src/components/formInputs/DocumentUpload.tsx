import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Select,
  Text,
  VStack,
  useToast,
  Spinner,
} from '@chakra-ui/react';
import { useDropzone } from 'react-dropzone';

interface DocumentUploadProps {
  onDocumentProcessed: (data: {
    extracted_text: string;
    extracted_fields: Record<string, string>;
  }) => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ onDocumentProcessed }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [documentType, setDocumentType] = useState('passport');
  const toast = useToast();

  const onDrop = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    // Проверяем тип файла
    if (!file.type.startsWith('image/')) {
      toast({
        title: 'Ошибка',
        description: 'Пожалуйста, загрузите изображение',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('document_type', documentType);

      const response = await fetch('http://localhost:8000/api/v1/ocr/upload_document', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Ошибка при обработке документа');
      }

      const data = await response.json();
      onDocumentProcessed(data);

      toast({
        title: 'Успех',
        description: 'Документ успешно обработан',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: 'Ошибка',
        description: error instanceof Error ? error.message : 'Произошла ошибка при обработке документа',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff']
    },
    maxFiles: 1,
  });

  return (
    <VStack spacing={4} align="stretch">
      <FormControl>
        <FormLabel>Тип документа</FormLabel>
        <Select
          value={documentType}
          onChange={(e) => setDocumentType(e.target.value)}
        >
          <option value="passport">Паспорт</option>
          {/* Можно добавить другие типы документов */}
        </Select>
      </FormControl>

      <Box
        {...getRootProps()}
        p={6}
        border="2px dashed"
        borderColor={isDragActive ? 'blue.400' : 'gray.200'}
        borderRadius="md"
        textAlign="center"
        cursor="pointer"
        _hover={{ borderColor: 'blue.400' }}
      >
        <input {...getInputProps()} />
        {isLoading ? (
          <Spinner size="xl" />
        ) : isDragActive ? (
          <Text>Отпустите файл здесь...</Text>
        ) : (
          <Text>Перетащите изображение документа сюда или нажмите для выбора</Text>
        )}
      </Box>
    </VStack>
  );
};

export default DocumentUpload; 