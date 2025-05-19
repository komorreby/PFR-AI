# backend/app/rag_core/engine.py
import os
import glob
import json
import logging
import re # <--- ДОБАВЛЕН ИМПОРТ
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Document,
    QueryBundle
)
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.retrievers import BaseRetriever
from llama_index.llms.ollama import Ollama
from llama_index.core.vector_stores import MetadataFilter, ExactMatchFilter, MetadataFilters
from sentence_transformers import CrossEncoder
import torch
from cachetools import TTLCache # Импорт для кэширования

from . import config
from . import document_parser
# Ожидаемые методы KnowledgeGraphBuilder:
# - __init__(self, uri: str, user: str, password: str, db_name: Optional[str] = None)
# - add_nodes_and_edges(self, nodes: List[Dict], edges: List[Dict]) -> None: Добавляет узлы и ребра в граф Neo4j.
# - get_article_enrichment_data(self, article_id: str) -> Optional[Dict[str, Any]]: Возвращает данные обогащения для статьи.
# - close(self) -> None: Закрывает соединение с Neo4j.
# - _clean_neo4j_database(self, graph_builder: KnowledgeGraphBuilder) -> None: (этот метод в engine.py, но он вызывает методы graph_builder._driver.session)
from ..graph_builder import KnowledgeGraphBuilder
from .document_parser import extract_graph_data_from_document

logging.basicConfig(level=config.LOGGING_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Основные импорты из текущего пакета
from .loader import load_documents
from .embeddings import JinaV3Embedding

# Импорт моделей Pydantic из родительского пакета app
try:
    from ..models import CaseDataInput
except ImportError:
    logger.error("Не удалось импортировать CaseDataInput из ..models. Проверьте структуру проекта и PYTHONPATH.", exc_info=True)
    # Если engine.py когда-либо будет запускаться как главный скрипт (что нетипично для FastAPI-приложения)
    # и PYTHONPATH будет указывать на директорию выше 'app', то можно попробовать импорт из 'app.models'
    # Но в рамках FastAPI-приложения, работающего из корня 'backend', '..models' должно работать.
    # Поднятие исключения здесь заставит обратить внимание на проблему конфигурации/структуры.
    raise RuntimeError("Критическая ошибка импорта: CaseDataInput не найден. Проверьте структуру проекта.")


def calculate_age(birth_date: date) -> int:
    """Рассчитывает возраст на текущую дату."""
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

class PensionRAG:
    """
    Класс, инкапсулирующий логику RAG для пенсионного законодательства.
    Отвечает за загрузку данных, создание/загрузку индекса,
    инициализацию моделей и обработку запросов.
    """
    def __init__(self):
        logger.info("Initializing PensionRAG engine...")
        
        self.config = config 
        
        self.llm = self._initialize_llm()
        self.embed_model = self._initialize_embedder()
        self.reranker = self._initialize_reranker()
        self.retrieval_cache = TTLCache(maxsize=100, ttl=3600) # Кэш на 100 записей, TTL 1 час
        
        # Инициализируем KnowledgeGraphBuilder один раз
        self.graph_builder: Optional[KnowledgeGraphBuilder] = None # Типизация для ясности
        try:
            self.graph_builder = KnowledgeGraphBuilder(
                uri=self.config.NEO4J_URI,
                user=self.config.NEO4J_USER,
                password=self.config.NEO4J_PASSWORD,
                db_name=self.config.NEO4J_DATABASE
            )
            logger.info("KnowledgeGraphBuilder initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize KnowledgeGraphBuilder: {e}", exc_info=True)
            # В зависимости от критичности, можно либо пробросить исключение, либо работать без графа
            # self.graph_builder = None # Уже None, но для ясности
            # raise RuntimeError(f"Could not initialize KnowledgeGraphBuilder: {e}") from e
            logger.warning("PensionRAG will operate without KnowledgeGraphBuilder due to initialization error.")

        self.index = self._load_or_create_index() # Передаем self.graph_builder внутрь
        
        logger.info("PensionRAG engine initialized successfully.")

    def _initialize_llm(self) -> Ollama:
        """Инициализирует и возвращает экземпляр LLM (Ollama)."""
        logger.debug(
            f"Initializing LLM. Model: {self.config.OLLAMA_LLM_MODEL_NAME}, "
            f"Base URL: {self.config.OLLAMA_BASE_URL}"
        )
        try:
            llm = Ollama(
                model=self.config.OLLAMA_LLM_MODEL_NAME,
                base_url=self.config.OLLAMA_BASE_URL,
                request_timeout=self.config.LLM_REQUEST_TIMEOUT,
                # Дополнительные параметры можно передать здесь, если Ollama их поддерживает
                # Например, temperature, top_p и т.д. через options или напрямую, если есть
            )
            # Попытка простого запроса для проверки доступности
            try:
                # Проверяем, есть ли у модели метод .show() или аналогичный для проверки
                # Вместо реального запроса, который может быть долгим, можно проверить доступность сервиса
                # Например, через GET запрос к base_url/api/tags, если это возможно без доп. библиотек.
                # Пока что оставим как есть, предполагая, что сама инициализация вызовет ошибку если URL недоступен.
                pass # llm.show(self.config.OLLAMA_LLM_MODEL_NAME) # Это может не работать или быть не тем
            except Exception as check_e:
                 logger.warning(f"LLM service at {self.config.OLLAMA_BASE_URL} might be available, but model check failed: {check_e}")

            logger.info(f"LLM initialized successfully. Model: {self.config.OLLAMA_LLM_MODEL_NAME}")
            return llm
        except Exception as e:
            logger.error(
                f"Failed to initialize LLM. Model: {self.config.OLLAMA_LLM_MODEL_NAME}, "
                f"Base URL: {self.config.OLLAMA_BASE_URL}, Error: {str(e)}",
                exc_info=True # Добавляем информацию о трассировке стека
            )
            # Пробрасываем исключение дальше, чтобы приложение не запустилось с неработающим LLM
            raise RuntimeError(f"Could not initialize LLM '{self.config.OLLAMA_LLM_MODEL_NAME}' at '{self.config.OLLAMA_BASE_URL}': {e}") from e

    def _initialize_embedder(self) -> JinaV3Embedding:
        """Инициализирует и возвращает модель эмбеддингов Jina V3 из Hugging Face."""
        logger.debug("Initializing Jina V3 Embeddings model...")
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Using device for Jina V3 embeddings: {device}")
        
        try:
            embed_model = JinaV3Embedding(
                model_name=self.config.HF_EMBED_MODEL_NAME,
                device=device,
            )
            logger.info(f"Embeddings model initialized: {embed_model.class_name()} (model_name={self.config.HF_EMBED_MODEL_NAME}) on {device}")
            return embed_model
        except Exception as e:
            logger.error(f"Failed to initialize JinaV3Embedding: {e}", exc_info=True)
            raise RuntimeError(f"Could not initialize JinaV3Embedding model '{self.config.HF_EMBED_MODEL_NAME}'. Error: {e}") from e

    def _initialize_reranker(self) -> Optional[CrossEncoder]:
        """Инициализирует и возвращает модель реранкера CrossEncoder."""
        logger.debug("Initializing Reranker model...")
        if not self.config.RERANKER_MODEL_NAME:
             logger.warning("Reranker model name is not configured. Skipping reranker initialization.")
             return None
        try:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"Using device for reranker: {device}")
            
            reranker_model = CrossEncoder(
                self.config.RERANKER_MODEL_NAME, 
                max_length=self.config.RERANKER_MAX_LENGTH,
                device=device,
            )
            logger.info(f"Reranker model initialized: CrossEncoder (model_name={self.config.RERANKER_MODEL_NAME}) on {device}")
            return reranker_model
        except Exception as e:
            logger.error(f"Failed to initialize Reranker model '{self.config.RERANKER_MODEL_NAME}': {e}", exc_info=True)
            logger.warning("Proceeding without reranker due to initialization error.")
            return None

    def _check_and_handle_reindex(self) -> bool:
        """
        Проверяет необходимость переиндексации на основе файла параметров.
        Удаляет старый индекс и лог при необходимости. Возвращает True, если нужна переиндексация.
        """
        logger.debug("Checking if reindexing is required...")
        current_params = self.config.get_current_index_params()
        params_log_file = self.config.PARAMS_LOG_FILE
        persist_dir = self.config.PERSIST_DIR
        force_reindex = False

        if not os.path.exists(params_log_file):
            logger.warning(f"Parameter log file {params_log_file} not found. Forcing reindex.")
            force_reindex = True
        else:
            try:
                with open(params_log_file, 'r') as f:
                    logged_params = json.load(f)
                
                if current_params != logged_params:
                    logger.warning("Index parameters have changed. Forcing reindex.")
                    changed_params = {k: (logged_params.get(k, 'N/A'), current_params.get(k, 'N/A')) 
                                     for k in set(logged_params) | set(current_params) 
                                     if logged_params.get(k) != current_params.get(k)}
                    logger.info(f"Changed parameters (old -> new): {changed_params}")
                    force_reindex = True
                else:
                    logger.info("Index parameters match logged parameters. No reindex needed based on parameters.")
            except Exception as e:
                logger.error(f"Error reading parameter log file {params_log_file}: {e}. Forcing reindex.", exc_info=True)
                force_reindex = True

        if force_reindex:
            logger.info(f"Reindexing required. Removing old index files from {persist_dir}...")
            deleted_count = 0
            index_files = glob.glob(os.path.join(persist_dir, "*store.json"))
            for f_path in index_files:
                 try:
                     logger.debug(f"Deleting {f_path}")
                     os.remove(f_path)
                     deleted_count += 1
                 except OSError as e:
                     logger.error(f"Error deleting file {f_path}: {e}", exc_info=True)
            
            deleted_log = False
            if os.path.exists(params_log_file):
                 try:
                     os.remove(params_log_file)
                     logger.debug(f"Deleting {params_log_file}")
                     deleted_log = True
                 except OSError as e:
                     logger.error(f"Error deleting parameter log file {params_log_file}: {e}", exc_info=True)
            
            total_deleted = deleted_count + (1 if deleted_log else 0)
            if total_deleted > 0:
                 logger.info(f"Deleted {total_deleted} old index-related file(s).")
            else:
                 logger.info("No old index files found to delete.")
        return force_reindex

    def _write_index_params(self):
        """Записывает текущие параметры индексации в лог-файл."""
        params_log_file = self.config.PARAMS_LOG_FILE
        persist_dir = self.config.PERSIST_DIR
        current_params = self.config.get_current_index_params()
        try:
            os.makedirs(persist_dir, exist_ok=True)
            with open(params_log_file, 'w') as f:
                json.dump(current_params, f, indent=4)
            logger.info(f"Index parameters saved to {params_log_file}")
        except Exception as e:
            logger.error(f"Error writing index parameters to {params_log_file}: {e}", exc_info=True)

    def _parse_documents(self, graph_builder_instance: Optional[KnowledgeGraphBuilder]) -> List[TextNode]:
         """Загружает документы и парсит их на узлы (TextNode), используя document_parser.
         Также извлекает данные для графа и загружает их в Neo4j, если graph_builder_instance предоставлен.
         """
         logger.info(f"Starting _parse_documents. Will use graph_builder: {graph_builder_instance is not None}")
         logger.info(f"Loading documents from {self.config.DOCUMENTS_DIR}...")
         
         raw_documents = load_documents(self.config.DOCUMENTS_DIR)
         all_parsed_nodes: List[TextNode] = []

         if not raw_documents:
             logger.warning(f"No documents found in {self.config.DOCUMENTS_DIR}. Index will be empty if it's being created.")
             return []

         logger.info(f"Loaded {len(raw_documents)} raw documents for parsing.")

         for i, doc in enumerate(raw_documents):
             doc_file_name = doc.metadata.get("file_name", f"unknown_doc_{i}")
             logger.debug(f"Processing raw document: {doc_file_name}")
             
             try:
                 parsed_nodes_from_doc = document_parser.parse_document_hierarchical(doc)
                 logger.info(f"Successfully parsed {len(parsed_nodes_from_doc)} TextNodes from {doc_file_name}.")
                 all_parsed_nodes.extend(parsed_nodes_from_doc)
             except Exception as e:
                 logger.error(f"Error parsing document {doc_file_name} with hierarchical parser: {e}", exc_info=True)
                 continue

             if graph_builder_instance:
                 logger.info(f"Extracting graph data for Neo4j from document: {doc_file_name}")
                 try:
                     nodes_data, edges_data = extract_graph_data_from_document(
                         parsed_nodes=parsed_nodes_from_doc,
                         doc_metadata=doc.metadata,
                         pension_type_map=self.config.PENSION_KEYWORD_MAP,
                         pension_type_filters=self.config.PENSION_TYPE_FILTERS
                     )
                     
                     if nodes_data or edges_data:
                         logger.debug(f"Extracted {len(nodes_data)} nodes and {len(edges_data)} edges for graph from {doc_file_name}. Adding to Neo4j...")
                         graph_builder_instance.add_nodes_and_edges(nodes_data, edges_data)
                         logger.info(f"Successfully added graph data from {doc_file_name} to Neo4j.")
                     else:
                         logger.info(f"No graph nodes or edges extracted from {doc_file_name}.")
                 except Exception as e:
                     logger.error(f"Error extracting/adding graph data for {doc_file_name}: {e}", exc_info=True)
             else:
                 logger.debug(f"Graph builder instance is None, skipping graph data extraction for {doc_file_name}.")
         
         logger.info(f"Finished parsing all documents. Total TextNodes created: {len(all_parsed_nodes)}")
         return all_parsed_nodes

    def _load_or_create_index(self) -> VectorStoreIndex:
        """
        Загружает существующий индекс LlamaIndex из хранилища или создает новый,
        если он не найден, устарел или требуется переиндексация.
        Использует self.graph_builder, если он доступен.
        """
        persist_dir = self.config.PERSIST_DIR
        force_reindex = self._check_and_handle_reindex()
        # graph_builder_instance больше не создается здесь локально

        if not force_reindex and (
           os.path.exists(os.path.join(persist_dir, "docstore.json")) and 
           os.path.exists(os.path.join(persist_dir, "default__vector_store.json"))
        ):
            logger.info(f"Loading existing LlamaIndex index from {persist_dir}...")
            try:
                storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
                index = load_index_from_storage(
                    storage_context, 
                    embed_model=self.embed_model
                )
                logger.info("LlamaIndex Index loaded successfully from storage.")
                return index
            except Exception as e:
                logger.error(f"Failed to load LlamaIndex index from storage: {e}. Will attempt to re-create.", exc_info=True)
                self._check_and_handle_reindex() 
                force_reindex = True

        logger.info("Creating new LlamaIndex index...")
        try:
            # graph_builder_instance уже self.graph_builder
            if self.graph_builder and force_reindex:
                logger.info("Cleaning Neo4j database before rebuilding the graph...")
                self._clean_neo4j_database(self.graph_builder) # Используем self.graph_builder
                logger.info("Neo4j database cleaned successfully.")
            
            nodes = self._parse_documents(graph_builder_instance=self.graph_builder) # Используем self.graph_builder
            
            if not nodes:
                logger.warning("No nodes were parsed from documents. Cannot create LlamaIndex index.")
                # Закрытие graph_builder здесь не нужно, т.к. он управляется жизненным циклом PensionRAG
                raise RuntimeError("Cannot create index: No text nodes parsed from documents.")

            logger.info(f"Building LlamaIndex VectorStoreIndex with {len(nodes)} TextNode(s).")
            index = VectorStoreIndex(
                nodes, 
                embed_model=self.embed_model,
            )
            logger.info("LlamaIndex VectorStoreIndex built successfully.")
            
            logger.debug(f"Persisting LlamaIndex index to {persist_dir}...")
            os.makedirs(persist_dir, exist_ok=True)
            index.storage_context.persist(persist_dir=persist_dir)
            logger.info(f"LlamaIndex Index persisted to {persist_dir}.")
            
            self._write_index_params()
            
            return index
        except Exception as e:
            logger.error(f"Fatal error during LlamaIndex index creation: {e}", exc_info=True)
            # Закрытие self.graph_builder здесь не требуется, это делается при уничтожении PensionRAG
            raise RuntimeError(f"Could not create LlamaIndex index: {e}") from e

    def _clean_neo4j_database(self, graph_builder: KnowledgeGraphBuilder) -> None:
        """
        Очищает базу данных Neo4j перед созданием нового графа.
        """
        if not graph_builder or not hasattr(graph_builder, '_driver'):
            logger.error("Cannot clean Neo4j database: graph_builder not initialized properly.")
            return
        
        try:
            with graph_builder._driver.session(database=graph_builder._db_name) as session:
                session.run("MATCH ()-[r]-() DELETE r")
                logger.debug("All relationships deleted from Neo4j database.")
                
                session.run("MATCH (n) DELETE n")
                logger.debug("All nodes deleted from Neo4j database.")
                
                logger.info("Neo4j database successfully cleaned.")
        except Exception as e:
            logger.error(f"Error cleaning Neo4j database: {e}", exc_info=True)
            logger.warning("Continuing with graph building despite database cleaning error.")

    def _get_retriever(self, filters: Optional[List[MetadataFilter]] = None, similarity_top_k: Optional[int] = None) -> BaseRetriever:
         """Создает и возвращает ретривер для индекса с опциональными фильтрами."""
         top_k = similarity_top_k if similarity_top_k is not None else self.config.INITIAL_RETRIEVAL_TOP_K
         logger.debug(f"Creating retriever with similarity_top_k={top_k} and filters={'yes' if filters else 'no'}")
         return self.index.as_retriever(
             similarity_top_k=top_k,
             filters=filters
         )
         
    def _apply_filters(self, query_bundle: QueryBundle, pension_type: Optional[str]) -> Tuple[List[MetadataFilter], bool]:
        """
        Определяет фильтры метаданных на основе типа пенсии и текста запроса.
        Возвращает (список фильтров, флаг применения фильтров).
        """
       
        if not pension_type or pension_type not in self.config.PENSION_TYPE_FILTERS:
            logger.debug("No valid pension type provided or found in config, skipping filters.")
            return [], False

        filter_config = self.config.PENSION_TYPE_FILTERS[pension_type]
        query_text = query_bundle.query_str.lower()
        condition_keywords = filter_config.get('condition_keywords', [])
        
        apply = True
        if condition_keywords:
             if not any(keyword in query_text for keyword in condition_keywords):
                 logger.debug(f"Query does not contain required keywords {condition_keywords} for '{pension_type}', skipping filters.")
                 apply = False

        if apply and filter_config.get('filters'):
            metadata_filter_list = [
                ExactMatchFilter(key=f['key'], value=f['value']) 
                for f in filter_config['filters']
            ]
            logger.info(f"Applying metadata filters for pension type '{pension_type}': {filter_config['filters']}")
            return MetadataFilters(filters=metadata_filter_list), True
        else:
             return [], False

    def _perform_actual_retrieval(self, query_bundle: QueryBundle, pension_type: Optional[str], effective_config: Dict) -> List[NodeWithScore]:
        """Этот метод содержит оригинальную логику _retrieve_nodes."""
        logger.info(f"Performing actual retrieval for query: '{query_bundle.query_str[:100]}...'")
        target_filters, filters_applied = self._apply_filters(query_bundle, pension_type)
        
        filtered_nodes: List[NodeWithScore] = []
        filtered_top_k = effective_config['FILTERED_RETRIEVAL_TOP_K']
        initial_top_k = effective_config['INITIAL_RETRIEVAL_TOP_K']

        if filters_applied:
            try:
                logger.debug(f"Creating filtered retriever with similarity_top_k={filtered_top_k} and filters=yes")
                filtered_retriever = self._get_retriever(filters=target_filters, similarity_top_k=filtered_top_k)
                filtered_nodes = filtered_retriever.retrieve(query_bundle)
                logger.debug(f"Retrieved {len(filtered_nodes)} nodes with filters (asked for {filtered_top_k}).")
                for node in filtered_nodes:
                     node.metadata['retrieval_score'] = node.score
            except Exception as e:
                 logger.error(f"Error retrieving nodes with filters: {e}", exc_info=True)
                 filtered_nodes = []
        else:
            logger.debug("Filters were not applied for this query.")
        
        logger.debug(f"Creating base retriever with similarity_top_k={initial_top_k} and filters=no")
        base_retriever = self._get_retriever(filters=None, similarity_top_k=initial_top_k)
        base_nodes = base_retriever.retrieve(query_bundle)
        logger.debug(f"Retrieved {len(base_nodes)} base nodes (asked for {initial_top_k}).")
        for node in base_nodes:
             node.metadata['retrieval_score'] = node.score 
        
        combined_nodes_dict: Dict[str, NodeWithScore] = {node.node.node_id: node for node in filtered_nodes}
        added_from_base = 0
        for node in base_nodes:
            if node.node.node_id not in combined_nodes_dict:
                combined_nodes_dict[node.node.node_id] = node
                added_from_base += 1
        
        combined_nodes = list(combined_nodes_dict.values())
        combined_nodes.sort(key=lambda x: x.metadata.get('retrieval_score', x.score), reverse=True)
        
        logger.info(f"Combined nodes: {len(combined_nodes)} (priority given to {len(filtered_nodes)} filtered nodes, added {added_from_base} from base search)")
        
        return combined_nodes

    def _retrieve_nodes(self, query_bundle: QueryBundle, pension_type: Optional[str], effective_config: Dict) -> List[NodeWithScore]:
        """Выполняет поиск узлов (retrieval) с использованием кэша."""
        # Ключ кэша должен учитывать все параметры, влияющие на результат ретривинга
        cache_key_parts = [
            query_bundle.query_str,
            pension_type,
            effective_config.get('INITIAL_RETRIEVAL_TOP_K'),
            effective_config.get('FILTERED_RETRIEVAL_TOP_K')
        ]
        # Добавляем информацию о фильтрах, если они применялись, т.к. это меняет результат
        # Простой способ - сериализовать фильтры, но это может быть громоздко.
        # Пока ограничимся типом пенсии, который определяет фильтры.
        cache_key = tuple(cache_key_parts)
                
        if cache_key in self.retrieval_cache:
            logger.info(f"Returning CACHED retrieval results for query: '{query_bundle.query_str[:50]}...', type: {pension_type}")
            return self.retrieval_cache[cache_key]
        
        logger.info(f"NO CACHE - Performing retrieval for query: '{query_bundle.query_str[:50]}...', type: {pension_type}")
        nodes = self._perform_actual_retrieval(query_bundle, pension_type, effective_config)
        self.retrieval_cache[cache_key] = nodes
        return nodes

    def _rerank_nodes(self, query_bundle: QueryBundle, nodes: List[NodeWithScore], effective_config: Dict) -> Tuple[List[NodeWithScore], float]:
        """Применяет реранкер (если доступен) к узлам-кандидатам.
        Возвращает кортеж: (список лучших N узлов, скор уверенности, основанный на топ-1 узле).
        """
        reranker_top_n = effective_config['RERANKER_TOP_N']

        if not self.reranker or not nodes:
            logger.debug("Reranker not available or no nodes to rerank. Returning top N initial nodes with 0.0 score.")
            initial_top_nodes = nodes[:reranker_top_n]
            return initial_top_nodes, 0.0

        logger.info(f"Reranking {len(nodes)} nodes...")
        query_text = query_bundle.query_str
        passages = [node.get_content() for node in nodes]
        rerank_pairs = [[query_text, passage] for passage in passages]
        
        try:
            scores = self.reranker.predict(rerank_pairs, show_progress_bar=False)
            
            for node, score in zip(nodes, scores):
                node.metadata['rerank_score'] = float(score) 
                node.score = float(score)

            nodes.sort(key=lambda x: x.score, reverse=True)
            reranked_nodes = nodes[:reranker_top_n]
            logger.info(f"Reranking complete. Selected top {len(reranked_nodes)} nodes.")
            
            logger.info("--- Top nodes selected for LLM context: ---")
            for i, node in enumerate(reranked_nodes):
                metadata = node.metadata
                log_entry = (
                    f"  {i+1}. Score: {node.score:.4f}, "
                    f"File: {metadata.get('file_name', '?')}, "
                    f"Article: {metadata.get('article', '?')}, "
                    f"Header: {metadata.get('header', '?')} "
                    f"(Node ID: {node.node.node_id})"
                )
                logger.info(log_entry)
            
            confidence_score = 0.0
            if reranked_nodes:
                confidence_score = float(reranked_nodes[0].score)
                logger.info(f"Using top-1 reranked score as confidence score: {confidence_score:.4f}")
            else:
                 logger.warning("No nodes left after reranking, confidence score is 0.0")
            
            return reranked_nodes, confidence_score 
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}", exc_info=True)
            logger.warning("Reranking failed. Returning top N nodes based on initial retrieval scores.")
            nodes.sort(key=lambda x: x.metadata.get('retrieval_score', x.score), reverse=True) 
            return nodes[:reranker_top_n], 0.0


    def _build_prompt(self, query_text: str, context_nodes: List[NodeWithScore], case_data: CaseDataInput, disability_info: Optional[dict]) -> str:
        """Формирует финальный промпт для LLM, используя метаданные и структурированные данные."""
        logger.debug("Building final prompt for LLM...")
        
        context_parts = []
        sources_summary = set()
        for i, node_with_score in enumerate(context_nodes):
            node = node_with_score.node
            content = node.get_content()
            metadata = node.metadata
            graph_enrichment = metadata.get('graph_enrichment')

            source_desc_parts = [
                f"Источник {i+1}: {metadata.get('file_name', 'Неизвестный файл')}"
            ]
            article_number_text = metadata.get('article_meta', {}).get('number_text') 
            if not article_number_text:
                article_number_text = metadata.get('article')

            if article_number_text:
                source_desc_parts.append(f"Статья {article_number_text}")
            
            article_title_from_graph = None
            if graph_enrichment and graph_enrichment.get('article_title'):
                article_title_from_graph = graph_enrichment['article_title']
                source_desc_parts.append(f'"{article_title_from_graph}"')

            related_pension_types_from_graph = []
            if graph_enrichment and graph_enrichment.get('related_pension_types'):
                related_pension_types_from_graph = graph_enrichment['related_pension_types']
                if related_pension_types_from_graph:
                    source_desc_parts.append(f"(Относится к типам пенсий: {', '.join(related_pension_types_from_graph)})")

            if metadata.get('paragraph'):
                source_desc_parts.append(f"Пункт {metadata.get('paragraph')}")
            if metadata.get('subparagraph'):
                 source_desc_parts.append(f"Подпункт {metadata.get('subparagraph')}")
            
            source_desc = ", ".join(source_desc_parts)
            
            enrichment_details_str = ""
            if graph_enrichment:
                conditions = graph_enrichment.get('conditions', [])
                if conditions:
                    conditions_strs = []
                    for cond in conditions:
                        cond_desc = cond.get("condition", "н/д")
                        cond_val = cond.get("value", "н/д")
                        cond_pt = cond.get("pension_type", "н/д")
                        conditions_strs.append(f"  - Условие: {cond_desc}, Значение: {cond_val} (для типа пенсии: {cond_pt})")
                    if conditions_strs:
                        enrichment_details_str += "\nДополнительная информация из графа знаний для данной статьи:\nОпределенные условия:\n" + "\n".join(conditions_strs)
            
            context_parts.append(f"{source_desc}\n{content}{enrichment_details_str}")
            
            summary_source_name = metadata.get('file_name', 'Неизвестный файл')
            if article_number_text:
                summary_source_name += f" (Статья {article_number_text}"
                if article_title_from_graph:
                    summary_source_name += f": {article_title_from_graph}"
                summary_source_name += ")"
            sources_summary.add(summary_source_name)

        context_str = "\n\n---\n\n".join(context_parts)
        sources_str = ", ".join(sorted(list(sources_summary))) or "Не указаны"

        disability_str = ""
        if disability_info:
            group_code = disability_info.get("group")
            group_name = self.config.DISABILITY_GROUP_MAP.get(str(group_code), f"Группа {group_code}" if group_code else "не указана")
            reason = disability_info.get("reason", "не указана")
            disability_str = f"\nДополнительная информация: Инвалидность {group_name}, причина - {reason}."

        current_date_str = datetime.now().strftime("%d.%m.%Y")
        
        pd = case_data.personal_data
        we = case_data.work_experience
        calculated_age_val = calculate_age(pd.birth_date)
        pension_type_str = self.config.PENSION_TYPE_MAP.get(case_data.pension_type, case_data.pension_type)
        applicant_ipk_value = case_data.pension_points 

        prompt = f"""
            Запрос на правовой анализ пенсионного случая в соответствии с законодательством РФ
            **Актуальность данных на**: {current_date_str}

            **Сведения о заявителе:**
            - Описание ситуации: {query_text}{disability_str}
            
            **Ключевые параметры заявителя (для анализа):**
            - Возраст на {current_date_str}: {calculated_age_val}
            - Общий стаж (указанный): {we.total_years}
            - ИПК (указанный): {applicant_ipk_value} 
            - Категория запрашиваемой пенсии: {pension_type_str}
            
            **Нормативная база (основные источники контекста):** {sources_str}
            --- Контекст из базы знаний --- 
            {context_str}
            --- Конец контекста ---

            **Порядок обработки запроса:**
            1. Установление правовых оснований:
            • Определить соответствие случая статьям законодательства из предоставленного контекста (с указанием конкретных пунктов)
            • Выявить наличие/отсутствие обязательных критериев назначения

            2. Анализ условий назначения:
            • Возрастные требования: Сравни возраст заявителя (из 'Ключевые параметры заявителя') с нормативным возрастом (из контекста) на {current_date_str}.
            • Страховой стаж: Сравни общий стаж заявителя (из 'Ключевые параметры заявителя') с минимальным требуемым стажем (из контекста) на {current_date_str}.
            • Величина ИПК: **ОБЯЗАТЕЛЬНО** используй значение ИПК заявителя из раздела 'Ключевые параметры заявителя' ({applicant_ipk_value}). Сравни это значение с пороговым значением ИПК из контекста (обычно 30 для Статьи 8 ФЗ-400). Четко укажи **оба** значения (заявителя и требуемое) при сравнении и сделай вывод о соответствии.
            • Специальные условия (для льготных категорий): Проверь, применимы ли льготы на основе описания и контекста.

            3. Требуемые документы:
            • Установленный перечень по выявленным основаниям
            • Отсутствующие в описании данные (справки, подтверждения)

            **Требования к ответу:**
            ✓ Ссылки только на предоставленный контекст (например, "Согласно {{источник}}, Статья X..."). Не ссылайся на статьи или законы, которых нет в контексте.
            ✓ Отказ от интерпретаций вне предоставленного контекста
            ✓ Четкое разделение выводов на:
            - Удовлетворяющие условия (со ссылкой на норму права из контекста)
            - Неудовлетворяющие условия (с указанием причины)
            - Недостающие сведения (перечень документов/справок)
            ✓ Добавь в самый конец ответа **обязательную** фразу в одной из формулировок: "ИТОГ: СООТВЕТСТВУЕТ" или "ИТОГ: НЕ СООТВЕТСТВУЕТ".

            **Примечание:** 
            Ответ подлежит оформлению в соответствии с Приказом Минтруда № 958н от 28.12.2022 
            "Об утверждении Административного регламента...". Конфиденциальная информация не подлежит разглашению.

            **Важно:**
            - Отвечай только на основе предоставленного контекста.
            - Не придумывай информацию.
            - Будь кратким и по существу.
            - Отвечай на русском языке.
            - Перепроверяй все факты и цифры. Например, возраст, стаж, ИПК ({applicant_ipk_value}) и т.д. Человек не может быть старше 100 лет, иметь стаж работы больше чем его возраст.
            """
        logger.debug(f"Generated prompt (first 200 chars): {prompt[:200]}...")
        return prompt


    def query(self, 
              case_description: str, 
              pension_type: Optional[str] = None, 
              disability_info: Optional[dict] = None,
              case_data: Optional[CaseDataInput] = None,
              config_override: Optional[dict] = None
              ) -> Tuple[str, float]:
        """
        Обрабатывает запрос пользователя, включая ретривинг, реранкинг и генерацию ответа.

        Args:
            case_description (str): Описание случая или вопрос пользователя.
            pension_type (Optional[str]): Тип пенсии, если известен.
            disability_info (Optional[dict]): Информация об инвалидности.
            case_data (Optional[CaseDataInput]): Дополнительные данные о случае.
            config_override (Optional[dict]): Позволяет переопределить параметры конфигурации для этого запроса.

        Returns:
            Tuple[str, float]: Сгенерированный ответ и оценка уверенности.
        """
        effective_config = {
            'INITIAL_RETRIEVAL_TOP_K': self.config.INITIAL_RETRIEVAL_TOP_K,
            'FILTERED_RETRIEVAL_TOP_K': self.config.FILTERED_RETRIEVAL_TOP_K,
            'RERANKER_TOP_N': self.config.RERANKER_TOP_N
        }

        if config_override:
            logger.info(f"Applying config override: {config_override}")
            effective_config.update(config_override)
            # Валидация и корректировка переопределенных значений
            if effective_config['FILTERED_RETRIEVAL_TOP_K'] > effective_config['INITIAL_RETRIEVAL_TOP_K']:
                logger.warning(f"FILTERED_RETRIEVAL_TOP_K ({effective_config['FILTERED_RETRIEVAL_TOP_K']}) cannot be greater than INITIAL_RETRIEVAL_TOP_K ({effective_config['INITIAL_RETRIEVAL_TOP_K']}). Adjusting...")
                effective_config['FILTERED_RETRIEVAL_TOP_K'] = effective_config['INITIAL_RETRIEVAL_TOP_K']
            
            if effective_config['RERANKER_TOP_N'] > effective_config['INITIAL_RETRIEVAL_TOP_K']:
                 logger.warning(f"RERANKER_TOP_N ({effective_config['RERANKER_TOP_N']}) cannot be greater than INITIAL_RETRIEVAL_TOP_K ({effective_config['INITIAL_RETRIEVAL_TOP_K']}). Adjusting...")
                 effective_config['RERANKER_TOP_N'] = effective_config['INITIAL_RETRIEVAL_TOP_K']
        
        logger.info(f"Effective RAG params: Initial K={effective_config['INITIAL_RETRIEVAL_TOP_K']}, Filtered K={effective_config['FILTERED_RETRIEVAL_TOP_K']}, Reranker N={effective_config['RERANKER_TOP_N']}")

        if not case_description:
            logger.warning("Query text is empty. Returning default message.")
            return "Пожалуйста, предоставьте описание вашего случая или вопрос.", 0.0

        query_bundle = QueryBundle(case_description)
        confidence_score = 0.0

        try:
            logger.debug(f"Starting retrieval for query: '{query_bundle.query_str[:100]}...'")
            retrieved_nodes = self._retrieve_nodes(query_bundle, pension_type=pension_type, effective_config=effective_config)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes initially.")

            if self.reranker:
                logger.debug(f"Reranking {len(retrieved_nodes)} nodes...")
                ranked_nodes, confidence_score_from_reranker = self._rerank_nodes(query_bundle, retrieved_nodes, effective_config=effective_config)
                logger.info(f"Reranked to {len(ranked_nodes)} nodes. Confidence score from reranker: {confidence_score_from_reranker:.4f}")
                confidence_score = confidence_score_from_reranker
            else:
                logger.info("Reranker not available. Using top N nodes from retrieval without reranking.")
                ranked_nodes = retrieved_nodes[:effective_config['RERANKER_TOP_N']]
                if ranked_nodes and all(hasattr(n, 'score') and n.score is not None for n in ranked_nodes):
                    pass
                else:
                    logger.debug("No scores available from retrieved nodes to calculate average, or no nodes retrieved.")

            if not ranked_nodes:
                 logger.warning(f"No relevant documents found for query: '{query_bundle.query_str[:100]}...'")
                 return "К сожалению, я не смог найти релевантную информацию по вашему запросу в базе знаний. Попробуйте переформулировать вопрос.", 0.0

            logger.info(f"Enriching {len(ranked_nodes)} nodes with graph data...")
            enriched_nodes = self._enrich_nodes_with_graph_data(ranked_nodes)
            logger.info("Node enrichment complete.")

            if case_data is None:
                logger.warning("CaseDataInput is None. Cannot build prompt without case_data.")
                return "Ошибка: Отсутствуют данные о деле (case_data). Невозможно сформировать ответ.", 0.0
            
            logger.debug("Building prompt with enriched context...")
            final_prompt = self._build_prompt(case_description, enriched_nodes, case_data, disability_info)
            logger.debug(f"Final prompt (first 200 chars): {final_prompt[:200]}...")

            # Добавляем собранный текст промпта в QueryBundle для возможного использования в ретривере или реранкере, если они его ожидают
            query_bundle = QueryBundle(query_str=final_prompt)

            logger.debug("Sending prompt to LLM...")
            response = self.llm.complete(final_prompt)
            
            llm_output_text = str(response)
            logger.info("Received response from LLM.")
            logger.debug(f"LLM Response (raw, first 500 chars): {llm_output_text[:500]}...")

            cleaned_response_text = re.sub(r"<think>.*?</think>\s*", "", llm_output_text, flags=re.DOTALL | re.IGNORECASE).strip()

            # Если нужно сохранить "мысли" для логов, но не показывать пользователю:
            match = re.search(r"<think>(.*?)</think>", llm_output_text, flags=re.DOTALL | re.IGNORECASE)
            if match:
                thoughts = match.group(1).strip()
                logger.debug(f"LLM Thoughts:\n{thoughts}")
            # cleaned_response_text уже определен выше и не требует повторного присвоения, если thoughts нужны только для лога

            logger.debug(f"LLM Response (cleaned, first 100 chars): {cleaned_response_text[:100]}...")

            final_confidence_score = confidence_score # Используем confidence_score, который обновляется в блоке reranker

            return cleaned_response_text, final_confidence_score

        except Exception as e:
            logger.error(f"Error during query processing: {e}", exc_info=True)
            return f"Произошла ошибка при обработке вашего запроса: {e}. Пожалуйста, попробуйте позже.", 0.0
        finally:
            pass


    def _enrich_nodes_with_graph_data(self, nodes: List[NodeWithScore]) -> List[NodeWithScore]:
        """Enriches nodes with data from the knowledge graph."""
        if not nodes:
            logger.warning("No nodes provided for enrichment.")
            return []

        if not self.graph_builder:
            logger.warning("KnowledgeGraphBuilder not available. Skipping graph enrichment.")
            return nodes # Возвращаем исходные узлы, если нет графа

        logger.info(f"Starting graph data enrichment for {len(nodes)} nodes using self.graph_builder...")
        # graph_builder больше не создается и не закрывается здесь
        enriched_count = 0
        missing_article_id_count = 0
        no_data_found_count = 0
        
        try:
            enriched_nodes = []
            
            for idx, node_with_score in enumerate(nodes):
                text_node = node_with_score.node
                article_id_for_graph = text_node.metadata.get('canonical_article_id') 
                
                if article_id_for_graph:
                    logger.debug(f"Node {idx+1}/{len(nodes)}: Querying graph for enrichment with article_id: {article_id_for_graph}")
                    try:
                        enrichment_data = self.graph_builder.get_article_enrichment_data(article_id_for_graph)
                        if enrichment_data:
                            text_node.metadata['graph_enrichment'] = enrichment_data
                            logger.debug(f"Node {idx+1}/{len(nodes)}: Enriched with data for article_id {article_id_for_graph}: {enrichment_data}")
                            enriched_count += 1
                        else:
                            logger.debug(f"Node {idx+1}/{len(nodes)}: No enrichment data found in graph for article_id: {article_id_for_graph}")
                            no_data_found_count += 1
                    except Exception as node_e:
                        logger.error(f"Error enriching node {idx+1} with article_id {article_id_for_graph}: {node_e}")
                        no_data_found_count += 1
                else:
                    logger.debug(f"Node {idx+1}/{len(nodes)}: No canonical_article_id found in metadata for node {text_node.node_id}")
                    missing_article_id_count += 1
                
                enriched_nodes.append(node_with_score)
            
            logger.info(f"Graph enrichment complete. Stats: {enriched_count} nodes enriched, "
                        f"{missing_article_id_count} nodes without article_id, "
                        f"{no_data_found_count} nodes without enrichment data in graph.")
            return enriched_nodes
            
        except Exception as e:
            logger.error(f"Error during node enrichment with graph data: {e}", exc_info=True)
            logger.warning("Continuing without graph enrichment due to error.")
            return nodes

# --- Пример использования (для локального тестирования) ---
if __name__ == '__main__':
    logging.getLogger(__name__).setLevel(logging.DEBUG)
         
    logger.info("="*20 + " Starting PensionRAG engine test " + "="*20)
    try:
        # Создаем экземпляр двигателя. Инициализация и загрузка/создание индекса происходят здесь.
        rag_engine = PensionRAG() 
    except Exception as e:
        logger.exception("An error occurred during the PensionRAG test run.")
        print(f"\n--- FATAL ERROR ---")
        print(f"An critical error occurred during initialization or querying: {e}")
        
    logger.info("="*20 + " PensionRAG engine test finished " + "="*20) 