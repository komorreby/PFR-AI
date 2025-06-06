# app/auth.py
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

# --- Настройки JWT ---
# В реальном приложении эти значения лучше брать из переменных окружения или конфигурационного файла
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt-should-be-long-and-random") # ЗАМЕНИТЕ НА СЛУЧАЙНЫЙ КЛЮЧ
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")) # Токен живет 30 минут

# --- Контекст для хэширования паролей ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Схема OAuth2 ---
# tokenUrl указывает на эндпоинт, где клиент может получить токен
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token") # Путь относительно корня API

# --- Вспомогательные функции ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет обычный пароль с хэшированным."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Генерирует хэш для пароля."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создает JWT токен доступа."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Зависимость для получения текущего пользователя ---
async def get_current_user_data(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Декодирует токен, извлекает данные пользователя (username, role, user_id).
    Не обращается к БД за пользователем, полагается на данные в токене.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        user_id: Optional[int] = payload.get("user_id")

        if username is None or role is None or user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # ВАЖНО: Для повышения безопасности (проверка is_active, смена роли)
    # рекомендуется после декодирования токена делать запрос к БД за пользователем.
    # В данном примере мы полагаемся на токен для простоты.
    return {"username": username, "role": role, "user_id": user_id}


# --- Зависимости для проверки ролей ---
def require_role(required_roles: Union[str, List[str]]):
    """
    Фабрика зависимостей для проверки роли пользователя.
    - Администратор ('admin') имеет доступ к ресурсам, требующим роль 'admin' или 'manager'.
    - Менеджер ('manager') имеет доступ только к ресурсам, требующим роль 'manager'.
    """
    if isinstance(required_roles, str):
        _required_roles = [required_roles]
    else:
        _required_roles = required_roles

    async def role_checker(current_user_data: Dict[str, Any] = Depends(get_current_user_data)):
        user_role = current_user_data.get("role")

        if user_role == "admin":
            if "admin" in _required_roles or "manager" in _required_roles:
                return current_user_data
        elif user_role == "manager":
            if "manager" in _required_roles:
                return current_user_data

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation not permitted. Required role(s): {', '.join(_required_roles)}, your role: {user_role}",
        )
    return role_checker

# Зависимость для эндпоинтов, доступных только администратору.
# Менеджер сюда доступа не имеет.
require_admin_role = require_role("admin")

# Зависимость для эндпоинтов, доступных менеджеру.
# Администратор также получит доступ благодаря иерархии ролей в `require_role`.
require_manager_role = require_role("manager") 