// src/pages/CaseHistoryPage.tsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Typography,
  Table,
  Spin,
  Alert,
  Button,
  Input,
  Row,
  Card,
  Col,
  Tag,
  Tooltip,
  Space,
  Modal,
  message as antdMessage, // Для уведомлений о скачивании
  Empty,
} from 'antd';
import {
  HistoryOutlined,
  SyncOutlined,
  SearchOutlined,
  DownloadOutlined,
  EyeOutlined,
  FilePdfOutlined,
  FileWordOutlined,
} from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { getCaseHistory, downloadCaseDocument } from '../services/apiClient';
import type { CaseHistoryEntry, ApiError, PersonalData, DocumentFormat } from '../types';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { Search } = Input;

const ITEMS_PER_PAGE = 10; // Количество элементов на одной странице таблицы

const CaseHistoryPage: React.FC = () => {
  const [historyData, setHistoryData] = useState<CaseHistoryEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalItems, setTotalItems] = useState<number>(0); // Пока не используется, т.к. API не возвращает total

  const fetchHistory = useCallback(async (page: number, currentSearchTerm: string) => {
    setLoading(true);
    setError(null);
    try {
      // API пока не поддерживает серверную пагинацию и поиск по тексту,
      // поэтому загружаем все и фильтруем/пагинируем на клиенте.
      // Если бы API поддерживал, параметры skip/limit и search передавались бы сюда.
      // const skip = (page - 1) * ITEMS_PER_PAGE;
      // const limit = ITEMS_PER_PAGE;
      // В данном API /history имеет skip и limit, но не имеет поиска по тексту.
      // Загрузим больше данных, чтобы было что фильтровать на клиенте, если нужно.
      // Для реального приложения с большим количеством данных нужна серверная фильтрация/пагинация.
      const data = await getCaseHistory(0, 100); // Загружаем первые 100 для примера
      setHistoryData(data);
      // setTotalItems(data.length); // Если бы API не возвращал все, а только страницу
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.message || 'Не удалось загрузить историю дел.');
      console.error('Error fetching case history:', apiErr);
      setHistoryData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory(currentPage, searchTerm);
  }, [fetchHistory, currentPage]); // searchTerm пока не используется в fetchHistory

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    setCurrentPage(1); // Сбрасываем на первую страницу при поиске
    // Перезагрузка данных не нужна, если фильтрация клиентская
  };

  const handleTableChange = (pagination: any) => {
    setCurrentPage(pagination.current);
  };

  const handleDownload = async (caseId: number, format: DocumentFormat) => {
    const key = `download-${caseId}-${format}`;
    antdMessage.loading({ content: `Загрузка ${format.toUpperCase()} для дела #${caseId}...`, key, duration: 0 });

    try {
      const blob = await downloadCaseDocument(caseId, format);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      // Имя файла лучше получать из заголовка Content-Disposition, если бэкенд его отдает
      // Пока используем стандартное имя
      const filename = `case_document_${caseId}.${format}`;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
      antdMessage.success({ content: `Файл ${filename} успешно скачан.`, key, duration: 3 });
    } catch (err) {
      const apiErr = err as ApiError;
      console.error('Download error:', apiErr);
      antdMessage.error({ content: `Ошибка скачивания: ${apiErr.message}`, key, duration: 5 });
    }
  };

  const filteredData = useMemo(() => {
    if (!searchTerm) {
      return historyData;
    }
    const lowerSearchTerm = searchTerm.toLowerCase();
    return historyData.filter(entry => {
      const fio = entry.personal_data ?
        `${entry.personal_data.last_name || ''} ${entry.personal_data.first_name || ''} ${entry.personal_data.middle_name || ''}`.toLowerCase() : '';
      const snils = entry.personal_data?.snils?.replace(/\D/g, '') || '';

      return (
        entry.id.toString().includes(lowerSearchTerm) ||
        fio.includes(lowerSearchTerm) ||
        (snils && snils.includes(lowerSearchTerm.replace(/\D/g, ''))) ||
        entry.pension_type.toLowerCase().includes(lowerSearchTerm) ||
        entry.final_status.toLowerCase().includes(lowerSearchTerm)
      );
    });
  }, [historyData, searchTerm]);


  const columns = [
    {
      title: 'ID Дела',
      dataIndex: 'id',
      key: 'id',
      sorter: (a: CaseHistoryEntry, b: CaseHistoryEntry) => a.id - b.id,
      render: (id: number) => <Link to={`/history/${id}`}>{id}</Link>,
    },
    {
      title: 'Дата создания',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('DD.MM.YYYY HH:mm'),
      sorter: (a: CaseHistoryEntry, b: CaseHistoryEntry) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
    },
    {
      title: 'ФИО Заявителя',
      key: 'fio',
      render: (_: any, record: CaseHistoryEntry) => {
        const pd = record.personal_data;
        if (!pd) return <Text type="secondary">Нет данных</Text>;
        return `${pd.last_name || ''} ${pd.first_name || ''} ${pd.middle_name || ''}`.trim() || <Text type="secondary">Не указано</Text>;
      },
    },
    {
      title: 'СНИЛС',
      key: 'snils',
      render: (_: any, record: CaseHistoryEntry) => record.personal_data?.snils || <Text type="secondary">Нет данных</Text>,
    },
    {
      title: 'Тип пенсии',
      dataIndex: 'pension_type',
      key: 'pension_type',
      // Можно добавить фильтры, если типы пенсий известны и их немного
    },
    {
      title: 'Итоговый статус',
      dataIndex: 'final_status',
      key: 'final_status',
      render: (status: string) => {
        let color = 'default';
        if (status.toLowerCase().includes('соответствует')) color = 'success';
        else if (status.toLowerCase().includes('не соответствует')) color = 'error';
        else if (status.toLowerCase().includes('processing')) color = 'processing';
        else if (status.toLowerCase().includes('failed') || status.toLowerCase().includes('error')) color = 'error';
        return <Tag color={color}>{status}</Tag>;
      },
      // filters: [ ...список статусов... ], onFilter: (value, record) => record.final_status.indexOf(value) === 0,
    },
    {
      title: 'Уверенность RAG',
      dataIndex: 'rag_confidence',
      key: 'rag_confidence',
      render: (confidence: number | null) => confidence !== null ? `${(confidence * 100).toFixed(1)}%` : <Text type="secondary">-</Text>,
      sorter: (a: CaseHistoryEntry, b: CaseHistoryEntry) => (a.rag_confidence || 0) - (b.rag_confidence || 0),
    },
    {
      title: 'Действия',
      key: 'actions',
      align: 'center' as const,
      render: (_: any, record: CaseHistoryEntry) => (
        <Space size="small">
          <Tooltip title="Просмотреть детали дела">
            <Link to={`/history/${record.id}`}>
              <Button icon={<EyeOutlined />} size="small" />
            </Link>
          </Tooltip>
          <Tooltip title="Скачать PDF">
            <Button
              icon={<FilePdfOutlined />}
              size="small"
              onClick={() => handleDownload(record.id, 'pdf')}
              disabled={record.final_status === "PROCESSING"} // Пример: не даем скачать, если в обработке
            />
          </Tooltip>
          <Tooltip title="Скачать DOCX">
            <Button
              icon={<FileWordOutlined />}
              size="small"
              onClick={() => handleDownload(record.id, 'docx')}
              disabled={record.final_status === "PROCESSING"}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  if (loading && historyData.length === 0) { // Спиннер на всю страницу только при первой загрузке
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" tip="Загрузка истории дел..." />
      </div>
    );
  }
  
  return (
    <Card>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <HistoryOutlined style={{ marginRight: 8 }} />
            История обработанных дел
          </Title>
        </Col>
        <Col>
          <Button icon={<SyncOutlined />} onClick={() => fetchHistory(currentPage, searchTerm)} loading={loading}>
            Обновить
          </Button>
        </Col>
      </Row>

      <Search
        placeholder="Поиск по ID, ФИО, СНИЛС, типу пенсии или статусу..."
        allowClear
        enterButton={<Button icon={<SearchOutlined />}>Поиск</Button>}
        size="large"
        onSearch={handleSearch}
        onChange={(e) => { if(!e.target.value) handleSearch('');}} // Очистка поиска при пустом инпуте
        style={{ marginBottom: 24 }}
        loading={loading && searchTerm !== ''} // Показываем загрузку на кнопке поиска если фильтрация серверная
      />

      {error && (
        <Alert
          message="Ошибка загрузки истории дел"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      <Table
        columns={columns}
        dataSource={filteredData}
        rowKey="id"
        loading={loading}
        pagination={{
          current: currentPage,
          pageSize: ITEMS_PER_PAGE,
          total: filteredData.length, // Общее количество элементов после фильтрации для клиентской пагинации
          showSizeChanger: true,
          pageSizeOptions: ['10', '20', '50'],
        }}
        onChange={handleTableChange}
        scroll={{ x: 1200 }} // Горизонтальный скролл для маленьких экранов
        locale={{ emptyText: <Empty description="Дела не найдены или соответствуют фильтру."/> }}
      />
    </Card>
  );
};

export default CaseHistoryPage;