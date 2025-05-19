import React, { useState, useEffect } from 'react';
import { useForm, useFieldArray, SubmitHandler, FieldPath, FieldValues, UseFormRegister, FieldErrors, Control, UseFormGetValues, UseFormSetValue, UseFormWatch, UseFormTrigger } from 'react-hook-form';
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
import { processCase, analyzeCase } from '../services/client';
// <<< Импорт новой утилиты
import { prepareDataForApi } from '../utils';
// <<< Импорт ReactMarkdown
import ReactMarkdown from 'react-markdown';

// Импортируем типы и компоненты шагов
import PersonalDataStep from './formSteps/PersonalDataStep';
import WorkExperienceStep from './formSteps/WorkExperienceStep';
import AdditionalInfoStep from './formSteps/AdditionalInfoStep';
import PensionTypeStep from './formSteps/PensionTypeStep';
import DisabilityInfoStep from './formSteps/DisabilityInfoStep';
import SummaryStep from './formSteps/SummaryStep';
import OcrStepComponent from './formSteps/OcrStepComponent';

// Импорт типов из types.ts
import { 
  CaseFormDataTypeForRHF, 
  CaseFormData, 
  ProcessOutput as BackendProcessOutput,
  ApiErrorDetail,
  WorkRecord,
  PersonalData as PersonalDataModel // Импортируем оригинальный PersonalData для defaultValues
} from '../types';

// Определяем типы для данных формы, основываясь на Pydantic моделях
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

// <<< Определяем тип для полного ответа от /process
export type ProcessResult = {
  status: 'approved' | 'rejected';
  explanation: string;
};

// Пропсы компонента: добавляем колбэки
interface CaseFormProps {
  onSubmitSuccess: (result: BackendProcessOutput) => void; 
  onSubmitError: (errorMessage: string) => void;
}

// Общий интерфейс для пропсов, передаваемых в компоненты шагов
interface StepComponentProps {
  register: UseFormRegister<CaseFormDataTypeForRHF>;
  errors: FieldErrors<CaseFormDataTypeForRHF>; // TODO: Сделать более строгим для каждого шага
  control: Control<CaseFormDataTypeForRHF>;
  getValues: UseFormGetValues<CaseFormDataTypeForRHF>;
  setValue: UseFormSetValue<CaseFormDataTypeForRHF>;
  getErrorMessage: (name: string) => string | undefined; // TODO: Можно сузить тип name
  watch: UseFormWatch<CaseFormDataTypeForRHF>;
  trigger: UseFormTrigger<CaseFormDataTypeForRHF>;
  // Дополнительные пропсы для конкретных шагов могут быть добавлены через пересечение типов
  // Например: selectedValue?: string; onChange?: (value: string) => void; fieldArray?: any; pensionType?: string | null; formData?: CaseFormDataTypeForRHF
}

// Определяем интерфейс для описания шага с типизированными полями для валидации
interface StepDefinition<TFieldValues extends FieldValues = CaseFormDataTypeForRHF> {
  id: string;
  title: string;
  description: string;
  component: React.FC<StepComponentProps & any>;
  fieldsToValidate?: FieldPath<TFieldValues>[];
}

// <<< Определяем полные последовательности шагов
const stepDefinitions: { [key: string]: StepDefinition<CaseFormDataTypeForRHF> } = {
  pensionType: {
    id: 'pensionType', title: 'Шаг 1', description: 'Тип пенсии', component: PensionTypeStep,
    fieldsToValidate: ['pension_type']
  },
  ocrStep: {
    id: 'ocrStep', title: 'Шаг 2', description: 'Автозаполнение', component: OcrStepComponent,
    fieldsToValidate: [] // OCR шаг сам по себе не валидирует поля формы, он их заполняет
  },
  personalData: {
    id: 'personalData', title: 'Шаг 3', description: 'Личные данные', component: PersonalDataStep,
    fieldsToValidate: [ // Убрали 'personal_data.dependents'
      'personal_data.last_name', 'personal_data.first_name',
      'personal_data.birth_date', 'personal_data.snils',
      'personal_data.gender', 'personal_data.citizenship',
      // Новые поля не добавляем в валидацию, т.к. они необязательные
    ]
  },
  workExperience: {
    id: 'workExperience', title: 'Шаг 4', description: 'Трудовой стаж', component: WorkExperienceStep,
    fieldsToValidate: ['work_experience.total_years']
  },
  disabilityInfo: {
    // Этот шаг может называться по-разному в зависимости от потока, 
    // но ID должен быть уникальным, если это отдельный компонент.
    // Если это тот же AdditionalInfoStep, но с другими полями, то ID может быть тем же.
    // Пока оставим так, подразумевая что DisabilityInfoStep - это отдельный компонент шага.
    id: 'disabilityInfo', title: 'Шаг 4', description: 'Инвалидность', component: DisabilityInfoStep,
    fieldsToValidate: ['disability.group', 'disability.date'] // Поля для валидации при инвалидности
  },
  additionalInfo: {
    id: 'additionalInfo', title: 'Шаг 5', description: 'Доп. инфо', component: AdditionalInfoStep,
    fieldsToValidate: ['pension_points', 'dependents'] // Добавили 'dependents' сюда
  },
  summary: {
    id: 'summary', title: 'Шаг 6', description: 'Сводка', component: SummaryStep,
    fieldsToValidate: []
  },
};

// Функция для получения последовательности шагов по типу пенсии
const getStepsForPensionType = (type: string | null): StepDefinition<CaseFormDataTypeForRHF>[] => {
  const initialStep = stepDefinitions.pensionType; // Шаг выбора типа пенсии всегда первый

  if (!type) {
    // Если тип пенсии еще не выбран, показываем только выбор типа пенсии
    return [initialStep];
  }

  // После выбора типа пенсии, добавляем OCR как второй шаг, затем личные данные
  const commonStepsAfterTypeSelection = [initialStep, stepDefinitions.ocrStep, stepDefinitions.personalData];

  switch (type) {
    case 'retirement_standard':
      return [
        ...commonStepsAfterTypeSelection,
        stepDefinitions.workExperience,
        stepDefinitions.additionalInfo,
        stepDefinitions.summary
      ];
    case 'disability_social':
      return [
        ...commonStepsAfterTypeSelection,
        stepDefinitions.disabilityInfo, 
        stepDefinitions.additionalInfo,
        stepDefinitions.summary
      ];
    default:
      // По умолчанию, если тип не распознан (например, пустая строка после инициализации), 
      // возвращаем только первый шаг - выбор типа пенсии.
      return [initialStep];
  }
};

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
  const [currentSteps, setCurrentSteps] = useState<StepDefinition<CaseFormDataTypeForRHF>[]>(() => getStepsForPensionType(null));

  // <<< Обновляем useSteps при изменении currentSteps
  const { activeStep, goToNext, goToPrevious, setActiveStep } = useSteps({
    index: 0,
    count: currentSteps.length,
  });

  useEffect(() => {
    if (activeStep >= currentSteps.length && currentSteps.length > 0) {
        setActiveStep(currentSteps.length - 1);
    }
  }, [currentSteps, activeStep, setActiveStep]);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isDirty },
    watch,
    trigger,
    getValues,
    setValue,
    reset
  } = useForm<CaseFormDataTypeForRHF>({
    mode: 'onBlur',
    defaultValues: {
      pension_type: '',
      personal_data: { // dependents здесь нет
        last_name: '',
        first_name: '',
        middle_name: '',
        birth_date: '',
        snils: '',
        gender: '',
        citizenship: '', // По умолчанию пустое
        name_change_info: null,
        // Новые поля:
        birth_place: '',
        passport_series: '',
        passport_number: '',
        issue_date: '',
        issuing_authority: '',
        department_code: '',
      } as Omit<PersonalDataModel, 'dependents'>, // Явное приведение типа
      dependents: 0, // dependents теперь здесь
      work_experience: {
        total_years: 0,
        records: [],
      },
      pension_points: 0,
      benefits: '',
      documents: '',
      has_incorrect_document: false,
      disability: undefined,
      other_documents_extracted_data: [], // НОВОЕ ПОЛЕ - инициализируем пустым массивом
    },
  });

  // Указываем тип для useFieldArray более конкретно, если возможно
  const { fields, append, remove } = useFieldArray<CaseFormDataTypeForRHF, "work_experience.records", "id">({
    control, 
    name: "work_experience.records"
  });
  // Переименовал fieldArray в стандартные имена из RHF для ясности: fields, append, remove, update
  // Это изменение потребует обновить использование fieldArray.fields, fieldArray.append и т.д. в WorkExperienceStep.tsx

  const onSubmit: SubmitHandler<CaseFormDataTypeForRHF> = async (data) => {
    setIsSubmitting(true);
    onSubmitError('');
    setAnalysisResult(null);
    setAnalysisError(null);
    setConfidenceScore(null);

    const pensionTypeToUse = selectedPensionType || data.pension_type;
    if (!pensionTypeToUse) {
        onSubmitError("Тип пенсии не выбран. Пожалуйста, вернитесь на первый шаг.");
        setIsSubmitting(false);
        return;
    }

    const dataToSend: CaseFormData = prepareDataForApi({ 
        ...data, 
        pension_type: pensionTypeToUse 
    });

    try {
      const result: BackendProcessOutput = await processCase(dataToSend); 
      onSubmitSuccess(result);
      
      reset();
      setSelectedPensionType(null);
      setCurrentSteps(getStepsForPensionType(null));
      setActiveStep(0);
      setAnalysisResult(null);
      setConfidenceScore(null);
      setAnalysisError(null);

    } catch (error) {
      const err = error as Error & Partial<ApiErrorDetail>;
      const errorMessage = err.message || "Неизвестная ошибка отправки";
      console.error("Submit Error Details:", err.details, "Status:", err.status);
      onSubmitError(`Ошибка отправки данных: ${errorMessage}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getErrorMessage = (fieldName: string): string | undefined => {
    const keys = fieldName.split('.');
    let currentError: unknown = errors; // Используем unknown вместо any

    for (const key of keys) {
      // Проверяем, что currentError это объект и содержит ключ
      if (typeof currentError === 'object' && currentError !== null && key in currentError) {
        currentError = (currentError as Record<string, unknown>)[key];
      } else {
        // Если ключ не найден или currentError не объект, ошибки нет на этом уровне
        return undefined;
      }
    }

    // После цикла, проверяем, имеет ли currentError свойство message
    if (typeof currentError === 'object' && currentError !== null && 'message' in currentError && typeof (currentError as { message?: string }).message === 'string') {
      return (currentError as { message: string }).message;
    }

    return undefined;
  };

  const handlePensionTypeChange = (value: string) => {
    setSelectedPensionType(value);
    setValue('pension_type', value, { shouldValidate: true, shouldDirty: true });
    const newSteps = getStepsForPensionType(value);
    setCurrentSteps(newSteps);
    setPensionTypeError(null);
    if (activeStep === 0 && value) {
      if (newSteps.length > 1) {
          setActiveStep(1);
      }
    } else if (!value) {
        setActiveStep(0);
    }
  };

  const handleNext = async () => {
    let isValidStep = true;
    setPensionTypeError(null);

    const currentStepDefinition = currentSteps[activeStep];
    const currentValues = getValues();

    if (currentStepDefinition.id === 'pensionType') {
        if (!selectedPensionType) {
            setPensionTypeError('Пожалуйста, выберите тип пенсии');
            return;
        }
        if (!currentValues.pension_type) {
             setValue('pension_type', selectedPensionType, { shouldValidate: true });
             const isValidPensionType = await trigger('pension_type');
             if (!isValidPensionType) return;
        }
    }

    const fieldsForRHFValidation: FieldPath<CaseFormDataTypeForRHF>[] =
        currentStepDefinition.fieldsToValidate
            ? [...currentStepDefinition.fieldsToValidate]
            : [];

    if (currentStepDefinition.id === 'personalData') {
      if (currentValues.personal_data?.name_change_info?.old_full_name || currentValues.personal_data?.name_change_info?.date_changed) {
          // Валидируем поля name_change_info только если они были активированы/заполнены
          fieldsForRHFValidation.push('personal_data.name_change_info.old_full_name');
          fieldsForRHFValidation.push('personal_data.name_change_info.date_changed');
      }
    }

    if (currentStepDefinition.id === 'workExperience') {
        currentValues.work_experience.records.forEach((_record: Partial<WorkRecord>, index: number) => {
            fieldsForRHFValidation.push(`work_experience.records.${index}.organization` as FieldPath<CaseFormDataTypeForRHF>);
            fieldsForRHFValidation.push(`work_experience.records.${index}.start_date` as FieldPath<CaseFormDataTypeForRHF>);
            fieldsForRHFValidation.push(`work_experience.records.${index}.end_date` as FieldPath<CaseFormDataTypeForRHF>);
            fieldsForRHFValidation.push(`work_experience.records.${index}.position` as FieldPath<CaseFormDataTypeForRHF>);
        });
    }
    // Для disabilityInfo поля уже указаны в stepDefinitions.
    // Для additionalInfo 'dependents' теперь будет валидироваться.

    if (fieldsForRHFValidation.length > 0) {
        const uniqueFields = Array.from(new Set(fieldsForRHFValidation));
        isValidStep = await trigger(uniqueFields);
        console.log(`Validation for step ${currentStepDefinition.id} (${currentStepDefinition.description}): ${isValidStep}`, uniqueFields);
        if (!isValidStep) {
            console.log('Validation errors:', errors);
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

  const handleAnalyzeCase = async () => {
    setIsLoadingAnalysis(true);
    setAnalysisResult(null);
    setAnalysisError(null);
    setConfidenceScore(null);

    const currentData = getValues();
    const pensionTypeToUse = selectedPensionType || currentData.pension_type;

    if (!pensionTypeToUse) {
        setAnalysisError("Тип пенсии не выбран. RAG-анализ не может быть выполнен.");
        setIsLoadingAnalysis(false);
        return;
    }

    const dataToSend: CaseFormData = prepareDataForApi({ 
        ...currentData, 
        pension_type: pensionTypeToUse 
    });
    
    console.log("Sending prepared data to /api/v1/analyze_case:", dataToSend);

    try {
      const response = await analyzeCase(dataToSend);
      setAnalysisResult(response.analysis_result);
      setConfidenceScore(response.confidence_score);
      if (response.analysis_result) {
        onCopy();
      }
    } catch (error) {
      const err = error as Error & Partial<ApiErrorDetail>;
      let errorMessage = 'Не удалось выполнить RAG-анализ.';
      if (err.message) {
        errorMessage = err.message;
      }
      console.error("RAG Analysis Error Details:", err.details, "Status:", err.status);
      setAnalysisError(errorMessage);
    } finally {
      setIsLoadingAnalysis(false);
    }
  };

  // --- Отображение текущего шага --- 
  const renderStepContent = () => {
    const currentStepDef = currentSteps[activeStep];
    // Если currentStepDef или currentStepDef.component не определены, вернуть заглушку
    if (!currentStepDef || !currentStepDef.component) {
        // Можно добавить более информативное сообщение или компонент-заглушку
        console.error('Current step definition or component is undefined', activeStep, currentSteps);
        return <Box>Ошибка: Шаг не найден или неверно сконфигурирован.</Box>;
    }
    const CurrentStepComponent = currentStepDef.component;

    // Общие пропсы для всех шагов
    const commonProps: StepComponentProps = {
      register,
      errors: errors as FieldErrors<CaseFormDataTypeForRHF>,
      control,
      getValues,
      setValue,
      getErrorMessage,
      watch,
      trigger,
    };

    // Пропсы, специфичные для определенных шагов
    let specificProps: any = {}; // Используем any временно для упрощения, можно уточнить тип
    if (currentStepDef.id === 'pensionType') {
      specificProps = {
        selectedValue: selectedPensionType,
        onChange: handlePensionTypeChange,
        error: pensionTypeError
      };
    } else if (currentStepDef.id === 'summary') {
      specificProps = {
        formData: getValues(), // Передаем все данные формы
        onEditStep: (stepIndex: number) => setActiveStep(stepIndex), // Функция для перехода к шагу для редактирования
        steps: currentSteps // Передаем определения шагов для навигации
      };
    } else if (currentStepDef.id === 'ocrStep') {
        specificProps = {
            // setValue и getValues уже в commonProps
            // trigger также в commonProps
            // Если есть onOcrErrorProp, его нужно определить и передать
            // onOcrErrorProp: (error, docType) => { /* обработка ошибки OCR в CaseForm, если нужно */ }
        };
    } else if (currentStepDef.id === 'workExperience') {
        specificProps = {
            fields,
            append,
            remove,
            // control также нужен для каждого элемента массива, но он уже есть в commonProps
        };
    }
    // Добавляем передачу pensionType в AdditionalInfoStep и DisabilityInfoStep
    if (currentStepDef.id === 'additionalInfo' || currentStepDef.id === 'disabilityInfo') {
        specificProps = {
            ...specificProps, // Сохраняем другие specificProps, если они есть (например, от workExperience, если id совпадут, хотя это маловероятно)
            pensionType: selectedPensionType,
        };
    }

    return <CurrentStepComponent {...commonProps} {...specificProps} />;
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
    strong: (props: React.ComponentProps<'strong'>) => <ChakraText as="strong" fontWeight="bold" {...props} />,
  };

  return (
    <Box as="form" onSubmit={handleSubmit(onSubmit)} p={5} borderWidth="1px" borderRadius="lg" boxShadow="md" bg="cardBackground">
       <Heading as="h2" size="lg" textAlign="center" mb={6} color="primary">
         Ввод данных пенсионного дела
       </Heading>

        <Stepper index={activeStep} mb={8} colorScheme="blue">
            {currentSteps.map((step, index) => (
                <Step
                    key={step.id}
                    onClick={() => {
                        if (index <= activeStep) {
                            setActiveStep(index);
                        }
                    }}
                    cursor={index <= activeStep ? "pointer" : "default"}
                    opacity={index > activeStep ? 0.5 : 1}
                    _hover={index <= activeStep ? { bg: 'gray.100', borderRadius: 'md', _dark: { bg: 'gray.700' } } : {}}
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
                    <Button
                       onClick={handleNext}
                       colorScheme="primary"
                       rightIcon={<ArrowForwardIcon />}
                    >
                       Далее
                    </Button>
                )}
                {activeStep === currentSteps.length - 1 && (
                    <Flex direction="row" justify="flex-end">
                         <Button
                             type="button"
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
                    </Flex>
                )}
            </Flex>

             {activeStep === currentSteps.length - 1 && (
                 <VStack spacing={4} align="stretch" mt={4}>
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
        </VStack>
    </Box>
  );
}

export default CaseForm; 