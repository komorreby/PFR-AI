import React, { useState, useEffect } from 'react';
import { useForm, useFieldArray, SubmitHandler } from 'react-hook-form';
// import { isValid, differenceInYears } from 'date-fns';

// Импорты Chakra UI (оставляем только нужные для обертки формы и навигации)
import {
  Box, Button, Heading, Stepper, Step, StepIndicator, StepStatus,
  StepIcon, StepNumber, StepTitle, StepDescription, StepSeparator,
  Flex, Spacer, useSteps,
  // Добавляем нужные компоненты для вывода результата
  Alert, AlertIcon, AlertTitle, AlertDescription, CircularProgress, Text, VStack,
  // <<< Новые импорты для RAG-результата
  IconButton,
  useClipboard, // Хук для копирования
  ListItem, Text as ChakraText, Heading as ChakraHeading, OrderedList, UnorderedList
} from '@chakra-ui/react';

// <<< Импорт иконок для кнопок навигации и RAG
import { ArrowBackIcon, ArrowForwardIcon, CopyIcon, InfoIcon } from '@chakra-ui/icons';
// <<< Импорт функций API клиента
import { processCase, analyzeCase } from '../api/client';
// <<< Импорт новой утилиты
import { createComprehensiveRagDescription } from '../utils';
// <<< Импорт ReactMarkdown
import ReactMarkdown from 'react-markdown';

// Импортируем типы и компоненты шагов
import PersonalDataStep from './formSteps/PersonalDataStep';
import WorkExperienceStep from './formSteps/WorkExperienceStep';
import AdditionalInfoStep from './formSteps/AdditionalInfoStep';
import PensionTypeStep from './formSteps/PensionTypeStep';
import DisabilityInfoStep from './formSteps/DisabilityInfoStep';
import SummaryStep from './formSteps/SummaryStep';

// Определяем типы для данных формы, основываясь на Pydantic моделях
// (Упрощенно, без дат как Date объектов пока, используем string)
type NameChangeInfoType = {
  old_full_name: string;
  date_changed: string;
};

export type PersonalDataType = {
  last_name: string;  // Фамилия
  first_name: string; // Имя
  middle_name?: string; // Отчество (опционально)
  birth_date: string;
  snils: string;
  gender: string; // 'male' | 'female' | ''; // Можно использовать Enum
  citizenship: string;
  name_change_info: NameChangeInfoType | null; // null если нет
  dependents: number;
};

// <<< Добавляем export
export type WorkRecordType = {
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

type DisabilityInfoType = {
    group: string; // "1", "2", "3", "child"
    date: string; // "YYYY-MM-DD"
    cert_number?: string;
};

// Полный тип данных формы
export type CaseFormDataType = {
  pension_type: string;
  personal_data: PersonalDataType;
  work_experience: WorkExperienceType;
  pension_points: number;
  benefits: string; // Будем хранить как строку, разделим при отправке
  documents: string; // Будем хранить как строку, разделим при отправке
  has_incorrect_document: boolean;
  disability?: DisabilityInfoType; // <<< Добавляем опциональное поле для данных об инвалидности
};

// Определяем тип для ошибок (соответствует ErrorOutput в бэкенде)
export type ApiError = {
  code: string;
  description: string;
  law: string;
  recommendation: string;
};

// <<< Определяем тип для полного ответа от /process
export type ProcessResult = {
  errors: ApiError[];
  status: 'approved' | 'rejected';
  explanation: string;
};

// Пропсы компонента: добавляем колбэки
interface CaseFormProps {
  onSubmitSuccess: (result: ProcessResult) => void; // <<< Используем новый тип ProcessResult
  onSubmitError: (errorMessage: string) => void;
}

// <<< Определяем интерфейс для описания шага
interface StepDefinition {
  id: string; // Уникальный идентификатор шага
  title: string;
  description: string;
  component: React.FC<any>; // Компонент для рендера
  fieldsToValidate?: (keyof CaseFormDataType | string)[]; // Поля для валидации на этом шаге (может быть сложнее)
}

// <<< Определяем полные последовательности шагов
const stepDefinitions: { [key: string]: StepDefinition } = {
  pensionType: { id: 'pensionType', title: 'Шаг 1', description: 'Тип пенсии', component: PensionTypeStep },
  personalData: { id: 'personalData', title: 'Шаг 2', description: 'Личные данные', component: PersonalDataStep },
  workExperience: { id: 'workExperience', title: 'Шаг 3', description: 'Трудовой стаж', component: WorkExperienceStep },
  disabilityInfo: { id: 'disabilityInfo', title: 'Шаг 3', description: 'Инвалидность', component: DisabilityInfoStep },
  additionalInfo: { id: 'additionalInfo', title: 'Шаг 4', description: 'Доп. инфо', component: AdditionalInfoStep },
  summary: { id: 'summary', title: 'Шаг 5', description: 'Сводка', component: SummaryStep },
};

// Функция для получения последовательности шагов по типу пенсии
const getStepsForPensionType = (type: string | null): StepDefinition[] => {
  const baseSequence = [stepDefinitions.pensionType, stepDefinitions.personalData];
  if (!type) {
    return [stepDefinitions.pensionType];
  }
  switch (type) {
    case 'retirement_standard':
      return [
        ...baseSequence,
        stepDefinitions.workExperience,
        stepDefinitions.additionalInfo,
        stepDefinitions.summary
      ];
    case 'disability_social':
      return [
        ...baseSequence,
        stepDefinitions.disabilityInfo,
        stepDefinitions.additionalInfo,
        stepDefinitions.summary
      ];
    default:
      return [stepDefinitions.pensionType];
  }
};

// // Функция для вычисления возраста
// const calculateAge = (birthDateString: string): number | string => {
//   try {
//     const birthDate = new Date(birthDateString);
//     if (isValid(birthDate)) {
//       return differenceInYears(new Date(), birthDate);
//     }
//   } catch (e) {
//     // ignore
//   }
//   return 'неизвестно'; // Возвращаем строку, если дата некорректна
// };

function CaseForm({ onSubmitSuccess, onSubmitError }: CaseFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedPensionType, setSelectedPensionType] = useState<string | null>(null);
  const [pensionTypeError, setPensionTypeError] = useState<string | null>(null);
  // --- Состояния для RAG анализа --- 
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  // <<< Добавляем состояние для confidence score
  const [confidenceScore, setConfidenceScore] = useState<number | null>(null);
  // <<< Используем хук useClipboard для результата RAG
  const { hasCopied, onCopy } = useClipboard(analysisResult || '');
  // ----------------------------------

  // <<< Состояние для текущей последовательности шагов
  const [currentSteps, setCurrentSteps] = useState<StepDefinition[]>(() => getStepsForPensionType(null));

  // <<< Обновляем useSteps при изменении currentSteps
  const { activeStep, goToNext, goToPrevious, setActiveStep } = useSteps({
    index: 0,
    count: currentSteps.length,
  });

  useEffect(() => {
    // Если шаги изменились, а активный шаг выходит за пределы, сбрасываем на последний
    if (activeStep >= currentSteps.length) {
        setActiveStep(currentSteps.length - 1);
    }
    // Примечание: Простое изменение count в useSteps не работает, хук нужно пересоздавать
    // или использовать setActiveStep для коррекции. Оставляем так для простоты.
  }, [currentSteps, activeStep, setActiveStep]);

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
      pension_type: '',
      personal_data: {
        last_name: '',  
        first_name: '', 
        middle_name: '',
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
      disability: undefined, // <<< Начальное значение для инвалидности
    },
  });

  const fieldArray = useFieldArray({ control, name: "work_experience.records" });

  const onSubmit: SubmitHandler<CaseFormDataType> = async (data) => {
    console.log("onSubmit triggered"); // <<< Добавляем лог
    setIsSubmitting(true);
    onSubmitError('');
    setAnalysisResult(null);
    setAnalysisError(null);
    setConfidenceScore(null); // <<< Сбрасываем скор при новой отправке
    const dataToSend = JSON.parse(JSON.stringify(data));
    dataToSend.benefits = (data.benefits || '').split(',').map(s => s.trim()).filter(Boolean);
    dataToSend.documents = (data.documents || '').split(',').map(s => s.trim()).filter(Boolean);
    dataToSend.pension_type = selectedPensionType || '';
    if (dataToSend.personal_data.name_change_info && !dataToSend.personal_data.name_change_info.old_full_name && !dataToSend.personal_data.name_change_info.date_changed) {
        dataToSend.personal_data.name_change_info = null;
    }

    // --- Преобразование данных для эндпоинта /process --- 
    const payloadForProcess = JSON.parse(JSON.stringify(dataToSend)); // Снова глубокая копия
    payloadForProcess.personal_data.full_name = [
        payloadForProcess.personal_data.last_name,
        payloadForProcess.personal_data.first_name,
        payloadForProcess.personal_data.middle_name
    ].filter(Boolean).join(' ');
    // Удаляем раздельные поля
    delete payloadForProcess.personal_data.last_name;
    delete payloadForProcess.personal_data.first_name;
    delete payloadForProcess.personal_data.middle_name;
    // ----------------------------------------------------

    try {
      // <<< Отправляем преобразованный payloadForProcess
      const result = await processCase(payloadForProcess); 
      onSubmitSuccess(result); // <<< Передаем весь результат
      setActiveStep(0); // Сбрасываем на первый шаг после успешной отправки
      setSelectedPensionType(null); // Сбрасываем тип пенсии
      // TODO: Возможно, нужно сбросить и сами данные формы?
    } catch (error) {
       // <<< Ошибка теперь приходит из handleResponse
      onSubmitError(`Ошибка отправки данных: ${error instanceof Error ? error.message : String(error)}`);
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

  // <<< Обработчик изменения типа пенсии: обновляет шаги
  const handlePensionTypeChange = (value: string) => {
    setSelectedPensionType(value);
    setPensionTypeError(null);
    const newSteps = getStepsForPensionType(value);
    setCurrentSteps(newSteps);
    setValue('pension_type', value);
    // Сбрасываем на первый шаг ПОСЛЕ выбора типа (т.е. на Личные данные)
    // Но только если мы были на шаге выбора типа
    if (activeStep === 0) {
        setActiveStep(1); // Переходим ко второму шагу в новой последовательности
    }
  };

  const handleNext = async () => {
    let isValidStep = true;
    setPensionTypeError(null);

    const currentStepDefinition = currentSteps[activeStep];
    const currentValues = getValues(); // Получаем текущие значения для динамической валидации
    let fieldsToValidate: (keyof CaseFormDataType | string)[] = []; // Массив полей для trigger

    // <<< Логика валидации на основе ID шага
    if (currentStepDefinition.id === 'pensionType') {
        if (!selectedPensionType) {
            isValidStep = false;
            setPensionTypeError('Пожалуйста, выберите тип пенсии');
        } else {
             // Действий не требуется, тип установлен
        }
    } else if (currentStepDefinition.id === 'personalData') {
        fieldsToValidate = [
            'personal_data.last_name', 'personal_data.first_name', 
            'personal_data.birth_date', 'personal_data.snils',
            'personal_data.gender', 'personal_data.citizenship', 'personal_data.dependents'
        ];
        // Валидация полей смены ФИО, если они есть
        if (currentValues.personal_data.name_change_info) {
             fieldsToValidate.push(
                 'personal_data.name_change_info.old_full_name',
                 'personal_data.name_change_info.date_changed'
             );
        }
    } else if (currentStepDefinition.id === 'workExperience') {
       fieldsToValidate = ['work_experience.total_years'];
       // Динамическая валидация записей о стаже
       currentValues.work_experience.records.forEach((_, index) => {
           fieldsToValidate.push(
               `work_experience.records.${index}.organization`,
               `work_experience.records.${index}.start_date`,
               `work_experience.records.${index}.end_date`,
               `work_experience.records.${index}.position`
               // `work_experience.records.${index}.special_conditions` - обычно boolean, валидация не так критична
           );
       });
    } else if (currentStepDefinition.id === 'disabilityInfo') {
        fieldsToValidate = ['disability.group', 'disability.date'];
        // 'disability.cert_number' - опциональное, не валидируем
    } else if (currentStepDefinition.id === 'additionalInfo') {
       fieldsToValidate = ['pension_points', 'benefits', 'documents'];
       // 'has_incorrect_document' - boolean
    }
    // Шаг сводки валидации не требует, поэтому здесь нет блока для summary

    // <<< Выполняем trigger, если есть поля для валидации
    if (fieldsToValidate.length > 0) {
        try {
            isValidStep = await trigger(fieldsToValidate as any);
            console.log(`Validation for step ${currentStepDefinition.id}: ${isValidStep}`, fieldsToValidate);
        } catch (e) {
            console.error("Validation error:", e);
            isValidStep = false; // Считаем невалидным при ошибке trigger
        }
    }

    if (isValidStep) {
      if (activeStep < currentSteps.length - 1) {
          goToNext();
      }
    }
  };

  const handlePrevious = () => {
    goToPrevious();
  };

  // <<< Функция для запуска RAG анализа
  const handleAnalyzeCase = async () => {
    console.log("Analyzing case...");
    setIsLoadingAnalysis(true);
    setAnalysisResult(null);
    setAnalysisError(null);
    setConfidenceScore(null); 

    try {
      const currentData = getValues();
      
      // <<< Применяем ту же логику подготовки данных, что и в onSubmit >>>
      const dataToSend = JSON.parse(JSON.stringify(currentData)); // Глубокая копия
      // Преобразуем строки в массивы (если они не пустые)
      dataToSend.benefits = (currentData.benefits || '').split(',').map(s => s.trim()).filter(Boolean);
      dataToSend.documents = (currentData.documents || '').split(',').map(s => s.trim()).filter(Boolean);
      // Убедимся, что тип пенсии установлен (хотя он должен быть в currentData, но для надежности)
      dataToSend.pension_type = selectedPensionType || currentData.pension_type || ''; 
      // Обрабатываем пустой объект смены ФИО
      if (dataToSend.personal_data.name_change_info && !dataToSend.personal_data.name_change_info.old_full_name && !dataToSend.personal_data.name_change_info.date_changed) {
          dataToSend.personal_data.name_change_info = null;
      }
      // <<< КОНЕЦ логики подготовки данных >>>

      console.log("Sending prepared data to /api/v1/analyze_case:", dataToSend);

      // <<< Вызываем analyzeCase, передавая подготовленный объект dataToSend >>>
      const response = await analyzeCase(dataToSend); 
      console.log("RAG response:", response);

      setAnalysisResult(response.analysis_result); 
      setConfidenceScore(response.confidence_score); 

    } catch (error: any) {
      // <<< Логируем исходную ошибку для диагностики >>>
      console.error("RAG Analysis error (raw):", error);
      // Формируем сообщение об ошибке
      let errorMessage = 'Не удалось выполнить RAG-анализ.';
      if (error instanceof Error) {
          errorMessage = error.message;
      } else if (typeof error === 'string') {
          errorMessage = error;
      }
      // Пытаемся извлечь детали из 422 ошибки, если они есть
      if (error?.response?.data?.detail) {
          try {
              const details = JSON.stringify(error.response.data.detail);
              errorMessage += `: ${details}`;
          } catch (_) { /* ignore stringify error */ }
      } else if (error?.message) {
           // Уже содержит сообщение из handleResponse
      }
      console.error("RAG Analysis error (processed message):", errorMessage);
      setAnalysisError(errorMessage); 
      setAnalysisResult(null);
      setConfidenceScore(null); 
    } finally {
      setIsLoadingAnalysis(false);
    }
  };

  // --- Отображение текущего шага --- 
  const renderStepContent = () => {
    if (activeStep >= currentSteps.length || activeStep < 0) {
        // Обработка случая, когда activeStep некорректен
        console.warn("Invalid active step index:", activeStep, "for steps count:", currentSteps.length);
        return <Text color="red.500">Ошибка отображения шага.</Text>;
    }

    const CurrentComponent = currentSteps[activeStep].component;
    const stepId = currentSteps[activeStep].id;

    // <<< Передаем пропсы в зависимости от компонента
    // TODO: Сделать более строго типизированным
    const commonProps = { register, errors, control, getValues, setValue, getErrorMessage, watch };

    if (stepId === 'pensionType') {
        return (
            <CurrentComponent
                selectedValue={selectedPensionType}
                onChange={handlePensionTypeChange} // <<< Передаем новый обработчик
                errorMessage={pensionTypeError || undefined}
            />
        );
    } else if (stepId === 'personalData') {
        return <CurrentComponent {...commonProps} errors={errors.personal_data || {}} />;
    } else if (stepId === 'workExperience') {
        return <CurrentComponent {...commonProps} errors={errors.work_experience || {}} fieldArray={fieldArray} />;
    } else if (stepId === 'disabilityInfo') {
        return <CurrentComponent {...commonProps} errors={errors.disability || {}} />;
    } else if (stepId === 'additionalInfo') {
        return <CurrentComponent {...commonProps} pensionType={selectedPensionType} />;
    } else if (stepId === 'summary') {
        return <CurrentComponent formData={getValues()} />;
    }

    return <Text>Компонент для шага "{currentSteps[activeStep].title}" не найден.</Text>;

  };
  // ------------------------------------

  // <<< Добавляем конфигурацию компонентов для ReactMarkdown
  const markdownComponents = {
    h1: (props: React.ComponentProps<'h1'>) => <ChakraHeading as="h1" size="xl" my={4} {...props} />,
    h2: (props: React.ComponentProps<'h2'>) => <ChakraHeading as="h2" size="lg" my={3} {...props} />,
    h3: (props: React.ComponentProps<'h3'>) => <ChakraHeading as="h3" size="md" my={2} {...props} />,
    h4: (props: React.ComponentProps<'h4'>) => <ChakraHeading as="h4" size="sm" my={1} {...props} />,
    h5: (props: React.ComponentProps<'h5'>) => <ChakraHeading as="h5" size="xs" my={1} {...props} />,
    h6: (props: React.ComponentProps<'h6'>) => <ChakraHeading as="h6" size="xs" my={1} {...props} />,
    p: (props: React.ComponentProps<'p'>) => <ChakraText fontSize="sm" mb={2} {...props} />,
    ol: (props: React.ComponentProps<'ol'>) => <OrderedList spacing={1} ml={6} mb={2} {...props} />,
    ul: (props: React.ComponentProps<'ul'>) => <UnorderedList spacing={1} ml={6} mb={2} {...props} />,
    li: (props: React.ComponentProps<'li'>) => <ListItem fontSize="sm" {...props} />,
    // Добавьте другие теги по мере необходимости (например, strong, em, code)
    strong: (props: React.ComponentProps<'strong'>) => <ChakraText as="strong" fontWeight="bold" {...props} />,
    // em: (props: any) => <ChakraText as="em" fontStyle="italic" {...props} />,
    // code: (props: any) => <Code {...props} />
  };

  return (
    <Box as="form" onSubmit={handleSubmit(onSubmit)} p={5} borderWidth="1px" borderRadius="lg" boxShadow="md" bg="cardBackground">
       <Heading as="h2" size="lg" textAlign="center" mb={6} color="primary">
         Ввод данных пенсионного дела
       </Heading>

        <Stepper index={activeStep} mb={8} colorScheme="blue">
            {/* <<< Рендерим шаги из currentSteps */}
            {currentSteps.map((step, index) => (
                <Step
                    key={step.id}
                    onClick={() => {
                        // Разрешаем переход только к пройденным или текущему шагу
                        if (index <= activeStep) {
                            setActiveStep(index);
                        }
                    }}
                    cursor={index <= activeStep ? "pointer" : "default"}
                    // <<< Добавляем стиль для неактивных будущих шагов
                    opacity={index > activeStep ? 0.5 : 1}
                    _hover={index <= activeStep ? { bg: 'gray.100', borderRadius: 'md', _dark: { bg: 'gray.700' } } : {}} // Эффект при наведении только для активных + темная тема
                 >
                    <StepIndicator>
                        <StepStatus
                        complete={<StepIcon />}
                        incomplete={<StepNumber />}
                        active={<StepNumber />}
                        />
                    </StepIndicator>
                    <Box flexShrink='0'>
                        <StepTitle>{step.title}</StepTitle>
                        <StepDescription>{step.description}</StepDescription>
                    </Box>
                    <StepSeparator />
                </Step>
             ))}
        </Stepper>

        <Box mb={8}>
           {renderStepContent()}
        </Box>

        <VStack spacing={4} align="stretch">
            <Flex>
                {/* <<< Добавлена leftIcon для кнопки Назад */}
                <Button
                   onClick={handlePrevious}
                   isDisabled={activeStep === 0}
                   variant="outline"
                   leftIcon={<ArrowBackIcon />}
                >
                   Назад
                </Button>
                <Spacer />
                 {}
                {activeStep < currentSteps.length - 1 && (
                    /* <<< Добавлена rightIcon для кнопки Далее */
                    <Button
                       onClick={handleNext}
                       colorScheme="blue" // Используем стандартный синий
                       rightIcon={<ArrowForwardIcon />}
                    >
                       Далее
                    </Button>
                )}
                 {/* Кнопки и результаты на последнем шаге */}
                {activeStep === currentSteps.length - 1 && (
                    // Используем Flex вместо VStack для горизонтального расположения кнопок
                    <Flex direction="row" justify="flex-end"> {/* Выравниваем кнопки по правому краю */}
                         <Button
                             type="button"
                             onClick={handleAnalyzeCase}
                             isLoading={isLoadingAnalysis}
                             isDisabled={isLoadingAnalysis || isSubmitting}
                             colorScheme="teal" // Оставляем бирюзовый для RAG
                             variant="outline"
                             mr={3} // Отступ справа
                         >
                             Провести RAG-анализ
                         </Button>
                         <Button
                             type="submit"
                             isLoading={isSubmitting}
                             isDisabled={!isDirty || isSubmitting || isLoadingAnalysis}
                             colorScheme="primary" // Используем основной синий цвет
                         >
                             Отправить на проверку
                         </Button>
                    </Flex>
                )}
            </Flex> {/* Закрываем Flex для кнопок Назад/Далее/Отправить */}

             {/* Отображение статуса/результата RAG (теперь под кнопками) */}
             {activeStep === currentSteps.length - 1 && ( // Показываем только на последнем шаге
                 <VStack spacing={4} align="stretch" mt={4}> {/* Отступ сверху */}
                      {isLoadingAnalysis && (
                          <Flex justify="center" align="center" direction="column" p={4}>
                              <CircularProgress isIndeterminate color="teal.300" />
                              <Text mt={2} color="gray.500" _dark={{ color: "gray.400" }}>Выполняется RAG-анализ...</Text>
                          </Flex>
                      )}
                      {analysisError && (
                          <Alert status="error">
                              <AlertIcon />
                              <Box>
                                 <AlertTitle>Ошибка RAG-анализа!</AlertTitle>
                                 <AlertDescription>{analysisError}</AlertDescription>
                              </Box>
                          </Alert>
                      )}
                      {analysisResult && !isLoadingAnalysis && (
                          <Box position="relative" p={4} borderWidth="1px" borderRadius="md" borderColor="teal.200" bg="teal.50" _dark={{ borderColor: "teal.600", bg: "teal.900" }}>
                             <Flex justify="space-between" align="flex-start" mb={2}>
                                 <Heading size="sm" display="flex" alignItems="center" color="teal.700" _dark={{ color: "teal.200" }}>
                                     <InfoIcon mr={2} />
                                     Результат RAG-анализа:
                                 </Heading>
                                 <Flex align="center">
                                     {confidenceScore !== null && (
                                         <Text fontSize="sm" color="gray.600" mr={2}>
                                             Уверенность: {(confidenceScore * 100).toFixed(1)}%
                                         </Text>
                                     )}
                                     <IconButton
                                         aria-label="Copy analysis result"
                                         icon={<CopyIcon />}
                                         size="sm"
                                         variant="ghost"
                                         colorScheme={hasCopied ? "green" : "gray"}
                                         onClick={onCopy}
                                         title={hasCopied ? 'Скопировано!' : 'Копировать'}
                                     />
                                 </Flex>
                             </Flex>
                             <ReactMarkdown components={markdownComponents}>
                                 {analysisResult}
                             </ReactMarkdown>
                          </Box>
                      )}
                 </VStack>
             )}
        </VStack> {/* Закрываем основной VStack */}
    </Box> /* Закрываем Box формы */
  );
}

export default CaseForm; 