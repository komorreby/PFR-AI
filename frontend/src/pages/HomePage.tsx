// src/pages/HomePage.tsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  Layout,
  Steps,
  Button,
  Form,
  message as antdMessage,
  Spin,
  Alert,
  Card,
  Typography,
  Result,
  Row,
  Col,
  Tag,
  Select,
} from 'antd';
import {
  SolutionOutlined,
  UserOutlined,
  FileDoneOutlined,
  ExperimentOutlined,
  AuditOutlined,
  ScheduleOutlined,
  IdcardOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useForm, FormProvider, useFieldArray, Controller } from 'react-hook-form';

// API клиент и типы
import { createCase, getCaseStatus, getPensionTypes, getStandardDocumentNames, getPensionDocuments, submitOcrTask, getOcrTaskStatus } from '../services/apiClient';
import type {
  CaseDataInput,
  ProcessOutput,
  ApiError,
  PensionTypeInfo,
  PersonalData,
  WorkExperience,
  DisabilityInfo,
  OtherDocumentData,
  OcrTaskSubmitResponse,
  OcrTaskStatusResponse,
  DocumentTypeToExtract,
  PassportData,
  SnilsData,
  WorkBookData,
  DocumentDetail,
  CaseFormDataTypeForRHF,
  OcrResultData
} from '../types';

// Компоненты шагов (будем создавать их позже)
import PensionTypeStep from '../components/formSteps/PensionTypeStep';
import DocumentUploadStep from '../components/formSteps/DocumentUploadStep';
import PersonalDataStep from '../components/formSteps/PersonalDataStep';
import WorkExperienceStep from '../components/formSteps/WorkExperienceStep';
import DisabilityInfoStep from '../components/formSteps/DisabilityInfoStep';
import AdditionalInfoStep from '../components/formSteps/AdditionalInfoStep';
import SummaryStep from '../components/formSteps/SummaryStep';
import ProcessResultDisplay from '../components/ProcessResultDisplay';

const { Title } = Typography;
const { Content } = Layout; // Если нужен свой Layout для страницы

const POLLING_INTERVAL = 5000; // 5 секунд для опроса статуса дела

// Начальные значения для react-hook-form, используем CaseFormDataTypeForRHF
const initialRHFValues: CaseFormDataTypeForRHF = {
  pension_type: undefined,
  personal_data: {
    last_name: '',
    first_name: '',
    middle_name: null,
    birth_date: '',
    snils: '',
    gender: '', // Должно быть 'male' или 'female' или другое валидное значение
    citizenship: 'Россия',
    name_change_info: null,
    name_change_info_checkbox: false,
    dependents: 0, // dependents по API в personal_data
    // Поля паспорта из CaseFormDataTypeForRHF
    passport_series: '',
    passport_number: '',
    passport_issue_date: '',
    issuing_authority: '',
    department_code: '',
    birth_place: '',
  },
  disability: null,
  work_experience: {
    total_years: 0,
    records: [],
  },
  pension_points: null,
  benefits: '', // Строка тегов
  // submitted_documents теперь называется 'documents' в AdditionalInfoStep для RHF
  documents: '', // Строка тегов для стандартных документов
  has_incorrect_document: false,
  other_documents_extracted_data: [],
  // Убираем dependentsUi, т.к. dependents теперь часть personal_data и CaseFormDataTypeForRHF
};


const HomePage: React.FC = () => {
  const [antdForm] = Form.useForm(); // Экземпляр формы Ant Design для layout и validateFields (если нужно)

  // Инициализация React Hook Form
  const rhfMethods = useForm<CaseFormDataTypeForRHF>({
    defaultValues: initialRHFValues,
    mode: 'onChange', // или 'onBlur', 'onSubmit'
  });
  const { control, watch, setValue, getValues, formState: { errors: rhfErrors }, trigger, handleSubmit, reset: rhfReset } = rhfMethods;

  // Для WorkExperienceStep (динамические поля стажа)
  const { fields: workExperienceFields, append: appendWorkExperience, remove: removeWorkExperience } = useFieldArray({
    control,
    name: "work_experience.records",
  });

  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submissionResult, setSubmissionResult] = useState<ProcessOutput | null>(null);
  const [pollingCaseId, setPollingCaseId] = useState<number | null>(null);
  const [finalCaseStatus, setFinalCaseStatus] = useState<ProcessOutput | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [allOcrDocsProcessed, setAllOcrDocsProcessed] = useState(false);
  const [ocrStepNextButtonDisabled, setOcrStepNextButtonDisabled] = useState(false);
  const [personalDataStepValid, setPersonalDataStepValid] = useState(false);

  // Состояния для справочников
  const [pensionTypes, setPensionTypes] = useState<PensionTypeInfo[]>([]);
  const [loadingPensionTypes, setLoadingPensionTypes] = useState(true);
  const [standardDocNames, setStandardDocNames] = useState<string[]>([]); // Для AdditionalInfoStep
  const [requiredDocsForType, setRequiredDocsForType] = useState<DocumentDetail[]>([]); // Документы для выбранного типа пенсии


  // Загрузка типов пенсий при монтировании
  useEffect(() => {
    const fetchInitialData = async () => {
      setLoadingPensionTypes(true);
      try {
        const types = await getPensionTypes();
        setPensionTypes(types);
        const stdNames = await getStandardDocumentNames();
        setStandardDocNames(stdNames);
      } catch (error) {
        console.error("Error fetching initial data for form:", error);
        antdMessage.error('Ошибка загрузки справочников для формы.');
      } finally {
        setLoadingPensionTypes(false);
      }
    };
    fetchInitialData();
  }, []);

  const selectedPensionTypeRHF = watch('pension_type');

  useEffect(() => {
    if (selectedPensionTypeRHF) {
      const fetchReqDocs = async () => {
        try {
          const docs = await getPensionDocuments(selectedPensionTypeRHF);
          setRequiredDocsForType(docs);
        } catch (error) {
          console.error("Error fetching required documents:", error);
          setRequiredDocsForType([]);
        }
      };
      fetchReqDocs();
    } else {
      setRequiredDocsForType([]);
    }
  }, [selectedPensionTypeRHF]);

  const steps = [
    {
      title: 'Тип пенсии',
      icon: <SolutionOutlined />,
      content: (
        <Controller
          name="pension_type"
          control={control}
          rules={{ required: 'Пожалуйста, выберите тип пенсии!' }}
          render={({ field }) => (
            <PensionTypeStep
              form={antdForm}
              pensionTypes={pensionTypes}
              loadingPensionTypes={loadingPensionTypes}
              currentValue={field.value}
              onChange={(value) => {
                field.onChange(value);
                // Сброс зависимых полей при смене типа пенсии
                setValue('work_experience', initialRHFValues.work_experience, { shouldValidate: true });
                setValue('disability', initialRHFValues.disability, { shouldValidate: true });
                setValue('pension_points', initialRHFValues.pension_points, { shouldValidate: true });
                // Также сбросим поля из AdditionalInfoStep, которые могли быть заполнены
                setValue('benefits', initialRHFValues.benefits, { shouldValidate: false });
                setValue('documents', initialRHFValues.documents, { shouldValidate: false }); // это submitted_documents в RHF
                setValue('other_documents_extracted_data', initialRHFValues.other_documents_extracted_data, { shouldValidate: false });
                // Пересчитываем видимые шаги и валидируем форму
                trigger();
              }}
            />
          )}
        />
      ),
      fieldsToValidate: ['pension_type'],
    },
    {
      title: 'Документы (OCR)',
      icon: <FileDoneOutlined />,
      content: (
        <DocumentUploadStep
          setValue={setValue}
          control={control}
          errors={rhfErrors}
          trigger={trigger}
          onOcrStepNextButtonDisabledStateChange={setOcrStepNextButtonDisabled}
        />
      ),
      fieldsToValidate: [],
    },
    {
      title: 'Личные данные',
      icon: <UserOutlined />,
      content: (
        <PersonalDataStep
          control={control}
          watch={watch}
          setValue={setValue}
          form={antdForm}
          errors={rhfErrors}
          onValidationStateChange={setPersonalDataStepValid}
        />
      ),
      fieldsToValidate: [
        'personal_data.last_name', 'personal_data.first_name',
        'personal_data.birth_date', 'personal_data.snils',
        'personal_data.gender', 'personal_data.citizenship',
        'personal_data.dependents'
      ],
    },
    {
      title: 'Трудовой стаж',
      icon: <ScheduleOutlined />,
      content: (
        <WorkExperienceStep
          control={control}
          errors={rhfErrors}
          fields={workExperienceFields}
          append={appendWorkExperience}
          remove={removeWorkExperience}
          getValues={getValues}
          form={antdForm}
        />
      ),
      fieldsToValidate: ['work_experience.total_years'],
    },
    {
      title: 'Инвалидность',
      icon: <IdcardOutlined />,
      content: (
        <DisabilityInfoStep
          control={control}
          errors={rhfErrors}
        />
      ),
      fieldsToValidate: ['disability.group', 'disability.date'],
    },
    {
      title: 'Доп. информация',
      icon: <InfoCircleOutlined />,
      content: (
        <AdditionalInfoStep
          control={control}
          errors={rhfErrors}
          pensionType={selectedPensionTypeRHF || null}
          setValue={setValue}
          getValues={getValues}
          trigger={trigger}
        />
      ),
      fieldsToValidate: selectedPensionTypeRHF === 'retirement_standard' ? ['pension_points'] : [],
    },
    {
      title: 'Сводка и отправка',
      icon: <AuditOutlined />,
      content: <SummaryStep formData={getValues()} />,
    },
  ];

  const getVisibleSteps = () => {
    const pensionType = watch('pension_type');
    let visibleStepsConfig = [steps[0]];

    visibleStepsConfig.push(steps[1]);

    visibleStepsConfig.push(steps[2]);

    if (pensionType === 'retirement_standard' || pensionType === 'retirement_early_teacher' || pensionType === 'retirement_early_north' || pensionType === 'disability_insurance') {
      visibleStepsConfig.push(steps[3]);
    }
    if (pensionType === 'disability_social' || pensionType === 'disability_insurance') {
      visibleStepsConfig.push(steps[4]);
    }

    visibleStepsConfig.push(steps[5]);
    visibleStepsConfig.push(steps[6]);

    return visibleStepsConfig;
  };

  const currentVisibleSteps = getVisibleSteps();
  const activeStepContent = currentVisibleSteps[currentStep]?.content;
  let activeStepFieldsToValidate = currentVisibleSteps[currentStep]?.fieldsToValidate as string[] | undefined;
  if (currentVisibleSteps[currentStep]?.title === 'Доп. информация') {
    activeStepFieldsToValidate = selectedPensionTypeRHF === 'retirement_standard' ? ['pension_points'] : [];
  }


  const next = async () => {
    let isValid = true;
    if (activeStepFieldsToValidate && activeStepFieldsToValidate.length > 0) {
        isValid = await trigger(activeStepFieldsToValidate);
    }
    if (isValid) {
      setCurrentStep(currentStep + 1);
    } else {
      antdMessage.error('Пожалуйста, заполните все обязательные поля на текущем шаге.');
    }
  };

  const prev = () => {
    setCurrentStep(currentStep - 1);
  };

  const handleFormSubmitRHF = async (data: CaseFormDataTypeForRHF) => {
    setLoading(true);
    setSubmissionError(null);
    setSubmissionResult(null);
    setFinalCaseStatus(null);

    // Маппинг данных из CaseFormDataTypeForRHF в CaseDataInput (API)
    const apiPayload: CaseDataInput = {
        pension_type: data.pension_type!, 
        personal_data: {
            last_name: data.personal_data!.last_name!,
            first_name: data.personal_data!.first_name!,
            middle_name: data.personal_data!.middle_name || null,
            birth_date: data.personal_data!.birth_date!,
            snils: data.personal_data!.snils!,
            gender: data.personal_data!.gender!,
            citizenship: data.personal_data!.citizenship!,
            name_change_info: data.personal_data!.name_change_info_checkbox && data.personal_data!.name_change_info 
                                ? data.personal_data!.name_change_info 
                                : null,
            dependents: data.personal_data!.dependents || 0,
        },
        // Если disability есть, но group или date отсутствуют, то это невалидный объект для API.
        // Передаем null, если объект неполный.
        disability: (data.disability && data.disability.group && data.disability.date) 
                        ? data.disability as DisabilityInfo 
                        : null,
        work_experience: data.work_experience 
            ? {
                total_years: data.work_experience.total_years || 0,
                records: data.work_experience.records || [],
              }
            : null,
        pension_points: data.pension_points || null,
        benefits: data.benefits ? data.benefits.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
        submitted_documents: data.documents ? data.documents.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
        has_incorrect_document: data.has_incorrect_document || false,
        // Фильтруем other_documents_extracted_data, чтобы убедиться, что все элементы соответствуют OtherDocumentData
        // Поля в OtherDocumentData (кроме extracted_fields) все nullable, так что Partial<OtherDocumentData> подходит, если extracted_fields тоже null или объект.
        // Главное, чтобы сам объект other_documents_extracted_data был массивом OtherDocumentData[]
        other_documents_extracted_data: data.other_documents_extracted_data
            ? data.other_documents_extracted_data.filter(
                doc => doc && (doc.identified_document_type || doc.standardized_document_type)
            ).map(doc => ({
                identified_document_type: doc.identified_document_type || null,
                standardized_document_type: doc.standardized_document_type || null,
                extracted_fields: doc.extracted_fields || null,
                multimodal_assessment: doc.multimodal_assessment || null,
                text_llm_reasoning: doc.text_llm_reasoning || null,
            } as OtherDocumentData)) // Приведение типа к OtherDocumentData
            : [],
    };
    
    console.log('Submitting API Payload:', apiPayload);

    try {
      const result = await createCase(apiPayload);
      setSubmissionResult(result);
      if (result.case_id && result.final_status === 'PROCESSING') {
        setPollingCaseId(result.case_id);
      } else {
        setFinalCaseStatus(result);
      }
    } catch (err) {
      const apiErr = err as ApiError;
      console.error('Form submission error:', apiErr);
      let errorMessageText = apiErr.message || 'Произошла ошибка при отправке дела.';
      if (apiErr.validationDetails && Array.isArray(apiErr.validationDetails)) {
        const fieldsErrors = apiErr.validationDetails.map(detail => {
            let fieldPath = (detail as any).field?.replace(/^body\./, '') || (detail as any).loc?.slice(1).join('.');
            // Проверяем наличие msg или message
            const message = (detail as any).msg || (detail as any).message || 'Неизвестная ошибка поля';
            return `${fieldPath}: ${message}`;
        }).join('; ');
        errorMessageText += ` Детали: ${fieldsErrors}`;
      }
      setSubmissionError(errorMessageText);
      antdMessage.error(errorMessageText, 7);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let intervalId: number | undefined;
    if (pollingCaseId) {
      setLoading(true);
      const pollStatus = async () => {
        try {
          console.log(`Polling status for case ID: ${pollingCaseId}`);
          const statusResult = await getCaseStatus(pollingCaseId);
          if (statusResult.final_status !== 'PROCESSING') {
            setFinalCaseStatus(statusResult);
            setPollingCaseId(null);
            if (intervalId) clearInterval(intervalId);
            setLoading(false);
            antdMessage.success(`Обработка дела #${statusResult.case_id} завершена. Статус: ${statusResult.final_status}`);
          } else {
            setSubmissionResult(statusResult);
          }
        } catch (error) {
          console.error('Polling error:', error);
          antdMessage.warning('Ошибка при опросе статуса дела. Поллинг будет продолжен.');
        }
      };
      pollStatus();
      intervalId = window.setInterval(pollStatus, POLLING_INTERVAL);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
      if (pollingCaseId) setLoading(false);
    };
  }, [pollingCaseId]);


  const resetFormAndState = () => {
    rhfReset(initialRHFValues);
    antdForm.resetFields();
    setCurrentStep(0);
    setSubmissionResult(null);
    setPollingCaseId(null);
    setFinalCaseStatus(null);
    setSubmissionError(null);
    setLoading(false);
    setOcrStepNextButtonDisabled(false);
    setPersonalDataStepValid(false);
  };

  if (finalCaseStatus) {
    return (
      <Result
        status={finalCaseStatus.final_status.toLowerCase().includes('соответствует') ? 'success' : finalCaseStatus.final_status.toLowerCase().includes('не соответствует') ? 'error' : 'info'}
        title={`Обработка дела завершена`}
        subTitle={`Статус дела ID ${finalCaseStatus.case_id}: ${finalCaseStatus.final_status}`}
        extra={[
          <Button type="primary" key="new" onClick={resetFormAndState}>
            Создать новое дело
          </Button>,
        ]}
      >
        <div style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'left' }}>
            <ProcessResultDisplay result={finalCaseStatus} />
        </div>
      </Result>
    );
  }

  if (submissionResult && pollingCaseId) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} tip={`Дело #${submissionResult.case_id} принято в обработку. Ожидаем результат...`} size="large" />
        <Typography.Paragraph style={{ marginTop: 20 }}>
            Текущий статус: <Tag color="blue">{submissionResult.final_status}</Tag>
        </Typography.Paragraph>
        <Typography.Paragraph style={{whiteSpace: 'pre-wrap', color: '#888'}}>
            {submissionResult.explanation}
        </Typography.Paragraph>
      </div>
    );
  }

  return (
    <FormProvider {...rhfMethods}>
        <Card style={{ maxWidth: '1000px', margin: '20px auto' }}>
        <Title level={2} style={{ textAlign: 'center', marginBottom: '30px' }}>
            Создание нового пенсионного дела
        </Title>
        <Steps 
          current={currentStep} 
          items={currentVisibleSteps.map(item => ({ key: item.title, title: item.title, icon: item.icon }))} 
          style={{marginBottom: '40px'}} 
          progressDot
        />

        <Form
            form={antdForm}
            layout="vertical"
            name="pension_case_form_rhf"
            onFinish={handleSubmit(handleFormSubmitRHF)}
        >
            <Spin spinning={loading && currentStep === currentVisibleSteps.length -1} tip="Отправка данных...">
                <div style={{ minHeight: '300px', marginBottom: '24px' }}>
                    {activeStepContent}
                </div>
            </Spin>

            {submissionError && !pollingCaseId && (
                <Alert message="Ошибка отправки" description={submissionError} type="error" showIcon style={{marginBottom: '24px'}}/>
            )}

            <Row justify="space-between">
            <Col>
                {currentStep > 0 && (
                <Button style={{ margin: '0 8px' }} onClick={prev}>
                    Назад
                </Button>
                )}
            </Col>
            <Col>
                {currentStep < currentVisibleSteps.length - 1 && (
                <Button 
                    type="primary" 
                    onClick={next}
                    disabled={
                        (currentVisibleSteps[currentStep]?.title === 'Документы (OCR)' && ocrStepNextButtonDisabled) ||
                        (currentVisibleSteps[currentStep]?.title === 'Личные данные' && !personalDataStepValid)
                    } 
                >
                    Далее
                </Button>
                )}
                {currentStep === currentVisibleSteps.length - 1 && (
                <Button type="primary" htmlType="submit" loading={loading}> 
                    Отправить дело
                </Button>
                )}
            </Col>
            </Row>
        </Form>
        </Card>
    </FormProvider>
  );
};

export default HomePage;