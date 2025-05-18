import logging
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, Driver, Session, Transaction
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
            
            # Формируем Cypher запрос. Используем $id_param для MERGE,
            # а остальные properties устанавливаем через SET.
            # Лейбл устанавливается динамически (но это безопасно, т.к. мы его контролируем).
            # Убедимся, что node_label не содержит вредоносного кода (хотя он должен быть из нашего списка).
            # ВАЖНО: Динамическое формирование лейбла требует осторожности.
            # Neo4j не позволяет параметризовать лейблы напрямую в Cypher.
            # Мы должны убедиться, что node_label безопасен.
            # Можно использовать список разрешенных лейблов.
            # Для свойства ID создаем отдельный параметр, чтобы индекс по нему работал.
            
            # Свойства для SET (исключая 'id', если он там есть, т.к. он используется в MERGE)
            # и добавляем сам id в properties узла, если он еще не там (для удобства запросов)
            props_to_set = properties.copy()
            if 'id' not in props_to_set and 'node_id' not in props_to_set : # Добавляем id, если его нет
                 props_to_set['id'] = node_id # или props_to_set[node_label.lower() + '_id'] = node_id

            # Если это узел Article, добавляем ему свойство article_id равное его node_id (который и есть canonical_article_id)
            if node_label == "Article":
                props_to_set['article_id'] = node_id

            query = (
                f"MERGE (n:{node_label} {{id: $id_param}})\n"
                f"SET n = $props_to_set \n" # Перезаписывает все свойства, включая id
                f"SET n.id = $id_param" # Убеждаемся, что id остается $id_param
            )
            #logger.debug(f"Executing node query: {query} with params: id_param={node_id}, props_to_set={props_to_set}")
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
                f"MATCH (a {{id: $source_id}}), (b {{id: $target_id}})\n"
                f"MERGE (a)-[r:{edge_type}]->(b)\n" # MERGE для ребра (без свойств пока)
                # Если нужно установить/обновить свойства ребра:
                # f"SET r = $props" 
            )
            #logger.debug(f"Executing edge query: {query} with params: source_id={source_id}, target_id={target_id}, props={properties}")
            if properties: # Если есть свойства у ребра
                 query_with_props = query.replace("MERGE (a)-[r", f"MERGE (a)-[r:{edge_type}]->(b)\nSET r = $props\nMERGE (a)-[r") # Грязновато, но для примера
                 # Более чистый способ - разделить MERGE для структуры и SET для свойств, или использовать APOC.
                 # Для простоты пилота, если свойства ребер не меняются часто, можно просто SET r = $props после MERGE.
                 # Если свойства ребер важны для уникальности ребра, их надо включать в MERGE.
                 # Пока что для простоты будем считать, что ребра уникальны по (source)-[type]->(target)
                 # и свойства можно просто перезаписать, если они есть.
                 final_query = (
                    f"MATCH (a {{id: $source_id}}), (b {{id: $target_id}})\n"
                    f"MERGE (a)-[r:{edge_type}]->(b)\n"
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

# TODO: Заменить Document на актуальный тип из LlamaIndex, если он будет использоваться
# class Document: # Placeholder
#     def __init__(self, text: str, metadata: Dict = None):
#         self.text = text
#         self.metadata = metadata or {}

# def extract_graph_data_from_document(doc: Document, pension_type_map: Dict, pension_type_filters: Dict) -> Tuple[List[Dict], List[Dict]]:
#     # Это заглушка, реальная функция находится в document_parser.py
#     logger.warning("Using MOCK extract_graph_data_from_document in graph_builder.py")
#     # Пример возвращаемых данных
#     file_name = doc.metadata.get("file_name", "unknown.pdf")
#     law_id = file_name.replace(".pdf", "")
#     nodes = [
#         {"id": law_id, "label": "Law", "properties": {"law_id": law_id, "title": f"Закон {law_id}"}},
#         {"id": f"{law_id}_Ст1", "label": "Article", "properties": {"article_id": f"{law_id}_Ст1", "number_text": "Статья 1"}},
#         {"id": "пенсия_по_старости", "label": "PensionType", "properties": {"pension_type_id": "пенсия_по_старости", "name": "Страховая пенсия по старости"}}
#     ]
#     edges = [
#         {"source_id": law_id, "target_id": f"{law_id}_Ст1", "type": "CONTAINS_ARTICLE", "properties": {}},
#         {"source_id": f"{law_id}_Ст1", "target_id": "пенсия_по_старости", "type": "RELATES_TO_PENSION_TYPE", "properties": {}}
#     ]
#     return nodes, edges


# def build_graph_from_documents(
#     documents: List[Document], # Список документов LlamaIndex 
#     pension_type_map: Dict[str, str], 
#     pension_type_filters: Dict[str, Dict[str, Any]],
#     neo4j_uri: str = NEO4J_URI, 
#     neo4j_user: str = NEO4J_USER, 
#     neo4j_password: str = NEO4J_PASSWORD
# ):
#     """
#     Основная функция для извлечения данных из документов и построения графа.
#     1. Инициализирует KnowledgeGraphBuilder.
#     2. Итерирует по документам:
#         - Вызывает extract_graph_data_from_document.
#         - Добавляет узлы и ребра в Neo4j.
#     3. Закрывает соединение.
#     """
#     builder = None
#     try:
#         builder = KnowledgeGraphBuilder(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
#         
#         all_extracted_nodes = []
#         all_extracted_edges = []

#         for doc in documents:
#             logger.info(f"Processing document: {doc.metadata.get('file_name', 'N/A')} for graph building.")
#             # В реальном сценарии здесь будет вызов функции из document_parser
#             # nodes, edges = extract_graph_data_from_document(doc, pension_type_map, pension_type_filters)
            
#             # Используем заглушку для примера работы builder.add_nodes_and_edges
#             # Это нужно будет заменить на реальный вызов extract_graph_data_from_document
#             # из backend.app.rag_core.document_parser
#             # Для этого нужно будет правильно настроить импорты.
            
#             # Пока что, чтобы этот файл был синтаксически корректен и можно было показать структуру,
#             # закомментируем прямое использование extract_graph_data_from_document, так как
#             # импорт из rag_core может потребовать дополнительной настройки путей или структуры проекта.
            
#             # Имитация вызова (замените это реальным вызовом, когда импорты настроены):
#             # nodes, edges = extract_graph_data_from_document(doc, pension_type_map, pension_type_filters)
#             # logger.info(f"Extracted {len(nodes)} nodes and {len(edges)} edges from {doc.metadata.get('file_name')}.")
#             # builder.add_nodes_and_edges(nodes, edges)
            
#             # Для демонстрации, можно добавить тестовые данные напрямую, если extract_graph_data_from_document не импортирован
#             mock_nodes, mock_edges = extract_graph_data_from_document(doc, pension_type_map, pension_type_filters) # Используем заглушку
#             logger.info(f"Extracted (mock) {len(mock_nodes)} nodes and {len(mock_edges)} edges from {doc.metadata.get('file_name')}.")
#             if mock_nodes or mock_edges: # Добавляем, только если что-то извлечено
#                 builder.add_nodes_and_edges(mock_nodes, mock_edges)


#         logger.info("Graph building process completed for all documents.")

#     except Exception as e:
#         logger.error(f"An error occurred during graph building: {e}", exc_info=True)
#     finally:
#         if builder:
#             builder.close()

if __name__ == '__main__':
    # Пример использования (требует настройки LlamaIndex Document и карты типов пенсий)
    # Это для локального тестирования модуля, если потребуется.
    
    # Настройка логирования для примера
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 1. Замените это на реальные импорты и данные
    # from llama_index.core import Document # Нужен LlamaIndex
    # from .rag_core.config import PENSION_TYPE_MAP, PENSION_TYPE_FILTERS # Нужен ваш config.py
    
    # Мок-объект документа (должен соответствовать структуре LlamaIndex Document)
    class Document: 
        def __init__(self, text: str, metadata: Dict = None):
            self.text = text # Используем text вместо get_content() для мока
            self.metadata = metadata if metadata is not None else {}

        def get_content(self): # Добавим метод для совместимости, если он где-то ожидается
            return self.text
    
    # Мок-версия функции извлечения данных (упрощенная)
    def extract_graph_data_from_document_mock(doc: Document, pension_type_map: Dict, pension_type_filters: Dict) -> tuple[List[Dict], List[Dict]]:
        nodes = []
        edges = []
        
        # Предполагаем, что doc.metadata содержит file_name и другие данные, как в document_parser
        file_name = doc.metadata.get("file_name", "unknown.pdf")
        doc_id = doc.metadata.get("doc_id", file_name) # doc_id должен быть уникальным для документа

        # 1. Создаем узел для документа (Law)
        law_node_id = f"law_{doc_id}"
        nodes.append({
            "id": law_node_id,
            "label": "Law",
            "properties": {"name": file_name, "source_file": file_name, "doc_id": doc_id}
        })
        
        # Пример: извлечение "Статьи 8" из ФЗ-400 (очень упрощенно)
        if "ФЗ-400" in file_name and "Статья 8" in doc.text:
            article_8_text_content = "Текст Статьи 8... условия назначения..."
            article_8_id = "ФЗ-400-ФЗ-28_12_2013_Ст_8" # Это canonical_article_id
            nodes.append({
                "id": article_8_id,
                "label": "Article",
                "properties": {
                    "number_text": "Статья 8", 
                    "title": "Условия назначения страховой пенсии по старости", 
                    "text_content_summary": article_8_text_content[:100],
                    "canonical_article_id": article_8_id # Добавляем для консистентности
                }
            })
            edges.append({"source_id": law_node_id, "target_id": article_8_id, "type": "CONTAINS_ARTICLE"})

            # Mock RELATES_TO_PENSION_TYPE based on filters
            # ID типа пенсии из PENSION_TYPE_FILTERS_EXAMPLE для "Страховая по старости (общий случай)"
            target_pension_type_code = "retirement_standard" 

            if target_pension_type_code in pension_type_filters:
                filter_config_for_type = pension_type_filters[target_pension_type_code]
                applies = True # Флаг, что все условия фильтра выполнены
                
                # Проверяем, соответствует ли текущий документ и статья условиям фильтра
                for rule in filter_config_for_type.get("filters", []):
                    metadata_value_to_check = None
                    if rule["key"] == "file_name":
                        metadata_value_to_check = file_name
                    elif rule["key"] == "canonical_article_id": # Используем canonical_article_id
                        metadata_value_to_check = article_8_id # В нашем моке это article_8_id
                    # Можно добавить другие проверки ключей, если они есть в фильтрах
                    
                    if metadata_value_to_check is None or rule["value"] != metadata_value_to_check:
                        applies = False
                        break
                
                if applies:
                    # Создаем узел PensionType, если его еще нет (для мока)
                    # В реальной системе они должны быть предопределены или создаваться отдельно
                    if not any(n["id"] == target_pension_type_code and n["label"] == "PensionType" for n in nodes):
                        nodes.append({
                            "id": target_pension_type_code,
                            "label": "PensionType",
                            "properties": {"name": pension_type_map.get(target_pension_type_code, target_pension_type_code)}
                        })
                    edges.append({"source_id": article_8_id, "target_id": target_pension_type_code, "type": "RELATES_TO_PENSION_TYPE"})
                    logger.info(f"[MOCK] Создана связь RELATES_TO_PENSION_TYPE для {article_8_id} и {target_pension_type_code}")
                else:
                    logger.info(f"[MOCK] Фильтры для {target_pension_type_code} не применились к {article_8_id} / {file_name}")
            else:
                logger.warning(f"[MOCK] Конфигурация фильтра для типа пенсии {target_pension_type_code} не найдена.")

        return nodes, edges

    # Функция-обертка для вызова из __main__
    def build_graph_from_documents_main(
        documents: List[Document], 
        pension_type_map: Dict[str, str], 
        pension_type_filters: Dict[str, Dict[str, Any]],
        neo4j_uri: str = NEO4J_URI, 
        neo4j_user: str = NEO4J_USER, 
        neo4j_password: str = NEO4J_PASSWORD
    ):
        builder = None
        try:
            builder = KnowledgeGraphBuilder(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
            
            for doc_idx, doc_obj in enumerate(documents):
                logger.info(f"Processing document {doc_idx + 1}/{len(documents)}: {doc_obj.metadata.get('file_name', 'N/A')}")
                
                # Используем extract_graph_data_from_document_MOCK для этого примера
                nodes_to_add, edges_to_add = extract_graph_data_from_document_mock(doc_obj, pension_type_map, pension_type_filters)
                
                if nodes_to_add or edges_to_add:
                    logger.info(f"Extracted {len(nodes_to_add)} nodes and {len(edges_to_add)} edges.")
                    builder.add_nodes_and_edges(nodes_to_add, edges_to_add)
                else:
                    logger.info("No graph data extracted from this document.")

            logger.info("Graph building process completed for all documents.")

        except Exception as e:
            logger.error(f"An error occurred during graph building: {e}", exc_info=True)
        finally:
            if builder:
                builder.close()

    logger.info("Starting Neo4j graph builder example script.")
    
    # Пример создания документов (замените на реальную загрузку)
    example_docs = [
        Document(text="Текст закона ФЗ-400... Статья 8...", metadata={"file_name": "ФЗ-400-ФЗ-28_12_2013.pdf"}),
        Document(text="Текст закона ФЗ-166...", metadata={"file_name": "ФЗ-166-ФЗ-15_12_2001.pdf"})
    ]

    # Проверка соединения с Neo4j (убедитесь, что Neo4j запущен и доступен)
    try:
        # Передаем параметры конфигурации явно
        build_graph_from_documents_main(
            example_docs, 
            PENSION_TYPE_MAP_EXAMPLE, 
            PENSION_TYPE_FILTERS_EXAMPLE,
            neo4j_uri=NEO4J_URI,
            neo4j_user=NEO4J_USER,
            neo4j_password=NEO4J_PASSWORD # Убедитесь, что пароль правильный
        )
        logger.info("Neo4j graph builder example script finished.")
    except Exception as main_e:
        logger.error(f"Failed to run graph builder example: {main_e}", exc_info=True)
        logger.info("Please ensure Neo4j is running and credentials (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD) are correct.") 