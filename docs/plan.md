# Детальный План Реализации: Агентский RAG с Qwen3 для Анализа Пенсионных Дел

Этот документ описывает пошаговый план внедрения агентского подхода для анализа пенсионных дел с использованием Qwen3, Qwen-Agent, кастомного RAG-инструмента и графа знаний Neo4j.

1. Разработка Кастомного RAG-Инструмента (PensionKnowledgeRetrieverTool)

Цель: Создать инструмент для Qwen-Agent, инкапсулирующий логику RAG и обогащение из Neo4j.

Место: Создайте новый файл backend/app/agent_tools/pension_knowledge_retriever_tool.py.

Шаги:

Определить класс PensionKnowledgeRetrieverTool:

# backend/app/agent_tools/pension_knowledge_retriever_tool.py
import json5 # Используем json5 для более гибкого парсинга JSON от LLM
from qwen_agent.tools.base import BaseTool, register_tool
from typing import Optional, Dict, Any, List

# Импортируем ваш PensionRAG и QueryBundle (если он где-то определен как тип)
# Предполагается, что PensionRAG можно импортировать так:
from app.rag_core.engine import PensionRAG 
# QueryBundle обычно из llama_index.core, если используется для типизации
from llama_index.core import QueryBundle 
from llama_index.core.schema import NodeWithScore
import logging # <--- Добавить
import traceback # <--- Добавить для детального стека ошибок

logger = logging.getLogger(__name__) # <--- Инициализировать логгер

@register_tool('pension_knowledge_retriever')
class PensionKnowledgeRetrieverTool(BaseTool):
    name: str = "pension_knowledge_retriever"
    description: str = (
        "Извлекает и обобщает релевантные статьи пенсионного законодательства РФ "
        "и связанные с ними условия на основе поискового запроса. "
        "Может использовать информацию о типе пенсии или краткий контекст дела для уточнения поиска. "
        "Используй этот инструмент, когда нужно найти нормативную базу или конкретные условия для анализа пенсионного дела."
    )
    parameters: List[Dict[str, Any]] = [{
        'name': 'query',
        'type': 'string',
        'description': 'Поисковый запрос, сформулированный на основе анализа ситуации или вопроса пользователя. Должен быть максимально конкретным.',
        'required': True
    }, {
        'name': 'pension_type',
        'type': 'string',
        'description': '(Опционально) Код типа пенсии для уточнения поиска (например, "retirement_standard", "disability_insurance").',
        'required': False
    }, {
        'name': 'case_context', # Пока не используется напрямую в логике ниже, но агент может его передавать
        'type': 'string',
        'description': '(Опционально) Краткий дополнительный контекст по делу, который может помочь сфокусировать поиск.',
        'required': False
    }]

    # Добавляем pension_rag_engine как атрибут инстанса
    # Он будет передан при создании экземпляра инструмента
    def __init__(self, cfg: Optional[Dict] = None, pension_rag_engine: Optional[PensionRAG] = None):
        super().__init__(cfg=cfg)
        if pension_rag_engine is None:
            raise ValueError("PensionKnowledgeRetrieverTool требует экземпляр PensionRAG при инициализации.")
        self.pension_rag_engine: PensionRAG = pension_rag_engine

    def call(self, params: str, **kwargs) -> str:
        try:
            params_dict = json5.loads(params)
            query_text = params_dict.get("query")
            pension_type = params_dict.get("pension_type")
            # case_context = params_dict.get("case_context")

            logger.debug(f"Инструмент {self.name} вызван с параметрами: {params_dict}")

            if not query_text:
                logger.warning(f"В инструменте {self.name} не предоставлен поисковый запрос (query).")
                return "Ошибка: Поисковый запрос (query) не был предоставлен."

            effective_rag_config = {
                'INITIAL_RETRIEVAL_TOP_K': self.pension_rag_engine.config.INITIAL_RETRIEVAL_TOP_K,
                'FILTERED_RETRIEVAL_TOP_K': self.pension_rag_engine.config.FILTERED_RETRIEVAL_TOP_K,
                'RERANKER_TOP_N': self.pension_rag_engine.config.RERANKER_TOP_N 
            }

            # Шаг 1 и 2: Retrieval и Reranking через новый публичный метод
            ranked_nodes: List[NodeWithScore] = self.pension_rag_engine.retrieve_and_rerank_nodes(
                query_text=query_text, 
                pension_type=pension_type,
                effective_config=effective_rag_config
            )

            if not ranked_nodes:
                logger.info(f"Для запроса '{query_text}' инструментом {self.name} не найдено релевантных документов после реранжирования.")
                return "По вашему запросу не найдено релевантных документов в базе знаний или после реранжирования их не осталось."
            
            # Шаг 3: Обогащение из Neo4j
            enriched_nodes: List[NodeWithScore]
            if self.pension_rag_engine.graph_builder and ranked_nodes: # Проверяем ranked_nodes перед обогащением
                enriched_nodes = self.pension_rag_engine.enrich_nodes_from_graph(ranked_nodes)
            else:
                enriched_nodes = ranked_nodes 

            # Шаг 4: Формирование результата в виде строки
            context_parts = []
            for i, node_with_score in enumerate(enriched_nodes):
                node = node_with_score.node
                content = node.get_content()
                metadata = node.metadata
                graph_enrichment = metadata.get('graph_enrichment')

                source_info = f"Источник {i+1} (ID: {node.node_id}, Score: {node_with_score.score:.4f}):\n"
                source_info += f"  Файл: {metadata.get('file_name', 'N/A')}\n"
                if metadata.get('article'):
                    source_info += f"  Статья: {metadata.get('article')}\n"
                if metadata.get('header'):
                     source_info += f"  Раздел/заголовок: {metadata.get('header')}\n"
                
                source_info += f"  Текст: \"{content[:500]}{'...' if len(content) > 500 else ''}\"\n"

                if graph_enrichment:
                    source_info += "  Данные из графа знаний:\n"
                    if graph_enrichment.get('article_title'):
                        source_info += f"    Заголовок статьи: {graph_enrichment['article_title']}\n"
                    if graph_enrichment.get('related_pension_types'):
                        source_info += f"    Связанные типы пенсий: {', '.join(graph_enrichment['related_pension_types'])}\n"
                    if graph_enrichment.get('conditions'):
                        source_info += "    Условия:\n"
                        for cond in graph_enrichment['conditions']:
                            source_info += f"      - {cond.get('condition', 'N/A')}: {cond.get('value', 'N/A')} (для {cond.get('pension_type', 'N/A')})\n"
                
                context_parts.append(source_info)
            
            if not context_parts:
                logger.warning(f"Для запроса {params_dict.get('query')} инструментом {self.name} не удалось сформировать контекст.")
                return "Не удалось сформировать контекст на основе найденных документов."

            result_text = "\n\n---\n\n".join(context_parts)
            logger.info(f"Инструмент {self.name} успешно вернул контекст длиной {len(result_text)} для запроса: {params_dict.get('query')}")
            return result_text

        except json5.JSONDecodeError as json_err:
            logger.error(f"Ошибка декодирования JSON параметров в {self.name}: {json_err}. Параметры: '{params}'")
            return f"Ошибка: неверный формат входных параметров (ожидался JSON). Детали: {str(json_err)}"
        except Exception as e:
            logger.error(f"Критическая ошибка в {self.name}: {e}\n{traceback.format_exc()}")
            return f"Внутренняя ошибка при выполнении поиска в базе знаний. Пожалуйста, проверьте логи сервера. Детали: {str(e)}"

Начальное тестирование инструмента (изолированно):

Создайте временный скрипт для проверки.

Вам понадобится инициализированный PensionRAG.

# Временный тестовый скрипт (например, test_tool.py в корне backend)
# import asyncio # Если PensionRAG использует async, но он синхронный
from app.rag_core.engine import PensionRAG
from app.agent_tools.pension_knowledge_retriever_tool import PensionKnowledgeRetrieverTool

if __name__ == "__main__":
    print("Инициализация PensionRAG (может занять время)...")
    rag_engine_instance = PensionRAG() # Убедитесь, что ваш PensionRAG может быть так инициализирован
    print("PensionRAG инициализирован.")

    tool = PensionKnowledgeRetrieverTool(pension_rag_engine=rag_engine_instance)

    test_params = {
        "query": "Условия назначения страховой пенсии по старости",
        "pension_type": "retirement_standard"
    }
    # Метод call ожидает строку JSON
    params_str = json5.dumps(test_params) 
    
    print(f"\nВызов инструмента с параметрами: {params_str}")
    result = tool.call(params=params_str)
    print("\nРезультат от инструмента:")
    print(result)

    # Закрытие ресурсов PensionRAG, если необходимо (особенно Neo4j)
    if hasattr(rag_engine_instance, 'graph_builder') and rag_engine_instance.graph_builder:
        rag_engine_instance.graph_builder.close()
    print("Тестирование завершено.")

Запустите этот скрипт и убедитесь, что инструмент возвращает ожидаемый текст.

2. Создание Главного Агента (QwenPensionAgent)

Цель: Создать агента Qwen3, использующего разработанный инструмент.

Место: Создайте новый файл backend/app/agents/qwen_pension_agent.py.

Шаги:

Определить класс QwenPensionAgent:

# backend/app/agents/qwen_pension_agent.py
from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message
from typing import Dict, Any, Optional, List, Union
import json # Для парсинга JSON ответа
import re # Для поиска JSON в строке ответа

from app.models import CaseDataInput # Pydantic модель для структурированных данных
from app.rag_core.engine import PensionRAG # Для передачи в инструмент
from app.agent_tools.pension_knowledge_retriever_tool import PensionKnowledgeRetrieverTool # Наш инструмент

class QwenPensionAgent(Assistant):
    def __init__(self, 
                 pension_rag_engine: PensionRAG, # Передаем инстанс RAG-движка
                 llm_cfg: Optional[Dict[str, Any]] = None,
                 system_message: Optional[str] = None,
                 function_list: Optional[List[Union[str, Dict, Any]]] = None, # Any для инстанса BaseTool
                 **kwargs):
        
        # --- Конфигурация LLM для Ollama с Qwen3 ---
        # Замените 'qwen2:7b' на вашу модель Qwen3, если имя другое
        # (например, 'qwen3:32b' или имя, которое вы дали при ollama create)
        default_llm_cfg = {
            'model': 'qwen2:7b',  # Убедитесь, что эта модель запущена в Ollama
            'model_server': 'http://localhost:11434/v1', # OpenAI-совместимый API от Ollama
            'api_key': 'ollama', # Стандартное значение для локального Ollama
            'generate_cfg': {
                'top_p': 0.8,
                'temperature': 0.7, # Экспериментируйте с этим значением
                # 'enable_thinking': True # Это для DashScope. Для Ollama/vLLM не нужно напрямую.
                                       # Агент сам решает, когда вызывать инструменты.
                # 'extra_body': { # Для vLLM
                #    'chat_template_kwargs': {'enable_thinking': True}
                # }
                # Для Ollama и стандартного OpenAI API, 'enable_thinking' не используется в llm_cfg.
                # Если модель поддерживает свой формат типа <think>, Qwen-Agent может его парсить,
                # если 'thought_in_content': True в generate_cfg (см. README Qwen-Agent).
                # По умолчанию для Qwen3 оставим 'thought_in_content': False, если модель разделяет reasoning и content.
            }
        }
        _llm_cfg = {**default_llm_cfg, **(llm_cfg or {})} # Объединяем с переданной конфигурацией

        # --- Системный промпт ---
        default_system_message = (
            "Ты — высококвалифицированный ИИ-ассистент, эксперт по пенсионному законодательству Российской Федерации. "
            "Твоя задача — анализировать предоставленные пенсионные дела, используя доступные инструменты для поиска информации, "
            "и формулировать четкие, обоснованные ответы, ссылаясь на конкретные нормы законодательства.\n"
            "Тебе доступен следующий инструмент:\n"
            "- `pension_knowledge_retriever`: Используй этот инструмент, чтобы найти релевантные статьи законов, "
            "определения, условия назначения пенсий и другую нормативную информацию. Передавай ему в 'query' "
            "четкий поисковый запрос, а в 'pension_type' (если известен) — код типа пенсии.\n"
            "Твой финальный ответ ДОЛЖЕН БЫТЬ СТРОКОЙ В ФОРМАТЕ JSON. JSON должен содержать следующие ключи:\n"
            "- `analysis_summary`: (string) Краткое резюме анализа ситуации.\n"
            "- `compliance_status`: (string) Четкий вывод о соответствии или несоответствии условиям назначения пенсии. Допустимые значения: \"СООТВЕТСТВУЕТ\", \"НЕ СООТВЕТСТВУЕТ\", \"ТРЕБУЕТСЯ_УТОЧНЕНИЕ\".\n"
            "- `detailed_explanation`: (string) Подробное объяснение со ссылками на конкретные статьи и пункты законодательства, найденные с помощью инструмента.\n"
            "- `missing_information`: (list of strings, optional) Список недостающих документов или информации, если это необходимо.\n"
            "- `confidence_level`: (string, optional) Твоя оценка уверенности в предоставленном анализе. Допустимые значения: \"ВЫСОКАЯ\", \"СРЕДНЯЯ\", \"НИЗКАЯ\".\n"
            "- `confidence_reasoning`: (string, optional) Краткое обоснование уровня уверенности.\n\n"
            "Пример JSON-ответа:\n"
            "```json\n"
            "{\n"
            "  \"analysis_summary\": \"Заявитель соответствует основным критериям для назначения страховой пенсии по старости.\",\n"
            "  \"compliance_status\": \"СООТВЕТСТВУЕТ\",\n"
            "  \"detailed_explanation\": \"Согласно Статье X ФЗ-Y (Источник 1), возраст заявителя (65 лет) соответствует требуемому. Стаж (30 лет) превышает минимальный (15 лет). ИПК (150) также соответствует (требуется >30).\",\n"
            "  \"missing_information\": [\"Справка о заработной плате за период до 2002 года, если такой стаж учитывается.\"],\n"
            "  \"confidence_level\": \"ВЫСОКАЯ\",\n"
            "  \"confidence_reasoning\": \"Все ключевые параметры подтверждены информацией из базы знаний, условия выполнены.\"\n"
            "}\n"
            "```\n"
            "Убедись, что твой ответ является ВАЛИДНОЙ JSON-строкой. Не добавляй никакого текста до или после JSON объекта."
        )
        _system_message = system_message or default_system_message

        # --- Инициализация и передача инструмента ---
        # Создаем экземпляр нашего инструмента, передавая ему RAG-движок
        self.knowledge_retriever_tool = PensionKnowledgeRetrieverTool(pension_rag_engine=pension_rag_engine)
        
        # По умолчанию используем только наш инструмент
        _function_list = function_list or [self.knowledge_retriever_tool] 

        super().__init__(llm=_llm_cfg,
                         system_message=_system_message,
                         function_list=_function_list,
                         **kwargs)
        self.pension_rag_engine = pension_rag_engine # Сохраняем для возможного прямого доступа

    def run_pension_case_analysis(self, case_input_data: CaseDataInput) -> Dict[str, Any]:
        # Формируем текстовое описание дела для первичного запроса к агенту
        user_query_parts = [
            f"Проанализируй, пожалуйста, следующее пенсионное дело:",
            f"Тип запрашиваемой пенсии: {self.pension_rag_engine.config.PENSION_TYPE_MAP.get(case_input_data.pension_type, case_input_data.pension_type)} (код: {case_input_data.pension_type})."
        ]
        pd = case_input_data.personal_data
        # Расчет возраста, если это возможно и нужно для промпта
        # from datetime import date
        # today = date.today()
        # age = today.year - pd.birth_date.year - ((today.month, today.day) < (pd.birth_date.month, pd.birth_date.day))
        # user_query_parts.append(f"Основные данные заявителя: Дата рождения {pd.birth_date.strftime('%d.%m.%Y')} (возраст {age} лет), СНИЛС {pd.snils}.")
        user_query_parts.append(f"Основные данные заявителя: Дата рождения {pd.birth_date.strftime('%d.%m.%Y')}, СНИЛС {pd.snils}.")

        if case_input_data.disability:
            user_query_parts.append(f"Есть данные об инвалидности: группа {case_input_data.disability.group}.")
        
        user_query_parts.append(f"Стаж: {case_input_data.work_experience.total_years} лет. Пенсионные баллы (ИПК): {case_input_data.pension_points}.")
        if case_input_data.benefits:
            user_query_parts.append(f"Заявлены льготы: {', '.join(case_input_data.benefits)}.")
        
        user_query = "\n".join(user_query_parts)
        user_query += "\nПроанализируй дело и верни свой ответ СТРОГО в формате JSON согласно инструкциям из системного сообщения."

        messages = [Message(role='user', content=user_query)]
        
        raw_agent_response_content = ""
        # Запускаем Assistant.run() и собираем ответ
        for response_chunk in self.run(messages=messages):
            if response_chunk and isinstance(response_chunk, list) and len(response_chunk) > 0:
                last_message = response_chunk[-1]
                if last_message.role == 'assistant' and last_message.content:
                    raw_agent_response_content = last_message.content 
        
        if not raw_agent_response_content:
            logger.error("Агент не смог сформировать ответ (пустой контент).")
            return {
                "analysis_text": "Агент не смог сформировать ответ.",
                "status": "ERROR",
                "confidence": 0.0,
                "error_message": "Получен пустой ответ от агента."
            }

        try:
            logger.debug(f"Сырой ответ от агента: {raw_agent_response_content}")
            # Попытка распарсить JSON из ответа агента
            # LLM может вернуть JSON с ```json ``` оберткой
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_agent_response_content, re.DOTALL)
            if not json_match: # Если не найдена обертка ```json
                json_match = re.search(r'(\{.*?\})', raw_agent_response_content, re.DOTALL) # Ищем просто JSON объект

            if json_match:
                json_response_str = json_match.group(1) # Берем содержимое группы {.*?}
                parsed_response = json.loads(json_response_str)
                logger.info(f"Агент вернул структурированный JSON ответ: {parsed_response}")
                
                confidence_mapping = {"ВЫСОКАЯ": 0.9, "СРЕДНЯЯ": 0.6, "НИЗКАЯ": 0.3}
                confidence_level_text = parsed_response.get("confidence_level")
                mapped_confidence = confidence_mapping.get(confidence_level_text, 0.5) # 0.5 по умолчанию

                return {
                    "analysis_text": parsed_response.get("detailed_explanation", raw_agent_response_content),
                    "status": parsed_response.get("compliance_status", "UNKNOWN"),
                    "confidence": mapped_confidence,
                    "summary": parsed_response.get("analysis_summary"),
                    "missing_info": parsed_response.get("missing_information"),
                    "confidence_reasoning": parsed_response.get("confidence_reasoning"),
                    "raw_agent_json_response": parsed_response 
                }
            else:
                logger.warning("Агент не вернул ответ в ожидаемом формате JSON (не найден JSON объект). Возвращается сырой текст.")
                # Fallback to text parsing if JSON is not found

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON ответа от агента: {e}. Ответ: {raw_agent_response_content}")
            # Fallback to text parsing if JSON parsing fails
        except Exception as ex: 
            logger.error(f"Ошибка при обработке структурированного ответа от агента: {ex}. Ответ: {raw_agent_response_content}\n{traceback.format_exc()}")
            # Fallback to text parsing for other errors

        # Fallback логика, если парсинг JSON не удался или JSON не был найден
        logger.info("Ответ агента не в формате JSON или произошла ошибка парсинга. Используется текстовый анализ для определения статуса.")
        parsed_status_fallback = "UNKNOWN"
        if "ИТОГ: СООТВЕТСТВУЕТ" in raw_agent_response_content or "\"compliance_status\": \"СООТВЕТСТВУЕТ\"" in raw_agent_response_content :
            parsed_status_fallback = "СООТВЕТСТВУЕТ"
        elif "ИТОГ: НЕ СООТВЕТСТВУЕТ" in raw_agent_response_content or "\"compliance_status\": \"НЕ СООТВЕТСТВУЕТ\"" in raw_agent_response_content:
            parsed_status_fallback = "НЕ СООТВЕТСТВУЕТ"
        elif "ТРЕБУЕТСЯ_УТОЧНЕНИЕ" in raw_agent_response_content or "\"compliance_status\": \"ТРЕБУЕТСЯ_УТОЧНЕНИЕ\"" in raw_agent_response_content:
            parsed_status_fallback = "ТРЕБУЕТСЯ_УТОЧНЕНИЕ"
        
        return {
            "analysis_text": raw_agent_response_content,
            "status": parsed_status_fallback,
            "confidence": 0.2 # Низкая уверенность, так как не удалось распарсить JSON
        }

3. Интеграция QwenPensionAgent в FastAPI Эндпоинт

Цель: Подключить агента к API.

Место: Модификация backend/app/main.py.

Шаги:

Импорты:

# backend/app/main.py
# ... другие импорты ...
from app.agents.qwen_pension_agent import QwenPensionAgent
from app.rag_core.engine import PensionRAG # Убедитесь, что PensionRAG импортируется
# ...

Инициализация Агента в lifespan:

# backend/app/main.py
# ...
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag_engine = None
    app.state.pension_agent = None # Добавляем для агента

    print("Starting up...")
    print("Creating DB tables if they don't exist...")
    create_db_and_tables()
    
    print("Initializing PensionRAG Engine...")
    try:
        # Инициализируем PensionRAG и сохраняем в app.state
        app.state.rag_engine = PensionRAG()
        print("PensionRAG Engine initialized.")

        # Инициализируем QwenPensionAgent, передавая ему PensionRAG
        print("Initializing QwenPensionAgent...")
        if app.state.rag_engine: # Убедимся, что RAG инициализирован
            app.state.pension_agent = QwenPensionAgent(pension_rag_engine=app.state.rag_engine)
            print("QwenPensionAgent initialized.")
        else:
            print("!!! ERROR QwenPensionAgent not initialized because PensionRAG Engine failed to initialize.")

    except Exception as e:
        print(f"!!! ERROR during RAG or Agent initialization: {e}")
        # traceback.print_exc() # Можно добавить для детальной отладки
        if app.state.rag_engine is None:
             print("!!! PensionRAG Engine FAILED to initialize.")
        if app.state.pension_agent is None and app.state.rag_engine: # Если RAG есть, а агент нет
             print("!!! QwenPensionAgent FAILED to initialize.")


    print("Startup complete.")
    yield 
    print("Shutting down...")
    
    # Закрываем соединение с Neo4j, если оно было создано в PensionRAG
    if app.state.rag_engine and hasattr(app.state.rag_engine, 'graph_builder') and app.state.rag_engine.graph_builder:
        try:
            print("Closing Neo4j connection...")
            app.state.rag_engine.graph_builder.close()
            print("Neo4j connection closed.")
        except Exception as e:
            print(f"Error closing Neo4j connection: {e}")
            
    await async_engine.dispose()
    print("Database connection pool closed.")
    print("Shutdown complete.")
# ...

Модификация эндпоинта /process:

# backend/app/main.py
# ...
@app.post("/process_agent", response_model=ProcessOutput) # Новый эндпоинт или переименуйте существующий
async def process_case_with_agent(
    request: Request, 
    case_data: CaseDataInput, 
    conn: AsyncConnection = Depends(get_db_connection)
):
    if request.app.state.pension_agent is None:
        logger.error("QwenPensionAgent is not available.")
        raise HTTPException(status_code=503, detail="Агент анализа пенсионных дел временно недоступен.")

    try:
        agent: QwenPensionAgent = request.app.state.pension_agent
        
        # Вызов метода агента для анализа
        # Этот метод должен быть синхронным, если вызывается из синхронного FastAPI эндпоинта,
        # или эндпоинт должен быть async, а метод агента - awaitable.
        # Метод run() у Assistant из QwenAgent является генератором и выполняется итеративно.
        # run_pension_case_analysis должен это учитывать.
        
        # Если run_pension_case_analysis синхронный:
        agent_result = agent.run_pension_case_analysis(case_input_data=case_data)
        
        analysis_text = agent_result.get("analysis_text", "Анализ не предоставлен.")
        final_status_from_agent = agent_result.get("status", "UNKNOWN")
        # Уверенность пока берем из заглушки или, если агент сможет ее вернуть, оттуда
        agent_confidence = agent_result.get("confidence", 0.0) 

        # Используем статус, возвращенный агентом
        if final_status_from_agent not in ["СООТВЕТСТВУЕТ", "НЕ СООТВЕТСТВУЕТ"]:
            # Если агент не дал четкий статус, пытаемся определить по старой логике или ставим UNKNOWN
            logger.warning(f"Агент вернул статус '{final_status_from_agent}'. Пытаемся определить по тексту.")
            is_compliant = analyze_rag_for_compliance(analysis_text) # Ваша старая функция
            final_status_to_save = "СООТВЕТСТВУЕТ" if is_compliant else "НЕ СООТВЕТСТВУЕТ"
        else:
            final_status_to_save = final_status_from_agent
        
        # Сохранение в БД (логика из вашего старого /process)
        personal_data_dict = case_data.personal_data.model_dump()
        disability_dict = case_data.disability.model_dump() if case_data.disability else None
        work_experience_dict = case_data.work_experience.model_dump()

        errors_to_save_from_agent = [] # Пока агент не возвращает ошибки в структурированном виде

        saved_case_id = await crud.create_case(
            conn=conn,
            personal_data=personal_data_dict,
            errors=errors_to_save_from_agent, # Используем ошибки от агента, если есть
            pension_type=case_data.pension_type,
            disability=disability_dict,
            work_experience=work_experience_dict,
            pension_points=case_data.pension_points,
            benefits=case_data.benefits,
            documents=case_data.documents,
            has_incorrect_document=case_data.has_incorrect_document,
            final_status=final_status_to_save,
            final_explanation=analysis_text, # Полный текст от агента
            rag_confidence=agent_confidence # Уверенность от агента
        )

        return ProcessOutput(
            case_id=saved_case_id,
            final_status=final_status_to_save,
            explanation=analysis_text,
            confidence_score=agent_confidence
        )

    except HTTPException as he:
        logger.error(f"HTTPException in /process_agent: {he.detail}", exc_info=True)
        raise he
    except Exception as e:
        logger.error(f"Unhandled error in /process_agent endpoint: {e}", exc_info=True)
        # traceback.print_exc() # Уже логируется с exc_info=True
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера при обработке агентом: {str(e)}")

# ...

4. Адаптация RAG и Neo4j для Инструмента

**Рекомендация:**
В классе `PensionRAG` (`backend/app/rag_core/engine.py`) создать публичные методы, которые инкапсулируют необходимую логику, или переименовать существующие "защищенные" методы, если они по сути являются частью предполагаемого API для таких компонентов, как инструменты.

**Пример модификации `PensionRAG`:**

```python
# backend/app/rag_core/engine.py
from llama_index.core import QueryBundle # Убедитесь, что импорт есть
from typing import Optional, Dict, List # Убедитесь, что импорты есть
from llama_index.core.schema import NodeWithScore # Убедитесь, что импорт есть


class PensionRAG:
    # ... (существующий код __init__, _initialize_components, etc.) ...

    def retrieve_and_rerank_nodes(
        self, 
        query_text: str, 
        pension_type: Optional[str],
        effective_config: Dict # Передаем сюда или используем self.config
    ) -> List[NodeWithScore]:
        """
        Публичный метод для извлечения и реранжирования узлов.
        Инкапсулирует логику _retrieve_nodes и _rerank_nodes.
        """
        query_bundle = QueryBundle(query_text)
        
        # Предполагаем, что _retrieve_nodes был переименован или является частью этого публичного метода
        retrieved_nodes: List[NodeWithScore] = self._retrieve_nodes( 
            query_bundle, 
            pension_type, 
            effective_config=effective_config # Убедитесь, что _retrieve_nodes принимает effective_config
        )
        
        if not retrieved_nodes:
            return []

        ranked_nodes_final: List[NodeWithScore]
        if self.reranker:
            # Предполагаем, что _rerank_nodes был переименован или является частью этого публичного метода
            ranked_nodes_from_reranker, _ = self._rerank_nodes( 
                query_bundle, 
                retrieved_nodes, 
                effective_config=effective_config # Убедитесь, что _rerank_nodes принимает effective_config
            )
            ranked_nodes_final = ranked_nodes_from_reranker
        else:
            # Логика для случая без реранкера
            # Убедимся, что RERANKER_TOP_N имеет значение
            top_n_count = effective_config.get('RERANKER_TOP_N', 5) 
            retrieved_nodes.sort(key=lambda x: x.score or 0.0, reverse=True) # Сортируем на всякий случай
            ranked_nodes_final = retrieved_nodes[:top_n_count]
        
        return ranked_nodes_final

    def enrich_nodes_from_graph(self, nodes: List[NodeWithScore]) -> List[NodeWithScore]:
         """Публичный метод для обогащения узлов данными из графа."""
         if self.graph_builder: # Проверяем наличие graph_builder
             return self._enrich_nodes_with_graph_data(nodes)
         return nodes # Возвращаем как есть, если графа нет
```

Neo4j-модули (`graph_builder.py`):

Функция `get_article_enrichment_data` в `KnowledgeGraphBuilder` уже используется методом `_enrich_nodes_with_graph_data` в `PensionRAG`. Таким образом, для инструмента прямых изменений не требуется, так как он делегирует обогащение `PensionRAG`.

5. Промпт-Инжиниринг

Агент (ответ пользователю): Анализ... ИТОГ: СООТВЕТСТВУЕТ. Потому что... [ссылки]

Эти few-shot примеры лучше всего вставлять в системный промпт или в начало истории диалога. Формат JSON-ответа, который требуется от агента, уже включен в обновленный системный промпт.

**Стратегии определения Уверенности (Confidence):**

1.  **Использовать `confidence_level` и `confidence_reasoning` из JSON ответа агента:** Как предложено в обновленном системном промпте и логике парсинга `run_pension_case_analysis`, агент может сам оценивать свою уверенность и возвращать её в структурированном виде. Это значение затем можно смапить на числовое значение (0.0-1.0) в бэкенде.
2.  **Использовать скор от реранкера:** Если агент не предоставляет уверенность или для дополнительной метрики, можно использовать нормализованный скор топ-1 документа от реранкера как прокси-метрику уверенности в релевантности предоставленного контекста. `PensionKnowledgeRetrieverTool` может быть модифицирован, чтобы возвращать этот скор вместе с контекстом (текущая реализация уже включает `Score` в `Источник`). Агент мог бы его учитывать или это значение можно использовать на бэкенде.
3.  **Анализ текста ответа (Fallback):** Менее надежный способ – искать ключевые слова неуверенности ("возможно", "вероятно", "неясно" и т.д.) в ответе LLM и понижать оценку. Это можно использовать как дополнительную проверку, если JSON парсинг не удался.

Описание и параметры `PensionKnowledgeRetrieverTool`: Уже определены в классе инструмента. Они должны быть достаточно понятны для LLM.

