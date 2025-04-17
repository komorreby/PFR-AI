import React, { useState } from 'react';
import { useForm, useFieldArray, SubmitHandler, FieldErrors } from 'react-hook-form';
import { format, isValid, differenceInYears } from 'date-fns';

// Импорты Chakra UI (оставляем только нужные для обертки формы и навигации)
import {
  Box, Button, Heading, Stepper, Step, StepIndicator, StepStatus,
  StepIcon, StepNumber, StepTitle, StepDescription, StepSeparator,
  Flex, Spacer, useSteps,
  // Добавляем нужные компоненты для вывода результата
  Alert, AlertIcon, AlertTitle, AlertDescription, CircularProgress, Text, VStack
} from '@chakra-ui/react';

// Импортируем типы и компоненты шагов
import PersonalDataStep from './formSteps/PersonalDataStep';
import WorkExperienceStep from './formSteps/WorkExperienceStep';
import AdditionalInfoStep from './formSteps/AdditionalInfoStep';

// Определяем типы для данных формы, основываясь на Pydantic моделях
// (Упрощенно, без дат как Date объектов пока, используем string)
type NameChangeInfoType = {
  old_full_name: string;
  date_changed: string;
};

type PersonalDataType = {
  full_name: string;
  birth_date: string;
  snils: string;
  gender: string; // 'male' | 'female' | ''; // Можно использовать Enum
  citizenship: string;
  name_change_info: NameChangeInfoType | null; // null если нет
  dependents: number;
};

type WorkRecordType = {
  organization: string;
  start_date: string;
  end_date: string;
  position: string;
  special_conditions: boolean;
};

type WorkExperienceType = {
  total_years: number;
  records: WorkRecordType[];
};

// Полный тип данных формы
export type CaseFormDataType = {
  personal_data: PersonalDataType;
  work_experience: WorkExperienceType;
  pension_points: number;
  benefits: string; // Будем хранить как строку, разделим при отправке
  documents: string; // Будем хранить как строку, разделим при отправке
  has_incorrect_document: boolean;
};

// Определяем тип для ошибок (соответствует ErrorOutput в бэкенде)
export type ApiError = {
  code: string;
  description: string;
  law: string;
  recommendation: string;
};

// Пропсы компонента: добавляем колбэки
interface CaseFormProps {
  onSubmitSuccess: (errors: ApiError[]) => void;
  onSubmitError: (errorMessage: string) => void;
}

// Определяем шаги для Stepper
const steps = [
  { title: 'Шаг 1', description: 'Личные данные' },
  { title: 'Шаг 2', description: 'Трудовой стаж' },
  { title: 'Шаг 3', description: 'Доп. информация' },
];

// Функция для вычисления возраста
const calculateAge = (birthDateString: string): number | string => {
  try {
    const birthDate = new Date(birthDateString);
    if (isValid(birthDate)) {
      return differenceInYears(new Date(), birthDate);
    }
  } catch (e) {
    // ignore
  }
  return 'неизвестно'; // Возвращаем строку, если дата некорректна
};

function CaseForm({ onSubmitSuccess, onSubmitError }: CaseFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  // --- Состояния для RAG анализа --- 
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  // ----------------------------------

  const { activeStep, goToNext, goToPrevious, setActiveStep } = useSteps({ index: 0, count: steps.length });

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isDirty },
    watch,
    trigger,
    getValues,
    setValue
  } = useForm<CaseFormDataType>({
    mode: 'onBlur',
    defaultValues: {
      personal_data: {
        full_name: '',
        birth_date: '',
        snils: '',
        gender: '',
        citizenship: '',
        name_change_info: null,
        dependents: 0,
      },
      work_experience: {
        total_years: 0,
        records: [],
      },
      pension_points: 0,
      benefits: '',
      documents: '',
      has_incorrect_document: false,
    },
  });

  const fieldArray = useFieldArray({ control, name: "work_experience.records" });

  const onSubmit: SubmitHandler<CaseFormDataType> = async (data) => {
    setIsSubmitting(true);
    onSubmitError('');
    setAnalysisResult(null);
    setAnalysisError(null);
    const dataToSend = JSON.parse(JSON.stringify(data));
    dataToSend.benefits = (data.benefits || '').split(',').map(s => s.trim()).filter(Boolean);
    dataToSend.documents = (data.documents || '').split(',').map(s => s.trim()).filter(Boolean);
    if (dataToSend.personal_data.name_change_info && !dataToSend.personal_data.name_change_info.old_full_name && !dataToSend.personal_data.name_change_info.date_changed) {
        dataToSend.personal_data.name_change_info = null;
    }
    try {
      const response = await fetch('http://127.0.0.1:8000/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(dataToSend),
      });
      if (response.ok) {
        const result: { errors: ApiError[] } = await response.json();
        onSubmitSuccess(result.errors || []);
        setActiveStep(0);
      } else {
        let errorDetail = `Ошибка ${response.status}: ${response.statusText}`;
        try {
            const errorData = await response.json();
            errorDetail = errorData.detail || JSON.stringify(errorData);
        } catch (jsonError) { /* ignore */ }
        onSubmitError(`Ошибка отправки данных: ${errorDetail}`);
      }
    } catch (error) {
      onSubmitError(`Сетевая ошибка или другая проблема: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getErrorMessage = (fieldName: string): string | undefined => {
    const keys = fieldName.split('.');
    let error = errors as any;
    for (const key of keys) {
      if (!error || !error[key]) return undefined;
      error = error[key];
    }
    return error?.message;
  };

  const handleNext = async () => {
    let fieldsToValidate: string[] = [];
    const currentValues = getValues();

    if (activeStep === 0) {
        fieldsToValidate = [
            'personal_data.full_name', 'personal_data.birth_date', 'personal_data.snils',
            'personal_data.gender', 'personal_data.citizenship', 'personal_data.dependents'
        ];
        if (currentValues.personal_data.name_change_info) {
             fieldsToValidate.push(
                 'personal_data.name_change_info.old_full_name',
                 'personal_data.name_change_info.date_changed'
             );
        }
    } else if (activeStep === 1) {
       fieldsToValidate = ['work_experience.total_years'];
       currentValues.work_experience.records.forEach((_, index) => {
           fieldsToValidate.push(
               `work_experience.records.${index}.organization`,
               `work_experience.records.${index}.start_date`,
               `work_experience.records.${index}.end_date`,
               `work_experience.records.${index}.position`
           );
       });
    } else if (activeStep === 2) {
       fieldsToValidate = ['pension_points', 'benefits', 'documents'];
    }
    const isValidStep = await trigger(fieldsToValidate as any);
    if (isValidStep) {
      goToNext();
    }
  };

  // --- НОВЫЙ Обработчик для RAG анализа --- 
  const handleAnalyzeCase = async () => {
      setIsLoadingAnalysis(true);
      setAnalysisResult(null);
      setAnalysisError(null);
      onSubmitError(''); // Сброс основной ошибки

      try {
          const formData = getValues();
          // Формируем описание дела (упрощенный вариант)
          const genderText = formData.personal_data.gender === 'male' ? 'Мужчина' : formData.personal_data.gender === 'female' ? 'Женщина' : 'Пол не указан';
          const age = calculateAge(formData.personal_data.birth_date);
          const incorrectDocsText = formData.has_incorrect_document ? 'Есть некорректные документы' : 'Документы в порядке';
          // TODO: Добавить тип пенсии, если будет такое поле
          const case_description = [
              `${genderText}, ${age} лет`,
              `пенсия по старости`, // Заглушка
              `стаж ${formData.work_experience.total_years} лет`,
              `ИПК ${formData.pension_points}`,
              `${incorrectDocsText}`,
              `Гражданство: ${formData.personal_data.citizenship || 'не указано'}`,
              `Иждивенцы: ${formData.personal_data.dependents}`,
          ].join(', ');

          console.log("Sending for RAG analysis:", case_description);

          const response = await fetch('http://127.0.0.1:8000/api/v1/analyze_case', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
              body: JSON.stringify({ case_description }), // Отправляем объект
          });

          if (response.ok) {
              const result: { analysis_result: string } = await response.json();
              setAnalysisResult(result.analysis_result);
          } else {
              let errorDetail = `Ошибка ${response.status}: ${response.statusText}`;
              try {
                  const errorData = await response.json();
                  errorDetail = errorData.detail || JSON.stringify(errorData);
              } catch (jsonError) { /* ignore */ }
              console.error("RAG Analysis Error:", errorDetail);
              setAnalysisError(`Ошибка RAG-анализа: ${errorDetail}`);
          }
      } catch (error) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          console.error("Network/Fetch Error during RAG analysis:", errorMessage);
          setAnalysisError(`Сетевая ошибка или другая проблема при RAG-анализе: ${errorMessage}`);
      } finally {
          setIsLoadingAnalysis(false);
      }
  };
  // ------------------------------------------

  return (
    <Box as="form" onSubmit={handleSubmit(onSubmit)} p={5} borderWidth="1px" borderRadius="lg" boxShadow="md" bg="white">
       <Heading as="h2" size="lg" textAlign="center" mb={6} color="primary">
         Ввод данных пенсионного дела
       </Heading>

        <Stepper index={activeStep} mb={8} colorScheme="blue">
            {steps.map((step, index) => (
                <Step key={index} onClick={() => setActiveStep(index)} cursor="pointer">
                    <StepIndicator>
                        <StepStatus
                        complete={<StepIcon />}
                        incomplete={<StepNumber />}
                        active={<StepNumber />}
                        />
                    </StepIndicator>
                    <Box flexShrink='0'><StepTitle>{step.title}</StepTitle><StepDescription>{step.description}</StepDescription></Box>
                    <StepSeparator />
                </Step>
             ))}
        </Stepper>

        <Box mb={8}>
           {activeStep === 0 && (
               <PersonalDataStep 
                   control={control} 
                   register={register} 
                   errors={errors} 
                   watch={watch}
                   setValue={setValue}
                   getErrorMessage={getErrorMessage} 
               />
           )}
           {activeStep === 1 && (
               <WorkExperienceStep 
                   control={control} 
                   register={register} 
                   errors={errors} 
                   fieldArray={fieldArray} 
                   getErrorMessage={getErrorMessage}
                   getValues={getValues}
               />
           )}
            {activeStep === 2 && (
               <AdditionalInfoStep 
                   register={register} 
                   errors={errors} 
                   getErrorMessage={getErrorMessage} 
               />
           )}
        </Box>

        <VStack spacing={4} align="stretch">
            <Flex>
                <Button onClick={goToPrevious} isDisabled={activeStep === 0} variant="outline">Назад</Button>
                <Spacer />
                {activeStep < steps.length - 1 && (
                    <Button onClick={handleNext} colorScheme="blue">Далее</Button>
                )}
                {activeStep === steps.length - 1 && (
                    <>
                        <Button
                            onClick={handleAnalyzeCase}
                            isLoading={isLoadingAnalysis}
                            isDisabled={isLoadingAnalysis || isSubmitting}
                            colorScheme="teal"
                            variant="outline"
                            mr={3}
                        >
                            Провести RAG-анализ
                        </Button>
                        <Button 
                            type="submit" 
                            isLoading={isSubmitting} 
                            isDisabled={!isDirty || isSubmitting || isLoadingAnalysis}
                            colorScheme="primary"
                        >
                            Отправить на проверку
                        </Button>
                    </>
                )}
            </Flex>

            {isLoadingAnalysis && (
                <Flex justify="center" align="center" direction="column" p={4}>
                    <CircularProgress isIndeterminate color="teal.300" />
                    <Text mt={2} color="gray.500">Выполняется RAG-анализ...</Text>
                </Flex>
            )}
            {analysisError && (
                <Alert status="error" mt={4}>
                    <AlertIcon />
                    <Box>
                       <AlertTitle>Ошибка RAG-анализа!</AlertTitle>
                       <AlertDescription>{analysisError}</AlertDescription>
                    </Box>
                </Alert>
            )}
            {analysisResult && !isLoadingAnalysis && (
                <Alert status="info" mt={4} variant="subtle">
                    <AlertIcon />
                    <Box>
                        <AlertTitle>Результат RAG-анализа:</AlertTitle>
                        <AlertDescription whiteSpace="pre-wrap">
                            {analysisResult}
                        </AlertDescription>
                    </Box>
                </Alert>
            )}
        </VStack>
    </Box>
  );
}

export default CaseForm; 