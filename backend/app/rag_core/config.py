import os

# --- Пути ---
# Определяем базовую директорию относительно этого файла
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(os.path.dirname(CORE_DIR))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR) # Пример, если нужно выйти выше
PERSIST_DIR = os.path.join(BACKEND_DIR, "data") # Директория для хранения индекса
PARAMS_LOG_FILE = os.path.join(PERSIST_DIR, "index_params.log") # Файл лога параметров индекса
DOCUMENTS_DIR = os.path.join(BACKEND_DIR, "data") # Новый путь - директория с документами

# --- Модели ---
# Имена моделей Ollama
# OLLAMA_EMBED_MODEL_NAME = "mxbai-embed-large:latest" # Убираем или комментируем
HF_EMBED_MODEL_NAME = "jinaai/jina-embeddings-v3" # Новая модель эмбеддингов
OLLAMA_LLM_MODEL_NAME = "gemma3:latest" # Замените на вашу модель, если нужно
OLLAMA_BASE_URL = "http://localhost:11434"

# Модель для реранкера
RERANKER_MODEL_NAME = 'DiTy/cross-encoder-russian-msmarco'

# --- Параметры RAG ---
# Количество изначальных кандидатов для ретривера
INITIAL_RETRIEVAL_TOP_K = 25
# Количество узлов после реранкинга для передачи в LLM
RERANKER_TOP_N = 8 # Рекомендуется <= INITIAL_RETRIEVAL_TOP_K
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

# --- Параметры LLM ---
LLM_REQUEST_TIMEOUT = 300.0 # Таймаут запроса к LLM в секундах
LLM_CONTEXT_WINDOW = 100000 # Размер контекстного окна LLM (подберите под вашу модель)

# --- Параметры Реранкера ---
RERANKER_MAX_LENGTH = 512 # Максимальная длина последовательности для реранкера

# --- Общие параметры ---
LOGGING_LEVEL = "INFO" # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)


# --- Дополнительно: маппинг типов пенсий на фильтры ---
# Можно расширить для более сложных правил фильтрации
PENSION_TYPE_FILTERS = {
    'retirement_standard': {
        'description': 'Страховая по старости (общий случай)',
        'filters': [
            {"key": "article", "value": "Статья 8"},
            {"key": "file_name", "value": "fz400.pdf"}
        ],
        'condition_keywords': [] # Не применять, если есть эти слова в запросе
    },
    'retirement_early': { # Пример для досрочной
        'description': 'Досрочная страховая по старости',
        'filters': [
             # Могут быть другие статьи, например, 30, 31, 32 ФЗ-400
            {"key": "article", "value": "Статья 30"}, # Как пример
            {"key": "file_name", "value": "fz400.pdf"}
        ],
        'condition_keywords': ['досрочн'] # Применять, только если есть эти слова
    },
    'disability_social': {
        'description': 'Социальная по инвалидности',
        'filters': [
            {"key": "article", "value": "Статья 11"},
            {"key": "file_name", "value": "fz166.pdf"}
        ],
        'condition_keywords': []
    },
    # Добавить другие типы пенсий...
}

# --- Маппинг групп инвалидности для промпта ---
DISABILITY_GROUP_MAP = {"1": "I", "2": "II", "3": "III", "child": "Ребенок-инвалид"}


# Функция для получения текущих параметров индекса (используется для проверки необходимости переиндексации)
def get_current_index_params():
    return {
        "metadata_parser_version": METADATA_PARSER_VERSION,
        # "ollama_embed_model_name": OLLAMA_EMBED_MODEL_NAME, # Заменяем ключ
        "hf_embed_model_name": HF_EMBED_MODEL_NAME, # Новый ключ для новой модели
        "max_struct_chunk_length": MAX_STRUCT_CHUNK_LENGTH,
        "secondary_chunk_size": SECONDARY_CHUNK_SIZE,
        "secondary_chunk_overlap": SECONDARY_CHUNK_OVERLAP,
        # Можно добавить другие параметры, изменение которых требует переиндексации
    } 