# backend/app/rag_core/query_engine.py

from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage, Document
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.schema import NodeWithScore, TextNode # Снова нужен TextNode
from llama_index.llms.ollama import Ollama
from typing import List, Optional # Добавляем Optional
# Убедимся, что loader импортируется правильно
try:
    from .loader import load_documents
except ImportError:
    # Попытка импорта, если запускается как скрипт напрямую
    from loader import load_documents
import os
import glob # Добавили для удаления файлов
import json # Добавили для чтения/записи параметров
import re # Снова нужен re
from llama_index.core.node_parser import SimpleNodeParser # Для вторичного разбиения
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter # Добавили импорты для фильтрации
# Убираем VectorIndexRetriever, он не нужен явно
# from llama_index.core.retrievers import VectorIndexRetriever

# --- Определяем пути и константы --- 
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
PERSIST_DIR = os.path.join(BACKEND_DIR, "data")
PARAMS_LOG_FILE = os.path.join(PERSIST_DIR, "index_params.log") # Файл для хранения параметров индекса

EMBED_MODEL_NAME = "ollama:mxbai-embed-large:latest"
OLLAMA_EMBED_MODEL_NAME = "mxbai-embed-large:latest"
OLLAMA_LLM_MODEL_NAME = "gemma3:latest"
OLLAMA_BASE_URL = "http://localhost:11434"
SIMILARITY_TOP_K = 6
# Новая версия парсера с иерархическим чанкингом
METADATA_PARSER_VERSION = "v2_hierarchical_structure"
# Максимальная длина структурного чанка перед вторичным разбиением
MAX_STRUCT_CHUNK_LENGTH = 1500
# Параметры для вторичного разбиения (если чанк слишком длинный)
SECONDARY_CHUNK_SIZE = 512
SECONDARY_CHUNK_OVERLAP = 50
# -----------------------------------

query_engine = None
global_index = None # Глобальная переменная для хранения индекса

# --- Переработанная функция чанкования с иерархией ---
def split_text_by_structure_hierarchical(text: str, file_name: str) -> List[TextNode]:
    """
    Разбивает текст иерархически:
    1. По структурным заголовкам (Статья, Глава, Пункт и т.д.) с сохранением метаданных.
    2. Если структурный чанк > MAX_STRUCT_CHUNK_LENGTH, он разбивается дальше
       на более мелкие чанки, наследующие метаданные родителя.
    """
    final_nodes = []
    # Regex для поиска структурных заголовков (оставляем как был)
    pattern = r"^\s*((Статья)\s+(\d+)\.?.*|(Глава)\s+(\d+)\.?.*|(Раздел)\s+([IVXLC]+)\.?.*|(\d{1,3})\.\s.*|(\d{1,3})[\)\.]\s.*|(\d{1,3}\.\d{1,2})\.\s.*)"

    matches = list(re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE))

    start_pos = 0
    current_metadata = {"file_name": file_name, "article": None, "chapter": None, "section": None, "point": None, "header": "Начало документа"}
    
    # Создаем парсер для вторичного разбиения
    secondary_parser = SimpleNodeParser.from_defaults(
        chunk_size=SECONDARY_CHUNK_SIZE,
        chunk_overlap=SECONDARY_CHUNK_OVERLAP,
        paragraph_separator="\n\n\n" # Используем тройной перенос для надежности
    )

    struct_chunk_index = 0 # Индекс структурного чанка

    for i, match in enumerate(matches):
        end_pos = match.start()
        struct_chunk_text = text[start_pos:end_pos].strip()
        header_text = match.group(1).strip()

        # 1. Обрабатываем предыдущий структурный чанк
        if struct_chunk_text:
            # Проверяем длину структурного чанка
            if len(struct_chunk_text) > MAX_STRUCT_CHUNK_LENGTH:
                # Слишком длинный -> разбиваем вторично
                sub_nodes = secondary_parser.get_nodes_from_documents(
                    [Document(text=struct_chunk_text, metadata=current_metadata.copy())], # Передаем метаданные документу
                    show_progress=False
                )
                # Добавляем индекс под-чанка к метаданным и ID
                for sub_idx, node in enumerate(sub_nodes):
                    # Убедимся, что node это TextNode или имеет атрибут id_
                    if hasattr(node, 'id_'):
                         node.id_ = f"{file_name}_struct_{struct_chunk_index}_sub_{sub_idx}"
                    else: # Если это базовый Node, создаем TextNode
                         node = TextNode(
                             text=node.get_content(),
                             id_=f"{file_name}_struct_{struct_chunk_index}_sub_{sub_idx}",
                             metadata=node.metadata # Сохраняем исходные метаданные
                         )

                    node.metadata["parent_header"] = current_metadata.get("header", "N/A") # Добавляем заголовок родителя
                    final_nodes.append(node)
            else:
                # Нормальная длина -> создаем один узел
                node_id = f"{file_name}_struct_{struct_chunk_index}_full"
                final_nodes.append(TextNode(
                    text=struct_chunk_text,
                    id_=node_id,
                    metadata=current_metadata.copy()
                ))
            struct_chunk_index += 1


        # 2. Обновляем метаданные на основе ТЕКУЩЕГО заголовка для СЛЕДУЮЩЕГО чанка
        current_metadata["header"] = header_text
        # (Логика обновления article, chapter, section, point остается прежней)
        if match.group(2) and match.group(3): # Статья X
            article_str = f"Статья {match.group(3)}"
            current_metadata["article"] = article_str; current_metadata["point"] = None
        elif match.group(4) and match.group(5): # Глава X
            chapter_str = f"Глава {match.group(5)}"
            current_metadata["chapter"] = chapter_str; current_metadata["article"] = None; current_metadata["point"] = None
        elif match.group(6) and match.group(7): # Раздел X
            section_str = f"Раздел {match.group(7)}"
            current_metadata["section"] = section_str; current_metadata["chapter"] = None; current_metadata["article"] = None; current_metadata["point"] = None
        elif match.group(8): current_metadata["point"] = match.group(8) + "." # Пункт X.
        elif match.group(9): current_metadata["point"] = match.group(9) # Пункт X) или X.
        elif match.group(10): current_metadata["point"] = match.group(10) + "." # Пункт X.Y.

        start_pos = match.end()

    # 3. Обрабатываем последний структурный чанк (от последнего заголовка до конца)
    last_struct_chunk_text = text[start_pos:].strip()
    if last_struct_chunk_text:
        if len(last_struct_chunk_text) > MAX_STRUCT_CHUNK_LENGTH:
            # Слишком длинный -> разбиваем вторично
            sub_nodes = secondary_parser.get_nodes_from_documents(
                [Document(text=last_struct_chunk_text, metadata=current_metadata.copy())],
                show_progress=False
            )
            for sub_idx, node in enumerate(sub_nodes):
                 # Убедимся, что node это TextNode или имеет атрибут id_
                 if hasattr(node, 'id_'):
                      node.id_ = f"{file_name}_struct_{struct_chunk_index}_end_sub_{sub_idx}"
                 else: # Если это базовый Node, создаем TextNode
                      node = TextNode(
                          text=node.get_content(),
                          id_=f"{file_name}_struct_{struct_chunk_index}_end_sub_{sub_idx}",
                          metadata=node.metadata
                      )
                 node.metadata["parent_header"] = current_metadata.get("header", "N/A")
                 final_nodes.append(node)
        else:
            # Нормальная длина -> создаем один узел
            node_id = f"{file_name}_struct_{struct_chunk_index}_end_full"
            final_nodes.append(TextNode(
                text=last_struct_chunk_text,
                id_=node_id,
                metadata=current_metadata.copy()
            ))

    print(f"Текст разбит на {len(final_nodes)} узлов с помощью иерархического парсера (v={METADATA_PARSER_VERSION}).")
    return final_nodes
# -----------------------------------------------------------

# --- Обновляем проверку параметров --- 
def check_and_force_reindex(current_params: dict):
    force_reindex = False
    if not os.path.exists(PARAMS_LOG_FILE):
        print(f"Файл параметров {PARAMS_LOG_FILE} не найден. Принудительная индексация.")
        force_reindex = True
    else:
        try:
            with open(PARAMS_LOG_FILE, 'r') as f: logged_params = json.load(f)
            # Проверяем все релевантные параметры
            changed = False
            for key in current_params:
                 if logged_params.get(key) != current_params[key]:
                     print(f"Параметр '{key}' изменился (было: {logged_params.get(key)}, стало: {current_params[key]}).")
                     changed = True
            # Добавим проверку на случай удаления параметра из новой версии
            for key in logged_params:
                 if key not in current_params:
                      print(f"Параметр '{key}' удален (был: {logged_params[key]}).")
                      changed = True

            if changed:
                print(f"Параметры индекса изменились. Принудительная переиндексация.")
                force_reindex = True
            else:
                print("Параметры индекса совпадают с сохраненными.")
        except Exception as e:
            print(f"Ошибка чтения файла параметров {PARAMS_LOG_FILE}: {e}. Принудительная переиндексация.")
            force_reindex = True

    if force_reindex:
        print(f"Удаление старых файлов индекса из {PERSIST_DIR}...")
        deleted_count = 0
        # Удаляем все .json файлы, связанные с индексом LlamaIndex
        index_files = glob.glob(os.path.join(PERSIST_DIR, "*store.json"))
        for f_path in index_files:
             try:
                 print(f"Удаляем {f_path}")
                 os.remove(f_path)
                 deleted_count += 1
             except OSError as e: print(f"Ошибка удаления файла {f_path}: {e}")
        # Удаляем лог параметров
        deleted_log = False
        if os.path.exists(PARAMS_LOG_FILE):
             try:
                 os.remove(PARAMS_LOG_FILE)
                 print(f"Удаляем {PARAMS_LOG_FILE}")
                 deleted_log = True
             except OSError as e: print(f"Ошибка удаления файла {PARAMS_LOG_FILE}: {e}")
        print(f"Удалено {deleted_count + (1 if deleted_log else 0)} старых файлов индекса и лог параметров.")
    return force_reindex
# -------------------------------------

def write_index_params(params: dict):
    try:
        os.makedirs(PERSIST_DIR, exist_ok=True)
        with open(PARAMS_LOG_FILE, 'w') as f: json.dump(params, f, indent=2)
        print(f"Параметры индекса сохранены в {PARAMS_LOG_FILE}")
    except Exception as e: print(f"Ошибка записи параметров индекса в {PARAMS_LOG_FILE}: {e}")

def initialize_index():
    global query_engine, global_index # Объявляем, что будем менять глобальные переменные
    print("Инициализация/Загрузка индекса...")

    current_index_params = {
        "metadata_parser_version": METADATA_PARSER_VERSION,
        "embed_model_name": EMBED_MODEL_NAME,
        "max_struct_chunk_length": MAX_STRUCT_CHUNK_LENGTH, # Добавляем новые параметры
        "secondary_chunk_size": SECONDARY_CHUNK_SIZE,
        "secondary_chunk_overlap": SECONDARY_CHUNK_OVERLAP
    }

    try:
        embed_model = OllamaEmbedding(model_name=OLLAMA_EMBED_MODEL_NAME, base_url=OLLAMA_BASE_URL)
        print(f"Используется Embed модель: OllamaEmbedding (model_name={OLLAMA_EMBED_MODEL_NAME}, base_url={OLLAMA_BASE_URL})")
    except Exception as e:
        print(f"Ошибка при создании OllamaEmbedding: {e}. Убедитесь, что Ollama запущена и модель доступна.")
        return None

    llm = Ollama(model=OLLAMA_LLM_MODEL_NAME, base_url=OLLAMA_BASE_URL)
    print(f"Используется LLM: Ollama (Модель: {OLLAMA_LLM_MODEL_NAME}, URL: {OLLAMA_BASE_URL})")

    needs_reindex = check_and_force_reindex(current_index_params)
    docstore_path = os.path.join(PERSIST_DIR, "docstore.json")

    index = None # Инициализируем локальную переменную для индекса

    if needs_reindex or not os.path.exists(docstore_path):
        print(f"Создание нового индекса...")
        os.makedirs(PERSIST_DIR, exist_ok=True)

        loaded_docs = load_documents()
        if not loaded_docs:
            print("Документы для индексации не найдены.")
            return None

        # --- Применяем НОВЫЙ иерархический парсер ---
        all_nodes = []
        for doc in loaded_docs:
            nodes = split_text_by_structure_hierarchical(
                doc.get_content(),
                doc.metadata.get("file_name", "unknown_doc")
            )
            if nodes:
                all_nodes.extend(nodes)
        # -----------------------------------------

        if not all_nodes:
             print("Не удалось разбить текст на узлы.")
             return None

        # Создаем индекс из списка узлов (Nodes)
        print(f"Создание VectorStoreIndex из {len(all_nodes)} узлов...")
        index = VectorStoreIndex(nodes=all_nodes, embed_model=embed_model)

        print(f"Сохранение индекса в {PERSIST_DIR}...")
        index.storage_context.persist(persist_dir=PERSIST_DIR)
        write_index_params(current_index_params)
        print("Индекс создан и сохранен.")
    else:
        print(f"Загрузка существующего индекса из {PERSIST_DIR}...")
        storage_context = StorageContext.from_defaults(persist_dir=PERSIST_DIR)
        try:
            # Передаем embed_model при загрузке
            index = load_index_from_storage(storage_context, embed_model=embed_model)
            print("Индекс успешно загружен.")
        except Exception as e:
             print(f"Ошибка при загрузке индекса: {e}. Попробуйте удалить папку {PERSIST_DIR} и запустить снова.")
             return None

    # --- Сохраняем индекс в глобальную переменную ---
    global_index = index
    # ----------------------------------------------

    print("Query Transformation: None (HyDE отключен)")

    # Создаем query engine как и раньше
    query_engine = index.as_query_engine(
        llm=llm,
        similarity_top_k=SIMILARITY_TOP_K
    )
    print(f"Query engine готов (similarity_top_k={SIMILARITY_TOP_K}).")
    return query_engine # Возвращаем только query_engine для обратной совместимости
# -----------------------------------------------------------

# --- Функция запроса с уточненным промптом ---
def query_case(case_description: str) -> str:
    """
    Выполняет RAG-запрос, создавая ретриверы и объединяя результаты
    с приоритетом для отфильтрованных узлов. Промпт уточнен для Статьи 8.
    """
    engine = get_query_engine() # Инициализирует engine и global_index
    if not engine or not global_index:
        return "Ошибка: Query engine или Index не инициализированы."

    context_for_prompt = ""
    final_nodes_for_prompt = []

    try:
        print(f"Выполняется поиск по запросу: '{case_description[:100]}...'")

        target_filters = None
        if "пенсия по старости" in case_description.lower() and "досрочн" not in case_description.lower():
            print("Обнаружен запрос 'пенсия по старости'. Применяем фильтр для Статьи 8.")
            target_filters = MetadataFilters(
                filters=[MetadataFilter(key="article", value="Статья 8")]
            )

        print("Создание ретривера для основного поиска...")
        general_retriever = global_index.as_retriever(similarity_top_k=SIMILARITY_TOP_K * 2)
        general_nodes = general_retriever.retrieve(case_description)
        print(f"Основной поиск завершен, найдено {len(general_nodes)} узлов.")

        filtered_nodes = []
        if target_filters:
            print(f"Создание ретривера для поиска с фильтром: {target_filters}")
            filtered_retriever = global_index.as_retriever(
                similarity_top_k=SIMILARITY_TOP_K,
                filters=target_filters
            )
            filtered_nodes = filtered_retriever.retrieve(case_description)
            print(f"Найдено {len(filtered_nodes)} узлов с фильтром.")

        final_nodes_for_prompt_list = []
        added_node_ids = set()
        nodes_added_count = 0

        print("Добавление отфильтрованных узлов (приоритет)...")
        for node_with_score in filtered_nodes:
            if nodes_added_count < SIMILARITY_TOP_K:
                 if node_with_score and node_with_score.node and hasattr(node_with_score.node, 'id_'):
                    node_id = node_with_score.node.id_
                    if node_id not in added_node_ids:
                        # Исправляем форматирование для печати score внутри цикла
                        score_str = f"{node_with_score.score:.4f}" if isinstance(node_with_score.score, float) else str(node_with_score.score)
                        print(f"  Добавляем отфильтрованный узел: {node_id} (Score: {score_str})")
                        final_nodes_for_prompt_list.append(node_with_score)
                        added_node_ids.add(node_id)
                        nodes_added_count += 1
            else: break

        print(f"Добавление общих узлов (осталось мест: {SIMILARITY_TOP_K - nodes_added_count})...")
        sorted_general_nodes = sorted(general_nodes, key=lambda n: n.score if hasattr(n, 'score') else -1, reverse=True)

        for node_with_score in sorted_general_nodes:
            if nodes_added_count < SIMILARITY_TOP_K:
                 if node_with_score and node_with_score.node and hasattr(node_with_score.node, 'id_'):
                    node_id = node_with_score.node.id_
                    if node_id not in added_node_ids:
                         # Исправляем форматирование для печати score внутри цикла
                        score_str = f"{node_with_score.score:.4f}" if isinstance(node_with_score.score, float) else str(node_with_score.score)
                        print(f"  Добавляем общий узел: {node_id} (Score: {score_str})")
                        final_nodes_for_prompt_list.append(node_with_score)
                        added_node_ids.add(node_id)
                        nodes_added_count += 1
            else: break

        final_nodes_for_prompt = final_nodes_for_prompt_list

        print(f"\n--- Финальный контекст для LLM ({len(final_nodes_for_prompt)} узлов): ---")
        if final_nodes_for_prompt:
             for i, node_with_score in enumerate(final_nodes_for_prompt):
                 if node_with_score and node_with_score.node and hasattr(node_with_score.node, 'metadata'):
                     node = node_with_score.node
                     score = node_with_score.score if hasattr(node_with_score, 'score') else 'N/A'
                     metadata = node.metadata if node.metadata else {}
                     score_str = f"{score:.4f}" if isinstance(score, float) else str(score)
                     print(f"Фрагмент {i+1} (Score: {score_str}) [Metadata: {metadata}]")
                     text_preview = node.get_content() if hasattr(node, 'get_content') else "[Содержимое недоступно]"
                     print(f"Начало: {text_preview[:150]}...")
                     if len(text_preview) > 300: print(f"...Конец: ...{text_preview[-150:]}")
                     print("---")
                     context_for_prompt += f"Фрагмент {i+1} (Статья: {metadata.get('article', 'N/A')}, Пункт: {metadata.get('point', 'N/A')}, Заголовок: {metadata.get('header', 'N/A')}):\n{text_preview}\n\n"
                 else:
                     print(f"Фрагмент {i+1}: Ошибка доступа к узлу или его метаданным.")
        else:
            print("Не найдено релевантных фрагментов.")
            context_for_prompt = "Не найдено релевантных фрагментов в законе для данного запроса.\n"
        print("------------------------------------\n")

    except Exception as e:
        print(f"Ошибка при получении или обработке фрагментов: {e}")
        import traceback
        traceback.print_exc()
        context_for_prompt = f"Ошибка при получении контекста: {e}\n"

    # --- Обновленный Промпт ---
    prompt = (
        f"Ты — высококвалифицированный эксперт по пенсионному законодательству РФ (ФЗ-400). Твоя задача — провести детальный анализ описания пенсионного дела, предоставленного пользователем. \n"
        f"**ВАЖНО: Используй ТОЛЬКО и ИСКЛЮЧИТЕЛЬНО информацию из предоставленных ниже 'Фрагментов закона'. Категорически запрещается использовать внешние знания или предполагать содержание других статей.**\n\n"
        f"Описание пенсионного дела от пользователя:\n"
        f"-----------------------------------------\n"
        f"{case_description}\n"
        f"-----------------------------------------\n\n"
        f"Фрагменты закона для анализа (ФЗ-400):\n"
        f"------------------------------------\n"
        f"{context_for_prompt}"
        f"------------------------------------\n\n"
        f"**Инструкции по анализу:**\n"
        f"1.  **Проверь соответствие:** Последовательно проанализируй ключевые параметры дела (возраст, стаж, тип пенсии, условия работы, если указаны) на соответствие требованиям, изложенным в предоставленных фрагментах. **Если в контексте есть фрагменты из Статьи 8, обязательно проверь соответствие возраста (пункт 1), страхового стажа (пункт 2, обычно не менее 15 лет) и ИПК (пункт 3, обычно не менее 30) требованиям этой статьи.** Обрати особое внимание на условия досрочного назначения пенсии (например, из Статьи 30), если они релевантны запросу или найдены в фрагментах.\n"
        f"2.  **Выяви проблемы:** Четко укажи на любые несоответствия, проблемы или недостающую информацию, основываясь *только* на тексте фрагментов. Если для какого-то аспекта дела во фрагментах нет информации, прямо скажи об этом (например: \"Во фрагментах нет информации о требованиях к документам\").\n"
        f"3.  **Цитируй точно:** При ссылке на закон **обязательно указывай номер Статьи и/или Пункта**, используя информацию из метаданных фрагмента (например: \"согласно Статье 30 Пункту 5\", \"в соответствии с Главой 6 Статьей 30\"). Если метаданные недоступны, ссылайся на текст заголовка фрагмента.\n"
        f"4.  **Не додумывай:** Не предполагай содержание статей или пунктов, не представленных в фрагментах. Не делай выводов, не подкрепленных текстом фрагментов.\n"
        f"5.  **Структурируй ответ:** Сначала изложи анализ соответствия основным условиям (возраст, стаж, ИПК), затем — анализ особых условий или проблем (документы, льготы). Заверши ответ кратким итоговым резюме по выявленным проблемам или подтверждением соответствия (если проблем нет).\n\n"
        f"**Результат анализа:**\n"
     )
    # --------------------------

    print(f"Отправка запроса в Query Engine (начало): {prompt[:300]}...") # Увеличил превью, чтобы видеть изменение

    # Используем исходный query_engine для генерации ответа
    try:
        response = engine.query(prompt)
        response_text = str(response)
    except Exception as e:
        print(f"Ошибка при выполнении запроса к Query Engine: {e}")
        import traceback
        traceback.print_exc()
        response_text = f"Ошибка при обработке запроса: {e}"

    print(f"Ответ Query Engine (начало): {response_text[:250]}...")
    return response_text
# -------------------------------------------

# --- Функция получения движка (остается без изменений) ---
def get_query_engine():
    global query_engine, global_index # Убедимся, что используем глобальные переменные
    if query_engine is None or global_index is None: # Проверяем оба
        # initialize_index() теперь вернет только engine, но обновит global_index
        engine_result = initialize_index()
        if engine_result is None: # Если инициализация не удалась
             query_engine = None
             global_index = None
             print("Инициализация не удалась.") # Добавим сообщение
        else:
             query_engine = engine_result
        # global_index должен быть уже установлен внутри initialize_index()
    return query_engine
# -------------------------------------

# Пример использования при запуске модуля
if __name__ == '__main__':
    print("Тестирование RAG Query Engine...")
    test_engine = get_query_engine()
    if test_engine:
        # Изменяем тестовый запрос
        test_query = "Мужчина, 66 лет, пенсия по старости, стаж 12 лет, нет трудовой книжки."
        print(f"\nТестовый запрос: {test_query}")
        result = query_case(test_query)
        print(f"\nРезультат анализа:\n{result}")
    else:
        print("Не удалось инициализировать Query Engine для теста.") 