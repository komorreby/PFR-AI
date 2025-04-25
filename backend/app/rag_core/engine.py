# backend/app/rag_core/engine.py
import os
import glob
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Document,
    QueryBundle
)
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.retrievers import BaseRetriever
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core.vector_stores import MetadataFilter, ExactMatchFilter
from sentence_transformers import CrossEncoder
import torch

# Сначала импортируем config, так как он нужен для настройки логгера
from . import config
# Затем импортируем остальные компоненты
from . import document_parser # Используем новый модуль парсера

# Настройка логирования
# Настраиваем базовый конфиг, чтобы логгер был доступен сразу
logging.basicConfig(level=config.LOGGING_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Локальные импорты (теперь можно импортировать после логгера и config)
try:
    from .loader import load_documents
    from .embeddings import JinaV3Embedding
except ImportError as e:
    # Эта секция предназначена для возможности запуска engine.py напрямую как скрипта.
    # Если ошибка возникает при запуске основного приложения (main.py), 
    # скорее всего, проблема в зависимостях для embeddings.py или loader.py.
    # Проверьте установку: pip install sentence-transformers torch einops "numpy<2" transformers unstructured[local-inference]
    logger.error(f"Ошибка импорта в engine.py (возможно, запуск как скрипт или проблема зависимостей): {e}", exc_info=True)
    # Попытка импорта для случая запуска как скрипта
    try:
        from loader import load_documents
        from embeddings import JinaV3Embedding
        logger.warning("Импорты для запуска engine.py как скрипта выполнены.")
    except ModuleNotFoundError:
        logger.critical("Не удалось выполнить импорты ни как часть пакета, ни как скрипт. Проверьте структуру проекта и зависимости.")
        raise

# # --- Старое место настройки логгера --- 
# # Настройка логирования
# # Настраиваем базовый конфиг, чтобы логгер был доступен сразу
# logging.basicConfig(level=config.LOGGING_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)


class PensionRAG:
    """
    Класс, инкапсулирующий логику RAG для пенсионного законодательства.
    Отвечает за загрузку данных, создание/загрузку индекса,
    инициализацию моделей и обработку запросов.
    """
    def __init__(self):
        logger.info("Initializing PensionRAG engine...")
        
        # 1. Загружаем конфигурацию (через импортированный модуль)
        self.config = config 
        # Устанавливаем уровень логирования из конфига динамически (если нужно переопределить basicConfig)
        # logging.getLogger().setLevel(self.config.LOGGING_LEVEL) 
        
        # 2. Инициализируем компоненты
        self.llm = self._initialize_llm()
        self.embed_model = self._initialize_embedder()
        self.reranker_model = self._initialize_reranker()
        
        # 3. Загружаем или создаем индекс
        self.index = self._load_or_create_index()
        
        logger.info("PensionRAG engine initialized successfully.")

    def _initialize_llm(self) -> Ollama:
        """Инициализирует и возвращает LLM модель Ollama."""
        logger.debug("Initializing LLM...")
        try:
            llm = Ollama(
                model=self.config.OLLAMA_LLM_MODEL_NAME,
                base_url=self.config.OLLAMA_BASE_URL,
                request_timeout=self.config.LLM_REQUEST_TIMEOUT,
            )
            # Опционально: проверка соединения/доступности модели
            # llm.complete("Test prompt") 
            logger.info(f"LLM initialized: Ollama (model={self.config.OLLAMA_LLM_MODEL_NAME}, base_url={self.config.OLLAMA_BASE_URL})")
            return llm
        except Exception as e:
            logger.error(f"Failed to initialize Ollama LLM: {e}", exc_info=True)
            raise RuntimeError(f"Could not initialize LLM. Ensure Ollama is running and model '{self.config.OLLAMA_LLM_MODEL_NAME}' is available. Error: {e}") from e

    def _initialize_embedder(self) -> JinaV3Embedding:
        """Инициализирует и возвращает модель эмбеддингов Jina V3 из Hugging Face."""
        logger.debug("Initializing Jina V3 Embeddings model...")
        # Определяем устройство (предпочитаем GPU, если доступно)
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Using device for Jina V3 embeddings: {device}")
        
        try:
            # Используем наш кастомный класс
            embed_model = JinaV3Embedding(
                model_name=self.config.HF_EMBED_MODEL_NAME,
                device=device, # Передаем выбранное устройство
                # embed_batch_size можно взять из config, если нужно настроить
                # callback_manager=... # Если используется
            )
            # embed_model инициализируется и логирует внутри своего __init__
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
                # Можно добавить trust_remote_code=True, если модель требует
            )
            logger.info(f"Reranker model initialized: CrossEncoder (model_name={self.config.RERANKER_MODEL_NAME}) on {device}")
            return reranker_model
        except Exception as e:
            logger.error(f"Failed to initialize Reranker model '{self.config.RERANKER_MODEL_NAME}': {e}", exc_info=True)
            logger.warning("Proceeding without reranker due to initialization error.")
            return None # Реранкер опционален

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
            # Удаляем все .json файлы, связанные с LlamaIndex хранилищами
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

    def _parse_documents(self) -> List[TextNode]:
         """Загружает документы и парсит их на узлы (TextNode), используя document_parser."""
         logger.info(f"Loading documents from {self.config.DOCUMENTS_DIR}...")
         try:
             # Используем функцию загрузки из loader.py
             raw_documents = load_documents(self.config.DOCUMENTS_DIR) 
             if not raw_documents:
                  logger.warning(f"No documents found in {self.config.DOCUMENTS_DIR}.")
                  return []
             logger.info(f"Loaded {len(raw_documents)} raw document(s).")
         except Exception as e:
             logger.error(f"Failed to load documents: {e}", exc_info=True)
             raise RuntimeError(f"Could not load documents from {self.config.DOCUMENTS_DIR}: {e}") from e

         all_nodes = []
         logger.info("Parsing documents into nodes using hierarchical parser...")
         for doc in raw_documents:
             try:
                 # Используем функцию из модуля document_parser
                 nodes_for_doc = document_parser.parse_document_hierarchical(doc)
                 all_nodes.extend(nodes_for_doc)
             except Exception as e:
                 file_name = doc.metadata.get("file_name", "unknown")
                 logger.error(f"Failed to parse document {file_name}: {e}", exc_info=True)
                 # Решаем, пропустить ли документ или остановить процесс
                 # continue 
                 raise RuntimeError(f"Failed to parse document {file_name}: {e}") from e

         logger.info(f"Total nodes parsed: {len(all_nodes)}. Parser version: {self.config.METADATA_PARSER_VERSION}")
         if not all_nodes:
              logger.warning("No nodes were generated after parsing all documents.")
         return all_nodes

    def _load_or_create_index(self) -> VectorStoreIndex:
        """
        Загружает существующий индекс или создает новый.
        Использует _check_and_handle_reindex для определения необходимости пересоздания.
        Важно: Передает модель эмбеддингов при загрузке и создании.
        """
        persist_dir = self.config.PERSIST_DIR
        needs_reindex = self._check_and_handle_reindex()

        # Попытка загрузки, если не требуется принудительная переиндексация и папка существует
        if not needs_reindex and os.path.exists(persist_dir) and os.path.exists(os.path.join(persist_dir, "docstore.json")):
            try:
                logger.info(f"Attempting to load existing index from {persist_dir}...")
                storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
                # ! ВАЖНО: Передаем текущую модель эмбеддингов при загрузке !
                index = load_index_from_storage(
                    storage_context,
                    embed_model=self.embed_model 
                )
                logger.info("Existing index loaded successfully.")
                # Дополнительная проверка: убедиться, что модель в загруженном индексе совпадает
                # (LlamaIndex может не проверять это строго при загрузке)
                # if hasattr(index.embed_model, 'model_name') and index.embed_model.model_name != self.embed_model.model_name:
                #     logger.warning(f"Loaded index uses different embedding model ('{index.embed_model.model_name}') than configured ('{self.embed_model.model_name}'). Rebuilding index.")
                #     needs_reindex = True # Форсируем перестроение, если модель не совпадает
                # else:
                #     return index # Модель совпадает, возвращаем загруженный индекс
                return index # Пока просто возвращаем, надеясь, что LlamaIndex обработает

            except Exception as e:
                logger.warning(f"Failed to load index from {persist_dir}: {e}. Will rebuild index.", exc_info=True)
                # Если загрузка не удалась, удаляем потенциально поврежденные файлы и форсируем переиндексацию
                if not needs_reindex: # Проверяем, чтобы не вызывать дважды подряд
                    self._check_and_handle_reindex() # Вызываем еще раз, т.к. ошибка могла быть из-за несовместимости
                needs_reindex = True # Устанавливаем флаг для перехода к созданию
        
        # Создание нового индекса
        logger.info("Creating new index...")
        try:
            nodes = self._parse_documents()
            if not nodes:
                logger.error("No nodes were parsed from documents. Cannot create index.")
                # Возможно, стоит вернуть пустой индекс или поднять исключение
                raise RuntimeError("Failed to create index: no nodes parsed.")
                
            storage_context = StorageContext.from_defaults()
            # ! ВАЖНО: Передаем текущую модель эмбеддингов при создании !
            index = VectorStoreIndex(
                nodes,
                embed_model=self.embed_model, # <--- Передаем здесь
                storage_context=storage_context,
                show_progress=True # Показываем прогресс эмбеддинга
            )
            logger.info(f"New index created successfully with {len(nodes)} nodes.")
            
            logger.info(f"Persisting index to {persist_dir}...")
            os.makedirs(persist_dir, exist_ok=True)
            index.storage_context.persist(persist_dir=persist_dir)
            logger.info("Index persisted successfully.")
            
            # Записываем параметры ПОСЛЕ успешного создания и сохранения индекса
            self._write_index_params()
            
            return index

        except Exception as e:
            logger.error(f"Failed to create or persist index: {e}", exc_info=True)
            raise RuntimeError(f"Could not create or persist index: {e}") from e

    # --- Методы для выполнения запроса (пока плейсхолдеры) ---

    def _get_retriever(self, filters: Optional[List[MetadataFilter]] = None) -> BaseRetriever:
         """Создает и возвращает ретривер для индекса с опциональными фильтрами."""
         logger.debug(f"Creating retriever with similarity_top_k={self.config.INITIAL_RETRIEVAL_TOP_K} and filters={'yes' if filters else 'no'}")
         return self.index.as_retriever(
             similarity_top_k=self.config.INITIAL_RETRIEVAL_TOP_K,
             filters=filters
         )
         
    def _apply_filters(self, query_bundle: QueryBundle, pension_type: Optional[str]) -> Tuple[List[MetadataFilter], bool]:
        """
        Определяет фильтры метаданных на основе типа пенсии и текста запроса.
        Возвращает (список фильтров, флаг применения фильтров).
        """
        # TODO: Перенести логику из старого query_case / предыдущей версии engine.py
        logger.warning("_apply_filters method is not fully implemented yet.")
        
        if not pension_type or pension_type not in self.config.PENSION_TYPE_FILTERS:
            logger.debug("No valid pension type provided or found in config, skipping filters.")
            return [], False

        filter_config = self.config.PENSION_TYPE_FILTERS[pension_type]
        query_text = query_bundle.query_str.lower()
        condition_keywords = filter_config.get('condition_keywords', [])
        
        # Логика применения фильтров на основе ключевых слов
        apply = True
        if condition_keywords:
             # Фильтр применяется ТОЛЬКО если есть ключевое слово
             if not any(keyword in query_text for keyword in condition_keywords):
                 logger.debug(f"Query does not contain required keywords {condition_keywords} for '{pension_type}', skipping filters.")
                 apply = False
        # Добавить логику для 'exclude_keywords', если нужно

        if apply and filter_config.get('filters'):
            metadata_filters = [
                ExactMatchFilter(key=f['key'], value=f['value']) 
                for f in filter_config['filters']
            ]
            logger.info(f"Applying metadata filters for pension type '{pension_type}': {filter_config['filters']}")
            return metadata_filters, True
        else:
             # Либо не было фильтров в конфиге, либо не выполнилось условие по словам
             return [], False


    def _retrieve_nodes(self, query_bundle: QueryBundle, pension_type: Optional[str]) -> List[NodeWithScore]:
        """Выполняет поиск узлов (retrieval) с фильтрами и без, объединяет результаты."""
        # TODO: Перенести логику из старого query_case / предыдущей версии engine.py
        logger.warning("_retrieve_nodes method is not fully implemented yet.")

        logger.info(f"Retrieving nodes for query: '{query_bundle.query_str[:100]}...'")
        target_filters, filters_applied = self._apply_filters(query_bundle, pension_type)

        # Основной поиск
        base_retriever = self._get_retriever()
        base_nodes = base_retriever.retrieve(query_bundle)
        logger.debug(f"Retrieved {len(base_nodes)} base nodes.")
        for node in base_nodes: # Сохраняем исходный скор
             node.metadata['retrieval_score'] = node.score 

        # Поиск с фильтрами
        filtered_nodes = []
        if filters_applied:
            try:
                filtered_retriever = self._get_retriever(filters=target_filters)
                filtered_nodes = filtered_retriever.retrieve(query_bundle)
                logger.debug(f"Retrieved {len(filtered_nodes)} nodes with filters.")
                for node in filtered_nodes: # Сохраняем исходный скор
                     node.metadata['retrieval_score'] = node.score
            except Exception as e:
                 logger.error(f"Error retrieving nodes with filters: {e}", exc_info=True)
                 # Продолжаем без фильтрованных узлов в случае ошибки
                 filtered_nodes = []

        # Объединение и дедупликация
        all_nodes_dict: Dict[str, NodeWithScore] = {node.node.node_id: node for node in base_nodes}
        added_filtered = 0
        for node in filtered_nodes:
            if node.node.node_id not in all_nodes_dict:
                all_nodes_dict[node.node.node_id] = node
                added_filtered += 1
            # Можно добавить логику обновления score, если фильтрованный узел уже есть, но имеет лучший score
        
        combined_nodes = list(all_nodes_dict.values())
        combined_nodes.sort(key=lambda x: x.score, reverse=True) # Сортировка по исходному score
        
        logger.info(f"Combined and deduplicated nodes: {len(combined_nodes)} (added {added_filtered} from filtered search)")
        return combined_nodes


    def _rerank_nodes(self, query_bundle: QueryBundle, nodes: List[NodeWithScore]) -> Tuple[List[NodeWithScore], float]:
        """Применяет реранкер (если доступен) к узлам-кандидатам.
        Возвращает кортеж: (список лучших N узлов, скор уверенности, основанный на топ-1 узле).
        """
        if not self.reranker_model or not nodes:
            logger.debug("Reranker not available or no nodes to rerank. Returning top N initial nodes with 0.0 score.")
            initial_top_nodes = nodes[:self.config.RERANKER_TOP_N]
            return initial_top_nodes, 0.0 # Возвращаем 0.0 как скор

        logger.info(f"Reranking {len(nodes)} nodes...")
        query_text = query_bundle.query_str
        passages = [node.get_content() for node in nodes]
        rerank_pairs = [[query_text, passage] for passage in passages]
        
        try:
            scores = self.reranker_model.predict(rerank_pairs, show_progress_bar=False)
            
            # Присваиваем новые скоры узлам
            for node, score in zip(nodes, scores):
                node.metadata['rerank_score'] = float(score) 
                node.score = float(score) # Используем rerank_score как основной score

            nodes.sort(key=lambda x: x.score, reverse=True)
            reranked_nodes = nodes[:self.config.RERANKER_TOP_N]
            logger.info(f"Reranking complete. Selected top {len(reranked_nodes)} nodes.")
            top_scores_log = [f"{n.score:.4f}" for n in reranked_nodes[:3]] # Оставляем для логов
            logger.debug(f"Top reranked scores: {top_scores_log}")
            
            # --- ИЗМЕНЕННАЯ ЛОГИКА СКОРА УВЕРЕННОСТИ ---
            confidence_score = 0.0
            if reranked_nodes:
                # Используем скор самого релевантного (первого) узла
                confidence_score = float(reranked_nodes[0].score)
                logger.info(f"Using top-1 reranked score as confidence score: {confidence_score:.4f}")
            else:
                 logger.warning("No nodes left after reranking, confidence score is 0.0")
            # -------------------------------------------
            
            # Возвращаем ноды и новый скор уверенности
            return reranked_nodes, confidence_score 
            
        except Exception as e:
            logger.error(f"Error during reranking: {e}", exc_info=True)
            logger.warning("Reranking failed. Returning top N nodes based on initial retrieval scores.")
            # Сортируем по исходному скору (если сохранили в metadata)
            nodes.sort(key=lambda x: x.metadata.get('retrieval_score', x.score), reverse=True) 
            # Возвращаем изначальные ноды и скор 0.0 при ошибке
            return nodes[:self.config.RERANKER_TOP_N], 0.0 


    def _build_prompt(self, query_text: str, context_nodes: List[NodeWithScore], pension_type: Optional[str], disability_info: Optional[dict]) -> str:
        """Формирует финальный промпт для LLM."""
        # TODO: Перенести логику из старого query_case / предыдущей версии engine.py
        logger.warning("_build_prompt method is not fully implemented yet.")

        logger.debug("Building final prompt for LLM...")
        context_str = "\n\n---\n\n".join([node.get_content() for node in context_nodes])
        
        disability_str = ""
        if disability_info:
            group_code = disability_info.get("group")
            group_name = self.config.DISABILITY_GROUP_MAP.get(str(group_code), f"Группа {group_code}" if group_code else "не указана")
            reason = disability_info.get("reason", "не указана")
            disability_str = f"\nДополнительная информация: Инвалидность {group_name}, причина - {reason}."

        current_date = datetime.now().strftime("%d.%m.%Y")  # Формат ДД.ММ.ГГГГ

        prompt = f"""
            Запрос на правовой анализ пенсионного случая в соответствии с законодательством РФ
            **Актуальность данных на**: {current_date}

            **Сведения о заявителе:**
            - Описание ситуации: {query_text}{disability_str}
            - Категория запрашиваемой пенсии: {pension_type or 'не определена'}

            **Нормативная база:**
            ---
            {context_str}
            ---

            **Порядок обработки запроса:**
            1. Установление правовых оснований:
            • Определить соответствие случая статьям {context_str.split('ФЗ')[1].split()[0]} (с указанием конкретных пунктов)
            • Выявить наличие/отсутствие обязательных критериев назначения

            2. Анализ условий назначения:
            • Возрастные требования (указать нормативный возраст)
            • Страховой стаж (минимальные значения)
            • Величина ИПК (пороговое значение)
            • Специальные условия (для льготных категорий)

            3. Требуемые документы:
            • Установленный перечень по выявленным основаниям
            • Отсутствующие в описании данные (справки, подтверждения)

            **Требования к ответу:**
            ✓ Ссылки только на приведенные статьи законов
            ✓ Отказ от интерпретаций вне предоставленного контекста
            ✓ Четкое разделение выводов на:
            - Удовлетворяющие условия (со ссылкой на норму права)
            - Неудовлетворяющие условия (с указанием причины)
            - Недостающие сведения (перечень документов/справок)

            **Примечание:** 
            Ответ подлежит оформлению в соответствии с Приказом Минтруда № 958н от 28.12.2022 
            "Об утверждении Административного регламента...". Конфиденциальная информация не подлежит разглашению.

            **Важно:**
            - Отвечай только на основе предоставленного контекста.
            - Не придумывай информацию.
            - Будь кратким и по существу.
            - Отвечай на русском языке.
            - перепроверяй все факты и цифры. Например, возраст, стаж, ИПК и т.д. Человек не может быть старше 100 лет, иметь стаж работы больше чем его возраст.
            """
        logger.debug(f"Generated prompt (first 200 chars): {prompt[:200]}...")
        return prompt


    def query(self, case_description: str, pension_type: Optional[str] = None, disability_info: Optional[dict] = None) -> Tuple[str, float]:
        """
        Основной метод для выполнения запроса к RAG системе.
        Возвращает кортеж: (текст ответа LLM, скор уверенности).
        """
        # TODO: Перенести логику из старого query_case / предыдущей версии engine.py
        logger.warning("Query method needs review/update for confidence score logic.")

        logger.info(f"Processing query: '{case_description[:100]}...', pension_type: {pension_type}")
        query_bundle = QueryBundle(case_description)
        
        try:
            # 1. Retrieve
            candidate_nodes = self._retrieve_nodes(query_bundle, pension_type)
            
            # 2. Rerank
            ranked_nodes, confidence_score = self._rerank_nodes(query_bundle, candidate_nodes) 

            if not ranked_nodes:
                 logger.warning("No relevant documents found after retrieval and reranking.")
                 # Возвращаем сообщение и скор 0.0
                 return "К сожалению, не удалось найти релевантную информацию в базе знаний для ответа на ваш запрос.", 0.0 

            # 3. Build Prompt
            final_prompt = self._build_prompt(case_description, ranked_nodes, pension_type, disability_info)
            
            # 4. Generate Response using LLM
            logger.info("Sending request to LLM...")
            # Используем прямой вызов LLM
            response = self.llm.complete(final_prompt)
            response_text = str(response)
            
            logger.info(f"LLM response received (length: {len(response_text)}).")
            logger.debug(f"LLM Response (first 100 chars): {response_text[:100]}...")
            
            # TODO: Добавить пост-обработку ответа LLM при необходимости
            
            # Возвращаем текст и скор уверенности
            return response_text, confidence_score 

        except Exception as e:
            logger.error(f"Error processing query '{case_description[:50]}...': {e}", exc_info=True)
            # Возвращаем сообщение об ошибке и скор 0.0
            return f"Произошла внутренняя ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже или обратитесь к администратору. (Ошибка: {e})", 0.0 


# --- Пример использования (для локального тестирования) ---
if __name__ == '__main__':
    # Устанавливаем уровень логирования DEBUG для подробной информации при запуске скрипта
    # logger.setLevel(logging.DEBUG) # Устанавливаем уровень для корневого логгера
    # for handler in logging.getLogger().handlers: # Устанавливаем уровень для всех хендлеров
    #      handler.setLevel(logging.DEBUG)
    logging.getLogger(__name__).setLevel(logging.DEBUG) # Устанавливаем DEBUG только для этого модуля
         
    logger.info("="*20 + " Starting PensionRAG engine test " + "="*20)
    try:
        # Создаем экземпляр двигателя. Инициализация и загрузка/создание индекса происходят здесь.
        rag_engine = PensionRAG() 
        
        # --- Тестовые запросы ---
        test_cases = [
            {
                "description": "Мужчина, 66 лет, пенсия по старости, стаж 12 лет, 20 баллов ИПК. Есть трудовая.",
                "pension_type": "retirement_standard",
                "disability_info": None
            },
            {
                "description": "Женщина, 45 лет, инвалид II группы с детства.",
                "pension_type": "disability_social", 
                "disability_info": {"group": "2", "reason": "инвалид с детства"}
            },
             {
                "description": "Работала 15 лет на севере, хочу выйти на пенсию досрочно в 55.",
                "pension_type": "retirement_early", # Тип важен для фильтрации
                "disability_info": None
            },
             {
                "description": "Мне 60 лет, стаж 5 лет. Могу ли я получать пенсию?",
                 "pension_type": None, # Без типа, общий поиск
                "disability_info": None
            }
        ]

        for i, case in enumerate(test_cases):
             logger.info(f"--- Running Test Case {i+1} ---")
             print(f"\n--- Query {i+1}: {case['description']} (Type: {case['pension_type']}) ---")
             # Получаем и текст, и скор
             result_text, score = rag_engine.query(
                 case_description=case['description'], 
                 pension_type=case['pension_type'], 
                 disability_info=case['disability_info']
            )
             # Печатаем оба
             print(f"\nРезультат анализа {i+1} (Уверенность: {score:.4f}):\n{result_text}")
             logger.info(f"--- Test Case {i+1} Finished ---")

    except Exception as e:
        logger.exception("An error occurred during the PensionRAG test run.")
        print(f"\n--- FATAL ERROR ---")
        print(f"An critical error occurred during initialization or querying: {e}")
        
    logger.info("="*20 + " PensionRAG engine test finished " + "="*20) 