# create_initial_users.py
import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection
from sqlalchemy import select # Добавим импорт select

# Добавляем путь к app, чтобы импортировать модули
# Предполагаем, что скрипт находится в корне проекта, а backend - это папка PFR-AI/backend
APP_DIR = os.path.join(os.path.dirname(__file__), 'backend', 'app')
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend')) # Добавляем backend в sys.path

from app.database import DATABASE_URL, users_table, metadata # Убрали create_db_and_tables, будем вызывать синхронно
from app.crud import create_db_user
from app.models import UserCreate
# from app.auth import get_password_hash # Не используется напрямую, но хорошо, что есть в crud

# Определяем асинхронный движок здесь локально
# DATABASE_URL уже содержит имя файла, так что DATABASE_FILE_PATH не нужен здесь явно
# DATABASE_URL будет вида f"sqlite+aiosqlite:///C:/Users/alex/Desktop/PFR-AI/backend/cases.db"
async_engine_local = create_async_engine(DATABASE_URL)

async def main():
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "adminPas")
    manager_username = os.getenv("MANAGER_USERNAME", "manager")
    manager_password = os.getenv("MANAGER_PASSWORD", "managerPas")

    admin_user_data = UserCreate(username=admin_username, password=admin_password, role="admin", is_active=True)
    manager_user_data = UserCreate(username=manager_username, password=manager_password, role="manager", is_active=True)

    async with async_engine_local.connect() as conn:
        async with conn.begin(): # Начинаем транзакцию
            # Проверяем, существует ли админ
            existing_admin_result = await conn.execute(
                select(users_table).where(users_table.c.username == admin_user_data.username)
            )
            if existing_admin_result.fetchone() is None:
                try:
                    created_admin = await create_db_user(conn, admin_user_data)
                    print(f"Admin user '{created_admin['username']}' created with ID {created_admin['id']}.")
                except Exception as e_create_admin:
                    print(f"Error creating admin user '{admin_user_data.username}': {e_create_admin}")
            else:
                print(f"Admin user '{admin_user_data.username}' already exists.")

            # Проверяем, существует ли менеджер
            existing_manager_result = await conn.execute(
                select(users_table).where(users_table.c.username == manager_user_data.username)
            )
            if existing_manager_result.fetchone() is None:
                try:
                    created_manager = await create_db_user(conn, manager_user_data)
                    print(f"Manager user '{created_manager['username']}' created with ID {created_manager['id']}.")
                except Exception as e_create_manager:
                    print(f"Error creating manager user '{manager_user_data.username}': {e_create_manager}")
            else:
                print(f"Manager user '{manager_user_data.username}' already exists.")
        
        # Коммит произойдет автоматически при выходе из `async with conn.begin():`

    await async_engine_local.dispose()

if __name__ == "__main__":
    from sqlalchemy import create_engine as create_sync_engine
    # SYNC_DATABASE_URL должен указывать на тот же файл БД
    # DATABASE_URL = f"sqlite+aiosqlite:///C:/path/to/your/project/backend/cases.db"
    # SYNC_DATABASE_URL = f"sqlite:///C:/path/to/your/project/backend/cases.db"
    
    # Получаем путь к файлу БД из DATABASE_URL
    # Пример: "sqlite+aiosqlite:///C:/.../backend/cases.db" -> "C:/.../backend/cases.db"
    db_file_path_from_url = DATABASE_URL.split("///", 1)[1] if "///" in DATABASE_URL else None
    if not db_file_path_from_url:
        print(f"Could not determine DB file path from DATABASE_URL: {DATABASE_URL}")
        sys.exit(1)
        
    sync_db_url_for_script = f"sqlite:///{db_file_path_from_url}"

    db_dir = os.path.dirname(db_file_path_from_url)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    try:
        sync_engine = create_sync_engine(sync_db_url_for_script)
        metadata.create_all(bind=sync_engine)
        print(f"Tables checked/created successfully using DB path: {db_file_path_from_url}")
    except Exception as e_sync_create:
        print(f"Error creating tables in script: {e_sync_create}")
    finally:
        if 'sync_engine' in locals() and sync_engine:
            sync_engine.dispose()

    asyncio.run(main()) 