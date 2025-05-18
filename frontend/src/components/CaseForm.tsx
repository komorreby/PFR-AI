import React, { useState, useEffect } from 'react';
import { useForm, useFieldArray, SubmitHandler } from 'react-hook-form';

// Импорты Chakra UI
import {
  Box, Button, Heading, Stepper, Step, StepIndicator, StepStatus,
  StepIcon, StepNumber, StepTitle, StepDescription, StepSeparator,
  Flex, Spacer, useSteps,
  Alert, AlertIcon, AlertTitle, AlertDescription, CircularProgress, Text, VStack,
  IconButton,
  useClipboard,
  ListItem, Text as ChakraText, Heading as ChakraHeading, OrderedList, UnorderedList,
  Badge,
  FormControl, FormLabel, Input, Select, Textarea,
  useToast, HStack,
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalCloseButton, ModalBody, ModalFooter,
  StackDivider, useColorModeValue, Switch, Checkbox,
  Menu, MenuButton, MenuList, MenuItem,
  Tooltip
} from '@chakra-ui/react';

// Иконки
import { ArrowBackIcon, ArrowForwardIcon, CopyIcon, InfoIcon, DownloadIcon, AddIcon, DeleteIcon, EditIcon, QuestionOutlineIcon } from '@chakra-ui/icons';
// API клиент
import { analyzeCase } from '../api/client'; // processCase не используется напрямую в этой версии CaseForm

// Типы и компоненты шагов
import PersonalDataStep from './formSteps/PersonalDataStep';
import WorkExperienceStep from './formSteps/WorkExperienceStep';
import AdditionalInfoStep from './formSteps/AdditionalInfoStep';
import PensionTypeStep from './formSteps/PensionTypeStep';
import DisabilityInfoStep from './formSteps/DisabilityInfoStep';
import SummaryStep from './formSteps/SummaryStep';
import DocumentUploadStep, { ALL_POSSIBLE_DOCUMENT_IDS } from './formSteps/DocumentUploadStep';

// Типы для ответа от check_document_set
interface OcrData {
    [key: string]: any;
}

interface CheckedDocumentInfo {
    id: string;
    name: string;
    status: string;
    description?: string | null;
    condition_text?: string | null;
    is_critical: boolean;
    ocr_data?: OcrData | null;
}

export interface DocumentSetCheckResponse {
    pension_type_key: string;
    pension_display_name: string;
    pension_description: string;
    overall_status: string;
    checked_documents: CheckedDocumentInfo[];
    missing_critical_documents: string[];
    missing_other_documents: string[];
}

// Типы данных формы
type NameChangeInfoType = {
  old_full_name: string;
  date_changed: string | null;
};

export type PersonalDataType = {
  last_name: string;
  first_name: string;
  middle_name?: string;
  birth_date: string | null;
  snils: string;
  gender: string;
  citizenship: string;
  name_change_info: NameChangeInfoType | null;
  dependents: number;
};

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
    group: string;
    date: string;
    cert_number?: string;
};

export type CaseFormDataType = {
  pension_type: string;
  personal_data: PersonalDataType;
  work_experience: WorkExperienceType;
  pension_points: number;
  benefits: string;
  documents: string;
  has_incorrect_document: boolean;
  disability?: DisabilityInfoType;
  passport_file_for_check?: File | null;
  uploaded_document_ids_for_check?: string[];
};

interface CaseFormProps {
  onSubmitSuccess: (result: DocumentSetCheckResponse) => void;
  onSubmitError: (errorMessage: string) => void;
}

interface StepDefinition {
  id: string;
  title: string;
  description: string;
  component: React.FC<any>;
  fieldsToValidate?: (keyof CaseFormDataType | string)[];
}

const stepDefinitions: { [key: string]: StepDefinition } = {
  pensionType: { id: 'pensionType', title: 'Шаг 1', description: 'Тип пенсии', component: PensionTypeStep },
  documentUpload: { id: 'documentUpload', title: 'Шаг 2', description: 'Загрузка документов', component: DocumentUploadStep },
  personalData: { id: 'personalData', title: 'Шаг 3', description: 'Личные данные', component: PersonalDataStep },
  workExperience: { id: 'workExperience', title: 'Шаг 4', description: 'Трудовой стаж', component: WorkExperienceStep },
  disabilityInfo: { id: 'disabilityInfo', title: 'Шаг 4', description: 'Инвалидность', component: DisabilityInfoStep },
  additionalInfo: { id: 'additionalInfo', title: 'Шаг 5', description: 'Доп. инфо', component: AdditionalInfoStep },
  summary: { id: 'summary', title: 'Шаг 6', description: 'Сводка', component: SummaryStep },
};

const getStepsForPensionType = (type: string | null): StepDefinition[] => {
  // Оригинальная логика:
  const baseSequence = [
    stepDefinitions.pensionType,
    stepDefinitions.documentUpload,
    stepDefinitions.personalData
  ];
  if (!type) return [stepDefinitions.pensionType]; // Если тип не выбран, показываем только первый шаг
  switch (type) {
    case 'retirement_standard':
      return [...baseSequence, stepDefinitions.workExperience, stepDefinitions.additionalInfo, stepDefinitions.summary];
    case 'disability_social':
      return [...baseSequence, stepDefinitions.disabilityInfo, stepDefinitions.additionalInfo, stepDefinitions.summary];
    case 'disability_insurance':
      return [...baseSequence, stepDefinitions.disabilityInfo, stepDefinitions.workExperience, stepDefinitions.additionalInfo, stepDefinitions.summary];
    case 'survivor_benefit':
      // Для пособия по потере кормильца может быть свой набор шагов или такой же, как стандартный
      // Пока оставим как стандартный + трудовой стаж, если он релевантен (часто бывает).
      // Уточните, если нужны другие шаги.
      return [stepDefinitions.pensionType, stepDefinitions.documentUpload, stepDefinitions.personalData, stepDefinitions.workExperience, stepDefinitions.additionalInfo, stepDefinitions.summary];
    default:
      console.warn(`Неизвестный тип пенсии для определения шагов: ${type}, возвращаем только выбор типа.`);
      // Возвращаем только первый шаг, если тип не определен или неизвестен, чтобы пользователь мог выбрать
      return [stepDefinitions.pensionType];
  }
};

// НОВАЯ ФУНКЦИЯ МАСКИРОВКИ ПЕРСОНАЛЬНЫХ ДАННЫХ
function maskPiiInReport(reportText: string, pii: PersonalDataType | undefined): string {
    if (!reportText || !pii) {
        return reportText;
    }
    let maskedText = reportText;

    const escapeRegExp = (string: string) => string.replace(/[.*+?^${}()|[\\\]\\\\]/g, '\\\\$&');

    // Маскировка ФИО (Фамилия, Имя, Отчество)
    const { last_name, first_name, middle_name } = pii;
    const nameVariations: string[] = [];

    if (last_name && first_name && middle_name) {
        nameVariations.push(`${last_name} ${first_name} ${middle_name}`);
        nameVariations.push(`${first_name} ${middle_name} ${last_name}`);
        if (first_name.length > 0 && middle_name.length > 0) {
          nameVariations.push(`${last_name} ${first_name.charAt(0)}\. ${middle_name.charAt(0)}\.`); // L F. M.
          nameVariations.push(`${first_name.charAt(0)}\. ${middle_name.charAt(0)}\. ${last_name}`); // F. M. L
        }
    } else if (last_name && first_name) {
        nameVariations.push(`${last_name} ${first_name}`);
        nameVariations.push(`${first_name} ${last_name}`);
        if (first_name.length > 0) {
            nameVariations.push(`${last_name} ${first_name.charAt(0)}\.`); // L F.
            nameVariations.push(`${first_name.charAt(0)}\. ${last_name}`); // F. L
        }
    }
    // Добавляем отдельные части имени, если они достаточно длинные
    [last_name, first_name, middle_name].forEach(part => {
        if (part && part.trim().length > 2) {
            nameVariations.push(part);
        }
    });
    
    const uniqueNameVariations = [...new Set(nameVariations.filter(Boolean))] // Убираем пустые строки, если есть
                                 .sort((a, b) => b.length - a.length); // Сначала длинные варианты

    uniqueNameVariations.forEach(nameVar => {
        if (nameVar && nameVar.trim()) {
            const regex = new RegExp(`\\b${escapeRegExp(nameVar)}\\b`, 'gi');
            maskedText = maskedText.replace(regex, '[ФИО ЗАМАСКИРОВАНО]');
        }
    });

    // Маскировка Даты Рождения
    if (pii.birth_date) { // Ожидаемый формат YYYY-MM-DD
        const [year, month, day] = pii.birth_date.split('-');
        // Варианты написания даты, которые мог использовать LLM
        const datePatternsToSearch = [
            pii.birth_date, // YYYY-MM-DD
            `${day}\.${month}\.${year}`, // DD.MM.YYYY (экранируем точки для regex)
            // Можно добавить более сложные текстовые варианты, если LLM их генерирует,
            // например, "22 сентября 1962" (потребует преобразования месяца)
        ];
        datePatternsToSearch.forEach(datePattern => {
            try {
                const regex = new RegExp(`\\b${datePattern}\\b`, 'g');
                maskedText = maskedText.replace(regex, '[ДАТА РОЖДЕНИЯ ЗАМАСКИРОВАНА]');
            } catch (e) {
                console.warn("Ошибка создания regex для даты:", datePattern, e)
            }
        });
    }

    // Маскировка СНИЛС
    if (pii.snils && pii.snils.trim()) {
        const snilsNormalized = pii.snils.replace(/[-\s]/g, ''); // Убираем дефисы и пробелы
        const snilsVariations = [
            pii.snils, // Оригинальный формат, например "123-456-789 00"
            snilsNormalized, // Формат без разделителей "12345678900"
            `${snilsNormalized.substring(0,3)}-${snilsNormalized.substring(3,6)}-${snilsNormalized.substring(6,9)} ${snilsNormalized.substring(9,11)}` // Восстановленный формат с дефисами
        ].filter(Boolean);

        [...new Set(snilsVariations)].forEach(snilsVar => {
             if (snilsVar.trim()){
                const regex = new RegExp(escapeRegExp(snilsVar), 'g');
                maskedText = maskedText.replace(regex, '[СНИЛС ЗАМАСКИРОВАН]');
             }
        });
    }
    return maskedText;
}

function CaseForm({ onSubmitSuccess, onSubmitError }: CaseFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedPensionType, setSelectedPensionType] = useState<string | null>(null);
  const [pensionTypeError, setPensionTypeError] = useState<string | null>(null);
  
  const [availablePensionTypes, setAvailablePensionTypes] = useState<{ [key: string]: string }>({});
  const [pensionTypesLoading, setPensionTypesLoading] = useState<boolean>(true);
  const [pensionTypesError, setPensionTypesError] = useState<string | null>(null);

  const [analysisResult, setAnalysisResult] = useState<string | null>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false); 
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [confidenceScore, setConfidenceScore] = useState<number | null>(null);
  const { hasCopied, onCopy } = useClipboard(analysisResult || '');
  
  const [currentSteps, setCurrentSteps] = useState<StepDefinition[]>(() => getStepsForPensionType(null));
  const [documentCheckResult, setDocumentCheckResult] = useState<DocumentSetCheckResponse | null>(null);
  const [finalReportText, setFinalReportText] = useState<string | null>(null);

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
    register, handleSubmit, control,
    formState: { errors, isDirty },
    watch, trigger, getValues, setValue, setError, clearErrors
  } = useForm<CaseFormDataType>({
    mode: 'onBlur',
    defaultValues: {
      pension_type: '',
      personal_data: {
        last_name: '', first_name: '', middle_name: '',
        birth_date: null, snils: '', gender: '', citizenship: '',
        name_change_info: null, dependents: 0,
      },
      work_experience: { total_years: 0, records: [] },
      pension_points: 0, benefits: '', documents: '',
      has_incorrect_document: false, disability: undefined,
      passport_file_for_check: null, uploaded_document_ids_for_check: [],
    },
  });

  const fieldArray = useFieldArray({ control, name: "work_experience.records" });

  useEffect(() => {
    const fetchPensionTypes = async () => {
      setPensionTypesLoading(true);
      setPensionTypesError(null);
      try {
        const response = await fetch('http://127.0.0.1:8000/api/v1/pension_types');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data: { [key: string]: string } = await response.json();
        setAvailablePensionTypes(data);
      } catch (err: any) {
        console.error("Ошибка загрузки типов пенсий:", err);
        setPensionTypesError(err.message || "Не удалось загрузить справочник типов пенсий.");
      }
      setPensionTypesLoading(false);
    };
    fetchPensionTypes();
  }, []);
  
  const watchedUploadedDocIds = watch('uploaded_document_ids_for_check');
  useEffect(() => {
    if (watchedUploadedDocIds && ALL_POSSIBLE_DOCUMENT_IDS) {
      const selectedDocNames = watchedUploadedDocIds
        .map(id => ALL_POSSIBLE_DOCUMENT_IDS.find(doc => doc.id === id)?.name)
        .filter(name => name !== undefined) as string[];
      setValue('documents', selectedDocNames.join(', '), { shouldDirty: true });
    }
  }, [watchedUploadedDocIds, setValue, ALL_POSSIBLE_DOCUMENT_IDS]);

  // Выносим вызовы useColorModeValue на верхний уровень
  const stepperHoverBg = useColorModeValue('gray.100', 'gray.700');
  const resultsVStackBorderColor = useColorModeValue("gray.200", "gray.600");
  const resultsVStackBg = useColorModeValue("gray.50", "gray.750");
  const progressTextColor = useColorModeValue("gray.600", "gray.300");
  const docCheckBorderColor = useColorModeValue("blue.300", "blue.700");
  const docCheckHeadingColor = useColorModeValue("blue.700", "blue.300");
  const pensionDescTextColor = useColorModeValue("gray.600", "gray.300"); // такой же как progressTextColor, можно переиспользовать
  const docDescriptionTextColor = useColorModeValue("gray.500", "gray.400");
  const docConditionTextColor = useColorModeValue("blue.500", "blue.300");
  const missingCriticalColor = useColorModeValue("red.600", "red.400");
  const missingOtherColor = useColorModeValue("orange.600", "orange.400");
  const analysisBorderColor = useColorModeValue("teal.300", "teal.700");
  const analysisHeadingColor = useColorModeValue("teal.700", "teal.300");
  const analysisConfidenceColor = useColorModeValue("gray.600", "gray.400"); // такой же как progressTextColor, можно переиспользовать
  const analysisMarkdownBg = useColorModeValue("gray.100", "gray.800");
  const mainBoxBg = useColorModeValue('white', 'gray.750'); // Возвращаем, если он был удален, но теперь вызывается наверху

  const runRagAnalysis = async (currentFormData: CaseFormDataType): Promise<{ analysis_result: string; confidence_score: number; } | null> => {
    console.log("Запуск RAG-анализа...");
    setAnalysisResult(null);
    setAnalysisError(null);
    setConfidenceScore(null); 

    try {
      const dataToSend = JSON.parse(JSON.stringify(currentFormData)); 
      dataToSend.benefits = (currentFormData.benefits || '').split(',').map(s => s.trim()).filter(Boolean);
      dataToSend.documents = (currentFormData.documents || '').split(',').map(s => s.trim()).filter(Boolean);
      dataToSend.pension_type = selectedPensionType || currentFormData.pension_type || ''; 
      if (dataToSend.personal_data.name_change_info && !dataToSend.personal_data.name_change_info.old_full_name && !dataToSend.personal_data.name_change_info.date_changed) {
          dataToSend.personal_data.name_change_info = null;
      }
      
      const response = await analyzeCase(dataToSend); 
      console.log("RAG Response from analyzeCase:", JSON.stringify(response, null, 2));
      
      // Маскируем персональные данные перед сохранением и отображением
      const rawAnalysisResult = response.analysis_result;
      const personalDataForMasking = currentFormData.personal_data; // Используем PersonalDataType из текущих данных формы
      const maskedAnalysisResult = maskPiiInReport(rawAnalysisResult, personalDataForMasking);
      
      setAnalysisResult(maskedAnalysisResult); 
      setConfidenceScore(response.confidence_score); 
      // Возвращаем замаскированный результат, чтобы он попал в finalReportText
      return { analysis_result: maskedAnalysisResult, confidence_score: response.confidence_score };
    } catch (error: any) {
      console.error("Ошибка RAG-анализа:", error);
      let errorMessage = 'Не удалось выполнить RAG-анализ.';
      if (error instanceof Error) errorMessage = error.message;
      else if (typeof error === 'string') errorMessage = error;
      else if (error && typeof error.detail === 'string') errorMessage = error.detail;
      else if (typeof error === 'object') try {errorMessage += ': ' + JSON.stringify(error);} catch {errorMessage += ': [object Object]';}
      setAnalysisError(errorMessage); 
      return null;
    }
  };

  const handleFinalSubmit: SubmitHandler<CaseFormDataType> = async (data) => {
    console.log("Старт handleFinalSubmit, данные формы:", data);
    if (!data.pension_type) {
        onSubmitError("Тип пенсии не выбран. Пожалуйста, вернитесь на Шаг 1.");
        return;
    }

    setIsSubmitting(true); 
    setIsLoadingAnalysis(true); 
    onSubmitError(''); 
    setDocumentCheckResult(null); 
    setAnalysisResult(null); 
    setAnalysisError(null);
    setConfidenceScore(null);
    setFinalReportText(null);
    clearErrors("root.serverError" as any); // Очистка специфической ошибки формы

    const checkFormData = new FormData();
    checkFormData.append('pension_type_key', data.pension_type);
    if (data.passport_file_for_check) checkFormData.append('passport_file', data.passport_file_for_check);
    if (data.uploaded_document_ids_for_check?.length) checkFormData.append('uploaded_document_ids', data.uploaded_document_ids_for_check.join(','));

    let docCheckRes: DocumentSetCheckResponse | null = null;
    let ragResOuter: { analysis_result: string; confidence_score: number; } | null = null;

    try {
        console.log("Этап 1: Проверка комплекта документов...");
        const response = await fetch('http://127.0.0.1:8000/api/v1/check_document_set', { method: 'POST', body: checkFormData });
        const responseData = await response.json();
        if (!response.ok) {
            const errorMsg = responseData.detail || `HTTP error! status: ${response.status}`;
            throw new Error(`Ошибка проверки документов: ${errorMsg}`);
        }
        docCheckRes = responseData as DocumentSetCheckResponse;
        setDocumentCheckResult(docCheckRes);
        onSubmitSuccess(docCheckRes); 
        console.log("Этап 1 (Проверка документов) успешно завершен. Результат:", docCheckRes);

        console.log("Этап 2: RAG-анализ...");
        ragResOuter = await runRagAnalysis(data); 
        console.log("Этап 2 (RAG-анализ) завершен. Результат (ragResOuter):", JSON.stringify(ragResOuter, null, 2));
        
        console.log("Этап 3: Формирование общего отчета...");
        let reportLines = [];
        reportLines.push("=== Общий отчет по пенсионному делу ===");
        
        if (docCheckRes) {
            reportLines.push("\n--- Результат проверки комплекта документов ---");
            reportLines.push(`Тип пенсии: ${docCheckRes.pension_display_name} (${docCheckRes.pension_type_key})`);
            reportLines.push(`Общий статус: ${docCheckRes.overall_status}`);
            if (docCheckRes.pension_description) reportLines.push(`Описание пенсии: ${docCheckRes.pension_description}`);
            reportLines.push("Проверенные документы:");
            docCheckRes.checked_documents.forEach(d => {
                reportLines.push(`  - ${d.name || d.id}: ${d.status}${d.is_critical ? " (Критичный)" : ""}${d.description ? ` (${d.description})` : ""}${d.condition_text ? ` [Условие: ${d.condition_text}]` : ""}`);
            });
            if (docCheckRes.missing_critical_documents?.length) reportLines.push("ОТСУТСТВУЮТ КРИТИЧНЫЕ ДОКУМЕНТЫ: " + docCheckRes.missing_critical_documents.join(', '));
            if (docCheckRes.missing_other_documents?.length) reportLines.push("Отсутствуют другие документы: " + docCheckRes.missing_other_documents.join(', '));
        }

        if (ragResOuter?.analysis_result) {
            reportLines.push("\n--- Результат RAG-анализа ---");
            reportLines.push(`Уверенность: ${(ragResOuter.confidence_score * 100).toFixed(1)}%`);
            reportLines.push("Анализ:\n" + ragResOuter.analysis_result);
        } else if (analysisError) {
             reportLines.push("\n--- Результат RAG-анализа ---");
             reportLines.push(`Ошибка RAG-анализа: ${analysisError}`);
        } else {
             reportLines.push("\n--- Результат RAG-анализа ---");
             reportLines.push("RAG-анализ не дал результатов или не был выполнен.");
        }
        setFinalReportText(reportLines.join('\n'));
        console.log("Этап 3 (Формирование отчета) завершен.");

    } catch (err: any) {
        console.error("Ошибка в handleFinalSubmit:", err);
        onSubmitError(err.message || "Произошла ошибка при финальной обработке дела.");
        setError("root.serverError" as any, { type: "manual", message: err.message || "Произошла ошибка на сервере" });
    } finally {
        setIsSubmitting(false);
        setIsLoadingAnalysis(false); 
        console.log("handleFinalSubmit полностью завершен.");
    }
  };

  const handleAnalyzeCaseSeparate = async () => { // Переименована для ясности
    setIsLoadingAnalysis(true);
    await runRagAnalysis(getValues());
    setIsLoadingAnalysis(false);
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

  const handlePensionTypeChange = (value: string) => {
    setSelectedPensionType(value);
    setValue('pension_type', value, { shouldDirty: true });
    setPensionTypeError(null);
    const newSteps = getStepsForPensionType(value);
    setCurrentSteps(newSteps);
    // Сбрасываем финальные результаты, если меняется тип пенсии
    setDocumentCheckResult(null);
    setAnalysisResult(null);
    setAnalysisError(null);
    setFinalReportText(null);
    if (activeStep >= newSteps.length) {
      setActiveStep(newSteps.length > 0 ? newSteps.length - 1 : 0);
    }
  };

  const handleNext = async () => {
    let isValidStep = true;
    setPensionTypeError(null);
    const currentStepDefinition = currentSteps[activeStep];
    const fieldsToValidate: (keyof CaseFormDataType | string)[] = currentStepDefinition.fieldsToValidate || [];
    
    // Динамическая валидация для WorkExperienceStep
    if (currentStepDefinition.id === 'workExperience') {
        const workRecords = getValues('work_experience.records');
        workRecords.forEach((_, index) => {
            fieldsToValidate.push(`work_experience.records.${index}.organization`);
            fieldsToValidate.push(`work_experience.records.${index}.start_date`);
            fieldsToValidate.push(`work_experience.records.${index}.end_date`);
            fieldsToValidate.push(`work_experience.records.${index}.position`);
        });
    }
     // Динамическая валидация для PersonalDataStep (name_change_info)
    if (currentStepDefinition.id === 'personalData' && getValues('personal_data.name_change_info')) {
        fieldsToValidate.push('personal_data.name_change_info.old_full_name');
        fieldsToValidate.push('personal_data.name_change_info.date_changed');
    }


    if (fieldsToValidate.length > 0) {
        isValidStep = await trigger(fieldsToValidate as any);
    }
    if (currentStepDefinition.id === 'pensionType' && !selectedPensionType) {
        isValidStep = false;
        setPensionTypeError('Пожалуйста, выберите тип пенсии');
    }

    if (isValidStep && activeStep < currentSteps.length - 1) goToNext();
  };

  const handlePrevious = () => goToPrevious();

  const renderStepContent = () => {
    if (activeStep >= currentSteps.length || activeStep < 0) return <Text color="red.500">Ошибка отображения шага.</Text>;
    const CurrentComponent = currentSteps[activeStep].component;
    const stepId = currentSteps[activeStep].id;
    const commonProps = { register, errors, control, getValues, setValue, getErrorMessage, watch, availablePensionTypes, pensionTypesLoading, pensionTypesError };

    if (stepId === 'pensionType') return <CurrentComponent selectedValue={selectedPensionType} onChange={handlePensionTypeChange} errorMessage={pensionTypeError || undefined} {...commonProps} />;
    if (stepId === 'documentUpload') return <CurrentComponent setValue={setValue} />;
    if (stepId === 'personalData') return <CurrentComponent {...commonProps} errors={errors.personal_data || {}} />;
    if (stepId === 'workExperience') return <CurrentComponent {...commonProps} errors={errors.work_experience || {}} fieldArray={fieldArray} />;
    if (stepId === 'disabilityInfo') return <CurrentComponent {...commonProps} errors={errors.disability || {}} />;
    if (stepId === 'additionalInfo') return <CurrentComponent {...commonProps} pensionType={selectedPensionType} />;
    if (stepId === 'summary') return <CurrentComponent formData={getValues()} availablePensionTypes={availablePensionTypes} />;
    return <Text>Компонент для шага "{currentSteps[activeStep].title}" не найден.</Text>;
  };

  const downloadTxtFile = (text: string | null, filename: string) => {
    if (!text) return;
    const element = document.createElement("a");
    const file = new Blob([text], {type: 'text/plain;charset=utf-8'});
    element.href = URL.createObjectURL(file);
    element.download = filename;
    document.body.appendChild(element); 
    element.click();
    document.body.removeChild(element);
    URL.revokeObjectURL(element.href);
  };

  return (
    <Box 
        as="form" 
        onSubmit={handleSubmit(handleFinalSubmit)} 
        p={5} 
        borderWidth="1px" 
        borderRadius="lg" 
        boxShadow="md"
        bg={mainBoxBg}
    >
       <Heading as="h2" size="lg" textAlign="center" mb={6} color="primary">Ввод данных пенсионного дела</Heading>
        <Stepper index={activeStep} mb={8} colorScheme="blue">
            {currentSteps.map((step, index) => (
                <Step key={step.id} onClick={() => { if (index <= activeStep) setActiveStep(index);}}
                    cursor={index <= activeStep ? "pointer" : "default"}
                    opacity={index > activeStep ? 0.5 : 1}
                    _hover={index <= activeStep ? { bg: stepperHoverBg, borderRadius: 'md' } : {}} >
                    <StepIndicator>
                        <StepStatus complete={<StepIcon />} incomplete={<StepNumber />} active={<StepNumber />} />
                    </StepIndicator>
                    <Box flexShrink='0'> <StepTitle>{step.title}</StepTitle> <StepDescription>{step.description}</StepDescription> </Box>
                    <StepSeparator />
                </Step>
             ))}
        </Stepper>

        <Box mb={8}> {renderStepContent()} </Box>

        <VStack spacing={4} align="stretch">
            <Flex>
                <Button onClick={handlePrevious} isDisabled={activeStep === 0 || isSubmitting || isLoadingAnalysis} variant="outline" leftIcon={<ArrowBackIcon />}>Назад</Button>
                <Spacer />
                {activeStep < currentSteps.length - 1 && (
                    <Button onClick={handleNext} colorScheme="blue" rightIcon={<ArrowForwardIcon />} isDisabled={isSubmitting || isLoadingAnalysis}>Далее</Button>
                )}
                {(activeStep === currentSteps.length - 1) && (
                    <Flex direction="row" justify="flex-end">
                         {!finalReportText && !isSubmitting && (
                            <Button type="button" onClick={handleAnalyzeCaseSeparate} isLoading={isLoadingAnalysis} isDisabled={isLoadingAnalysis} colorScheme="teal" variant="outline" mr={3}>
                                RAG-анализ (отдельно)
                            </Button>
                         )}
                         <Button type="submit" isLoading={isSubmitting} isDisabled={isSubmitting || isLoadingAnalysis} colorScheme="primary">
                             {finalReportText ? "Сформировать отчет повторно" : "Проверить и сформировать отчет"}
                         </Button>
                    </Flex>
                )}
            </Flex> 

            {(isSubmitting || isLoadingAnalysis || finalReportText || analysisError || documentCheckResult || errors.root?.serverError) && (
                 <VStack spacing={5} align="stretch" mt={6} p={5} borderWidth="1px" borderRadius="lg" 
                         borderColor={resultsVStackBorderColor}
                         bg={resultsVStackBg}
                 >
                    {(isSubmitting || isLoadingAnalysis) && !(documentCheckResult || analysisResult || analysisError || finalReportText) && (
                        <Flex justify="center" align="center" direction="column" p={4}>
                            <CircularProgress isIndeterminate color="blue.500" />
                            <Text mt={3} color={progressTextColor}>
                                {isSubmitting && !documentCheckResult ? "Проверка комплекта документов..." : ""}
                                {isLoadingAnalysis && !analysisResult && documentCheckResult ? " RAG-анализ..." : ""}
                                {isSubmitting && isLoadingAnalysis && !documentCheckResult && !analysisResult ? "Обработка..." : ""}
                            </Text>
                        </Flex>
                    )}
                    
                    {errors.root?.serverError && (
                        <Alert status="error" variant="subtle"> <AlertIcon /> <AlertTitle>Ошибка обработки!</AlertTitle> <AlertDescription>{(errors.root.serverError as any).message}</AlertDescription> </Alert>
                    )}

                    {documentCheckResult && (
                        <Box borderWidth="1px" borderRadius="md" p={4} borderColor={docCheckBorderColor}>
                            <Heading size="md" mb={3} color={docCheckHeadingColor} borderBottomWidth="1px" pb={2}>Результат проверки комплекта документов</Heading>
                            <VStack spacing={1.5} align="stretch">
                                <Text><strong>Тип пенсии:</strong> {documentCheckResult.pension_display_name} ({documentCheckResult.pension_type_key})</Text>
                                <Text><strong>Общий статус:</strong>
                                    <Badge ml={2} fontSize="0.9em" colorScheme={documentCheckResult.overall_status === 'Документы в порядке' ? 'green' : documentCheckResult.overall_status === 'Требуются критичные документы' ? 'red' : 'orange'}>
                                        {documentCheckResult.overall_status}
                                    </Badge>
                                </Text>
                                {documentCheckResult.pension_description && (<Text fontSize="sm" color={pensionDescTextColor}><em>{documentCheckResult.pension_description}</em></Text>)}
                                <Heading size="sm" mt={2} mb={1}>Проверенные документы:</Heading>
                                {documentCheckResult.checked_documents?.length > 0 ? (
                                    <UnorderedList spacing={1.5} ml={5}>
                                        {documentCheckResult.checked_documents.map(doc => (
                                            <ListItem key={doc.id}>
                                                <Text as="span" fontWeight={doc.is_critical ? "bold" : "normal"}> {doc.name || doc.id}: 
                                                    <Badge ml={1.5} fontSize="0.85em" colorScheme={doc.status === 'Предоставлен и корректен' ? 'green' : doc.status === 'Предоставлен, но есть замечания' ? 'yellow' : doc.status === 'Отсутствует (критичный)' ? 'red' : doc.status === 'Отсутствует' ? 'orange' : 'gray'}>
                                                        {doc.status}
                                                    </Badge>
                                                    {doc.is_critical && <Badge ml={1} colorScheme="red" variant="outline" fontSize="0.8em">Критичный</Badge>}
                                                </Text>
                                                {doc.description && <Text fontSize="xs" color={docDescriptionTextColor} pl={0}><em>{doc.description}</em></Text>}
                                                {doc.condition_text && <Text fontSize="xs" color={docConditionTextColor} pl={0}><em>Условие: {doc.condition_text}</em></Text>}
                                            </ListItem>
                                        ))}
                                    </UnorderedList>
                                ) : (<Text>Нет информации о проверенных документах.</Text>)}
                                {documentCheckResult.missing_critical_documents?.length > 0 && (<>
                                    <Heading size="sm" mt={2} mb={1} color={missingCriticalColor}>Отсутствуют критичные документы:</Heading>
                                    <UnorderedList spacing={1} color={missingCriticalColor} ml={5}>
                                        {documentCheckResult.missing_critical_documents.map((docName: string) => ( <ListItem key={docName}>{docName}</ListItem> ))}
                                    </UnorderedList>
                                </>)}
                                {documentCheckResult.missing_other_documents?.length > 0 && (<>
                                    <Heading size="sm" mt={2} mb={1} color={missingOtherColor}>Отсутствуют другие документы:</Heading>
                                    <UnorderedList spacing={1} color={missingOtherColor} ml={5}>
                                        {documentCheckResult.missing_other_documents.map((docName: string) => ( <ListItem key={docName}>{docName}</ListItem> ))}
                                    </UnorderedList>
                                </>)}
                            </VStack>
                        </Box>
                    )}

                    {(analysisResult || analysisError) && (
                         <Box borderWidth="1px" borderRadius="md" p={4} borderColor={analysisBorderColor} mt={documentCheckResult ? 4 : 0}>
                             <Flex justify="space-between" align="flex-start" mb={2} borderBottomWidth="1px" pb={2}>
                                 <Heading size="md" display="flex" alignItems="center" color={analysisHeadingColor}><InfoIcon mr={2} />Результат RAG-анализа:</Heading>
                                 {analysisResult && (
                                    <Flex align="center">
                                        {confidenceScore !== null && (<Text fontSize="sm" color={analysisConfidenceColor} mr={2}>Уверенность: {(confidenceScore * 100).toFixed(1)}%</Text>)}
                                        <IconButton aria-label="Copy analysis result" icon={<CopyIcon />} size="sm" variant="ghost" colorScheme={hasCopied ? "green" : "gray"} onClick={onCopy} title={hasCopied ? 'Скопировано!' : 'Копировать'}/>
                                    </Flex>
                                 )}
                             </Flex>
                             {analysisError && !analysisResult && (<Alert status="error" variant="subtle" mt={2}> <AlertIcon /> <AlertDescription>{analysisError}</AlertDescription></Alert>)}
                             {analysisResult && (
                                <Box p={2} bg={analysisMarkdownBg} borderRadius="md">
                                     <Text as="div" whiteSpace="pre-wrap" sx={{wordBreak: 'break-word'}}>
                                        {analysisResult}
                                    </Text>
                                </Box>
                             )}
                         </Box>
                    )}
                    
                    {finalReportText && (
                        <Button 
                            mt={4} 
                            colorScheme="green" 
                            leftIcon={<DownloadIcon />} 
                            onClick={() => {
                                if (finalReportText) {
                                    const filename = `pension_case_report_${new Date().toISOString().split('T')[0]}.txt`;
                                    downloadTxtFile(finalReportText, filename);
                                }
                            }}
                            isDisabled={!finalReportText}
                        >
                            Скачать общий отчет (TXT)
                        </Button>
                    )}
                 </VStack>
            )}
        </VStack>
    </Box>
  );
}

export default CaseForm;