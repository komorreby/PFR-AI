import React from 'react';
import { IMaskInput } from 'react-imask';
import { Input, InputProps } from '@chakra-ui/react';
import { parse, format, isValid, isAfter } from 'date-fns';

interface CustomDateInputProps extends Omit<InputProps, 'onChange'> {
    value?: string; // Значение в формате dd.MM.yyyy от DatePicker
    onClick?: () => void;
    fieldOnChange: (value: string) => void; // RHF field.onChange
    id: string;
    maxDate?: Date;
}

const CustomDateInput = React.forwardRef<HTMLInputElement, CustomDateInputProps>(
    ({ value, onClick, fieldOnChange, id, maxDate, ...rest }, ref) => {
        const today = new Date();
        const effectiveMaxDate = maxDate instanceof Date && !isNaN(maxDate.getTime()) ? maxDate : today;

        return (
            <Input
                as={IMaskInput}
                mask={'00.00.0000'}
                value={value || ''}
                placeholder="ДД.ММ.ГГГГ"
                id={id}
                onClick={onClick}
                ref={ref}
                bg="white"
                borderColor="inherit"
                _hover={{ borderColor: "gray.300" }}
                _focus={{ zIndex: 1, borderColor: "primary", boxShadow: `0 0 0 1px var(--chakra-colors-primary)` }}
                width="100%"
                autoComplete="off"
                onAccept={(acceptedValue: any) => {
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
                {...rest}
            />
        );
    }
);

CustomDateInput.displayName = 'CustomDateInput';

export default CustomDateInput; 