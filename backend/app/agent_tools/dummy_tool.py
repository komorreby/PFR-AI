# backend/app/agent_tools/dummy_tool.py
from qwen_agent.tools.base import BaseTool, register_tool
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

@register_tool('dummy_tool_for_testing')
class DummyTool(BaseTool):
    name: str = "dummy_tool_for_testing"
    description: str = (
        "Это простой заглушечный инструмент. Используй его, если пользователь просит выполнить тестовое действие."
    )
    parameters: List[Dict[str, Any]] = [{
        'name': 'test_param',
        'type': 'string',
        'description': 'Любой тестовый строковый параметр.',
        'required': True
    }]

    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg=cfg)
        logger.info(f"Инструмент {self.name} инициализирован.")

    def call(self, params: str, **kwargs) -> str:
        logger.info(f"Инструмент {self.name} ВЫЗВАН с параметрами: {params} и kwargs: {kwargs}")
        return "DummyTool успешно вызван и вернул этот тестовый результат." 