from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class DocumentDetail(BaseModel):
    """Модель для описания требуемых документов."""
    id: str
    name: str
    description: str
    is_critical: bool
    condition_text: Optional[str] = None
    ocr_type: Optional[str] = None


class PensionTypeDocuments(BaseModel):
    """Модель для списка документов, требуемых для определенного типа пенсии."""
    documents: List[DocumentDetail]


class PensionTypeInfo(BaseModel):
    """Модель для информации о типе пенсии."""
    id: str
    display_name: str
    description: str


class PensionTypesConfig(BaseModel):
    """Модель для списка всех типов пенсий."""
    pension_types: List[PensionTypeInfo]
    

class DocumentRequirementsConfig(BaseModel):
    """Модель для требований к документам по всем типам пенсий."""
    requirements: Dict[str, PensionTypeDocuments]
    
    
def load_pension_types_config(data: List[Dict[str, Any]]) -> List[PensionTypeInfo]:
    """
    Загружает и валидирует конфигурацию типов пенсий.
    
    Args:
        data: Данные из JSON-файла pension_types.json
        
    Returns:
        Список валидированных объектов PensionTypeInfo
    """
    return [PensionTypeInfo(**item) for item in data]


def load_document_requirements_config(data: Dict[str, Dict[str, Any]]) -> Dict[str, PensionTypeDocuments]:
    """
    Загружает и валидирует конфигурацию требований к документам.
    
    Args:
        data: Данные из JSON-файла document_requirements.json
        
    Returns:
        Словарь с требованиями к документам для каждого типа пенсии
    """
    return {pension_type_id: PensionTypeDocuments(**reqs) for pension_type_id, reqs in data.items()} 