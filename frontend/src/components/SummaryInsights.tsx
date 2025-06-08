import React, { useMemo } from 'react';
import { Alert, Space, Button } from 'antd';
import { CaseFormDataTypeForRHF } from '../types';
import {
    CheckCircleOutlined,
    InfoCircleOutlined,
    WarningOutlined,
    CloseCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

interface InsightMessage {
    text: string;
    type: 'success' | 'info' | 'warning' | 'error';
    stepIndex?: number; // Для опциональной навигации
}

interface SummaryInsightsProps {
    formData: CaseFormDataTypeForRHF;
    onEditStep?: (stepIndex: number) => void;
}

const SummaryInsights: React.FC<SummaryInsightsProps> = ({ formData, onEditStep }) => {
    const insights: InsightMessage[] = [];

    // Правило 1: Критические отсутствующие данные
    const missingCriticalFields: string[] = [];
    if (!formData.pension_type) missingCriticalFields.push("Тип пенсии (Шаг 1)");
    if (!formData.personal_data?.last_name) missingCriticalFields.push("Фамилия (Шаг 3)");
    if (!formData.personal_data?.first_name) missingCriticalFields.push("Имя (Шаг 3)");
    if (!formData.personal_data?.snils) missingCriticalFields.push("СНИЛС (Шаг 3)");

    if (missingCriticalFields.length > 0) {
        insights.push({
            text: `Не заполнены обязательные поля: ${missingCriticalFields.join(', ')}. Пожалуйста, вернитесь и укажите их.`,
            type: 'error',
            // stepIndex можно определить более точно, если есть маппинг полей на шаги
        });
    }

    // Правило 2: Некорректные документы
    if (formData.has_incorrect_document) {
        insights.push({
            text: "Вы указали, что есть некорректно оформленные документы. Рекомендуем проверить их на шаге 'Доп. информация' или загрузить исправленные версии.",
            type: 'warning',
            stepIndex: 5, // Предполагая, что "Доп. информация" - это шаг с индексом 5
        });
    }

    // Правило 3: Потенциальные несоответствия для типа пенсии
    if (formData.pension_type === 'retirement_standard') {
        const workYears = formData.work_experience?.calculated_total_years;
        const points = formData.pension_points;
        if ((workYears !== null && workYears !== undefined && workYears < 15) || (points !== null && points !== undefined && points < 10)) { // Примерные пороговые значения
            insights.push({
                text: "Указанный стаж и/или количество пенсионных баллов могут быть недостаточными для назначения страховой пенсии по старости. Рекомендуем проверить данные или приложить подтверждающие документы.",
                type: 'info',
                stepIndex: 3, // Стаж
            });
        }
    } else if (formData.pension_type === 'disability_social') {
        if (!formData.disability?.group || !formData.disability?.date) {
            insights.push({
                text: "Для социальной пенсии по инвалидности необходимо указать сведения об инвалидности.",
                type: 'warning',
                stepIndex: 4, // Инвалидность
            });
        }
    }

    // Правило 4: Много "других документов"
    if (formData.other_documents_extracted_data && formData.other_documents_extracted_data.length > 3) {
        insights.push({
            text: "Загружено несколько дополнительных документов. Убедитесь, что данные из них корректно извлечены и учтены на шаге 'Доп. информация'.",
            type: 'info',
            stepIndex: 5, // Доп. информация
        });
    }
    
    // Определение приоритетной подсказки или нескольких
    let displayedInsights = insights;
    const errors = insights.filter(i => i.type === 'error');
    const warnings = insights.filter(i => i.type === 'warning');

    if (errors.length > 0) {
        displayedInsights = errors; // Показываем только ошибки, если они есть
    } else if (warnings.length > 0) {
        displayedInsights = warnings; // Или только предупреждения, если нет ошибок
    }

    // Правило 5: Все хорошо (если нет других сообщений)
    if (insights.length === 0) {
        insights.push({
            text: "Похоже, все основные данные заполнены корректно. Вы можете переходить к отправке.",
            type: 'success',
        });
        displayedInsights = insights;
    }

    if (displayedInsights.length === 0) {
        return null; // Не отображаем ничего, если нет релевантных подсказок
    }

    const getIcon = (type: InsightMessage['type']) => {
        switch (type) {
            case 'success': return <CheckCircleOutlined />;
            case 'info': return <InfoCircleOutlined />;
            case 'warning': return <WarningOutlined />;
            case 'error': return <CloseCircleOutlined />;
            default: return null;
        }
    };

    return (
        <Space direction="vertical" style={{ width: '100%', marginBottom: '20px' }} size="middle">
            <Alert
                message="Рекомендации и важные замечания"
                description={
                    <Space direction="vertical" style={{ width: '100%' }}>
                        {displayedInsights.map((insight, index) => (
                            <div key={index} style={{ display: 'flex', alignItems: 'flex-start' }}>
                                <span style={{ marginRight: 8, fontSize: '16px', color: insight.type === 'error' ? '#ff4d4f' : insight.type === 'warning' ? '#faad14' : insight.type === 'info' ? '#1890ff' : '#52c41a' }}>
                                    {getIcon(insight.type)}
                                </span>
                                <div style={{ flex: 1 }}>
                                    <span style={{color: insight.type === 'error' ? '#ff4d4f' : 'inherit'}}>{insight.text}</span>
                                    {insight.stepIndex !== undefined && onEditStep && (
                                        <Button
                                            type="link"
                                            size="small"
                                            onClick={() => onEditStep(insight.stepIndex!)}
                                            style={{ marginLeft: '8px', padding: '0' }}
                                        >
                                            Перейти к шагу
                                        </Button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </Space>
                }
                type={errors.length > 0 ? 'error' : warnings.length > 0 ? 'warning' : displayedInsights[0]?.type || 'info'}
                showIcon
            />
        </Space>
    );
};

export default SummaryInsights; 