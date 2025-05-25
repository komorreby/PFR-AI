import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Text,
    create_engine, # Need sync engine for initial table creation if using Core directly without alembic etc.
    Float, # Добавлено
    Boolean, # Добавлено
    DateTime, # <--- Добавлено
    func, # <--- Добавлено
    JSON, # Добавлено
    ForeignKey # Добавлено
)

# Определяем путь к файлу БД относительно текущего файла (database.py)
DATABASE_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cases.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FILE_PATH}"
SYNC_DATABASE_URL = f"sqlite:///{DATABASE_FILE_PATH}" # For initial table creation

# Асинхронный движок SQLAlchemy
async_engine = create_async_engine(DATABASE_URL, echo=True) # echo=True для логгирования SQL запросов

# Фабрика асинхронных сессий (если будем использовать ORM-подход позже)
# AsyncSessionLocal = sessionmaker(
#     autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession
# )

# --- Используем SQLAlchemy Core для определения таблицы ---
metadata = MetaData()

cases_table = Table(
    "cases",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("personal_data", Text, nullable=False),  # Storing as JSON string
    Column("errors", Text, nullable=False),         # Storing as JSON string
    Column("pension_type", String(100), nullable=True), # <<< Тип пенсии
    Column("disability", Text, nullable=True),          # <<< Данные об инвалидности (JSON)
    Column("work_experience", Text, nullable=True), # Новое поле
    Column("pension_points", Float, nullable=True), # Новое поле
    Column("benefits", Text, nullable=True), # Новое поле
    Column("documents", Text, nullable=True), # Новое поле
    Column("has_incorrect_document", Boolean, nullable=True), # Новое поле
    Column("final_status", String(50), nullable=True),   # Статус рассмотрения дела (approved/rejected)
    Column("final_explanation", Text, nullable=True),    # Итоговое объяснение от RAG + ML
    Column("rag_confidence", Float, nullable=True), # Новое поле
    Column("created_at", DateTime, server_default=func.now(), nullable=False), # <--- Добавлена колонка
    Column("updated_at", DateTime, onupdate=func.now(), nullable=True), # Дата обновления записи
    Column("other_documents_extracted_data", Text, nullable=True) # Будем хранить как JSON строку
)

# Новая таблица для задач OCR
ocr_tasks_table = Table(
    "ocr_tasks",
    metadata,
    Column("id", String(50), primary_key=True), # UUID задачи в виде строки
    Column("document_type", String(20), nullable=False), # Тип документа (passport, snils, work_book, other)
    Column("status", String(20), nullable=False), # Статус задачи (PROCESSING, COMPLETED, FAILED)
    Column("created_at", DateTime(timezone=True), server_default=func.now()), # Дата создания задачи
    Column("updated_at", DateTime(timezone=True), onupdate=func.now(), nullable=True), # Дата обновления задачи
    Column("data", Text, nullable=True), # JSON-строка с результатами OCR
    Column("error", Text, nullable=True), # JSON-строка с информацией об ошибке, если она произошла
    Column("filename", String(255), nullable=True), # Оригинальное имя файла
    Column("expire_at", DateTime(timezone=True), nullable=False) # Время, когда задача должна быть удалена (TTL)
)

# Новая таблица для пользователей
users_table = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("username", String, unique=True, index=True, nullable=False),
    Column("hashed_password", String, nullable=False),
    Column("role", String, nullable=False), # "admin" или "manager"
    Column("is_active", Boolean, default=True, nullable=False),
    Column("created_at", DateTime, server_default=func.now(), nullable=False),
)

# --- Функция для создания таблицы при старте (если не существует) ---
# SQLAlchemy Core не имеет встроенной проверки create_all как ORM.
# Мы можем использовать синхронный движок для однократного создания.
def create_db_and_tables():
    print(f"Database path: {DATABASE_FILE_PATH}")
    db_dir = os.path.dirname(DATABASE_FILE_PATH)
    if db_dir: # Создаем директорию, если она не существует
        os.makedirs(db_dir, exist_ok=True)

    try:
        sync_engine = create_engine(SYNC_DATABASE_URL)
        metadata.create_all(bind=sync_engine)
        print("Table 'cases' checked/created successfully (sync method).")
    except Exception as e:
        print(f"Error creating database tables (sync method): {e}")
    finally:
        if 'sync_engine' in locals() and sync_engine:
            sync_engine.dispose()

# --- Асинхронная функция для получения соединения ---
async def get_db_connection():
    async with async_engine.connect() as connection:
        yield connection