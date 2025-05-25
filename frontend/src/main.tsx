// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU'; // Локализация для Ant Design
import 'antd/dist/reset.css'; // Стили Ant Design (или import 'antd/dist/antd.min.css'; для v4)
// import './index.css'; // Ваши глобальные стили, если нужны

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <ConfigProvider locale={ruRU}> {/* Оборачиваем в ConfigProvider для локализации */}
        <App />
      </ConfigProvider>
    </BrowserRouter>
  </React.StrictMode>
);