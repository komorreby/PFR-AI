import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver, Session, Transaction
import re # <--- Убедимся, что re импортирован
# Предполагаем, что Document и extract_graph_data_from_document будут импортированы
# из соответствующего модуля RAG core, когда мы его подключим.
# from llama_index.core import Document # Placeholder
# from .rag_core.document_parser import extract_graph_data_from_document # Placeholder

# Импорты для конфигурации Neo4j (пока заглушки, потом можно брать из config.py)
# Пример:
# from .rag_core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# TODO: Заменить на реальные значения из конфигурации
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "12345678" # Замените на ваш пароль

logger = logging.getLogger(__name__)

class KnowledgeGraphBuilder:
    """
    Отвечает за построение и обновление графа знаний в Neo4j.
    """
    def __init__(self, uri: str, user: str, password: str, db_name: Optional[str] = None):
        """
        Инициализирует драйвер Neo4j.
        Args:
            uri: URI для подключения к Neo4j (e.g., "bolt://localhost:7687").
            user: Имя пользователя Neo4j.
            password: Пароль для Neo4j.
            db_name: Имя базы данных Neo4j (по умолчанию 'neo4j', если None).
        """
        try:
            self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
            self._driver.verify_connectivity() # Проверяем соединение при инициализации
            self._db_name: str = db_name if db_name is not None else "neo4j" # Сохраняем имя БД
            logger.info(f"Successfully connected to Neo4j at {uri}, database: '{self._db_name}'")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            # Можно пробросить исключение дальше или установить self._driver в None,
            # чтобы последующие операции безопасно завершались ошибкой.
            raise

    def close(self):
        """
        Закрывает соединение с Neo4j.
        """
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed.")

    def _create_nodes_tx(self, tx: Transaction, nodes: List[Dict]):
        """
        Приватный метод для создания/обновления узлов в транзакции.
        Использует MERGE для идемпотентности.
        Предполагается, что каждый узел в списке `nodes` это словарь вида:
        {
            "id": "unique_node_id",      // Используется для MERGE по этому свойству
            "label": "NodeLabel",         // Лейбл узла
            "properties": {                // Словарь остальных свойств
                "property1": "value1",
                "property2": 123
            }
        }
        """
        # TODO: Добавить проверку, что 'id' и 'label' существуют в каждом узле.
        # TODO: Обработать случай, когда properties пустые.
        for node_data in nodes:
            node_id = node_data.get("id")
            node_label = node_data.get("label")
            properties = node_data.get("properties", {})

            if not node_id or not node_label:
                logger.warning(f"Skipping node due to missing id or label: {node_data}")
                continue
            props_to_set = properties.copy()
            if 'id' not in props_to_set and 'node_id' not in props_to_set : # Добавляем id, если его нет
                 props_to_set['id'] = node_id # или props_to_set[node_label.lower() + '_id'] = node_id

            if node_label == "Article":
                props_to_set['article_id'] = node_id

            query = (
                f"MERGE (n:{node_label} {{id: $id_param}})\\n"
                f"SET n = $props_to_set \\n" # Перезаписывает все свойства, включая id
                f"SET n.id = $id_param" # Убеждаемся, что id остается $id_param
            )
            tx.run(query, id_param=node_id, props_to_set=props_to_set)
        logger.info(f"Processed {len(nodes)} nodes.")


    def _create_edges_tx(self, tx: Transaction, edges: List[Dict]):
        """
        Приватный метод для создания ребер в транзакции.
        Использует MERGE для идемпотентности (если ребра могут дублироваться по свойствам)
        или CREATE, если дубликаты не ожидаются или обрабатываются по-другому.
        Предполагается, что каждое ребро в списке `edges` это словарь вида:
        {
            "source_id": "id_of_source_node", // ID исходного узла
            "target_id": "id_of_target_node", // ID целевого узла
            "type": "RELATIONSHIP_TYPE",    // Тип отношения
            "properties": {                   // Свойства ребра (если есть)
                "property1": "value1"
            }
        }
        Предполагается, что узлы с source_id и target_id УЖЕ существуют.
        Также предполагается, что ID узлов (`source_id`, `target_id`) являются значениями свойства `id` у этих узлов.
        Лейблы узлов здесь не нужны, т.к. мы матчим по ID.
        """
        # TODO: Добавить проверку на наличие source_id, target_id, type.
        for edge_data in edges:
            source_id = edge_data.get("source_id")
            target_id = edge_data.get("target_id")
            edge_type = edge_data.get("type")
            properties = edge_data.get("properties", {})

            if not source_id or not target_id or not edge_type:
                logger.warning(f"Skipping edge due to missing source_id, target_id, or type: {edge_data}")
                continue

            # ВАЖНО: Динамическое формирование типа ребра требует осторожности.
            # Убедимся, что edge_type безопасен (из нашего списка разрешенных типов).
            query = (
                f"MATCH (a {{id: $source_id}}), (b {{id: $target_id}})\\n"
                f"MERGE (a)-[r:{edge_type}]->(b)\\n" # MERGE для ребра (без свойств пока)
                # Если нужно установить/обновить свойства ребра:
                # f"SET r = $props" 
            )
            #logger.debug(f"Executing edge query: {query} with params: source_id={source_id}, target_id={target_id}, props={properties}")
            if properties: # Если есть свойства у ребра
                 query_with_props = query.replace("MERGE (a)-[r", f"MERGE (a)-[r:{edge_type}]->(b)\\nSET r = $props\\nMERGE (a)-[r") # Грязновато, но для примера
                 # Более чистый способ - разделить MERGE для структуры и SET для свойств, или использовать APOC.
                 # Для простоты пилота, если свойства ребер не меняются часто, можно просто SET r = $props после MERGE.
                 # Если свойства ребер важны для уникальности ребра, их надо включать в MERGE.
                 # Пока что для простоты будем считать, что ребра уникальны по (source)-[type]->(target)
                 # и свойства можно просто перезаписать, если они есть.
                 final_query = (
                    f"MATCH (a {{id: $source_id}}), (b {{id: $target_id}})\\n"
                    f"MERGE (a)-[r:{edge_type}]->(b)\\n"
                    f"SET r = $props"
                 )
                 tx.run(final_query, source_id=source_id, target_id=target_id, props=properties)
            else:
                 tx.run(query, source_id=source_id, target_id=target_id)
        logger.info(f"Processed {len(edges)} edges.")

    def add_nodes_and_edges(self, nodes: List[Dict], edges: List[Dict]):
        """
        Добавляет узлы и ребра в граф Neo4j в рамках одной транзакции.
        """
        if not self._driver:
            logger.error("Driver not initialized. Cannot add data to Neo4j.")
            return

        with self._driver.session(database=self._db_name if hasattr(self, '_db_name') else None) as session:
            try:
                session.execute_write(self._create_nodes_tx, nodes)
                session.execute_write(self._create_edges_tx, edges)
                logger.info("Successfully added/updated nodes and edges.")
            except Exception as e:
                logger.error(f"Error during Neo4j transaction: {e}")
                # Здесь можно добавить логику отката или повторных попыток, если это необходимо.

    def get_article_enrichment_data(self, article_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves enrichment data for a given article_id from the graph.
        Includes article title, related pension types, and defined conditions.
        """
        if not self._driver:
            logger.error("Neo4j driver not initialized.")
            return None

        # Разделяем запрос на несколько простых запросов для более надежной работы
        try:
            with self._driver.session(database=self._db_name) as session:
                # 1. Получаем базовую информацию о статье
                article_info_query = """
                MATCH (a:Article {article_id: $article_id})
                RETURN a.title AS article_title
                """
                article_result = session.run(article_info_query, article_id=article_id).single()
                if not article_result:
                    logger.warning(f"No article found with article_id: {article_id}")
                    return None
                
                article_title = article_result.get("article_title")
                
                # 2. Находим связанные типы пенсий
                pension_types_query = """
                MATCH (a:Article {article_id: $article_id})-[:RELATES_TO_PENSION_TYPE]->(pt:PensionType)
                RETURN collect(pt.name) AS related_pension_types
                """
                pt_result = session.run(pension_types_query, article_id=article_id).single()
                related_pension_types = pt_result.get("related_pension_types", []) if pt_result else []
                
                # 3. Находим условия для данной статьи
                conditions_query = """
                MATCH (a:Article {article_id: $article_id})-[:DEFINES_CONDITION]->(ec:EligibilityCondition)
                MATCH (ec)-[:APPLIES_TO_PENSION_TYPE]->(pt:PensionType)
                RETURN collect({
                    condition: ec.description, 
                    value: ec.value, 
                    pension_type: pt.name
                }) AS conditions
                """
                cond_result = session.run(conditions_query, article_id=article_id).single()
                conditions = cond_result.get("conditions", []) if cond_result else []
                
                # Фильтруем пустые условия (если какие-то значения null)
                processed_conditions = [
                    cond for cond in conditions 
                    if cond.get("condition") is not None and cond.get("value") is not None
                ]
                
                # Собираем и возвращаем все данные
                return {
                    "article_title": article_title,
                    "related_pension_types": related_pension_types,
                    "conditions": processed_conditions,
                }
                
        except Exception as e:
            logger.error(f"Error querying graph for article enrichment data (article_id: {article_id}): {e}", exc_info=True)
            return None

    def get_articles_for_pension_types(self, pension_types: List[str], limit: int = 10) -> List[str]:
        """
        Получает список ID статей, связанных с указанными типами пенсий.
        Сортирует по убыванию уверенности связи (свойства 'confidence' ребра).
        
        Args:
            pension_types: Список идентификаторов типов пенсий (должны быть их ID, например, 'retirement_standard')
            limit: Максимальное количество статей для возврата
            
        Returns:
            Список canonical_article_id статей, связанных с указанными типами пенсий
        """
        if not self._driver: # Проверка инициализации драйвера
            logger.error("KnowledgeGraphBuilder: Neo4j driver not available or not properly initialized for get_articles_for_pension_types.")
            return []
            
        if not pension_types:
            logger.debug("KnowledgeGraphBuilder: No pension types provided to get_articles_for_pension_types.")
            return []
            
        # Убедимся, что pension_types это список строк
        if not all(isinstance(pt, str) for pt in pension_types):
            logger.error(f"KnowledgeGraphBuilder: pension_types должен быть списком строк, получено: {pension_types}")
            return []

        try:
            # Используем self._db_name, который устанавливается в __init__
            db_name_to_use = self._db_name 
            
            with self._driver.session(database=db_name_to_use) as session:
                # Очистка: оставляем только буквенно-цифровые символы, '_' и '-'
                # Это для формирования строки $pension_types_param, а не для самого параметра $pension_types_param
                cleaned_pension_types_for_log = [re.sub(r'[^\w-]', '', pt) for pt in pension_types if pt]
                
                # Используем параметризацию для списка типов пенсий
                # Используем правильный тип связи 'RELATES_TO_PENSION_TYPE'
                # и сортируем по свойству 'confidence' ребра, если оно есть
                query = """
                MATCH (pt:PensionType)-[r:RELATES_TO_PENSION_TYPE]-(a:Article)
                WHERE pt.id IN $pension_types_param 
                RETURN DISTINCT a.id AS article_id, 
                                COALESCE(r.confidence, 0.0) AS relevance_score 
                ORDER BY relevance_score DESC
                LIMIT $limit_param
                """
                # Используем COALESCE(r.confidence, 0.0) на случай, если у некоторых связей нет свойства confidence
                
                # Передаем сам список pension_types (не cleaned_pension_types_for_log) как параметр.
                # Neo4j драйвер должен корректно обработать список строк для оператора IN.
                params = {"pension_types_param": pension_types, "limit_param": limit}
                logger.debug(f"Executing Cypher query in KnowledgeGraphBuilder: {query} with params: {params}")
                
                result = session.run(query, params)
                articles = [record["article_id"] for record in result]
                
                logger.info(f"KnowledgeGraphBuilder: Found {len(articles)} articles related to pension types: {pension_types} (limit: {limit})")
                return articles
        except Exception as e:
            logger.error(f"KnowledgeGraphBuilder: Error retrieving articles for pension types {pension_types}: {e}", exc_info=True)
            return []
