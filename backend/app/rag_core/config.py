import os

# --- Пути ---
# Определяем базовую директорию относительно этого файла
CORE_DIR = os.path.dirname(os.path.abspath(__file__)) # .../backend/app/rag_core
APP_DIR = os.path.dirname(CORE_DIR)                   # .../backend/app
BACKEND_DIR = os.path.dirname(APP_DIR)                # .../backend
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)           # .../ (корень проекта, если backend не в корне)

PERSIST_DIR = os.path.join(BACKEND_DIR, "data") # Директория для хранения индекса (backend/data)
PARAMS_LOG_FILE = os.path.join(PERSIST_DIR, "index_params.log") # Файл лога параметров индекса (backend/data/index_params.log)
DOCUMENTS_DIR = os.path.join(BACKEND_DIR, "data") # Директория с документами (backend/data)

# --- Модели ---
HF_EMBED_MODEL_NAME = "jinaai/jina-embeddings-v3" # Новая модель эмбеддингов
OLLAMA_LLM_MODEL_NAME = "qwen3:latest" # Замените на вашу модель, если нужно
OLLAMA_BASE_URL = "http://localhost:11434"

# Модель для реранкера
RERANKER_MODEL_NAME = 'DiTy/cross-encoder-russian-msmarco'

# --- Параметры RAG ---
# Количество изначальных кандидатов для ретривера
INITIAL_RETRIEVAL_TOP_K = 40
# <<< Новый параметр: Количество кандидатов для поиска С ФИЛЬТРАМИ >>>
FILTERED_RETRIEVAL_TOP_K = 15 # Должно быть <= INITIAL_RETRIEVAL_TOP_K
# Количество узлов после реранкинга для передачи в LLM
RERANKER_TOP_N = 12 # Рекомендуется <= FILTERED_RETRIEVAL_TOP_K (если фильтры используются) или INITIAL_RETRIEVAL_TOP_K
# Старое значение, если нужно где-то использовать (но лучше опираться на INITIAL_RETRIEVAL_TOP_K и RERANKER_TOP_N)
# SIMILARITY_TOP_K = 12 

# --- Параметры парсинга и индексации ---
# Версия парсера (для отслеживания изменений, требующих переиндексации)
METADATA_PARSER_VERSION = "v2_hierarchical_structure"
# Максимальная длина структурного чанка перед вторичным разбиением
MAX_STRUCT_CHUNK_LENGTH = 1500
# Параметры для вторичного разбиения (если структурный чанк слишком длинный)
SECONDARY_CHUNK_SIZE = 512
SECONDARY_CHUNK_OVERLAP = 50
MAX_PDF_PAGES = 100 # Максимальное количество страниц в PDF для обработки

# --- Параметры LLM ---
LLM_REQUEST_TIMEOUT = 300.0 # Таймаут запроса к LLM в секундах
# Размер контекстного окна LLM (в токенах). Установите в соответствии с моделью (например, qwen3 обычно имеет большие окна, такие как 32k, 64k или даже больше в зависимости от версии).
# Это значение влияет на то, сколько информации (контекстных документов + промпт) можно передать LLM за один раз.
LLM_CONTEXT_WINDOW = 100000 

# --- Параметры Реранкера ---
# Максимальная длина последовательности для реранкера (в токенах). 
# Увеличение может улучшить точность реранжирования за счет анализа большего контекста, 
# но также увеличит потребление памяти и время обработки. Подберите значение, исходя из возможностей вашей модели реранкера и ресурсов.
RERANKER_MAX_LENGTH = 512 

# --- Общие параметры ---
LOGGING_LEVEL = "DEBUG" # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)


# --- Дополнительно: маппинг типов пенсий на фильтры ---
PENSION_TYPE_MAP = {
    'retirement_standard': 'Страховая по старости (общий случай)',
    'disability_insurance': 'Страховая пенсия по инвалидности',
    'survivor_insurance': 'Страховая пенсия по случаю потери кормильца',
    'disability_social': 'Социальная по инвалидности',
    'retirement_early': 'Досрочная страховая по старости',
    'retirement_social': 'Социальная пенсия по старости',
}

PENSION_KEYWORD_MAP = {
    # Для retirement_standard
    'страховая по старости': 'retirement_standard',
    'пенсия по старости': 'retirement_standard',
    'страховая пенсия': 'retirement_standard',
    'общеустановленного пенсионного возраста': 'retirement_standard',

    # Для disability_insurance
    'страховая пенсия по инвалидности': 'disability_insurance',
    # 'пенсия по инвалидности': 'disability_insurance', # Может конфликтовать с 'социальная пенсия по инвалидности'
    'инвалидам i группы': 'disability_insurance', 
    'инвалидам ii группы': 'disability_insurance',
    'инвалидам iii группы': 'disability_insurance',
    
    # Для survivor_insurance
    'страховая пенсия по случаю потери кормильца': 'survivor_insurance',
    'потеря кормильца': 'survivor_insurance',
    'потери кормильца': 'survivor_insurance',
    'иждивении': 'survivor_insurance',
    'нетрудоспособным членам семьи': 'survivor_insurance',

    # Для disability_social
    'социальная пенсия по инвалидности': 'disability_social',
    'инвалидам с детства': 'disability_social',

    # Для retirement_early
    'досрочное назначение': 'retirement_early',
    'досрочно назначаемая': 'retirement_early',
    'вредных условиях': 'retirement_early',
    'льготный стаж': 'retirement_early',
    'особых условиях труда': 'retirement_early',
    'северный стаж': 'retirement_early',

    # Для retirement_social
    'социальная пенсия по старости': 'retirement_social',
    'социальное обеспечение': 'retirement_social',
    'малочисленных народов севера': 'retirement_social',
    'по государственному пенсионному обеспечению': 'retirement_social',
}

PENSION_TYPE_FILTERS = {
    'retirement_standard': {
        'description': 'Страховая по старости (общий случай)',
        'filters': [{"key": "canonical_article_id", "value": "ФЗ-400-ФЗ-28_12_2013_Ст_8"}],
        'condition_keywords': []
    },
    'disability_insurance': {
        'description': 'Страховая пенсия по инвалидности',
        'filters': [{"key": "canonical_article_id", "value": "ФЗ-400-ФЗ-28_12_2013_Ст_9"}],
        'condition_keywords': ['инвалид'] 
    },
    'survivor_insurance': {
        'description': 'Страховая пенсия по случаю потери кормильца',
        'filters': [{"key": "canonical_article_id", "value": "ФЗ-400-ФЗ-28_12_2013_Ст_10"}],
        'condition_keywords': ['кормильца'] 
    },
    'disability_social': {
        'description': 'Социальная по инвалидности',
        'filters': [
            # ФЗ-166, Статья 11 определяет общие условия для социальных пенсий, включая по инвалидности.
            # Статья 5 определяет право на соц. пенсию, включая инвалидов.
            # Статья 9 этого же закона также относится к пенсиям по инвалидности (скорее к размерам и индексации). 
            # Выбираем Ст.11 как обобщающую по условиям, или Ст.5 как основополагающую.
            # Пусть будет Ст.11, но это требует верификации.
            {"key": "canonical_article_id", "value": "ФЗ-166-ФЗ-15_12_2001_Ст_11"} 
            # Или, если точнее, можно указать несколько статей через OR логику, 
            # но текущая система фильтров не поддерживает это напрямую.
            # Либо создать несколько записей в PENSION_TYPE_FILTERS для подтипов, если это необходимо.
        ],
        'condition_keywords': ['инвалид', 'социальн']
    },
    'retirement_early': {
        'description': 'Досрочная страховая по старости',
        'filters': [ 
             {"key": "canonical_article_id", "value": "ФЗ-400-ФЗ-28_12_2013_Ст_30"}
             # Для большей полноты можно добавить Ст_31, Ст_32 и др. отдельными записями
             # или если бы фильтры поддерживали список значений для одного ключа.
        ],
        'condition_keywords': ['досрочн']
    },
    'retirement_social': {
        'description': 'Социальная пенсия по старости',
        'filters': [
            {"key": "canonical_article_id", "value": "ФЗ-166-ФЗ-15_12_2001_Ст_11"} # Статья 11 ФЗ-166
        ],
        'condition_keywords': ['социальн', 'старост']
    },
}

DISABILITY_GROUP_MAP = {"1": "I", "2": "II", "3": "III", "child": "Ребенок-инвалид"}


# Функция для получения текущих параметров индекса (используется для проверки необходимости переиндексации)
def get_current_index_params():
    return {
        "metadata_parser_version": METADATA_PARSER_VERSION,
        "hf_embed_model_name": HF_EMBED_MODEL_NAME, # Новый ключ для новой модели
        "max_struct_chunk_length": MAX_STRUCT_CHUNK_LENGTH,
        "secondary_chunk_size": SECONDARY_CHUNK_SIZE,
        "secondary_chunk_overlap": SECONDARY_CHUNK_OVERLAP,
        # Можно добавить другие параметры, изменение которых требует переиндексации
    } 

# --- Neo4j Configuration ---
# URI для подключения к Neo4j
NEO4J_URI = "bolt://localhost:7687"
# Имя пользователя Neo4j (по умолчанию neo4j)
NEO4J_USER = "neo4j"
NEO4J_DATABASE = "neo4j"
NEO4J_PASSWORD = "12345678" # <--- ЗАМЕНИТЕ ЭТО НА ВАШ ПАРОЛЬ NEO4J 

# --- Валидация параметров RAG ---
if FILTERED_RETRIEVAL_TOP_K > INITIAL_RETRIEVAL_TOP_K:
    raise ValueError(
        f"FILTERED_RETRIEVAL_TOP_K ({FILTERED_RETRIEVAL_TOP_K}) "
        f"must be <= INITIAL_RETRIEVAL_TOP_K ({INITIAL_RETRIEVAL_TOP_K})"
    )

if RERANKER_TOP_N > INITIAL_RETRIEVAL_TOP_K: # Проверяем относительно INITIAL_RETRIEVAL_TOP_K как максимального количества
    # Более строгая проверка RERANKER_TOP_N <= FILTERED_RETRIEVAL_TOP_K может быть добавлена,
    # но только если FILTERED_RETRIEVAL_TOP_K всегда используется или его значение по умолчанию адекватно.
    # Пока что, убедимся что RERANKER_TOP_N не больше, чем максимально возможное количество извлеченных документов.
    raise ValueError(
        f"RERANKER_TOP_N ({RERANKER_TOP_N}) "
        f"must be <= INITIAL_RETRIEVAL_TOP_K ({INITIAL_RETRIEVAL_TOP_K}) for safety, ideally <= FILTERED_RETRIEVAL_TOP_K if filters are applied."
    )
# Можно добавить и RERANKER_TOP_N <= FILTERED_RETRIEVAL_TOP_K, если это жесткое требование
# if RERANKER_TOP_N > FILTERED_RETRIEVAL_TOP_K:
#     raise ValueError(
#         f"RERANKER_TOP_N ({RERANKER_TOP_N}) "
#         f"must be <= FILTERED_RETRIEVAL_TOP_K ({FILTERED_RETRIEVAL_TOP_K})"
#     ) 

# Мультимодальная LLM для анализа изображений (например, паспортов)
OLLAMA_MULTIMODAL_LLM_MODEL_NAME = "qwen2.5vl:latest" # Убедитесь, что имя правильное для вашей Ollama
# Таймаут для мультимодальной LLM
MULTIMODAL_LLM_REQUEST_TIMEOUT = 900.0

# Конфигурация для Google Vision API (если используется)
# ... existing code ... 