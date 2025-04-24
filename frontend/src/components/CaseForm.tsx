import React, { useState, useEffect, useMemo } from 'react';
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
import PensionTypeStep from './formSteps/PensionTypeStep';
import DisabilityInfoStep from './formSteps/DisabilityInfoStep';
import SummaryStep from './formSteps/SummaryStep';

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
  const [selectedPensionType, setSelectedPensionType] = useState<string | null>(null);
  const [pensionTypeError, setPensionTypeError] = useState<string | null>(null);
  // --- Состояния для RAG анализа --- 
  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
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
      disability: undefined, // <<< Начальное значение для инвалидности
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
    dataToSend.pension_type = selectedPensionType || '';
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
        const result: ProcessResult = await response.json(); // <<< Ожидаем ProcessResult
        onSubmitSuccess(result); // <<< Передаем весь результат
        setActiveStep(0); // Сбрасываем на первый шаг после успешной отправки
        setSelectedPensionType(null); // Сбрасываем тип пенсии
        // TODO: Возможно, нужно сбросить и сами данные формы?
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
            'personal_data.full_name', 'personal_data.birth_date', 'personal_data.snils',
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
          const pensionTypeText = selectedPensionType === 'retirement_standard' ? 'страховая по старости' :
                                selectedPensionType === 'disability_social' ? 'социальная по инвалидности' :
                                'тип не указан';
          const case_description = [
              `${genderText}, ${age} лет`,
              `${pensionTypeText}`,
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
              console.log("RAG analysis successful:", result.analysis_result);
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

  return (
    <Box as="form" onSubmit={handleSubmit(onSubmit)} p={5} borderWidth="1px" borderRadius="lg" boxShadow="md" bg="white">
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
                    _hover={index <= activeStep ? { bg: 'gray.100', borderRadius: 'md' } : {}} // Эффект при наведении только для активных
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
                <Button onClick={goToPrevious} isDisabled={activeStep === 0} variant="outline">Назад</Button>
                <Spacer />
                 {/* Кнопка "Далее" теперь корректно работает с динамическим количеством шагов */}
                {activeStep < currentSteps.length - 1 && (
                    <Button onClick={handleNext} colorScheme="blue">Далее</Button>
                )}
                 {/* Кнопка "Отправить" показывается на последнем шаге */} 
                {activeStep === currentSteps.length - 1 && (
                    <VStack spacing={4} align="stretch" mt={4}>
                        <Flex>
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
                        </Flex>
                    {/* Переносим отображение статуса/результата RAG внутрь этого блока */}
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
                )}
            </Flex>
        </VStack>
    </Box>
  );
}

export default CaseForm; 