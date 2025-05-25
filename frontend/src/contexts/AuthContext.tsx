import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import { User, TokenResponse } from '../types';
import { loginUser as apiLoginUser, getCurrentUser as apiGetCurrentUser, storeToken, getToken, removeToken } from '../services/apiClient';

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  login: (usernameValue: string, passwordValue: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  authError: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(getToken());
  const [isLoading, setIsLoading] = useState<boolean>(true); // Изначально true для проверки токена
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    const verifyToken = async () => {
      const currentToken = getToken();
      if (currentToken) {
        try {
          // Важно: apiClient должен быть настроен на отправку токена из localStorage
          const currentUser = await apiGetCurrentUser(); 
          setUser(currentUser);
          setIsAuthenticated(true);
          setToken(currentToken);
        } catch (error) {
          console.error("Token verification failed:", error);
          removeToken(); // Если токен невалиден, удаляем его
          setIsAuthenticated(false);
          setUser(null);
          setToken(null);
        }
      }
      setIsLoading(false);
    };

    verifyToken();
  }, []);

  const login = async (usernameValue: string, passwordValue: string) => {
    setIsLoading(true);
    setAuthError(null);
    try {
      const tokenResponse: TokenResponse = await apiLoginUser(usernameValue, passwordValue);
      storeToken(tokenResponse.access_token);
      setToken(tokenResponse.access_token);
      // После успешного логина и сохранения токена, получаем данные пользователя
      const currentUserData = await apiGetCurrentUser();
      setUser(currentUserData);
      setIsAuthenticated(true);
    } catch (error: any) {
      console.error("Login failed:", error);
      removeToken();
      setIsAuthenticated(false);
      setUser(null);
      setToken(null);
      setAuthError(error.message || "Ошибка входа. Проверьте логин и пароль.");
      throw error; // Перебрасываем ошибку, чтобы компонент LoginPage мог её обработать
    }
    setIsLoading(false);
  };

  const logout = () => {
    removeToken();
    setUser(null);
    setIsAuthenticated(false);
    setToken(null);
    // Можно добавить перенаправление на страницу входа здесь, если нужно
    // window.location.href = '/login';
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, token, login, logout, isLoading, authError }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}; 