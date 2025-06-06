import React, { useState, useEffect, useCallback } from 'react';
import { List, Button, Upload, message, Typography, Spin, Popconfirm, Alert, Space } from 'antd';
import { UploadOutlined, DeleteOutlined, FilePdfOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import type { UploadFile, RcFile } from 'antd/es/upload/interface';
import { listRagDocuments, uploadRagDocument, deleteRagDocument } from '../services/apiClient';
import type { DocumentListResponse, DocumentUploadResponse, DocumentDeleteResponse, ApiError } from '../types';
import { useAuth } from '../contexts/AuthContext';

const { Title, Text } = Typography;

const RagDocumentsPage: React.FC = () => {
    const [documents, setDocuments] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [fileList, setFileList] = useState<UploadFile[]>([]);
    const { user } = useAuth();

    const isAdmin = user?.role === 'admin';

    const fetchDocuments = useCallback(async () => {
        if (!isAdmin) {
            setError("У вас нет прав для просмотра этой страницы.");
            setIsLoading(false);
            return;
        }
        setIsLoading(true);
        setError(null);
        try {
            const response: DocumentListResponse = await listRagDocuments();
            setDocuments(response.filenames || []);
        } catch (e) {
            const apiError = e as ApiError;
            setError(apiError.message || 'Не удалось загрузить список документов.');
            message.error(apiError.message || 'Не удалось загрузить список документов.');
        } finally {
            setIsLoading(false);
        }
    }, [isAdmin]);

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    const handleUpload = async (options: any) => {
        const { file, onSuccess, onError } = options;
        if (!isAdmin) {
            message.error("У вас нет прав для загрузки документов.");
            onError(new Error("Нет прав"));
            return;
        }

        setIsUploading(true);
        setError(null);
        try {
            const response: DocumentUploadResponse = await uploadRagDocument(file as RcFile);
            message.success(response.message || `Файл ${response.filename} успешно загружен.`);
            onSuccess(response, file);
            fetchDocuments(); // Refresh the list
        } catch (e) {
            const apiError = e as ApiError;
            setError(apiError.message || `Не удалось загрузить файл ${file.name}.`);
            message.error(apiError.message || `Не удалось загрузить файл ${file.name}.`);
            onError(apiError);
        } finally {
            setIsUploading(false);
            setFileList([]); // Clear file list after attempt
        }
    };

    const handleDelete = async (filename: string) => {
        if (!isAdmin) {
            message.error("У вас нет прав для удаления документов.");
            return;
        }
        setIsLoading(true); // Можно использовать isDeleting, если нужно более гранулированно
        setError(null);
        try {
            const response: DocumentDeleteResponse = await deleteRagDocument(filename);
            message.success(response.message || `Файл ${filename} успешно удален.`);
            fetchDocuments(); // Refresh the list
        } catch (e) {
            const apiError = e as ApiError;
            setError(apiError.message || `Не удалось удалить файл ${filename}.`);
            message.error(apiError.message || `Не удалось удалить файл ${filename}.`);
        } finally {
            setIsLoading(false);
        }
    };

    const uploadProps = {
        fileList,
        customRequest: handleUpload,
        beforeUpload: (file: RcFile) => {
            if (!isAdmin) {
                message.error("У вас нет прав для загрузки документов.");
                return Upload.LIST_IGNORE;
            }
            const isPdf = file.type === 'application/pdf';
            if (!isPdf) {
                message.error('Вы можете загружать только PDF файлы!');
            }
            const isLt10M = file.size / 1024 / 1024 < 10; // Пример ограничения размера, можно настроить
            if (!isLt10M) {
                message.error('Файл должен быть меньше 10MB!');
            }
            if (isPdf && isLt10M) {
                 setFileList([file]); // Заменяем текущий файл в списке
            } else {
                setFileList([]);
            }
            return isPdf && isLt10M ? true : Upload.LIST_IGNORE;
        },
        onRemove: () => {
            setFileList([]);
        },
        maxCount: 1,
    };

    if (!isAdmin && !isLoading) { // Если уже не грузится и точно не админ
        return (
            <Alert
                message="Доступ запрещен"
                description="У вас нет прав администратора для доступа к этой странице."
                type="error"
                showIcon
            />
        );
    }
    
    return (
        <div style={{ padding: '24px' }}>
            <Title level={2} style={{ marginBottom: '24px' }}>Управление RAG Документами</Title>
            <Text type="secondary" style={{display: 'block', marginBottom: '16px'}}>
                На этой странице администраторы могут управлять документами, используемыми для базы знаний системы.
                Загруженные PDF файлы будут обработаны и добавлены в RAG.
            </Text>

            {isAdmin && (
                <div style={{ marginBottom: '24px' }}>
                    <Title level={4}>Загрузить новый документ</Title>
                    <Upload {...uploadProps}>
                        <Button icon={<UploadOutlined />} loading={isUploading} disabled={isUploading}>
                            Выбрать PDF файл для загрузки
                        </Button>
                    </Upload>
                    {isUploading && <Text style={{marginTop: '8px', display: 'block'}}>Загрузка файла...</Text>}
                </div>
            )}

            {error && <Alert message={error} type="error" showIcon style={{ marginBottom: '16px' }} />}

            <Title level={4} style={{ marginTop: '24px' }}>Список загруженных документов</Title>
            {isLoading ? (
                <Spin tip="Загрузка списка документов..." />
            ) : documents.length === 0 && !error && isAdmin ? (
                <Text>Нет загруженных документов.</Text>
            ) : (
                <List
                    bordered
                    dataSource={documents}
                    renderItem={(filename) => (
                        <List.Item
                            actions={isAdmin ? [
                                <Popconfirm
                                    title={`Вы уверены, что хотите удалить файл "${filename}"?`}
                                    onConfirm={() => handleDelete(filename)}
                                    okText="Да, удалить"
                                    cancelText="Отмена"
                                    icon={<QuestionCircleOutlined style={{ color: 'red' }} />}
                                >
                                    <Button type="text" danger icon={<DeleteOutlined />} disabled={isLoading}>
                                        Удалить
                                    </Button>
                                </Popconfirm>
                            ] : []}
                        >
                           <List.Item.Meta
                                avatar={<FilePdfOutlined style={{fontSize: '20px', color: '#1890ff'}}/>}
                                title={<Text>{filename}</Text>}
                           />
                        </List.Item>
                    )}
                />
            )}
        </div>
    );
};

export default RagDocumentsPage; 