# backend/app/rag_core/document_parser.py

import re
import logging
from typing import List

from llama_index.core import Document
from llama_index.core.schema import TextNode
from llama_index.core.node_parser import SimpleNodeParser

# Импортируем конфиг для доступа к параметрам парсинга
from . import config

logger = logging.getLogger(__name__)


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
    # Regex для поиска структурных заголовков
    # (Изменено для большей точности, например, чтобы не захватывать "ст. 1" как статью 1)
    pattern = r"^\s*(?:(Статья)\s+(\d+)(?:\.\d+)?(?:\.\s|\s|$)|(Глава)\s+(\d+)(?:\.\s|\s|$)|(Раздел)\s+([IVXLCDM]+)(?:\.\s|\s|$)|(\d{1,3})(?:\.(?=\s)|\)(?=\s))|(?:^\s*(\d{1,3}\.\d{1,2})\.))"
    
    # pattern = r"^\s*((Статья)\s+(\d+)\.?.*|(Глава)\s+(\d+)\.?.*|(Раздел)\s+([IVXLC]+)\.?.*|(\d{1,3})\.\s.*|(\d{1,3})[\)\.]\s.*|(\d{1,3}\.\d{1,2})\.\s.*)" # Старый вариант

    matches = list(re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE))

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

    for i, match in enumerate(matches):
        end_pos = match.start()
        struct_chunk_text = text[start_pos:end_pos].strip()
        
        # Определяем тип заголовка и его текст
        header_type = "unknown"
        header_content = ""
        # Важно проверять группы в правильном порядке, соответствующем регулярному выражению
        if match.group(1): # Статья
            header_type = "article"
            header_content = f"Статья {match.group(2)}"
        elif match.group(3): # Глава
            header_type = "chapter"
            header_content = f"Глава {match.group(4)}"
        elif match.group(5): # Раздел
            header_type = "section"
            header_content = f"Раздел {match.group(6)}"
        elif match.group(7): # Пункт X. или X)
            header_type = "point"
            header_content = f"Пункт {match.group(7)}"
        elif match.group(8): # Пункт X.Y.
            header_type = "subpoint"
            header_content = f"Пункт {match.group(8)}"
        else:
             # Если не удалось определить тип, используем весь захваченный текст
             header_content = match.group(0).strip()

        effective_header = current_metadata.get("header", "Начало документа") # Заголовок предыдущего блока
        
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
        # Используем header_content, полученный ранее
        current_metadata["header"] = header_content
        # Сбрасываем более низкие уровни иерархии при установке более высокого
        if header_type == "article":
            current_metadata["article"] = header_content
            current_metadata["point"] = None # Сбрасываем пункт при новой статье
        elif header_type == "chapter":
            current_metadata["chapter"] = header_content
            current_metadata["article"] = None
            current_metadata["point"] = None
        elif header_type == "section":
            current_metadata["section"] = header_content
            current_metadata["chapter"] = None
            current_metadata["article"] = None
            current_metadata["point"] = None
        elif header_type == "point":
            # Обновляем пункт, сохраняя статью/главу/раздел
             current_metadata["point"] = header_content
        elif header_type == "subpoint":
             # Обработка подпунктов вида X.Y. - можем сохранить как строку
             current_metadata["point"] = header_content # Перезаписываем предыдущий 'point'

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