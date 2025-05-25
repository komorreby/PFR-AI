import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import logging
from .config_models.config_models import (
    PensionTypeInfo, 
    PensionTypeDocuments,
    load_pension_types_config,
    load_document_requirements_config
)


logger = logging.getLogger(__name__)

# Определение путей к конфигурационным файлам
APP_DIR = Path(__file__).resolve().parent
CONFIG_DATA_DIR = APP_DIR.parent / "config_data"
PENSION_TYPES_FILE = CONFIG_DATA_DIR / "pension_types.json"
DOCUMENT_REQUIREMENTS_FILE = CONFIG_DATA_DIR / "document_requirements.json"

# Для отладки: добавляем глобальную переменную, чтобы избежать повторной загрузки
_config_cache = None

def load_configuration() -> tuple[List[PensionTypeInfo], Dict[str, PensionTypeDocuments]]:
    """
    Загружает конфигурации типов пенсий и требований к документам из JSON-файлов.
    
    Returns:
        Кортеж из (список типов пенсий, словарь требований к документам)
    
    Raises:
        FileNotFoundError: Если файлы конфигурации не найдены
        json.JSONDecodeError: Если файлы содержат некорректный JSON
        ValueError: Если данные в файлах не соответствуют схеме
    """
    global _config_cache
    if _config_cache:
        logger.info("Using cached configuration.")
        return _config_cache

    logger.info(f"Attempting to load configuration files.")
    logger.info(f"APP_DIR: {APP_DIR}")
    logger.info(f"CONFIG_DATA_DIR: {CONFIG_DATA_DIR}")
    logger.info(f"PENSION_TYPES_FILE path: {PENSION_TYPES_FILE.resolve()}")
    logger.info(f"DOCUMENT_REQUIREMENTS_FILE path: {DOCUMENT_REQUIREMENTS_FILE.resolve()}")

    try:
        # Загрузка типов пенсий
        if not PENSION_TYPES_FILE.exists():
            logger.error(f"Файл конфигурации типов пенсий не найден: {PENSION_TYPES_FILE.resolve()}")
            raise FileNotFoundError(f"Файл конфигурации типов пенсий не найден: {PENSION_TYPES_FILE.resolve()}")
            
        with open(PENSION_TYPES_FILE, "r", encoding="utf-8") as f:
            pension_types_content = f.read()
            # logger.debug(f"Содержимое {PENSION_TYPES_FILE.name}:\n{pension_types_content}")
            pension_types_data = json.loads(pension_types_content)
        pension_types = load_pension_types_config(pension_types_data)
        logger.info(f"Successfully loaded and parsed {PENSION_TYPES_FILE.name}")
        
        # Загрузка требований к документам
        if not DOCUMENT_REQUIREMENTS_FILE.exists():
            logger.error(f"Файл конфигурации требований к документам не найден: {DOCUMENT_REQUIREMENTS_FILE.resolve()}")
            raise FileNotFoundError(f"Файл конфигурации требований к документам не найден: {DOCUMENT_REQUIREMENTS_FILE.resolve()}")
            
        with open(DOCUMENT_REQUIREMENTS_FILE, "r", encoding="utf-8") as f:
            doc_requirements_content = f.read()
            # logger.debug(f"Содержимое {DOCUMENT_REQUIREMENTS_FILE.name}:\n{doc_requirements_content}")
            doc_requirements_data = json.loads(doc_requirements_content)
        doc_requirements = load_document_requirements_config(doc_requirements_data)
        logger.info(f"Successfully loaded and parsed {DOCUMENT_REQUIREMENTS_FILE.name}")
        
        # Проверка соответствия типов пенсий и требований к документам
        pension_type_ids = {pt.id for pt in pension_types}
        doc_requirement_ids = set(doc_requirements.keys())
        
        # Проверка на наличие типов пенсий, для которых нет требований к документам
        missing_doc_requirements = pension_type_ids - doc_requirement_ids
        if missing_doc_requirements:
            logger.warning(f"Для следующих типов пенсий не заданы требования к документам: {missing_doc_requirements}")
            
        # Проверка на наличие требований к документам для несуществующих типов пенсий
        unknown_pension_types = doc_requirement_ids - pension_type_ids
        if unknown_pension_types:
            logger.warning(f"Заданы требования к документам для несуществующих типов пенсий: {unknown_pension_types}")
        
        _config_cache = (pension_types, doc_requirements) # Кэшируем результат
        return pension_types, doc_requirements
        
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка в формате JSON файла конфигурации: {e}")
        raise
    except ValueError as e:
        logger.error(f"Ошибка в структуре данных конфигурации: {e}")
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при загрузке конфигурации: {e}")
        raise 

def get_standard_document_names_from_config(
    doc_requirements: Dict[str, PensionTypeDocuments]
) -> List[str]: # Возвращаем список уникальных имен
    """Извлекает уникальные имена документов из конфигурации document_requirements."""
    unique_doc_names: set[str] = set() # Используем set[str] для аннотации типа
    if not doc_requirements:
        return []
    for _, pension_docs in doc_requirements.items():
        for doc_detail in pension_docs.documents:
            if doc_detail.name: # Убедимся, что имя есть
                unique_doc_names.add(doc_detail.name)
    return sorted(list(unique_doc_names)) 