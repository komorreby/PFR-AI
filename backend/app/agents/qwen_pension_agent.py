# backend/app/agents/qwen_pension_agent.py
from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message
from typing import Dict, Any, Optional, List, Union
import json
import re
import logging
import traceback

# --- Переносим импорт BaseTool сюда ---
from qwen_agent.tools.base import BaseTool
# --- Конец переноса ---

# Предполагается, что Pydantic модель CaseDataInput и PensionRAG импортируются корректно
from app.models import CaseDataInput
# --- Возвращаем PensionRAG и PensionKnowledgeRetrieverTool ---
from app.rag_core.engine import PensionRAG
from app.agent_tools.pension_knowledge_retriever_tool import PensionKnowledgeRetrieverTool
# --- Конец возвращения ---

# Убираем наш DummyTool
# from app.agent_tools.dummy_tool import DummyTool 

logger = logging.getLogger(__name__)

class QwenPensionAgent(Assistant):
    def __init__(self, 
                 pension_rag_engine: PensionRAG, # Возвращаем для реального RAG
                 llm_cfg: Optional[Dict[str, Any]] = None,
                 system_message: Optional[str] = None,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 **kwargs):
        
        default_llm_cfg = {
            'model': 'qwen3:latest', 
            'model_server': 'http://localhost:11434/v1',
            'api_key': 'ollama',
            'generate_cfg': {
                'top_p': 0.8,
                'temperature': 0.1,
                'thought_in_content': False
            }
        }
        _llm_cfg = {**default_llm_cfg, **(llm_cfg or {})}
        logger.info(f"QwenPensionAgent LLM config: {_llm_cfg}")

        # --- Обновленный Системный Промпт для PensionKnowledgeRetrieverTool --- 
        default_system_message = (
            "Ты — ИИ-ассистент, специализирующийся на пенсионном законодательстве РФ.\n"
            "Если пользователь задает вопрос, требующий поиска информации по пенсионному законодательству (например, об условиях назначения пенсии), ты ДОЛЖЕН использовать доступный инструмент `pension_knowledge_retriever`.\n"
            "Не пытайся отвечать на такие вопросы самостоятельно, всегда используй инструмент для получения информации из базы знаний.\n"
            # --- ДОБАВЛЕНА ИНСТРУКЦИЯ ПО ОБРАБОТКЕ ВЫВОДА ИНСТРУМЕНТА ---
            "После того как инструмент `pension_knowledge_retriever` вернет информацию (она будет представлена тебе как сообщение с ролью 'function' или 'tool', содержащее результат вызова), твоя задача — внимательно проанализировать эту информацию и на её основе сформулировать четкий, подробный и полезный ответ на первоначальный вопрос пользователя. Твой ответ должен напрямую использовать сведения, полученные от инструмента. Если полученная от инструмента информация не позволяет полностью ответить на вопрос, кажется нерелевантной или недостаточной, честно укажи это в своем ответе, но всё равно постарайся дать максимально полезный ответ, агрегируя и объясняя то, что было найдено.\n"
            "ВАЖНО: Твой СЛЕДУЮЩИЙ ответ пользователю ПОСЛЕ того, как ты получишь данные от инструмента (сообщение с ролью 'function'/'tool'), ДОЛЖЕН БЫТЬ финальным текстовым ответом, адресованным пользователю. НЕ генерируй в этом следующем ответе <think> или <tool_call>. Просто предоставь анализ полученных данных.\n"
            # --- КОНЕЦ ДОБАВЛЕННОЙ ИНСТРУКЦИИ ---
            "Вот как ты должен вызывать инструмент `pension_knowledge_retriever`:\n"
            "Пользователь: какие условия назначения страховой пенсии по старости?\n"
            "<tool_call>\n"
            "{\"name\": \"pension_knowledge_retriever\", \"arguments\": {\"query\": \"условия назначения страховой пенсии по старости\", \"pension_type\": \"retirement_standard\"}}\n"
            "</tool_call>\n"
            # --- ДОБАВЛЕН ПРИМЕР ФОРМИРОВАНИЯ ОТВЕТА ПОСЛЕ ИНСТРУМЕНТА ---
            "Пример того, как ты должен ответить ПОСЛЕ получения информации от инструмента:\n"
            "Пользователь: (текст первоначального запроса пользователя)\n"
            "<!-- Предыдущие шаги: твой вызов <tool_call> и полученный <tool_response/function_message> от инструмента -->\n"
            "Ассистент: Основываясь на предоставленной информации из базы знаний, вот условия назначения страховой пенсии по старости: [здесь следует твой детальный ответ, извлеченный, агрегированный и синтезированный из информации, которую вернул инструмент]. Если какая-то специфическая информация не была найдена или требует уточнения, я сообщу об этом.\n"
            # --- КОНЕЦ ПРИМЕРА ---
        )
        _system_message = system_message or default_system_message

        # --- Инициализация и передача PensionKnowledgeRetrieverTool --- 
        self.pension_knowledge_tool = PensionKnowledgeRetrieverTool(pension_rag_engine=pension_rag_engine)
        _function_list = [self.pension_knowledge_tool]
        logger.info(f"QwenPensionAgent function list: {[f.name for f in _function_list]}")

        super().__init__(llm=_llm_cfg,
                         system_message=_system_message,
                         function_list=_function_list,
                         **kwargs)
        self.pension_rag_engine = pension_rag_engine 
        logger.info("QwenPensionAgent initialized successfully with PensionKnowledgeRetrieverTool.")

    def run_pension_case_analysis(self, case_input_data: CaseDataInput) -> Dict[str, Any]:
        # Формируем запрос на основе входных данных дела
        # Для примера возьмем описание из дела, если оно есть, или сформируем общий запрос
        user_query_parts = []
        if hasattr(case_input_data, 'case_description') and case_input_data.case_description:
            user_query_parts.append(case_input_data.case_description)
        else:
            user_query_parts.append("Проанализировать пенсионное дело.")
        
        if case_input_data.pension_type:
            user_query_parts.append(f"Тип пенсии: {case_input_data.pension_type}.")
            # Добавляем конкретный вопрос, чтобы стимулировать использование RAG
            user_query_parts.append("Каковы основные условия и требования для этого типа пенсии согласно законодательству?")


        user_query = " ".join(user_query_parts)
        logger.info(f"Generated user query for agent: {user_query}")
        messages = [Message(role='user', content=user_query)]
        
        final_assistant_content = ""
        all_messages_history = [] 

        try:
            logger.info("Sending request to Qwen-Agent Assistant.run...")
            
            for response_messages_chunk in self.run(messages=messages):
                all_messages_history.extend(response_messages_chunk) 
                if response_messages_chunk:
                    for msg in reversed(response_messages_chunk): 
                        if msg.role == 'assistant' and msg.content:
                            final_assistant_content = msg.content 
                        logger.debug(f"Message in chunk: Role: {msg.role}, Content: '{msg.content}', ToolCalls: {getattr(msg, 'tool_calls', None)}, FunctionCall: {getattr(msg, 'function_call', None)}")
            
            logger.info(f"Full conversation history collected. Last assistant content (first 500 chars): '{final_assistant_content[:500]}'")
            # --- ДОБАВЛЕНО ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ИСТОРИИ ---
            logger.info("--- DETAILED MESSAGE HISTORY ---")
            for i, hist_msg in enumerate(all_messages_history):
                content_display = str(hist_msg.content)
                if len(content_display) > 300: # Ограничиваем длину контента в логе
                    content_display = content_display[:300] + "... (truncated)"
                logger.info(f"HISTORY MSG {i}: Role: {hist_msg.role}, Content: '{content_display}', FC: {getattr(hist_msg, 'function_call', None)}, TC: {getattr(hist_msg, 'tool_calls', None)}")
            logger.info("--- END OF DETAILED MESSAGE HISTORY ---")
            # --- КОНЕЦ ДЕТАЛЬНОГО ЛОГИРОВАНИЯ ---

        except Exception as e:
            logger.error(f"Error during Qwen-Agent Assistant.run: {e}\n{traceback.format_exc()}")
            return {
                "analysis_text": f"Ошибка при выполнении анализа агентом: {e}",
                "status": "ERROR_IN_RUN", 
                "confidence": 0.0,
                "error_message": str(e)
            }
        
        if not final_assistant_content:
            logger.error("Агент не смог сформировать финальный содержательный ответ (пустой контент).")
            
            tool_actually_called_this_run = any(
                (hasattr(m, 'tool_calls') and m.tool_calls and m.tool_calls[0].function.name == self.pension_knowledge_tool.name) or \
                (hasattr(m, 'function_call') and m.function_call and m.function_call.name == self.pension_knowledge_tool.name)
                for m in all_messages_history if m.role == 'assistant'
            )

            if tool_actually_called_this_run:
                 logger.info(f"Инструмент {self.pension_knowledge_tool.name} БЫЛ вызван (определено по истории). Финальный ответ LLM пуст.")
                 return {
                    "analysis_text": f"Инструмент {self.pension_knowledge_tool.name} был вызван, но финальный ответ от LLM пуст.",
                    "status": "TOOL_CALLED_EMPTY_LLM_RESPONSE",
                    "confidence": 0.0,
                    "tool_was_called_flag_from_history": True
                 }
            else:
                 logger.error(f"Агент не смог сформировать ответ и инструмент {self.pension_knowledge_tool.name} не был вызван (судя по истории).")
                 return {
                    "analysis_text": f"Агент не смог сформировать ответ и не вызвал инструмент {self.pension_knowledge_tool.name}.",
                    "status": "ERROR_NO_RESPONSE_NO_TOOL_CALL",
                    "confidence": 0.0,
                    "tool_was_called_flag_from_history": False
                 }

        try:
            logger.debug(f"Attempting to parse JSON from final assistant content: {final_assistant_content[:1000]}")
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', final_assistant_content, re.DOTALL)
            if not json_match:
                json_match = re.search(r'(\{.*?\})', final_assistant_content, re.DOTALL) # Попытка найти JSON без обрамления

            if json_match:
                json_response_str = json_match.group(1)
                # Проверяем, не является ли строка просто текстовым ответом, который случайно похож на JSON
                # Например, если LLM просто вернула вывод инструмента без обертки в JSON {"message": "..."}
                # Для реального RAG, мы ожидаем структурированный ответ от LLM, а не просто сырой вывод инструмента.
                # Поэтому, если JSON не содержит ключей, которые мы ожидаем от LLM (например, 'analysis_summary', 'recommendations'),
                # то это может быть не тот JSON, который нам нужен. Пока оставим как есть.
                parsed_response = json.loads(json_response_str)
                logger.info(f"Agent returned structured JSON response: {parsed_response}")
                
                return {
                    "final_agent_json_response": parsed_response,
                    "status": "SUCCESS_JSON_PARSED",
                    "confidence": 1.0 
                }
            else:
                logger.warning("Final assistant response not in expected JSON format. Returning raw text.")
                # Это нормальный исход, если системный промпт не требует от LLM всегда возвращать JSON
                return {
                    "final_agent_raw_response": final_assistant_content,
                    "status": "SUCCESS_RAW_TEXT",
                    "confidence": 0.5 
                }
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error from final assistant response: {e}. Response: {final_assistant_content}")
            return {
                 "final_agent_raw_response_error_parsing": final_assistant_content,
                 "status": "ERROR_JSON_DECODE",
                 "confidence": 0.1
            }
        except Exception as ex:
            logger.error(f"Error processing final structured response from agent: {ex}. Response: {final_assistant_content}\n{traceback.format_exc()}")
            return {
                 "final_agent_raw_response_processing_error": final_assistant_content,
                 "status": "ERROR_PROCESSING_RESPONSE",
                 "confidence": 0.1
            } 