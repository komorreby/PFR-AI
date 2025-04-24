import React, { useState, useEffect, useCallback } from 'react';
import {
    Input,
    Tag,
    TagLabel,
    TagCloseButton,
    Wrap, // Используем Wrap для переноса тегов
    WrapItem,
    Box,
    useColorModeValue,
    InputProps,
} from '@chakra-ui/react';

interface TagInputProps extends Omit<InputProps, 'onChange' | 'value'> {
    id: string;
    value?: string; // Значение от RHF (строка, разделенная запятыми)
    fieldOnChange: (value: string) => void; // RHF field.onChange
    placeholder?: string;
}

const TagInput: React.FC<TagInputProps> = ({
    id,
    value,
    fieldOnChange,
    placeholder = "Добавьте тег и нажмите Enter",
    ...rest
}) => {
    const [tags, setTags] = useState<string[]>([]);
    const [inputValue, setInputValue] = useState('');
    const tagBg = useColorModeValue('blue.100', 'blue.700');
    const tagColor = useColorModeValue('blue.800', 'blue.100');

    // Эффект для инициализации тегов из строки value
    useEffect(() => {
        if (value) {
            setTags(value.split(',').map(tag => tag.trim()).filter(Boolean));
        } else {
            setTags([]);
        }
    }, [value]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setInputValue(e.target.value);
    };

    const handleInputKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && inputValue.trim() !== '') {
            e.preventDefault(); // Предотвращаем отправку формы, если она есть
            const newTag = inputValue.trim();
            if (!tags.includes(newTag)) {
                const newTags = [...tags, newTag];
                setTags(newTags);
                fieldOnChange(newTags.join(',')); // Обновляем значение RHF
            }
            setInputValue(''); // Очищаем поле ввода
        }
    }, [inputValue, tags, fieldOnChange]);

    const removeTag = useCallback((tagToRemove: string) => {
        const newTags = tags.filter(tag => tag !== tagToRemove);
        setTags(newTags);
        fieldOnChange(newTags.join(',')); // Обновляем значение RHF
    }, [tags, fieldOnChange]);

    return (
        <Box borderWidth="1px" borderRadius="md" p={2} onClick={() => document.getElementById(id)?.focus()} cursor="text" borderColor="inherit" _hover={{ borderColor: "gray.300" }} _focusWithin={{ zIndex: 1, borderColor: "primary", boxShadow: `0 0 0 1px var(--chakra-colors-primary)` }}>
            <Wrap spacing={2} align="center">
                {tags.map((tag) => (
                    <WrapItem key={tag}>
                        <Tag size="md" borderRadius="full" variant="subtle" bg={tagBg} color={tagColor}>
                            <TagLabel>{tag}</TagLabel>
                            <TagCloseButton onClick={(e) => {
                                e.stopPropagation(); // Предотвращаем фокус на Input при клике
                                removeTag(tag)
                            }} />
                        </Tag>
                    </WrapItem>
                ))}
                <WrapItem flexGrow={1}>
                    <Input
                        id={id}
                        variant="unstyled" // Убираем стандартные стили Input
                        value={inputValue}
                        onChange={handleInputChange}
                        onKeyDown={handleInputKeyDown}
                        placeholder={placeholder}
                        size="sm"
                        {...rest}
                        // Убираем явные стили, чтобы наследовались от Box
                        // borderColor="transparent"
                        // boxShadow="none"
                        // _focus={{ boxShadow: "none" }}
                        // minWidth="100px" // Минимальная ширина для поля ввода
                    />
                </WrapItem>
            </Wrap>
        </Box>
    );
};

export default TagInput; 