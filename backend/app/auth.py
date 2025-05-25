# app/auth.py
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel # Добавим импорт BaseModel

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

# --- Модели для данных пользователя (можно вынести в models.py, если нужно) ---
class TokenData(BaseModel): # Используем Pydantic из fastapi, если он там уже есть, или импортируем
    username: Optional[str] = None
    role: Optional[str] = None

class UserAuth(BaseModel): # Для представления пользователя в системе аутентификации
    username: str
    role: str
    is_active: bool = True # По умолчанию активен
    # Можно добавить другие поля, если они нужны из БД для аутентификации/авторизации

# --- Зависимость для получения текущего пользователя ---
# Эта функция будет вызываться для каждого защищенного эндпоинта
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

        if username is None or role is None or user_id is None: # Проверяем user_id
            raise credentials_exception
        # Можно валидировать TokenData здесь, если есть Pydantic модель
        # token_data = TokenData(username=username, role=role) # TokenData не включает user_id в вашем примере
    except JWTError:
        raise credentials_exception
    
    # ВАЖНО: Для повышения безопасности и актуальности данных (например, is_active, смена роли)
    # рекомендуется после декодирования токена все же делать запрос к БД за пользователем.
    # Но для простоты и скорости (особенно если роли меняются редко), можно полагаться на токен.
    # Сейчас мы будем полагаться на токен, но сделаем пометку, что это можно улучшить.
    
    # Возвращаем словарь с данными пользователя из токена
    return {"username": username, "role": role, "user_id": user_id}


# --- Зависимости для проверки ролей ---
def require_role(required_roles: Union[str, List[str]]): # Указываем List[str] для единообразия
    """
    Фабрика зависимостей для проверки роли пользователя.
    Администратор имеет доступ ко всему, к чему имеет доступ менеджер (если 'manager' включен в required_roles для админа).
    """
    if isinstance(required_roles, str):
        current_required_roles = [required_roles]
    else:
        current_required_roles = required_roles

    async def role_checker(current_user_data: Dict[str, Any] = Depends(get_current_user_data)):
        user_role = current_user_data.get("role")
        
        # Если роль пользователя - админ, он имеет доступ ко всему, что требует роли "admin"
        # А также ко всему, что требует роли "manager", если "manager" есть в current_required_roles
        # или если мы решим, что админ имеет доступ ко всему, что ниже его по иерархии.
        # В вашем примере: "Администратор имеет доступ ко всему, к чему имеет доступ менеджер."
        # Это значит, что если `current_required_roles` содержит "manager", и user_role == "admin", доступ разрешен.
        
        if user_role == "admin": # Админ имеет доступ ко всему, что доступно ему или менеджеру
             # Если требуется "admin", админ подходит.
             # Если требуется "manager", админ тоже подходит, так как он выше по иерархии.
            if "admin" in current_required_roles or "manager" in current_required_roles:
                 return current_user_data
        
        if user_role not in current_required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role(s): {', '.join(current_required_roles)}, your role: {user_role}",
            )
        return current_user_data
    return role_checker

# Примеры использования фабрики для конкретных ролей:
require_admin_role = require_role("admin")
# Для менеджера, мы хотим, чтобы и менеджер, и админ имели доступ
require_manager_role = require_role(["manager", "admin"])

# Если бы мы хотели, чтобы только менеджер (не админ) имел доступ:
# require_strict_manager_role = require_role("manager") 
# Но, исходя из "Администратор имеет доступ ко всему, к чему имеет доступ менеджер",
# require_manager_role должен включать админа.
# Либо, как в вашем примере, проверка на admin делается первой:

# Пересмотренная логика require_role для соответствия примеру:
# "Администратор имеет доступ ко всему, к чему имеет доступ менеджер."

def require_role_v2(required_roles_list: Union[str, List[str]]):
    if isinstance(required_roles_list, str):
        _required_roles = [required_roles_list]
    else:
        _required_roles = required_roles_list

    async def role_checker_v2(current_user_data: Dict[str, Any] = Depends(get_current_user_data)):
        user_role = current_user_data.get("role")

        if user_role == "admin": # Админ имеет доступ ко всему, что доступно админу или менеджеру
            if "admin" in _required_roles or "manager" in _required_roles:
                return current_user_data
        
        if user_role == "manager": # Менеджер имеет доступ только к тому, что доступно менеджеру
            if "manager" in _required_roles:
                return current_user_data
        
        # Если роль не админ и не менеджер, или если роль не соответствует требуемой
        # (например, менеджер пытается получить доступ к ресурсу только для админа)
        if user_role not in _required_roles:
             # Дополнительная проверка, если user_role == "manager", а требуется "admin"
            if user_role == "manager" and "admin" in _required_roles and "manager" not in _required_roles :
                pass # он уже должен был быть отфильтрован user_role not in _required_roles
            
            # Проверка на то, что админ может получить доступ к ресурсам менеджера, уже встроена выше.
            # Эта HTTPException сработает, если роль пользователя не дает ему доступ.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role(s): {', '.join(_required_roles)}, your role: {user_role}",
            )
        return current_user_data # Если дошли сюда, значит роль подходит
    return role_checker_v2


# Используем финальную версию require_role из вашего примера:
def require_role_final(required_roles_param: Union[str, List[str]]):
    if isinstance(required_roles_param, str):
        _required_roles_final = [required_roles_param]
    else:
        _required_roles_final = required_roles_param

    async def role_checker_final(current_user_data: Dict[str, Any] = Depends(get_current_user_data)):
        user_role = current_user_data.get("role")
        
        if user_role == "admin": # Админ имеет доступ ко всему
            return current_user_data
        
        # Если пользователь не админ, проверяем, есть ли его роль в списке требуемых
        if user_role not in _required_roles_final:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role(s): {', '.join(_required_roles_final)}, your role: {user_role}",
            )
        return current_user_data
    return role_checker_final
    
require_admin_role = require_role_final("admin")
require_manager_role = require_role_final(["manager", "admin"]) # Менеджер или админ

# Вариант, где менеджер - это только менеджер, а админ - это админ И менеджер
# require_manager_only_role = require_role_final("manager")
# require_admin_or_manager_role = require_role_final(["admin", "manager"])

# Чтобы точно следовать: "Администратор имеет доступ ко всему, к чему имеет доступ менеджер."
# Это означает, что если эндпоинт требует роль 'manager', то 'admin' тоже должен иметь доступ.
# Зависимость `require_manager_role` должна пропускать и 'manager', и 'admin'.
# Зависимость `require_admin_role` должна пропускать только 'admin'.

# Переопределяем для ясности и соответствия вашему описанию:
async def get_current_active_user_with_role(current_user_data: Dict[str, Any] = Depends(get_current_user_data)):
    # Здесь можно было бы добавить проверку user_in_db.is_active, если бы мы ходили в БД
    # Но так как мы полагаемся на токен, is_active из токена не используется напрямую,
    # а get_current_user_data просто возвращает данные.
    # Для примера предположим, что если токен валиден, пользователь активен.
    # Более строгая проверка is_active должна быть при логине и, возможно, при каждом запросе к БД.
    return current_user_data # Возвращаем просто данные из токена


def check_roles(required_roles: List[str]):
    async def role_dependency(user: Dict[str, Any] = Depends(get_current_active_user_with_role)):
        user_role = user.get("role")
        # Админ имеет доступ ко всему, что требует роль "manager" или "admin"
        if user_role == "admin":
            if "admin" in required_roles or "manager" in required_roles:
                return user
        # Менеджер имеет доступ только к тому, что требует роль "manager"
        elif user_role == "manager":
            if "manager" in required_roles:
                return user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Not enough permissions. Required: {', '.join(required_roles)}, yours: {user_role}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return role_dependency

require_admin = check_roles(["admin"])
require_manager = check_roles(["manager", "admin"]) # Админ тоже может делать то, что может менеджер


# Финальный вариант из вашего текста, он самый простой и правильный:
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]: # Переименовал для соответствия
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
        
        # Здесь можно добавить проверку, активен ли пользователь, если бы is_active было в токене
        # Например, is_active_from_token: bool = payload.get("is_active", False)
        # if not is_active_from_token:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user based on token")

    except JWTError:
        raise credentials_exception
    
    return {"username": username, "role": role, "user_id": user_id, "is_active": True} # Добавляем is_active=True по умолчанию из токена

async def require_role_dependency_factory(required_roles_list: Union[str, List[str]]):
    """
    Фабрика зависимостей для проверки роли пользователя.
    Администратор имеет доступ ко всему, к чему имеет доступ менеджер.
    """
    if isinstance(required_roles_list, str):
        _required_roles = [required_roles_list]
    else:
        _required_roles = required_roles_list

    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_role = current_user.get("role")
        
        if not current_user.get("is_active"): # Проверка на активность, если бы она была в токене
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

        if user_role == "admin": # Админ имеет доступ ко всему, что перечислено или если он сам требуется
            if "admin" in _required_roles or "manager" in _required_roles: # Админ может делать все, что может менеджер
                return current_user
        
        if user_role not in _required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role(s): {', '.join(_required_roles)}, your role: {user_role}",
            )
        return current_user
    return role_checker

# Примеры использования фабрики для конкретных ролей:
require_admin_role = require_role_dependency_factory("admin")
require_manager_role = require_role_dependency_factory(["manager", "admin"]) # Менеджер ИЛИ Админ


# Используем версию из вашего предоставленного кода - она самая чистая
# --- Зависимость для получения текущего пользователя ---
# Эта функция будет вызываться для каждого защищенного эндпоинта
# async def get_current_user_data(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]: ... уже определена выше, переиспользуем ее

# --- Зависимости для проверки ролей ---
# (Используем require_role_final из вашего кода, переименовав ее в require_role для краткости)
def require_role(required_roles_param: Union[str, List[str]]):
    if isinstance(required_roles_param, str):
        _required_roles = [required_roles_param]
    else:
        _required_roles = required_roles_param

    async def role_checker(current_user_data_from_token: Dict[str, Any] = Depends(get_current_user_data)): # Зависит от get_current_user_data
        user_role = current_user_data_from_token.get("role")
        
        # Важно: проверка is_active должна быть здесь, если бы мы получали пользователя из БД.
        # Так как get_current_user_data не ходит в БД, токен может быть от деактивированного юзера.
        # В auth.py при логине (login_for_access_token) есть проверка user_in_db.is_active.
        # Если пользователь деактивирован ПОСЛЕ выдачи токена, токен будет валиден.

        if user_role == "admin": # Админ имеет доступ ко всему (к тому, что разрешено ему И менеджеру)
            # Если "admin" есть в _required_roles, он проходит.
            # Если "manager" есть в _required_roles, он тоже проходит.
            if "admin" in _required_roles or "manager" in _required_roles:
                 return current_user_data_from_token
            # Если в _required_roles что-то другое, и это не admin/manager, то админ не должен иметь доступ,
            # но текущая логика "Админ имеет доступ ко всему" это перекрывает.
            # Для строгости, если админ должен иметь доступ ТОЛЬКО к admin и manager ресурсам:
            # if "admin" in _required_roles or ("manager" in _required_roles and user_role == "admin"):
            #    return current_user_data_from_token
            # Но ваш текст "Администратор имеет доступ ко всему, к чему имеет доступ менеджер."
            # означает, что если эндпоинт требует "manager", то админ его получит.
            # А если эндпоинт требует "admin", то админ его получит.
            # Если эндпоинт требует ["viewer"], то админ его НЕ получит по этой логике,
            # но ваш пример говорит "Админ имеет доступ ко всему".
            # Для простоты и следования вашему коду, где "if user_role == "admin": return current_user_data"
            return current_user_data_from_token # Админ имеет доступ ко всему, что требует его роль или роль менеджера
        
        if user_role not in _required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role(s): {', '.join(_required_roles)}, your role: {user_role}",
            )
        return current_user_data_from_token
    return role_checker

# Примеры использования фабрики для конкретных ролей:
require_admin_role = require_role("admin") # Доступ только для админа (и для админа, если менеджерские ресурсы требуют админа)
require_manager_role = require_role(["manager", "admin"]) # Доступ для менеджера или админа. Это соответствует "Админ имеет доступ ко всему, к чему имеет доступ менеджер" 