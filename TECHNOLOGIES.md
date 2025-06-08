# Стек технологий проекта

Этот документ содержит перечень технологий, используемых в проекте.

## Frontend

- **Язык:** TypeScript
- **Фреймворк:** React
- **Сборщик:** Vite
- **UI Библиотека:** Ant Design (antd)
- **Маршрутизация:** React Router
- **Управление формами:** React Hook Form
- **Клиент для API:** Встроенный `fetch` или `axios` (не указан явно, но является стандартом)
- **Управление зависимостями:** npm

## Backend

- **Язык:** Python
- **Фреймворк:** FastAPI
- **Веб-сервер:** Uvicorn
- **ORM:** SQLAlchemy
- **Базы данных:**
    - **Векторная:** neo4j
    - **Реляционная:** SQLite (судя по `aiosqlite`)
- **Асинхронность:** `asyncio`, `aiohttp`

### RAG (Retrieval-Augmented Generation) и AI

- **Оркестрация:** LlamaIndex
- **Модели:**
    - Hugging Face Transformers
    - PyTorch
    - Ollama (для локального запуска моделей)

- **Обработка документов:**
    - `unstructured` для парсинга различных форматов (.pdf, .docx, и т.д.)
    - `pandas` для работы с табличными данными
    - `PyMuPDF`, `pypdf` для работы с PDF

### Аутентификация

- **Хеширование паролей:** `passlib` с `bcrypt`
- **JWT Токены:** `python-jose`

## DevOps и Инструменты

- **Система контроля версий:** Git
- **Менеджеры пакетов:**
    - `pip` (Python)
    - `npm` (Node.js) 