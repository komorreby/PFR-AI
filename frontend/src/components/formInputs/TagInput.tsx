import React, { useState, useEffect, useCallback } from 'react';
import { Input, Tag, Space } from 'antd';
import type { InputProps } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

interface TagInputProps extends Omit<InputProps, 'onChange' | 'value'> {
    id?: string; // id не всегда нужен, если Input не основной элемент для focus
    value?: string; // Значение от RHF (строка, разделенная запятыми)
    fieldOnChange: (value: string) => void; // RHF field.onChange
    placeholder?: string;
    inputRef?: React.Ref<any>; // Для react-hook-form register
}

const TagInput: React.FC<TagInputProps> = ({
    id,
    value,
    fieldOnChange,
    placeholder = "Добавьте тег",
    inputRef, // Получаем ref от RHF
    ...rest
}) => {
    const [tags, setTags] = useState<string[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [inputVisible, setInputVisible] = useState(false);
    const internalInputRef = React.useRef<any>(null); // Внутренний ref для фокуса на Input

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

    const handleInputConfirm = useCallback(() => {
        if (inputValue.trim() !== '') {
            const newTag = inputValue.trim();
            if (!tags.includes(newTag)) {
                const newTags = [...tags, newTag];
                setTags(newTags);
                fieldOnChange(newTags.join(','));
            }
        }
        setInputValue('');
        setInputVisible(false);
    }, [inputValue, tags, fieldOnChange]);

    const removeTag = useCallback((tagToRemove: string) => {
        const newTags = tags.filter(tag => tag !== tagToRemove);
        setTags(newTags);
        fieldOnChange(newTags.join(','));
    }, [tags, fieldOnChange]);

    const showInput = () => {
        setInputVisible(true);
    };

    useEffect(() => {
        if (inputVisible) {
            internalInputRef.current?.focus();
        }
    }, [inputVisible]);

    // Объединяем ref от RHF с внутренним ref
    const mergedRefs = useCallback((node: any) => {
        internalInputRef.current = node;
        if (typeof inputRef === 'function') {
            inputRef(node);
        } else if (inputRef) {
            (inputRef as React.MutableRefObject<any>).current = node;
        }
    }, [inputRef]);

    return (
        <Space wrap size={[0, 8]} style={{ width: '100%', border: '1px solid #d9d9d9', borderRadius: '2px', padding: '4px 7px', cursor: 'text'}} onClick={() => inputVisible ? internalInputRef.current?.focus() : showInput()}>
            {tags.map((tag) => (
                <Tag
                    key={tag}
                    closable
                    onClose={(e) => {
                        e.preventDefault(); // Предотвращаем срабатывание onClick на Space
                        removeTag(tag);
                    }}
                    style={{ marginRight: 3 }}
                >
                    {tag}
                </Tag>
            ))}
            {inputVisible ? (
                <Input
                    ref={mergedRefs} // Используем объединенный ref
                    type="text"
                    size="small"
                    style={{ width: '78px' }} // Можно настроить
                    value={inputValue}
                    onChange={handleInputChange}
                    onBlur={handleInputConfirm}
                    onPressEnter={handleInputConfirm}
                    placeholder={placeholder}
                    id={id} // id привязываем к видимому Input
                    {...rest} // Передаем остальные пропсы от RHF (например, onBlur)
                />
            ) : (
                <Tag onClick={showInput} style={{ background: '#fff', borderStyle: 'dashed', cursor: 'pointer' }}>
                    <PlusOutlined /> {placeholder || 'Новый тег'}
                </Tag>
            )}
        </Space>
    );
};

export default TagInput; 