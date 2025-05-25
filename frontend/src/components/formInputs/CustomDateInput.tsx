import React from 'react';
import { IMaskInput } from 'react-imask';
// import { Input, InputProps } from '@chakra-ui/react'; // Удаляем Chakra UI
import { parse, format, isValid, isAfter } from 'date-fns';

// Заменяем InputProps от Chakra UI на стандартные атрибуты HTML для input или более специфичные, если нужно
interface CustomDateInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'onChange' | 'value'> {
    value?: string; // Значение в формате dd.MM.yyyy от DatePicker
    onClick?: () => void;
    fieldOnChange: (value: string) => void; // RHF field.onChange
    id: string;
    maxDate?: Date;
}

const CustomDateInput = React.forwardRef<HTMLInputElement, CustomDateInputProps>(
    ({ value, onClick, fieldOnChange, id, maxDate, className, ...rest }, ref) => {
        const today = new Date();
        const effectiveMaxDate = maxDate instanceof Date && !isNaN(maxDate.getTime()) ? maxDate : today;

        return (
            <IMaskInput
                mask={'00.00.0000'}
                value={value || ''}
                placeholder="ДД.ММ.ГГГГ"
                id={id}
                onClick={onClick}
                inputRef={ref as React.Ref<HTMLInputElement>} // Передаем ref в IMaskInput
                className={`ant-input ${className || ''}`} // Применяем класс ant-input для базовой стилизации
                style={{ width: '100%' }} // Общая стилизация для ширины
                autoComplete="off"
                onAccept={(acceptedValue: string) => {
                    try {
                        if (acceptedValue && acceptedValue.length === 10 && !String(acceptedValue).includes('_')) {
                             const parsedDate = parse(acceptedValue, 'dd.MM.yyyy', new Date());
                             if (isValid(parsedDate) && !isAfter(parsedDate, effectiveMaxDate)) {
                                fieldOnChange(format(parsedDate, 'yyyy-MM-dd'));
                             } else {
                                fieldOnChange('');
                             }
                        } else if (!acceptedValue) {
                            fieldOnChange('');
                        }
                    } catch {
                        fieldOnChange('');
                    }
                }}
                {...rest} // Передаем остальные HTML атрибуты
            />
        );
    }
);

CustomDateInput.displayName = 'CustomDateInput';

export default CustomDateInput; 