// src/pages/NotFoundPage.tsx
import React from 'react';
import { Result, Button } from 'antd';
import { Link } from 'react-router-dom';

const NotFoundPage: React.FC = () => {
  return (
    <Result
      status="404"
      title="404 - Страница не найдена"
      subTitle="Извините, страница, которую вы посетили, не существует."
      extra={<Button type="primary"><Link to="/">Вернуться на главную</Link></Button>}
    />
  );
};

export default NotFoundPage;