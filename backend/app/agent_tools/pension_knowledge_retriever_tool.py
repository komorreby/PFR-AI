# backend/app/agent_tools/pension_knowledge_retriever_tool.py
import json5
from qwen_agent.tools.base import BaseTool, register_tool
from typing import Optional, Dict, Any, List

# Импортируем ваш PensionRAG и QueryBundle (если он где-то определен как тип)
# Предполагается, что PensionRAG можно импортировать так:
from app.rag_core.engine import PensionRAG
# QueryBundle обычно из llama_index.core, если используется для типизации
from llama_index.core import QueryBundle
from llama_index.core.schema import NodeWithScore
import logging
import traceback

logger = logging.getLogger(__name__)

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

    def __init__(self, cfg: Optional[Dict] = None, pension_rag_engine: Optional[PensionRAG] = None):
        super().__init__(cfg=cfg)
        if pension_rag_engine is None:
            logger.critical("PensionKnowledgeRetrieverTool требует экземпляр PensionRAG при инициализации, но получил None.")
            raise ValueError("PensionKnowledgeRetrieverTool требует экземпляр PensionRAG при инициализации.")
        self.pension_rag_engine: PensionRAG = pension_rag_engine
        logger.info(f"Инструмент {self.name} инициализирован с PensionRAG engine.")


    def call(self, params: str, **kwargs) -> str:
        try:
            params_dict = json5.loads(params)
            query_text = params_dict.get("query")
            pension_type = params_dict.get("pension_type")
            case_context = params_dict.get("case_context")

            logger.info(f"Инструмент {self.name} вызван с параметрами: query='{query_text}', pension_type='{pension_type}', case_context='{case_context}'")

            if not query_text:
                logger.warning(f"В инструменте {self.name} не предоставлен поисковый запрос (query).")
                return "Ошибка: Поисковый запрос (query) не был предоставлен."

            effective_rag_config = {
                'INITIAL_RETRIEVAL_TOP_K': self.pension_rag_engine.config.INITIAL_RETRIEVAL_TOP_K,
                'FILTERED_RETRIEVAL_TOP_K': self.pension_rag_engine.config.FILTERED_RETRIEVAL_TOP_K,
                'RERANKER_TOP_N': self.pension_rag_engine.config.RERANKER_TOP_N
            }

            ranked_nodes: List[NodeWithScore] = self.pension_rag_engine.retrieve_and_rerank_nodes(
                query_text=query_text,
                pension_type=pension_type,
                effective_config=effective_rag_config
            )
            logger.debug(f"Инструмент {self.name}: Получено {len(ranked_nodes)} узлов после retrieve_and_rerank_nodes.")

            if not ranked_nodes:
                logger.info(f"Для запроса '{query_text}' инструментом {self.name} не найдено релевантных документов после реранжирования.")
                return "По вашему запросу не найдено релевантных документов в базе знаний или после реранжирования их не осталось."

            enriched_nodes: List[NodeWithScore]
            if self.pension_rag_engine.graph_builder and ranked_nodes: # Проверяем ranked_nodes перед обогащением
                enriched_nodes = self.pension_rag_engine.enrich_nodes_from_graph(ranked_nodes)
                logger.debug(f"Инструмент {self.name}: {len(enriched_nodes)} узлов после enrich_nodes_from_graph.")
            else:
                enriched_nodes = ranked_nodes
                logger.debug(f"Инструмент {self.name}: Обогащение графом пропущено (graph_builder: {self.pension_rag_engine.graph_builder is not None}, ranked_nodes: {bool(ranked_nodes)}).")

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
            logger.info(f"Инструмент {self.name} успешно вернул контекст длиной {len(result_text)} для запроса: '{params_dict.get('query')}'")
            logger.debug(f"Полный текст контекста от инструмента {self.name}:\n{result_text[:20]}...")
            return result_text

        except json5.JSONDecodeError as json_err:
            logger.error(f"Ошибка декодирования JSON параметров в {self.name}: {json_err}. Параметры: '{params}'")
            return f"Ошибка: неверный формат входных параметров (ожидался JSON). Детали: {str(json_err)}"
        except Exception as e:
            logger.error(f"Критическая ошибка в {self.name}: {e}\n{traceback.format_exc()}")
            return f"Внутренняя ошибка при выполнении поиска в базе знаний. Пожалуйста, проверьте логи сервера. Детали: {str(e)}" 