import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Spin } from 'antd';

interface ProtectedRouteProps {
  children: JSX.Element;
  // Можно добавить проп для проверки ролей, если потребуется
  // allowedRoles?: string[]; 
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    // Пока проверяется токен, показываем спиннер или заглушку
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" tip="Проверка аутентификации..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    // Пользователь не аутентифицирован, перенаправляем на страницу входа
    // Сохраняем текущий путь, чтобы перенаправить обратно после входа
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Если нужны роли:
  // if (allowedRoles && user && !allowedRoles.includes(user.role)) {
  //   // Пользователь аутентифицирован, но не имеет нужной роли
  //   return <Navigate to="/unauthorized" replace />; // или на другую страницу
  // }

  return children; // Пользователь аутентифицирован, отображаем запрошенный компонент
};

export default ProtectedRoute; 