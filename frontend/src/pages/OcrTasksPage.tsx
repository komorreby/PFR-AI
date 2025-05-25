// src/pages/OcrTasksPage.tsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  Typography,
  Card,
  Spin,
  Alert,
  Row,
  Col,
  Statistic,
  Button,
  Divider,
  Tooltip,
  Empty
} from 'antd';
import {
  ExperimentOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  HourglassOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { getOcrTasksStats } from '../services/apiClient';
import type { TasksStatsResponse, ApiError } from '../types';

const { Title, Text } = Typography;

const OcrTasksPage: React.FC = () => {
  const [statsData, setStatsData] = useState<TasksStatsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getOcrTasksStats();
      setStatsData(data);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.message || 'Не удалось загрузить статистику OCR задач.');
      console.error('Error fetching OCR tasks stats:', apiErr);
      setStatsData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  if (loading && !statsData) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" tip="Загрузка статистики OCR задач..." />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <Alert
          message="Ошибка загрузки статистики"
          description={error}
          type="error"
          showIcon
          action={
            <Button icon={<SyncOutlined />} onClick={fetchStats} loading={loading}>
              Повторить
            </Button>
          }
        />
      </Card>
    );
  }

  if (!statsData) {
    return (
      <Card>
        <Empty description="Данные статистики OCR задач отсутствуют или не удалось их загрузить.">
            <Button type="primary" icon={<SyncOutlined />} onClick={fetchStats} loading={loading}>
                Обновить
            </Button>
        </Empty>
      </Card>
    );
  }

  const { total, pending, expired_processing, status_specific_counts } = statsData;

  return (
    <Card>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <ExperimentOutlined style={{ marginRight: 8, color: '#1890ff' }} />
            Статистика OCR Задач
          </Title>
        </Col>
        <Col>
          <Button icon={<SyncOutlined />} onClick={fetchStats} loading={loading}>
            Обновить
          </Button>
        </Col>
      </Row>

      <Row gutter={[16, 24]}>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Card bordered={false} style={{backgroundColor: '#f0f5ff'}}>
            <Statistic
              title="Всего задач в системе"
              value={total}
              prefix={<ExperimentOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
         <Tooltip title="Задачи в статусе PROCESSING, которые еще не просрочены.">
          <Card bordered={false} style={{backgroundColor: '#fffbe6'}}>
            <Statistic
              title="Активные (в обработке)"
              value={pending}
              prefix={<HourglassOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
          </Tooltip>
        </Col>
        <Col xs={24} sm={12} md={8} lg={6}>
          <Tooltip title="Задачи в статусе PROCESSING, у которых истек срок жизни (TTL).">
          <Card bordered={false} style={{backgroundColor: '#fff1f0'}}>
            <Statistic
              title="Просроченные (в обработке)"
              value={expired_processing}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
          </Tooltip>
        </Col>
      </Row>

      <Divider orientation="left" style={{ marginTop: 32, marginBottom: 24 }}>
        <Text strong>Детализация по статусам</Text>
      </Divider>

      <Row gutter={[16, 24]}>
        {status_specific_counts && Object.entries(status_specific_counts).map(([status, count]) => {
          let icon = <ExclamationCircleOutlined />;
          let color = '#d9d9d9'; // Серый по умолчанию
          let cardBg = '#fafafa';
          let title = status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();

          if (status === 'PROCESSING') {
            icon = <HourglassOutlined />;
            color = '#1890ff'; // Синий
            cardBg = '#e6f7ff';
            title = 'В обработке (всего)';
          } else if (status === 'COMPLETED') {
            icon = <CheckCircleOutlined />;
            color = '#52c41a'; // Зеленый
            cardBg = '#f6ffed';
            title = 'Завершено успешно';
          } else if (status === 'FAILED') {
            icon = <CloseCircleOutlined />;
            color = '#f5222d'; // Красный
            cardBg = '#fff1f0';
            title = 'Завершено с ошибкой';
          }

          return (
            <Col xs={24} sm={12} md={8} key={status}>
              <Card bordered={false} style={{backgroundColor: cardBg}}>
                <Statistic
                  title={title}
                  value={count}
                  prefix={icon}
                  valueStyle={{ color: color }}
                />
              </Card>
            </Col>
          );
        })}
        {!status_specific_counts || Object.keys(status_specific_counts).length === 0 && (
            <Col span={24}>
                <Empty description="Данные по статусам отсутствуют." />
            </Col>
        )}
      </Row>
    </Card>
  );
};

export default OcrTasksPage;