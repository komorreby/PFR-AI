// src/pages/SystemHealthPage.tsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  Typography,
  Card,
  Spin,
  Alert,
  Descriptions,
  Tag,
  Button,
  Row,
  Col,
  Divider,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  SyncOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { getHealthCheck } from '../services/apiClient';
import type { HealthCheckResponse, DependencyStatus, ApiError } from '../types';
import dayjs from 'dayjs'; // Для форматирования даты
import 'dayjs/locale/ru'; // Опционально, для русской локализации dayjs
dayjs.locale('ru'); // Активируем русскую локаль

const { Title, Text } = Typography;

const statusColors: Record<DependencyStatus['status'] | HealthCheckResponse['overall_status'], string> = {
  healthy: 'green',
  ok: 'green',
  unhealthy: 'red',
  error: 'red',
  skipped: 'orange',
};

const statusIcons: Record<DependencyStatus['status'] | HealthCheckResponse['overall_status'], React.ReactNode> = {
  healthy: <CheckCircleOutlined />,
  ok: <CheckCircleOutlined />,
  unhealthy: <CloseCircleOutlined />,
  error: <CloseCircleOutlined />,
  skipped: <WarningOutlined />,
};

const statusText: Record<DependencyStatus['status'] | HealthCheckResponse['overall_status'], string> = {
  healthy: 'В порядке',
  ok: 'В порядке',
  unhealthy: 'Неполадки',
  error: 'Ошибка',
  skipped: 'Пропущено',
};


const SystemHealthPage: React.FC = () => {
  const [healthData, setHealthData] = useState<HealthCheckResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealthStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getHealthCheck();
      setHealthData(data);
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr.message || 'Не удалось загрузить состояние системы.');
      console.error('Error fetching system health:', apiErr);
      setHealthData(null); // Очищаем старые данные при ошибке
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealthStatus();
  }, [fetchHealthStatus]);

  const renderDependency = (dep: DependencyStatus) => (
    <Descriptions.Item
      key={dep.name}
      label={
        <Text strong>
          {dep.name.replace(/_/g, ' ')} {/* Замена _ на пробел для лучшего вида */}
        </Text>
      }
      span={3}
    >
      <Tag
        icon={statusIcons[dep.status]}
        color={statusColors[dep.status]}
        style={{ marginRight: 8, fontSize: '14px', padding: '2px 8px' }}
      >
        {statusText[dep.status]}
      </Tag>
      {dep.message && <Text type="secondary">{dep.message}</Text>}
    </Descriptions.Item>
  );

  if (loading && !healthData) { // Показываем спиннер только при первой загрузке
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" tip="Загрузка состояния системы..." />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <Alert
          message="Ошибка загрузки состояния системы"
          description={error}
          type="error"
          showIcon
          action={
            <Button icon={<SyncOutlined />} onClick={fetchHealthStatus} loading={loading}>
              Повторить
            </Button>
          }
        />
      </Card>
    );
  }

  if (!healthData) {
    return (
      <Card>
        <Alert
            message="Нет данных о состоянии системы"
            description="Не удалось получить информацию. Попробуйте обновить."
            type="warning"
            showIcon
            action={
                 <Button icon={<SyncOutlined />} onClick={fetchHealthStatus} loading={loading}>
                    Обновить
                </Button>
            }
        />
      </Card>
    );
  }

  return (
    <Card>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <ApiOutlined style={{ marginRight: 8, color: statusColors[healthData.overall_status]}} />
            Состояние системы
          </Title>
        </Col>
        <Col>
          <Button icon={<SyncOutlined />} onClick={fetchHealthStatus} loading={loading}>
            Обновить
          </Button>
        </Col>
      </Row>

      <Descriptions bordered column={1} size="middle">
        <Descriptions.Item label={<Text strong>Общий статус</Text>}>
          <Tag
            icon={statusIcons[healthData.overall_status]}
            color={statusColors[healthData.overall_status]}
            style={{ fontSize: '16px', padding: '4px 10px' }}
          >
            {statusText[healthData.overall_status]}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label={<Text strong>Время проверки</Text>}>
          {dayjs(healthData.timestamp).format('DD MMMM YYYY, HH:mm:ss')}
        </Descriptions.Item>
      </Descriptions>

      <Divider orientation="left" style={{ marginTop: 32, marginBottom: 24 }}>
        <Text strong>Статусы зависимостей</Text>
      </Divider>

      {healthData.dependencies && healthData.dependencies.length > 0 ? (
        <Descriptions bordered column={1} size="small">
          {healthData.dependencies.map(renderDependency)}
        </Descriptions>
      ) : (
        <Text type="secondary">Информация о зависимостях отсутствует.</Text>
      )}
    </Card>
  );
};

export default SystemHealthPage;