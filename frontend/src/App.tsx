// src/App.tsx
import React from 'react';
import { Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { Layout, Menu, Typography, theme as antdTheme, Breadcrumb, Button, Avatar, Dropdown, Spin, Space } from 'antd';
import {
  HistoryOutlined,
  QuestionCircleOutlined,
  HomeOutlined,
  ExperimentOutlined, // Для OCR
  ApiOutlined, // Для HealthCheck
  LoginOutlined, // Иконка для входа
  LogoutOutlined, // Иконка для выхода
  UserOutlined // Иконка для пользователя
} from '@ant-design/icons';

import HomePage from './pages/HomePage'; // Будет форма создания дела
import CaseHistoryPage from './pages/CaseHistoryPage';
import OcrTasksPage from './pages/OcrTasksPage'; // Для статистики OCR
import SystemHealthPage from './pages/SystemHealthPage';
import ConfigAndGuidesPage from './pages/ConfigAndGuidesPage'; // Для справочников
import CaseDetailPage from './pages/CaseDetailPage'; // Для просмотра деталей дела
import NotFoundPage from './pages/NotFoundPage';
import LoginPage from './pages/LoginPage'; // Страница входа
import ProtectedRoute from './components/ProtectedRoute'; // Защищенный маршрут
import { AuthProvider, useAuth } from './contexts/AuthContext'; // Провайдер и хук аутентификации

const { Header, Content, Footer } = Layout;
const { Text } = Typography;

const AppContent: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { token: { colorBgContainer, borderRadiusLG } } = antdTheme.useToken();
  const { isAuthenticated, user, logout, isLoading } = useAuth();

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: <Link to="/">Новое дело</Link>,
    },
    {
      key: '/history',
      icon: <HistoryOutlined />,
      label: <Link to="/history">История дел</Link>,
    },
    {
      key: '/ocr-tasks',
      icon: <ExperimentOutlined />,
      label: <Link to="/ocr-tasks">Статистика OCR</Link>,
    },
    {
      key: '/guides',
      icon: <QuestionCircleOutlined />,
      label: <Link to="/guides">Справочники</Link>,
    },
    {
      key: '/health',
      icon: <ApiOutlined />,
      label: <Link to="/health">Состояние системы</Link>,
    },
  ];

  const handleLogout = () => {
    logout();
    navigate('/login'); // Перенаправление на страницу входа после выхода
  };

  const userMenuItems = [
    {
        key: 'username',
        label: <Text strong>Пользователь: {user?.username || ''} ({user?.role || ''})</Text>,
        disabled: true,
        icon: <UserOutlined />
    },
    {
        type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выйти',
      onClick: handleLogout,
    },
  ];

  // Хлебные крошки
  const breadcrumbNameMap: Record<string, string> = {
    '/': 'Новое дело',
    '/history': 'История дел',
    '/history/:caseId': 'Детали дела',
    '/ocr-tasks': 'Статистика OCR задач',
    '/guides': 'Справочники и конфигурация',
    '/health': 'Состояние системы',
    '/login': 'Вход в систему'
  };

  const pathSnippets = location.pathname.split('/').filter(i => i);
  const extraBreadcrumbItems = pathSnippets.map((_, index) => {
    const url = `/${pathSnippets.slice(0, index + 1).join('/')}`;
    // Если это динамический параметр (например, caseId), отобразим его как есть
    // или можно будет получать название дела по ID
    let name = breadcrumbNameMap[url];
    if (!name && url.startsWith('/history/')) {
        name = `Дело #${pathSnippets[index]}`; // Просто отображаем ID
    }

    return (
      <Breadcrumb.Item key={url}>
        {index === pathSnippets.length -1 || !name ? ( // Последний элемент или нет имени в карте - не ссылка
          <span>{name || pathSnippets[index]}</span>
        ) : (
          <Link to={url}>{name}</Link>
        )}
      </Breadcrumb.Item>
    );
  });

  const breadcrumbItems = [
    <Breadcrumb.Item key="home">
      <Link to="/"><HomeOutlined /></Link>
    </Breadcrumb.Item>,
  ].concat(extraBreadcrumbItems);

  // Определение выбранного ключа меню на основе текущего пути
  // Это более надежный способ, чем просто location.pathname, особенно для вложенных роутов
  let selectedMenuKey = location.pathname;
  if (location.pathname.startsWith('/history/')) {
    selectedMenuKey = '/history'; // Для всех страниц деталей дела подсвечиваем "История дел"
  }
  // Если путь /history/:caseId, то selectedMenuKey должен быть '/history'
  // Дополнительно проверим, чтобы для главной страницы '/' тоже корректно подсвечивалось
  const pathSegments = location.pathname.split('/').filter(Boolean);
  if (pathSegments.length > 1 && menuItems.some(item => item.key === `/${pathSegments[0]}`)) {
    selectedMenuKey = `/${pathSegments[0]}`;
  } else if (pathSegments.length === 0 && location.pathname === '/') {
    selectedMenuKey = '/';
  } else if (location.pathname === '/login') {
      selectedMenuKey = ''; // Не подсвечивать ничего в меню для страницы логина
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', padding: '0 24px', background: colorBgContainer, justifyContent: 'space-between' }}>
        <Space>
            <div style={{ height: 32, /*width: 120,*/ marginRight: 24, background: 'rgba(0, 0, 0, 0.1)', textAlign: 'center', lineHeight: '32px', color: '#1677ff', borderRadius: '4px', padding: '0 10px', fontWeight: 'bold' }}>
                PFR-AI
            </div>
            {isAuthenticated && (
                 <Menu
                    theme="light"
                    mode="horizontal"
                    selectedKeys={[selectedMenuKey]}
                    items={menuItems}
                    style={{ flex: 1, minWidth: 0, borderBottom: 'none' }}
                    overflowedIndicator={<UserOutlined />} // Для маленьких экранов
                />
            )}
        </Space>
        
        <Space>
            {isLoading ? (
                <Spin size="small" />
            ) : isAuthenticated && user ? (
                <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                    <Button type="text" style={{height: 'auto'}}>
                        <Space>
                             <Avatar icon={<UserOutlined />} size="small" style={{backgroundColor: '#1890ff'}}/>
                             <Text style={{color: 'rgba(0, 0, 0, 0.85)'}}>{user.username}</Text>
                        </Space>
                    </Button>
                </Dropdown>
            ) : (
                location.pathname !== '/login' && (
                    <Button icon={<LoginOutlined />} onClick={() => navigate('/login')}>
                        Войти
                    </Button>
                )
            )}
        </Space>
      </Header>
      <Content style={{ margin: '0 16px' }}>
        { location.pathname !== '/login' && isAuthenticated && (
            <Breadcrumb style={{ margin: '16px 0' }}>
                {breadcrumbItems}
            </Breadcrumb>
        )}
        <div
          style={{
            padding: location.pathname === '/login' ? 0 : 24, // Убираем паддинг для LoginPage
            minHeight: 360,
            background: location.pathname === '/login' ? 'transparent' : colorBgContainer, // Прозрачный фон для LoginPage
            borderRadius: location.pathname === '/login' ? 0 : borderRadiusLG,
          }}
        >
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
            <Route path="/history" element={<ProtectedRoute><CaseHistoryPage /></ProtectedRoute>} />
            <Route path="/history/:caseId" element={<ProtectedRoute><CaseDetailPage /></ProtectedRoute>} />
            <Route path="/ocr-tasks" element={<ProtectedRoute><OcrTasksPage /></ProtectedRoute>} />
            <Route path="/guides" element={<ProtectedRoute><ConfigAndGuidesPage /></ProtectedRoute>} />
            <Route path="/health" element={<ProtectedRoute><SystemHealthPage /></ProtectedRoute>} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </div>
      </Content>
      <Footer style={{ textAlign: 'center' }}>
        Пенсионный Консультант AI ©{new Date().getFullYear()}
      </Footer>
    </Layout>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;