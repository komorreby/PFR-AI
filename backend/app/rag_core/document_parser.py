import re
import logging
import os
from typing import List, Dict, Tuple, Optional, Any, Set

from llama_index.core import Document
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import SimpleNodeParser

# Импортируем конфиг для доступа к параметрам парсинга
from . import config

logger = logging.getLogger(__name__)

# Глобальный маппинг для атрибутов закона (для пилота)
# В будущем это можно вынести в конфиг или базу данных
LAW_ATTRIBUTES_MAP = {
    "ФЗ-400-ФЗ-28_12_2013.pdf": {
        "title": "Федеральный закон 'О страховых пенсиях'",
        "number": "400-ФЗ",
        "adoption_date": "2013-12-28",
    },
    "ФЗ-166-ФЗ-15_12_2001.pdf": {
        "title": "Федеральный закон 'О государственном пенсионном обеспечении в Российской Федерации'",
        "number": "166-ФЗ",
        "adoption_date": "2001-12-15",
    },
    # Добавить другие законы по мере необходимости
}

def get_law_attributes(file_name: str) -> Dict[str, Optional[str]]:
    """
    Возвращает атрибуты закона на основе имени файла.
    Для пилота используется маппинг.
    """
    base_name = os.path.basename(file_name) # Убедимся, что работаем только с именем файла
    return LAW_ATTRIBUTES_MAP.get(base_name, {
        "title": None, # Или "Неизвестный закон"
        "number": None,
        "adoption_date": None
    })

def normalize_article_number(raw_text: Optional[str], is_main_article_header: bool = False) -> Optional[str]:
    """
    Нормализует текстовое представление номера статьи/пункта для использования в ID.
    `is_main_article_header` = True, если `raw_text` это точно заголовок типа "Статья X"
    Примеры:
    normalize_article_number("Статья 8", True) -> "8"
    normalize_article_number("Статья 8.1", True) -> "8.1"
    normalize_article_number("Пункт 1 Статьи 8", False) -> None (пока, нужна доработка для сложных случаев)
    normalize_article_number("1. ", False) -> "1"
    normalize_article_number("1.2.", False) -> "1-2"
    normalize_article_number("1)", False) -> "1"
    """
    if not raw_text:
        return None

    processed_text = raw_text.strip()
    if is_main_article_header:
        # Ищет: Статья X или Статья X.Y
        match_article = re.search(r"Статья\s+(\d+(?:\.\d+)?)\s*(?:\.|Пункт|Часть|$)?", processed_text, re.IGNORECASE)
        if match_article:
            return match_article.group(1)
    else:
        match_point = re.match(r"^\s*(\d+(?:\.\d+)?)(?:\.|\))(?=\s|$)", processed_text)
        if match_point:
            return match_point.group(1).replace('.', '-')

    log_message = "Could not normalize article/point number from: '{}' (is_main_article_header={})".format(raw_text, is_main_article_header)
    logger.debug(log_message)
    return None

def parse_document_hierarchical(doc: Document) -> List[TextNode]:
    """
    Разбивает текст одного документа иерархически:
    1. По структурным заголовкам (Статья, Глава, Пункт и т.д.) с сохранением метаданных.
    2. Если структурный чанк > MAX_STRUCT_CHUNK_LENGTH (из конфига), он разбивается дальше
       на более мелкие чанки SimpleNodeParser'ом, наследующие метаданные родителя.
    
    Args:
        doc: LlamaIndex Document для парсинга.
        
    Returns:
        Список TextNode для данного документа.
    """
    file_name = doc.metadata.get("file_name", "unknown_file")
    text = doc.get_content()
    logger.debug(f"Parsing document: {file_name} (length: {len(text)}) using hierarchical parser v={config.METADATA_PARSER_VERSION}")

    final_nodes = []
    # Определяем шаблоны для различных типов заголовков
    # Убедитесь, что порядок в словаре не важен, т.к. мы будем искать все совпадения и сортировать их
    header_patterns = {
        'article': r"^\s*(Статья)\s+(\d+(?:\.\d+)*)\s*(?:\.|\s|$)", # Статья X, Статья X.Y, Статья X.Y.Z
        'chapter': r"^\s*(Глава)\s+([\dIVXLCDM]+(?:\.[\dIVXLCDM]+)*)\s*(?:\.|\s|$)", # Глава X, Глава X.Y, Глава IV
        'section': r"^\s*(Раздел)\s+([\dIVXLCDM]+(?:\.[\dIVXLCDM]+)*)\s*(?:\.|\s|$)", # Раздел X, Раздел IV
        # Пункты могут быть более сложными, эта версия ловит основные случаи
        'point': r"^\s*(\d{1,3}(?:\.\d{1,2})*)\s*(?:\.(?![\d])|\))(?=\s|$)", # 1. , 1), 1.2. , 1.2)
        # 'subpoint': r"^\s*(\d{1,3}(?:\.\d+)+)\." # Убрал, т.к. point теперь может покрывать это, либо нужно более точное разграничение
    }
    
    all_matches = []
    for pattern_name, pattern_regex in header_patterns.items():
        for match in re.finditer(pattern_regex, text, re.MULTILINE | re.IGNORECASE):
            all_matches.append({
                "match_obj": match,
                "type": pattern_name,
                "start": match.start(),
                "end": match.end(),
                # Извлекаем основное содержание заголовка (номер/название)
                "content": match.group(2) if pattern_name in ['article', 'chapter', 'section'] else match.group(1)
            })
    
    # Сортируем все найденные заголовки по их начальной позиции в тексте
    all_matches.sort(key=lambda x: x["start"])

    start_pos = 0
    # Начальные метаданные для первого чанка (до первого заголовка)
    current_metadata = {
        "file_name": file_name, 
        "article": None, 
        "chapter": None, 
        "section": None, 
        "point": None, 
        "header": "Начало документа" # Заголовок для первого "структурного" чанка
    }
    
    # Парсер для вторичного разбиения длинных чанков
    secondary_parser = SimpleNodeParser.from_defaults(
        chunk_size=config.SECONDARY_CHUNK_SIZE,
        chunk_overlap=config.SECONDARY_CHUNK_OVERLAP,
        paragraph_separator="\n\n\n" # Используем тройной перенос для большей вероятности разделения абзацев
    )

    struct_chunk_index = 0 # Индекс структурного чанка внутри документа

    for i, match_info in enumerate(all_matches):
        match = match_info["match_obj"]
        header_type = match_info["type"]
        # header_content_val = match_info["content"] # Это номер/название, например, "8" или "IV"
        
        end_pos = match.start()
        struct_chunk_text = text[start_pos:end_pos].strip()
        
        # Формируем полный текст заголовка из объекта match
        full_header_text = match.group(0).strip()

        effective_header = current_metadata.get("header", "Начало документа")
        
        # 1. Обрабатываем структурный чанк ПЕРЕД текущим заголовком
        if struct_chunk_text:
            # Проверяем длину
            if len(struct_chunk_text) > config.MAX_STRUCT_CHUNK_LENGTH:
                # Слишком длинный -> разбиваем вторично
                logger.debug(f"Structural chunk {struct_chunk_index} ('{effective_header}') too long ({len(struct_chunk_text)} chars). Applying secondary splitting.")
                # Передаем метаданные родительского структурного чанка
                sub_docs = [Document(text=struct_chunk_text, metadata=current_metadata.copy())]
                sub_nodes = secondary_parser.get_nodes_from_documents(sub_docs, show_progress=False)
                
                # Добавляем индекс под-чанка к ID и метаданные родителя
                for sub_idx, node in enumerate(sub_nodes):
                    node_id = f"{file_name}_struct_{struct_chunk_index}_sub_{sub_idx}"
                    # Убедимся, что node это TextNode, иначе создадим его
                    if not isinstance(node, TextNode):
                        node = TextNode(
                            text=node.get_content(), 
                            id_=node_id, 
                            metadata=node.metadata # Сохраняем метаданные от парсера
                        )
                    else:
                        node.id_ = node_id
                        
                    node.metadata["parent_header"] = effective_header # Добавляем заголовок родителя
                    final_nodes.append(node)
            else:
                # Нормальная длина -> создаем один узел
                node_id = f"{file_name}_struct_{struct_chunk_index}_full"
                final_nodes.append(TextNode(
                    text=struct_chunk_text,
                    id_=node_id,
                    metadata=current_metadata.copy() # Метаданные относятся к этому блоку
                ))
            struct_chunk_index += 1

        # 2. Обновляем метаданные на основе ТЕКУЩЕГО заголовка для СЛЕДУЮЩЕГО чанка
        # Используем full_header_text, полученный из match.group(0)
        current_metadata["header"] = full_header_text 
        
        # article_number_normalized = normalize_article_number(full_header_text, is_main_article_header=(header_type == 'article'))
        # Вместо normalize_article_number используем content из match_info, если тип 'article'
        if header_type == "article":
            current_metadata["article"] = full_header_text # Например, "Статья 8. Обязательные условия"
            article_number_normalized = match_info["content"] # Это "8" или "8.1" и т.д.
            if article_number_normalized:
                # file_name уже есть в current_metadata или из doc.metadata
                base_file_name = os.path.basename(current_metadata.get("file_name", file_name))
                canonical_id = f"{base_file_name.replace('.pdf', '')}_Ст_{article_number_normalized.replace('.', '-')}"
                current_metadata["canonical_article_id"] = canonical_id
            else:
                current_metadata["canonical_article_id"] = None # Если не удалось определить
            current_metadata["point"] = None # Сбрасываем пункт при новой статье
        elif header_type == "chapter":
            current_metadata["chapter"] = full_header_text
            current_metadata["article"] = None
            current_metadata["canonical_article_id"] = None # Сбрасываем при новой главе
            current_metadata["point"] = None
        elif header_type == "section":
            current_metadata["section"] = full_header_text
            current_metadata["chapter"] = None
            current_metadata["article"] = None
            current_metadata["canonical_article_id"] = None # Сбрасываем при новом разделе
            current_metadata["point"] = None
        elif header_type == "point": 
            current_metadata["point"] = full_header_text
        # elif header_type == "subpoint": # Если будет subpoint
            # current_metadata["point"] = full_header_text # Можно перезаписать или добавить в иерархию

        start_pos = match.end()

    # 3. Обрабатываем последний структурный чанк (от последнего заголовка до конца файла)
    last_struct_chunk_text = text[start_pos:].strip()
    if last_struct_chunk_text:
        last_header = current_metadata.get("header", "Конец документа")
        if len(last_struct_chunk_text) > config.MAX_STRUCT_CHUNK_LENGTH:
            # Слишком длинный -> разбиваем вторично
            logger.debug(f"Last structural chunk ('{last_header}') too long ({len(last_struct_chunk_text)} chars). Applying secondary splitting.")
            sub_docs = [Document(text=last_struct_chunk_text, metadata=current_metadata.copy())]
            sub_nodes = secondary_parser.get_nodes_from_documents(sub_docs, show_progress=False)
            for sub_idx, node in enumerate(sub_nodes):
                node_id = f"{file_name}_struct_{struct_chunk_index}_end_sub_{sub_idx}"
                if not isinstance(node, TextNode):
                     node = TextNode(
                         text=node.get_content(), 
                         id_=node_id, 
                         metadata=node.metadata
                     )
                else:
                    node.id_ = node_id
                node.metadata["parent_header"] = last_header
                final_nodes.append(node)
        else:
            # Нормальная длина -> создаем один узел
            node_id = f"{file_name}_struct_{struct_chunk_index}_end_full"
            final_nodes.append(TextNode(
                text=last_struct_chunk_text,
                id_=node_id,
                metadata=current_metadata.copy()
            ))

    logger.debug(f"Parsed {len(final_nodes)} nodes from document {file_name}.")
    return final_nodes 

def find_pension_type_keywords(text: str, pension_type_map: Dict[str, str], 
                              log_results: bool = False) -> List[Tuple[str, str, str]]:
    """
    Улучшенная функция поиска ключевых слов для определения типов пенсий в тексте.
    Использует различные стратегии поиска для повышения точности.
    
    Args:
        text: Текст, в котором ищем ключевые слова.
        pension_type_map: Словарь маппинга ключевых слов на pension_type_id.
        log_results: Включить детальное логирование результатов поиска.
        
    Returns:
        Список кортежей (pension_type_id, найденное_ключевое_слово, метод_поиска).
    """
    results = []
    
    if not text:
        return results
    
    # 1. Предварительная обработка текста для поиска
    text_lowercase = text.lower()
    text_normalized = re.sub(r'[^\w\s]', ' ', text_lowercase)
    text_normalized = re.sub(r'\s+', ' ', text_normalized).strip()
    
    if log_results:
        logger.debug(f"Анализ текста (первые 100 символов): '{text[:100]}...'")
    
    # 2. Точное совпадение фраз (стандартный поиск)
    for keyword, pension_type_id in pension_type_map.items():
        keyword_lower = keyword.lower()
        regex_pattern = r'\b' + re.escape(keyword_lower) + r'\b'
        
        # Проверяем по стандартному регулярному выражению для границ слов
        if re.search(regex_pattern, text_lowercase, re.IGNORECASE):
            if log_results:
                match_text = re.search(regex_pattern, text_lowercase, re.IGNORECASE).group(0)
                logger.info(f"Найдено точное совпадение для типа пенсии '{pension_type_id}': '{match_text}'")
            results.append((pension_type_id, keyword, 'exact_match'))
            continue
        
        # 3. Поиск для составных фраз (без регулярных выражений)
        if len(keyword_lower.split()) > 1 and keyword_lower in text_lowercase:
            if log_results:
                logger.info(f"Найдено совпадение составной фразы для типа пенсии '{pension_type_id}': '{keyword_lower}'")
            results.append((pension_type_id, keyword, 'phrase_match'))
            continue
        
        # 4. Поиск по словоформам (только для русских слов)
        # Для слов длиннее 4 символов используем основу слова (без окончания)
        # Это упрощенный подход к морфологии русского языка
        words = keyword_lower.split()
        if any(len(word) > 4 for word in words):
            word_stems = []
            for word in words:
                if len(word) > 4:
                    # Используем простое правило для отсечения окончаний
                    if word.endswith(("ая", "ий", "ой", "ых", "их", "ые", "ое")):
                        stem = word[:-2]
                    elif word.endswith(("а", "я", "е", "и", "ы", "у", "ю", "ь")):
                        stem = word[:-1]
                    else:
                        stem = word
                    word_stems.append(stem)
                else:
                    word_stems.append(word)
            
            # Строим регулярное выражение для поиска основы слова
            stem_pattern = r'\b' + r'.*?\b'.join(re.escape(stem) for stem in word_stems) + r'.*?\b'
            if re.search(stem_pattern, text_normalized):
                match_text = re.search(stem_pattern, text_normalized).group(0)
                if log_results:
                    logger.info(f"Найдено сходство по основе слов для типа пенсии '{pension_type_id}': '{match_text}'")
                results.append((pension_type_id, keyword, 'stem_match'))
                continue
    
    # 5. Удаление дубликатов и возврат уникальных результатов
    unique_results = []
    seen_pension_types = set()
    
    for pt_id, keyword, method in results:
        if pt_id not in seen_pension_types:
            unique_results.append((pt_id, keyword, method))
            seen_pension_types.add(pt_id)
    
    return unique_results

def extract_graph_data_from_document(
    parsed_nodes: List[TextNode], # <--- ИЗМЕНЕНО: Принимаем список TextNode
    doc_metadata: Dict[str, Any], # <--- ДОБАВЛЕНО: Метаданные исходного документа (file_name, file_path)
    pension_type_map: Dict[str, str], 
    pension_type_filters: Dict[str, Dict[str, Any]]
) -> Tuple[List[Dict], List[Dict]]:
    """
    Извлекает узлы и ребра для графа знаний из списка распарсенных TextNode документа.
    Анализирует метаданные узлов и их текст для идентификации сущностей (Законы, Статьи, Типы пенсий)
    и связей между ними.

    Args:
        parsed_nodes: Список TextNode, полученный от parse_document_hierarchical.
        doc_metadata: Метаданные исходного LlamaIndex Document (содержит file_name, file_path).
        pension_type_map: Маппинг ключевых слов на канонические ID типов пенсий.
        pension_type_filters: Фильтры для дополнительной логики.

    Returns:
        Кортеж из двух списков: список словарей для узлов и список словарей для ребер.
    """
    nodes = []
    edges = []
    processed_graph_node_ids = set() # Отслеживаем ID уже добавленных в граф узлов (Law, PensionType, Article)

    file_name = doc_metadata.get("file_name", "unknown_file.pdf")
    file_path = doc_metadata.get("file_path", file_name)
    law_id_simple = file_name.replace(".pdf", "")
    
    law_attrs = get_law_attributes(file_name)

    # 1. Создаем узел Закона (если еще не добавлен)
    if law_id_simple not in processed_graph_node_ids:
        law_node = {
            "id": law_id_simple, 
            "label": "Law",
            "properties": {
                "law_id": law_id_simple,
                "title": law_attrs.get("title", f"Закон {law_id_simple}"),
                "number": law_attrs.get("number"),
                "adoption_date": law_attrs.get("adoption_date"),
                "file_path": file_path 
            }
        }
        nodes.append(law_node)
        processed_graph_node_ids.add(law_id_simple)

    # 2. Создаем/проверяем узлы Типов Пенсий.
    # pension_type_map здесь это PENSION_KEYWORD_MAP из конфига (keyword -> pt_id)
    # config.PENSION_TYPE_MAP это pt_id -> human_readable_name
    
    all_known_pension_type_ids = set(config.PENSION_TYPE_MAP.keys()) # Из карты id -> имя
    for pt_id_filter in config.PENSION_TYPE_FILTERS.keys(): # Из конфигурации фильтров
        all_known_pension_type_ids.add(pt_id_filter)
    # Также добавим ID из PENSION_KEYWORD_MAP, если они там есть и еще не учтены
    for pt_id_from_keyword_map in pension_type_map.values():
        all_known_pension_type_ids.add(pt_id_from_keyword_map)
        
    for pt_id in all_known_pension_type_ids:
        if pt_id not in processed_graph_node_ids:
            # Сначала берем имя из PENSION_TYPE_MAP (id -> human_readable_name)
            pt_name = config.PENSION_TYPE_MAP.get(pt_id)
            # Если нет, пытаемся взять из описания фильтра
            if not pt_name and pt_id in pension_type_filters:
                pt_name = pension_type_filters[pt_id].get('description', pt_id)
            # Если имени все еще нет, используем сам ID как имя (крайний случай)
            if not pt_name:
                pt_name = pt_id
            
            nodes.append({
                "id": pt_id,
                "label": "PensionType", 
                "properties": {
                    "pension_type_id": pt_id,
                    "name": pt_name, # Человекочитаемое имя
                    "id": pt_id
                }
            })
            processed_graph_node_ids.add(pt_id)
            logger.debug(f"Ensured PensionType node exists: {pt_id} with name '{pt_name}'")


    # Переменная для хранения ID статьи, к которой будет привязано демо-условие
    target_article_id_for_demo_condition = f"{law_id_simple}_Ст_8" # Пример для Статьи 8 ФЗ-400
    demo_condition_created = False

    # 3. Итерируемся по TextNode, полученным от parse_document_hierarchical
    for text_node in parsed_nodes: # text_node это TextNode с метаданными
        chunk_text = text_node.get_content()
        
        current_canonical_article_id = text_node.metadata.get("canonical_article_id")
        article_title_from_meta = text_node.metadata.get("article") # "Статья X"

        if current_canonical_article_id and current_canonical_article_id not in processed_graph_node_ids:
            # Определяем номер статьи из ID, если article_title_from_meta неполный
            default_number_text = f"Статья {current_canonical_article_id.split('_Ст_')[-1].replace('-', '.')}"
            
            article_node_props = {
                "article_id": current_canonical_article_id, # Это уже canonical_article_id
                "number_text": article_title_from_meta if article_title_from_meta else default_number_text,
                 # "title": article_title_from_meta # TODO: Извлекать полное название статьи, если возможно
            }
            # Попытка извлечь название статьи из текста чанка (если это первый чанк статьи)
            # Это очень упрощенная логика, требует улучшения
            if article_title_from_meta and len(chunk_text) < 500: # Предполагаем, что заголовок в коротком чанке
                lines = chunk_text.split('\n')
                if lines[0].strip().startswith(article_title_from_meta):
                    article_full_title_match = re.match(r"^Статья\s+\d+(?:\.\d+)?\s*\.?\s*(.*)", lines[0].strip())
                    if article_full_title_match and article_full_title_match.group(1):
                        article_node_props["title"] = article_full_title_match.group(1).strip()


            article_node = {
                "id": current_canonical_article_id,
                "label": "Article",
                "properties": article_node_props
            }
            nodes.append(article_node)
            processed_graph_node_ids.add(current_canonical_article_id)
            logger.debug(f"Created Article node: {current_canonical_article_id} with props: {article_node_props}")


            # Связь Закон -> Статья
            edges.append({
                "source_id": law_id_simple,
                "target_id": current_canonical_article_id,
                "type": "CONTAINS_ARTICLE",
                "properties": {}
            })
            logger.debug(f"Created edge Law '{law_id_simple}' -> Article '{current_canonical_article_id}'")


            # ==== ДЕМОНСТРАЦИОННАЯ ЛОГИКА для EligibilityCondition ====
            if current_canonical_article_id == target_article_id_for_demo_condition and not demo_condition_created:
                demo_condition_id = f"demo_cond_for_{current_canonical_article_id}"
                if demo_condition_id not in processed_graph_node_ids:
                    nodes.append({
                        "id": demo_condition_id,
                        "label": "EligibilityCondition",
                        "properties": {
                            "description": "Демонстрационное условие: наличие северного стажа",
                            "value": "15 лет",
                            "id": demo_condition_id 
                        }
                    })
                    processed_graph_node_ids.add(demo_condition_id)

                    edges.append({
                        "source_id": current_canonical_article_id,
                        "target_id": demo_condition_id,
                        "type": "DEFINES_CONDITION",
                        "properties": {}
                    })
                    
                    target_pension_type_id_for_demo = "retirement_standard"
                    # Узел PensionType 'retirement_standard' должен быть уже создан выше
                    
                    edges.append({
                        "source_id": demo_condition_id,
                        "target_id": target_pension_type_id_for_demo,
                        "type": "APPLIES_TO_PENSION_TYPE",
                        "properties": {}
                    })
                    demo_condition_created = True
                    logger.info(f"Created demo EligibilityCondition '{demo_condition_id}' for article '{current_canonical_article_id}' linked to pension type '{target_pension_type_id_for_demo}'.")
            # ==== КОНЕЦ ДЕМОНСТРАЦИОННОЙ ЛОГИКИ ====

        # Логика связывания Статьи с Типом Пенсии на основе текста
        # Это должно происходить для КАЖДОГО чанка, так как статья может упоминать типы пенсий в разных своих частях.
        # Но связь создаем от УЗЛА СТАТЬИ (current_canonical_article_id), если он определен для этого чанка.
        if current_canonical_article_id: # Убедимся, что мы находимся в контексте известной статьи
            logger.debug(f"Attempting to link Article ID: {current_canonical_article_id} to PensionTypes based on chunk content.")
            logger.debug(f"Chunk text (first 300 chars for Article ID {current_canonical_article_id}): {chunk_text[:300]}")
            
            # УЛУЧШЕНИЕ: Используем новую функцию для более точного поиска ключевых слов
            pension_type_matches = find_pension_type_keywords(
                chunk_text, 
                pension_type_map=pension_type_map, # Это уже PENSION_KEYWORD_MAP, переданный в функцию
                log_results=True
            )
            
            for pension_type_id, keyword, method in pension_type_matches:
                logger.info(f"Keyword '{keyword}' FOUND (method: {method}) in chunk for Article ID {current_canonical_article_id}. Attempting to create edge to PensionType '{pension_type_id}'.")
                # Проверяем, нет ли уже такой связи для этой статьи и этого типа пенсии
                edge_exists = any(
                    edge.get("source_id") == current_canonical_article_id and \
                    edge.get("target_id") == pension_type_id and \
                    edge.get("type") == "RELATES_TO_PENSION_TYPE"
                    for edge in edges
                )
                if not edge_exists:
                    edges.append({
                        "source_id": current_canonical_article_id,
                        "target_id": pension_type_id,
                        "type": "RELATES_TO_PENSION_TYPE",
                        "properties": {
                            "keyword": keyword,
                            "match_method": method,
                            "confidence": 0.9 if method == 'exact_match' else 0.8 if method == 'phrase_match' else 0.7
                        }
                    })
                    logger.debug(f"Created edge Article '{current_canonical_article_id}' -> PensionType '{pension_type_id}' based on keyword '{keyword}' (method: {method})")
                else:
                    logger.debug(f"Edge Article '{current_canonical_article_id}' -> PensionType '{pension_type_id}' already exists or planned. Skipping.")
            
            # Если не нашли соответствия по новому методу, используем старый для совместимости
            if not pension_type_matches:
                for keyword, pension_type_id_mapped in pension_type_map.items(): # pension_type_map это PENSION_KEYWORD_MAP
                    logger.debug(f"Article {current_canonical_article_id}: Searching for keyword '{keyword}' (maps to PensionType ID: {pension_type_id_mapped})")
                    # Используем r'\b' для поиска целых слов, чтобы избежать частичных совпадений
                    if re.search(r'\b' + re.escape(keyword) + r'\b', chunk_text, re.IGNORECASE):
                        logger.info(f"Keyword '{keyword}' FOUND in chunk for Article ID {current_canonical_article_id}. Attempting to create edge to PensionType '{pension_type_id_mapped}'.")
                        # Узел PensionType должен был быть создан ранее
                        
                        # Проверяем, нет ли уже такой связи для этой статьи и этого типа пенсии
                        edge_exists = any(
                            edge.get("source_id") == current_canonical_article_id and \
                            edge.get("target_id") == pension_type_id_mapped and \
                            edge.get("type") == "RELATES_TO_PENSION_TYPE"
                            for edge in edges
                        )
                        if not edge_exists:
                            edges.append({
                                "source_id": current_canonical_article_id,
                                "target_id": pension_type_id_mapped,
                                "type": "RELATES_TO_PENSION_TYPE",
                                "properties": {
                                    "keyword": keyword,
                                    "match_method": "legacy_exact",
                                    "confidence": 0.8
                                }
                            })
                            logger.debug(f"Created edge Article '{current_canonical_article_id}' -> PensionType '{pension_type_id_mapped}' based on keyword '{keyword}' using legacy method.")
                        else:
                            logger.debug(f"Edge Article '{current_canonical_article_id}' -> PensionType '{pension_type_id_mapped}' already exists or planned. Skipping.")
                    else:
                        logger.debug(f"Keyword '{keyword}' NOT FOUND in chunk for Article ID {current_canonical_article_id}.")
        else:
            logger.debug(f"Skipping PensionType linking for chunk because current_canonical_article_id is not set. Chunk text (first 100): {chunk_text[:100]}")
    
    final_node_count = len([n for n in nodes if n['id'] in processed_graph_node_ids]) # Считаем только уникальные добавленные узлы
    logger.info(f"Extracted {final_node_count} unique nodes and {len(edges)} edges from document {file_name}.")
    
    if not demo_condition_created and target_article_id_for_demo_condition in processed_graph_node_ids:
        # Эта проверка нужна, если target_article_id_for_demo_condition - это ID узла Article, который был создан
        pass # Логика уже есть выше, но можно уточнить
    elif not demo_condition_created and target_article_id_for_demo_condition not in processed_graph_node_ids:
        logger.warning(f"Target article for demo condition ('{target_article_id_for_demo_condition}') was not found among processed article IDs. Demo condition not created. Processed IDs: {processed_graph_node_ids}")

    return nodes, edges

# TODO: Для реального использования, эта функция должна быть значительно сложнее.
# Она должна анализировать семантику текста для корректного извлечения условий,
# их значений и связей с типами пенсий.
# Например, "мужчины, достигшие возраста 65 лет" -> 
#   Condition(description="возраст", value="65 лет", applies_to_gender="male")
#   APPLIES_TO_PENSION_TYPE -> "Страховая пенсия по старости"