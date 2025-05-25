import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Form, Input, Button, Typography, Card, Alert, Spin } from 'antd';
import { UserOutlined, LockOutlined, LoginOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const LoginPage: React.FC = () => {
  const [form] = Form.useForm();
  const { login, isLoading, authError } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [currentError, setCurrentError] = useState<string | null>(null);

  const from = location.state?.from?.pathname || "/";

  const onFinish = async (values: any) => {
    setCurrentError(null); // Сброс предыдущей ошибки перед новой попыткой
    try {
      await login(values.username, values.password);
      // При успешном логине AuthContext обновит isAuthenticated,
      // и ProtectedRoute должен автоматически перенаправить.
      // Если ProtectedRoute нет или нужно явное перенаправление:
      navigate(from, { replace: true });
    } catch (error: any) {
        // Ошибка уже обработана в AuthContext и установлена в authError
        // Если нужно показать ошибку именно здесь, можно использовать setCurrentError
        // или напрямую authError, если он не сбрасывается слишком быстро.
        // В данном случае, authError из useAuth() должен быть актуален.
        // Для примера, можно также установить локальную ошибку, если нужно специфичное поведение.
        // setCurrentError(error.message || "Произошла ошибка при входе.");
    }
  };

  // Следим за authError из контекста, чтобы отобразить его
  useEffect(() => {
    if (authError) {
        setCurrentError(authError);
    }
  }, [authError]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 'calc(100vh - 140px)', padding: '20px' }}>
      <Card style={{ width: 400, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} title={<Title level={3} style={{ textAlign: 'center', marginBottom: 0 }}><LoginOutlined /> Вход в систему</Title>}>
        <Spin spinning={isLoading} tip="Аутентификация...">
            <Form
              form={form}
              name="login-form"
              onFinish={onFinish}
              size="large"
              layout="vertical"
            >
              <Form.Item
                name="username"
                label="Имя пользователя"
                rules={[{ required: true, message: 'Пожалуйста, введите имя пользователя!' }]}
              >
                <Input prefix={<UserOutlined />} placeholder="Логин" />
              </Form.Item>

              <Form.Item
                name="password"
                label="Пароль"
                rules={[{ required: true, message: 'Пожалуйста, введите пароль!' }]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="Пароль" />
              </Form.Item>

              {currentError && (
                <Form.Item>
                  <Alert message={currentError} type="error" showIcon />
                </Form.Item>
              )}

              <Form.Item>
                <Button type="primary" htmlType="submit" block loading={isLoading} icon={<LoginOutlined />}>
                  Войти
                </Button>
              </Form.Item>
            </Form>
        </Spin>
        <Text type="secondary" style={{ textAlign: 'center', display: 'block', marginTop: 16 }}>
            Учетные данные по умолчанию: admin/adminPas или manager/managerPas
        </Text>
      </Card>
    </div>
  );
};

export default LoginPage; 