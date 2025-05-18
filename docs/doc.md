Эта документация будет охватывать:

Основы Qwen-Agent: Создание агентов и инструментов.

Конфигурация LLM (Qwen3 через Ollama/OpenAI-совместимый API): Как подключить вашу модель.

Разработка Кастомного Инструмента: На примере вашего PensionKnowledgeRetrieverTool.

Разработка Главного Агента: На примере вашего QwenPensionAgent, включая промпт-инжиниринг для JSON-ответа.

Интеграция с FastAPI: Как запустить и использовать агента в веб-сервисе.

Документация для Проекта "Агентский RAG с Qwen3 для Анализа Пенсионных Дел"
1. Основы Qwen-Agent

Qwen-Agent — это фреймворк, который упрощает создание LLM-приложений. Ключевые компоненты для вашего проекта:

Agent (Агент): Ядро вашего приложения. Он будет принимать структурированные данные о пенсионном деле, использовать инструменты для получения информации и генерировать анализ.

Вы будете использовать класс Assistant из qwen_agent.agents как основу для вашего QwenPensionAgent.

Агент получает список сообщений (messages) и генерирует поток ответных сообщений.

Ключевой файл для изучения: agent.md.

Tool (Инструмент): Расширение возможностей агента. Ваш PensionKnowledgeRetrieverTool будет таким инструментом.

Инструменты наследуются от BaseTool из qwen_agent.tools.base.

Агент решает, какой инструмент использовать, на основе его description и parameters.

Ключевой файл для изучения: tool.md.

LLM (Большая Языковая Модель): "Мозг" агента. В вашем случае это будет Qwen3, доступный через Ollama.

Qwen-Agent абстрагирует взаимодействие с LLM через конфигурационный словарь.

Ключевой файл для изучения: llm.md.

Установка Qwen-Agent (минимально необходимая для проекта):
pip install -U qwen-agent json5 # json5 для парсинга параметров в инструменте


Если вы планируете использовать встроенный GUI для отладки:

pip install -U "qwen-agent[gui]" json5
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END
2. Конфигурация LLM (Qwen3 через Ollama)

Ваш агент (QwenPensionAgent) будет использовать Qwen3, запущенный локально через Ollama (или другой OpenAI-совместимый API, например, vLLM).

Настройка в Ollama: Убедитесь, что у вас установлена и запущена нужная модель Qwen3 в Ollama. Например, если вы создали модель с именем qwen3:32b-custom, используйте это имя. По умолчанию Ollama предоставляет OpenAI-совместимый API по адресу http://localhost:11434/v1.

Конфигурация llm_cfg для Qwen-Agent:
Как указано в вашем plan.md для QwenPensionAgent:

default_llm_cfg = {
    'model': 'qwen2:7b',  # ЗАМЕНИТЕ НА ИМЯ ВАШЕЙ МОДЕЛИ QWEN3 В OLLAMA (например, 'qwen3:32b')
    'model_server': 'http://localhost:11434/v1', # Стандартный адрес Ollama
    'api_key': 'ollama', # Стандартное значение для локального Ollama (можно также 'EMPTY')
    'generate_cfg': {
        'top_p': 0.8,
        'temperature': 0.7, # Экспериментируйте с этим значением
        # 'thought_in_content': False, # Для Qwen3 обычно False, если модель разделяет reasoning и content.
                                     # Если ваша модель Qwen3 через Ollama выводит <think>...</think> в content, установите True.
        # 'max_input_tokens': 4096 # Опционально, если нужно ограничить длину входа для модели
    }
}
# LLM будет инициализирована внутри вашего агента примерно так:
# self.llm = get_chat_model(llm_cfg)
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Python
IGNORE_WHEN_COPYING_END

model: Точное имя модели, как оно известно вашему локальному серверу (Ollama).

model_server: URL OpenAI-совместимого API вашего локального сервера.

api_key: Обычно ollama или EMPTY для локальных развертываний без аутентификации.

generate_cfg:

temperature: Контролирует случайность вывода. Более низкие значения делают вывод более детерминированным.

top_p: Нуклеусная выборка.

thought_in_content: Важно для корректного парсинга мыслей агента, если модель их генерирует в формате <think>...</think> внутри основного контента. Для Qwen3, используемого через DashScope API с параметром enable_thinking, мысли обычно приходят в отдельном поле. При использовании OpenAI-совместимого API поведение может отличаться в зависимости от того, как модель и сервер (vLLM/Ollama) сконфигурированы для эмуляции "режима мышления" или вывода мыслей. Если ваш reasoning_parser (в vLLM) или формат вывода Ollama не разделяет мысли, и они встраиваются в content, установите True. По умолчанию False.

3. Разработка Кастомного Инструмента (PensionKnowledgeRetrieverTool)

Инструмент предоставляет агенту специфические возможности. LLM решает, когда и с какими параметрами его вызвать.

Определение класса инструмента: (из tool.md и вашего plan.md)

# backend/app/agent_tools/pension_knowledge_retriever_tool.py
import json5
from qwen_agent.tools.base import BaseTool, register_tool
from typing import Optional, Dict, Any, List
import logging
import traceback

# Импорт вашего PensionRAG и других необходимых типов
from app.rag_core.engine import PensionRAG
from llama_index.core.schema import NodeWithScore

logger = logging.getLogger(__name__)

@register_tool('pension_knowledge_retriever') # Регистрация инструмента
class PensionKnowledgeRetrieverTool(BaseTool):
    name: str = "pension_knowledge_retriever" # Уникальное имя инструмента
    description: str = ( # Описание для LLM: что делает инструмент и когда его использовать
        "Извлекает и обобщает релевантные статьи пенсионного законодательства РФ "
        "и связанные с ними условия на основе поискового запроса. "
        "Может использовать информацию о типе пенсии или краткий контекст дела для уточнения поиска. "
        "Используй этот инструмент, когда нужно найти нормативную базу или конкретные условия для анализа пенсионного дела."
    )
    parameters: List[Dict[str, Any]] = [{ # Описание параметров для LLM
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
        'name': 'case_context',
        'type': 'string',
        'description': '(Опционально) Краткий дополнительный контекст по делу, который может помочь сфокусировать поиск.',
        'required': False
    }]

    def __init__(self, cfg: Optional[Dict] = None, pension_rag_engine: Optional[PensionRAG] = None):
        super().__init__(cfg=cfg)
        if pension_rag_engine is None:
            raise ValueError("PensionKnowledgeRetrieverTool требует экземпляр PensionRAG при инициализации.")
        self.pension_rag_engine: PensionRAG = pension_rag_engine

    def call(self, params: str, **kwargs) -> str:
        # params - это JSON-строка от LLM
        try:
            params_dict = json5.loads(params) # Используйте json5 для гибкости
            query_text = params_dict.get("query")
            # ... (остальная логика из вашего plan.md)

            if not query_text:
                # ...
                return "Ошибка: Поисковый запрос (query) не был предоставлен."

            # ... вызов self.pension_rag_engine.retrieve_and_rerank_nodes(...)
            # ... вызов self.pension_rag_engine.enrich_nodes_from_graph(...)
            # ... формирование result_text

            logger.info(f"Инструмент {self.name} успешно вернул контекст...")
            return result_text # Результат должен быть строкой

        except json5.JSONDecodeError as json_err:
            logger.error(f"Ошибка декодирования JSON параметров в {self.name}: {json_err}. Параметры: '{params}'")
            return f"Ошибка: неверный формат входных параметров (ожидался JSON). Детали: {str(json_err)}"
        except Exception as e:
            logger.error(f"Критическая ошибка в {self.name}: {e}\n{traceback.format_exc()}")
            return f"Внутренняя ошибка при выполнении поиска в базе знаний. Детали: {str(e)}"
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Python
IGNORE_WHEN_COPYING_END

Ключевые моменты:

@register_tool('unique_tool_name'): Делает инструмент доступным для агента по этому имени.

description: LLM использует это описание, чтобы понять, когда использовать инструмент. Оно должно быть четким и информативным.

parameters: LLM использует это для понимания, какие данные передать в инструмент. Типы и описания важны.

__init__: Здесь вы передаете вашему инструменту необходимые зависимости, такие как pension_rag_engine.

call(self, params: str, **kwargs) -> str:

Принимает параметры от LLM в виде JSON-строки. Используйте json5.loads(params) для разбора.

Выполняет основную логику инструмента (взаимодействие с RAG, Neo4j).

Возвращает результат также в виде строки. Это может быть простой текст или строка JSON, если последующий шаг LLM ожидает структурированные данные от инструмента. В вашем случае, это текстовый контекст для LLM.

Логирование и обработка ошибок внутри call крайне важны для отладки.

Изолированное тестирование инструмента: Как предложено в plan.md, создайте временный скрипт для проверки работы инструмента отдельно от агента. Это поможет быстро выявить проблемы.

4. Разработка Главного Агента (QwenPensionAgent)

Агент будет использовать LLM и ваш кастомный инструмент для анализа пенсионных дел и возврата структурированного JSON.

Определение класса агента: (из agent.md и вашего plan.md)

# backend/app/agents/qwen_pension_agent.py
from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message
from typing import Dict, Any, Optional, List, Union
import json
import re
import logging # Добавлено для логгера агента
import traceback # Добавлено

from app.models import CaseDataInput
from app.rag_core.engine import PensionRAG
from app.agent_tools.pension_knowledge_retriever_tool import PensionKnowledgeRetrieverTool

logger = logging.getLogger(__name__) # Логгер для агента

class QwenPensionAgent(Assistant):
    def __init__(self,
                 pension_rag_engine: PensionRAG,
                 llm_cfg: Optional[Dict[str, Any]] = None,
                 system_message: Optional[str] = None,
                 # function_list не нужен, если инструмент передается как объект
                 **kwargs):

        # --- Конфигурация LLM (как в разделе 2) ---
        default_llm_cfg = {
            'model': 'qwen2:7b', # ЗАМЕНИТЕ НА ВАШУ МОДЕЛЬ QWEN3
            'model_server': 'http://localhost:11434/v1',
            'api_key': 'ollama',
            'generate_cfg': {'top_p': 0.8, 'temperature': 0.7}
        }
        _llm_cfg = {**default_llm_cfg, **(llm_cfg or {})}

        # --- Системный промпт (КРИТИЧЕСКИ ВАЖНО) ---
        # (Ваш подробный системный промпт из plan.md, включая описание формата JSON)
        default_system_message = (
            "Ты — высококвалифицированный ИИ-ассистент, эксперт по пенсионному законодательству..."
            # ... (полный текст вашего системного промпта) ...
            "Убедись, что твой ответ является ВАЛИДНОЙ JSON-строкой. Не добавляй никакого текста до или после JSON объекта."
        )
        _system_message = system_message or default_system_message

        # --- Инициализация и передача инструмента ---
        self.knowledge_retriever_tool = PensionKnowledgeRetrieverTool(pension_rag_engine=pension_rag_engine)
        
        # Передаем сам объект инструмента, а не его имя строкой
        _function_list = [self.knowledge_retriever_tool]

        super().__init__(llm=_llm_cfg,
                         system_message=_system_message,
                         function_list=_function_list, # Передаем список объектов инструментов
                         **kwargs)
        self.pension_rag_engine = pension_rag_engine

    def run_pension_case_analysis(self, case_input_data: CaseDataInput) -> Dict[str, Any]:
        # ... (логика формирования user_query из plan.md) ...
        user_query_parts = [
            f"Проанализируй, пожалуйста, следующее пенсионное дело:",
            # ... (добавление деталей дела) ...
        ]
        user_query = "\n".join(user_query_parts)
        user_query += "\nПроанализируй дело и верни свой ответ СТРОГО в формате JSON согласно инструкциям из системного сообщения."
        
        messages = [Message(role='user', content=user_query)]
        
        raw_agent_response_content = ""
        # Запускаем Assistant.run() и собираем ПОЛНЫЙ финальный ответ ассистента
        final_assistant_message_content = ""
        for response_list in self.run(messages=messages): # self.run() возвращает генератор СПИСКОВ сообщений
            if response_list:
                # Ищем последнее сообщение от ассистента в текущем чанке
                for msg_idx in range(len(response_list) -1, -1, -1):
                    msg = response_list[msg_idx]
                    if msg.role == 'assistant' and msg.content: # Берем контент от ассистента
                        final_assistant_message_content = msg.content # Обновляем на самый свежий контент ассистента
                        break # Нашли, выходим из внутреннего цикла
        
        raw_agent_response_content = final_assistant_message_content # Это финальный полный ответ LLM

        if not raw_agent_response_content:
            logger.error("Агент не смог сформировать ответ (пустой контент).")
            # ... (обработка ошибки)
            return {"error_message": "Получен пустой ответ от агента."}

        logger.debug(f"Сырой ответ от агента (после всех итераций): {raw_agent_response_content}")

        # --- Парсинг JSON ответа (логика из plan.md) ---
        try:
            # Попытка найти JSON в ```json ... ``` или просто { ... }
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_agent_response_content, re.DOTALL)
            if not json_match:
                json_match = re.search(r'(\{.*?\})', raw_agent_response_content, re.DOTALL)

            if json_match:
                json_response_str = json_match.group(1)
                parsed_response = json.loads(json_response_str)
                logger.info(f"Агент вернул структурированный JSON ответ: {parsed_response}")
                # ... (дальнейшая обработка parsed_response из plan.md)
                return {
                    "analysis_text": parsed_response.get("detailed_explanation", raw_agent_response_content),
                    # ... (остальные поля)
                    "raw_agent_json_response": parsed_response
                }
            else:
                logger.warning("Агент не вернул ответ в ожидаемом формате JSON. Ответ: " + raw_agent_response_content)
                # ... (Fallback логика, если JSON не найден)

        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON ответа от агента: {e}. Ответ: {raw_agent_response_content}")
            # ... (Fallback логика)
        except Exception as ex:
            logger.error(f"Ошибка при обработке ответа от агента: {ex}. Ответ: {raw_agent_response_content}\n{traceback.format_exc()}")
            # ... (Fallback логика)
        
        # Fallback, если ничего не получилось
        return {
            "analysis_text": raw_agent_response_content,
            "status": "UNKNOWN_FORMAT",
            "confidence": 0.1
        }
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Python
IGNORE_WHEN_COPYING_END

Ключевые моменты для агента:

system_message: Это ваш главный инструмент для управления поведением LLM. Он должен четко описывать роль агента, доступные инструменты (с кратким указанием, когда их использовать, даже если подробное описание в самом инструменте) и, самое важное для вас, точный формат JSON, который вы ожидаете на выходе. Примеры (few-shot) внутри системного промпта очень помогают LLM следовать формату.

function_list: Передавайте сюда объекты ваших кастомных инструментов (например, [self.knowledge_retriever_tool]). Агент будет использовать description и parameters из объекта инструмента.

Сбор ответа от self.run(): Метод Assistant.run() является генератором. Он может выдавать несколько "ходов" (например, сначала вызов инструмента, потом его результат, потом финальный ответ LLM). Вам нужно аккумулировать или дождаться финального ответа ассистента, который содержит итоговый JSON. В примере выше логика сбора ответа немного уточнена, чтобы получить именно финальное сообщение ассистента.

Парсинг JSON: LLM не всегда идеально следует инструкциям. Будьте готовы к тому, что JSON может быть обернут в текст или разметку (например, json ...). Используйте регулярные выражения для извлечения JSON-строки перед парсингом. Предусмотрите обработку ошибок json.JSONDecodeError.

Fallback-логика: Если LLM не вернула JSON или он не парсится, должна быть стратегия обработки "сырого" текстового ответа.

5. Интеграция с FastAPI

Вы будете инициализировать агента при старте FastAPI приложения и использовать его в эндпоинте.

Инициализация в lifespan: (из вашего plan.md)

# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
# ... другие импорты
from app.agents.qwen_pension_agent import QwenPensionAgent
from app.rag_core.engine import PensionRAG
from app.models import CaseDataInput, ProcessOutput # Ваши Pydantic модели
# ... crud, get_db_connection и т.д.
import logging # Добавлено для логгера FastAPI

logger = logging.getLogger(__name__) # Логгер для FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI приложение запускается...")
    app.state.rag_engine = None
    app.state.pension_agent = None
    # ... create_db_and_tables() ...

    try:
        logger.info("Инициализация PensionRAG Engine...")
        app.state.rag_engine = PensionRAG() # Убедитесь, что PensionRAG готов к синхронному использованию или адаптируйте
        logger.info("PensionRAG Engine инициализирован.")

        logger.info("Инициализация QwenPensionAgent...")
        app.state.pension_agent = QwenPensionAgent(pension_rag_engine=app.state.rag_engine)
        logger.info("QwenPensionAgent инициализирован.")
    except Exception as e:
        logger.error(f"!!! ОШИБКА во время инициализации RAG или Агента: {e}", exc_info=True)
        # ... (обработка ошибок инициализации)

    yield # Приложение работает

    logger.info("FastAPI приложение останавливается...")
    # ... (логика закрытия соединений, например, Neo4j в rag_engine) ...
    if app.state.rag_engine and hasattr(app.state.rag_engine, 'graph_builder') and app.state.rag_engine.graph_builder:
        try:
            logger.info("Закрытие соединения Neo4j...")
            app.state.rag_engine.graph_builder.close() # Если есть метод close
            logger.info("Соединение Neo4j закрыто.")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения Neo4j: {e}", exc_info=True)

    # ... await async_engine.dispose() ...
    logger.info("Остановка завершена.")

app = FastAPI(lifespan=lifespan) # Подключаем lifespan

@app.post("/process_agent", response_model=ProcessOutput)
async def process_case_with_agent(
    request: Request,
    case_data: CaseDataInput,
    # conn: AsyncConnection = Depends(get_db_connection) # Если нужно сохранение в БД
):
    if request.app.state.pension_agent is None:
        logger.error("QwenPensionAgent не доступен.")
        raise HTTPException(status_code=503, detail="Агент анализа пенсионных дел временно недоступен.")

    try:
        agent: QwenPensionAgent = request.app.state.pension_agent
        
        # Вызов метода агента.
        # ВАЖНО: FastAPI эндпоинты по умолчанию выполняются в event loop.
        # Если ваш `agent.run_pension_case_analysis` и все его внутренние вызовы
        # (включая `self.run()`, вызовы LLM, инструментов) являются блокирующими (синхронными),
        # они будут блокировать event loop FastAPI.
        # Для продакшена рекомендуется запускать блокирующие CPU-bound операции
        # (как вызов LLM) в отдельном потоке/процессе, например, используя `fastapi.concurrency.run_in_threadpool`.
        # Для простоты, предполагаем пока прямой вызов.
        
        # from fastapi.concurrency import run_in_threadpool
        # agent_result = await run_in_threadpool(agent.run_pension_case_analysis, case_input_data=case_data)
        
        # Прямой вызов (может блокировать, если не асинхронный внутри)
        agent_result = agent.run_pension_case_analysis(case_input_data=case_data)

        # ... (остальная логика из вашего plan.md для обработки agent_result и сохранения в БД) ...
        analysis_text = agent_result.get("analysis_text", "Анализ не предоставлен.")
        final_status_to_save = agent_result.get("status", "UNKNOWN")
        agent_confidence = agent_result.get("confidence", 0.0)

        # Пример сохранения в БД (адаптируйте под ваш CRUD)
        # saved_case_id = await crud.create_case(...)

        return ProcessOutput(
            case_id=1, # Замените на реальный ID
            final_status=final_status_to_save,
            explanation=analysis_text,
            confidence_score=agent_confidence
        )

    except HTTPException as he:
        logger.error(f"HTTPException в /process_agent: {he.detail}", exc_info=True)
        raise he
    except Exception as e:
        logger.error(f"Необработанная ошибка в эндпоинте /process_agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Python
IGNORE_WHEN_COPYING_END

Ключевые моменты для FastAPI:

Инициализация в lifespan: Гарантирует, что ваш агент (и его зависимости вроде RAG-движка) создаются один раз при старте приложения и корректно освобождают ресурсы при остановке.

Доступ к агенту через request.app.state.

Блокирующие операции: Вызовы LLM и сложная логика агента могут быть блокирующими. Для асинхронного FastAPI это означает, что пока выполняется такой вызов, сервер не сможет обрабатывать другие запросы. Рассмотрите использование fastapi.concurrency.run_in_threadpool для вызова agent.run_pension_case_analysis, чтобы не блокировать основной поток FastAPI.

from fastapi.concurrency import run_in_threadpool
# ...
agent_result = await run_in_threadpool(agent.run_pension_case_analysis, case_input_data=case_data)
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Python
IGNORE_WHEN_COPYING_END

Это потребует, чтобы pension_rag_engine и другие компоненты, используемые агентом, были потокобезопасными или чтобы каждый вызов в run_in_threadpool работал с собственными экземплярами, если это необходимо.

Обработка ошибок: Надежная обработка ошибок и логирование в эндпоинте.

6. Дополнительные Советы

Итеративная разработка: Начните с простого агента и одного простого инструмента. Постепенно усложняйте.

Логирование: Используйте logging обильно на всех этапах (в инструменте, в агенте, в FastAPI) для отслеживания потока данных и ошибок. Логируйте промпты, ответы LLM, вызовы инструментов и их результаты.

Отладка промптов: Если агент ведет себя не так, как ожидается (не использует инструмент, не возвращает JSON), в первую очередь проверяйте и корректируйте system_message и описания инструментов. Вывод промежуточных шагов агента (какие мысли он генерирует, какие инструменты пытается вызвать) может быть очень полезен. Если thought_in_content установлено в True и ваша модель генерирует мысли, вы сможете их увидеть в ответе. Некоторые версии Qwen-Agent могут также иметь опции для более детального вывода шагов агента.
