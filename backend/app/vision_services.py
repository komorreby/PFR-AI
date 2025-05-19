# app/vision_services.py
import logging
from typing import Optional, Union, Dict, Any, List, Tuple
import base64
import json
import re
from datetime import datetime, date

import httpx # <--- ДОБАВЛЕН ИМПОРТ
import ollama # Используем официальный клиент Ollama
from fastapi import HTTPException # <--- ДОБАВЛЕН ИМПОРТ HTTPException
from pydantic import BaseModel # Убедимся, что BaseModel импортирован

from .rag_core import config # Импорт конфигурации
from .models import PassportData, SnilsData, DocumentTypeToExtract, OtherDocumentData, PENSION_DOCUMENT_TYPES # Импорт моделей данных

logger = logging.getLogger(__name__)

# Промпт для LLM (паспорт)
PASSPORT_EXTRACTION_PROMPT = """Извлеки, пожалуйста, всю информацию из этого изображения паспорта РФ. Мне нужны: серия и номер паспорта, фамилия, имя, отчество, пол, дата рождения, место рождения (постарайся извлечь как можно полнее, включая город, регион, республику, если указано), кем выдан, дата выдачи, код подразделения.
Представь ответ в формате JSON. Пример:
{
  "passport_series": "1234",
  "passport_number": "567890",
  "last_name": "Иванов",
  "first_name": "Иван",
  "middle_name": "Иванович",
  "gender": "Мужской",
  "birth_date": "01.01.1980",
  "birth_place": "г. Москва, Российская Федерация",
  "issued_by": "ОВД 'Хорошево-Мневники' г. Москвы",
  "issue_date": "01.01.2010",
  "department_code": "770-123"
}
Убедись, что все поля присутствуют в ответе, даже если они пустые (null). 
**Очень важно правильно извлечь серию и номер паспорта. Ищи их в области, напечатанной вертикально красным цветом справа от фотографии.**
**Серия паспорта (`passport_series`) - это первые 4 цифры в этой вертикальной красной надписи.** Представляй серию паспорта всегда как строку из 4 цифр. Например, если видишь на документе серию '81 23' в этой красной вертикальной области, в JSON поле `passport_series` должно быть '8123'. Если видишь '56 78', верни '5678'. Категорически не используй дефисы в значении для `passport_series`. Значение `passport_series` не должно выглядеть как код подразделения (например, '030-003' – это НЕ серия, это код подразделения). Убедись, что `passport_series` содержит именно 4-значную серию паспорта из вертикальной красной области, а не код подразделения. Код подразделения (`department_code`) ищи отдельно, он обычно расположен горизонтально.
**Номер паспорта (`passport_number`) - это следующие 6 цифр в той же вертикальной красной надписи, после серии.** Он также должен быть представлен как строка из 6 цифр.
"""

# Промпт для LLM (СНИЛС)
SNILS_EXTRACTION_PROMPT = """Извлеки, пожалуйста, всю информацию из этого изображения СНИЛС. Мне нужны: фамилия, имя, отчество, пол, дата рождения, место рождения и номер СНИЛС.
Представь ответ в формате JSON. Пример:
{
  "last_name": "Иванов",
  "first_name": "Иван",
  "middle_name": "Иванович",
  "gender": "Мужской",
  "birth_date": "01.01.1980",
  "birth_place": "г. Москва",
  "snils_number": "123-456-789 00"
}
Убедись, что все поля присутствуют в ответе, даже если они пустые (null).
"""

# Промпт для LLM (Другие документы) - qwen2.5vl
OTHER_DOCUMENT_EXTRACTION_PROMPT = """Это изображение документа. Пожалуйста, внимательно изучи его и предоставь следующую информацию в формате JSON:
1.  **identified_document_type**: Определи и укажи точный тип документа (например, "Свидетельство о рождении", "Водительское удостоверение", "Договор аренды", "Справка с места работы", "Свидетельство о браке", "Диплом об образовании", "Медицинская справка", "Технический паспорт" и т.д.). Будь как можно более точным.
2.  **extracted_fields**: Извлеки все значимые поля и их значения из документа в виде словаря ключ-значение. Например, для свидетельства о рождении это могут быть ФИО ребенка, дата рождения, место рождения, ФИО родителей и т.д. Для договора - стороны договора, предмет договора, даты, суммы. Для справки - кем выдана, кому, содержание справки. Адаптируй ключи в зависимости от типа документа.
3.  **multimodal_assessment**: Дай краткую оценку изображения документа: его общее качество, читаемость текста, наличие видимых дефектов или искажений. (например, "Хорошее качество, текст четкий", "Среднее качество, есть небольшие размытия", "Низкое качество, текст трудночитаем").
4.  **raw_text**: Извлеки весь текст, который ты видишь на документе.

Вот структура JSON, которую ты должен вернуть:
```json
{
  "identified_document_type": "...",
  "extracted_fields": {
    "ключ1": "значение1",
    "ключ2": "значение2"
  },
  "multimodal_assessment": "...",
  "raw_text": "..."
}
```
Всегда возвращай все четыре ключа: `identified_document_type`, `extracted_fields`, `multimodal_assessment`, `raw_text`.
Если какое-то поле не удалось извлечь или оно неприменимо, используй null или пустую строку/словарь для соответствующего значения, но ключ должен присутствовать.
"""

def _extract_json_from_text(text: str) -> Optional[str]:
    """Извлекает JSON объект из текста, обернутого в ```json ... ``` или просто находящегося в тексте."""
    if not text:
        return None
    # Сначала ищем JSON, обернутый в ```json ... ```
    json_match_markdown = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match_markdown:
        return json_match_markdown.group(1)
    
    # Если не нашли в markdown, ищем первый попавшийся валидный JSON объект (от { до })
    # Это менее надежно, но может сработать для ответов, где LLM не использует markdown
    # Ищем наиболее "полный" JSON объект, начиная с первой { и заканчивая последней }
    # Это попытка избежать проблем с вложенными объектами или несколькими JSON в тексте (хотя ожидается один)
    potential_json_matches = re.findall(r"(\{.*?\})", text, re.DOTALL)
    if potential_json_matches:
        # Пытаемся вернуть наиболее "внешний" или первый полный JSON
        # Для простоты пока вернем первый найденный, который может быть распарсен
        for match in potential_json_matches:
            try:
                json.loads(match) # Проверяем, валидный ли это JSON
                return match
            except json.JSONDecodeError:
                continue
        logger.warning(f"Found JSON-like structures, but none could be parsed: {potential_json_matches}")
        return None

    logger.warning(f"Could not find JSON in text: {text[:500]}...") # Логируем только начало текста
    return None

def _parse_llm_json_safely(json_string: str, document_type_value: str) -> Optional[Dict[str, Any]]:
    """Безопасно парсит JSON строку от LLM, обрабатывая возможные ошибки."""
    try:
        data = json.loads(json_string)
        if not isinstance(data, dict):
            logger.error(f"Parsed JSON is not a dictionary for {document_type_value}. Got: {type(data)}. String: {json_string}")
            return None
        return data
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError while parsing LLM response for {document_type_value}: {e}. String: {json_string}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while parsing LLM response for {document_type_value}: {e}. String: {json_string}")
        return None

def parse_date_flexible(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    formats_to_try = ["%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"]
    for fmt in formats_to_try:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    logger.warning(f"Не удалось распознать строку с датой '{date_str}' ни одним из форматов. Возвращено None.")
    return None

async def get_reasoning_and_standardized_type_from_text_llm(
    extracted_data_from_multimodal: Dict[str, Any], 
    document_image_description: str,
    standard_document_types_list: List[str] # <--- Добавлен список стандартных типов
) -> Tuple[str, Optional[str]]: # Возвращает (текст осмысления, стандартизированный тип)
    """
    Получает "осмысление" от текстовой LLM и просит ее выбрать стандартизированный тип документа.
    """
    default_reasoning = "Текстовая LLM не предоставила осмысление."
    standardized_type_by_llm = None
    try:
        client = ollama.AsyncClient(
            host=config.OLLAMA_BASE_URL,
            timeout=config.LLM_REQUEST_TIMEOUT
        )
        
        identified_type = extracted_data_from_multimodal.get("identified_document_type", "Неизвестный тип документа")
        fields = extracted_data_from_multimodal.get("extracted_fields", {})
        raw_text_from_vision = extracted_data_from_multimodal.get("raw_text", "")
        multimodal_assessment = extracted_data_from_multimodal.get("multimodal_assessment", "")

        prompt_parts = [
            f"Проанализируй следующую информацию о документе. Мультимодальная модель (qwen-vl) предоставила следующие данные:",
            f"- Описание изображения: '{document_image_description}'.",
            f"- Предполагаемый тип документа (от qwen-vl): '{identified_type}'.",
        ]
        if multimodal_assessment:
            prompt_parts.append(f"- Оценка изображения от qwen-vl: '{multimodal_assessment}'.")

        if fields:
            prompt_parts.append("- Извлеченные поля и их значения (от qwen-vl):")
            prompt_parts.append(json.dumps(fields, ensure_ascii=False, indent=2))
        else:
            prompt_parts.append("- Значимые поля из документа не были извлечены qwen-vl или отсутствуют.")

        if raw_text_from_vision:
             prompt_parts.append("\n- Полный извлеченный текст с изображения (OCR от qwen-vl):")
             prompt_parts.append(raw_text_from_vision)
        else:
            prompt_parts.append("\n- Текст с изображения не был извлечен qwen-vl.")

        prompt_parts.append(f"\nТвоя задача как текстовой LLM ({config.OLLAMA_LLM_MODEL_NAME}):")
        prompt_parts.append("1. Дать развернутое осмысление этого документа. Основываясь на всей предоставленной информации (тип от qwen-vl, поля, OCR-текст, описание, оценка изображения):")
        prompt_parts.append("   a. Каков наиболее вероятный истинный тип этого документа и его основное назначение?")
        prompt_parts.append("   b. Насколько полны и корректны извлеченные qwen-vl данные? Есть ли что-то, что вызывает сомнения, требует проверки или было пропущено qwen-vl?")
        prompt_parts.append("   c. Любые другие важные наблюдения или выводы по документу.")
        prompt_parts.append("2. После основного анализа, выбери наиболее подходящий стандартизированный тип для этого документа из следующего списка.")
        prompt_parts.append("   Список стандартных типов:")
        for doc_type_item in standard_document_types_list:
            prompt_parts.append(f"   - {doc_type_item}")
        prompt_parts.append("   Если точного совпадения нет, выбери наиболее близкий по смыслу. Если ни один из предложенных типов не подходит, укажи 'null'.")
        prompt_parts.append("   В конце своего ответа, ПОСЛЕ основного текста осмысления, ОБЯЗАТЕЛЬНО добавь строку в следующем формате: ")
        prompt_parts.append("   Стандартизированный тип документа: [название из списка или null]")
        prompt_parts.append("\nОтветь подробно и по пунктам, если это уместно для основного осмысления.")

        text_llm_prompt = "\n".join(prompt_parts)

        logger.debug(f"Text LLM ({config.OLLAMA_LLM_MODEL_NAME}) prompt (начало): {text_llm_prompt[:1000]}...")
        logger.debug(f"Text LLM ({config.OLLAMA_LLM_MODEL_NAME}) prompt (конец): ...{text_llm_prompt[-500:]}")

        response = await client.generate(
            model=config.OLLAMA_LLM_MODEL_NAME,
            prompt=text_llm_prompt
        )
        
        full_reasoning_text = response.get("response", "").strip()
        logger.debug(f"Text LLM ({config.OLLAMA_LLM_MODEL_NAME}) full response: {full_reasoning_text}")
        
        if not full_reasoning_text:
            logger.warning(f"Text LLM ({config.OLLAMA_LLM_MODEL_NAME}) returned an empty response.")
            return default_reasoning, None

        # Извлечение стандартизированного типа
        match = re.search(r"(?:\*\*)?Стандартизированный тип документа(?:\*\*)?:\s*(.+)", full_reasoning_text, re.IGNORECASE)
        if match:
            full_matched_text = match.group(1).strip()
            extracted_type_str = None # Инициализируем как None

            # Пытаемся найти один из стандартных типов в полученном тексте
            for doc_type in standard_document_types_list:
                # Создаем паттерн для поиска типа, возможно обернутого в кавычки или звездочки
                # Обычные кавычки, ёлочки «», звездочки **
                # re.escape для самого типа, чтобы специальные символы в названии типа не ломали regex
                pattern = r"(?:\*\*|['\"\\u00AB])?\s*" + re.escape(doc_type) + r"\s*(?:\*\*|['\"\\u00BB])?"
                if re.search(pattern, full_matched_text, re.IGNORECASE):
                    extracted_type_str = doc_type # Нашли, присваиваем
                    break # Выходим из цикла, так как тип найден
            
            if not extracted_type_str:
                # Если точное совпадение не найдено в тексте, проверяем, не является ли весь текст 'null'
                # Очищаем full_matched_text от возможных Markdown символов по краям для проверки на 'null'
                cleaned_full_matched_text = full_matched_text.strip(" *_~`\"'\u00AB\u00BB") # Добавил ёлочки и сюда
                if cleaned_full_matched_text.lower() == 'null':
                    extracted_type_str = 'null' # Устанавливаем в 'null' для дальнейшей обработки

            logger.debug(f"Извлеченный стандартизированный тип (после поиска в тексте): '{extracted_type_str}' из '{full_matched_text}'")

            if extracted_type_str and extracted_type_str.lower() == 'null':
                standardized_type_by_llm = None
            elif extracted_type_str and extracted_type_str in standard_document_types_list:
                standardized_type_by_llm = extracted_type_str
            else:
                logger.warning(f"LLM вернула текст '{full_matched_text}', из которого не удалось извлечь валидный стандартный тип или 'null'. Игнорируем.")
                standardized_type_by_llm = None 
            
            reasoning_text_final = re.sub(r"(?:\*\*)?Стандартизированный тип документа(?:\*\*)?:\s*.+", "", full_reasoning_text, flags=re.IGNORECASE).strip()
            if not reasoning_text_final and standardized_type_by_llm: # если остался только выбор типа
                reasoning_text_final = f"LLM выбрала стандартный тип: {standardized_type_by_llm}, но не предоставила дополнительного осмысления."
            elif not reasoning_text_final:
                 reasoning_text_final = default_reasoning
            return reasoning_text_final, standardized_type_by_llm
        else:
            logger.warning(f"Не удалось извлечь 'Стандартизированный тип документа:' из ответа LLM: {full_reasoning_text[-300:]}")
            return full_reasoning_text, None # Возвращаем весь текст как есть, тип не извлечен

    except httpx.TimeoutException as e:
        logger.error(f"Timeout error interacting with text LLM ({config.OLLAMA_LLM_MODEL_NAME}): {e}")
        return f"Ошибка таймаута при получении осмысления от текстовой LLM: {str(e)}", None
    except Exception as e:
        logger.error(f"Error interacting with text LLM ({config.OLLAMA_LLM_MODEL_NAME}): {e}", exc_info=True)
        return f"Ошибка при получении осмысления от текстовой LLM: {str(e)}", None

def _clean_passport_series(series: Optional[str]) -> Optional[str]:
    if series:
        s = str(series).strip()

        # 1. Ищем формат XX XX или XXXX (две группы по две цифры или четыре цифры подряд)
        #    Это наиболее стандартные форматы серии.
        match_dd_dd = re.search(r'^(\d{2})\s*(\d{2})$', s) # Строго 2 цифры, пробел (опц), 2 цифры
        if match_dd_dd:
            return match_dd_dd.group(1) + match_dd_dd.group(2)

        match_dddd = re.search(r'^(\d{4})$', s) # Строго 4 цифры
        if match_dddd:
            return match_dddd.group(1)

        # 2. Если строка содержит дефис (например, "030-03" или "12-34")
        #    Это не стандартный формат для серии паспорта РФ. 
        #    LLM могла ошибиться или передать сюда код подразделения.
        #    В таком случае, чтобы избежать неверной обработки, лучше вернуть None.
        #    Предыдущая логика пыталась из "030-03" сделать "0300", что может быть неверно.
        if '-' in s:
            # Можно попробовать извлечь цифры, если формат типа "XX-XX" -> "XXXX"
            # Но "030-03" не подходит под это.
            # Для "12-34" можно было бы сделать "1234"
            parts = s.split('-')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                combined = parts[0] + parts[1]
                if len(combined) == 4:
                    return combined # Например, для "12-34" -> "1234"
            
            # Если это не "XX-XX" или другой явно обрабатываемый случай с дефисом,
            # и строка не подошла под dddd или dd dd, то это, вероятно, не серия.
            # Особенно если LLM вернула то же самое для кода подразделения.
            logger.warning(f"Серия паспорта '{s}' содержит дефис и не соответствует стандартным форматам. Возвращено None.")
            return None

        # 3. Если ничего из вышеперечисленного не подошло, но строка состоит только из 4 цифр 
        #    (после удаления пробелов, например, если LLM дала " 1234 ")
        cleaned_s = re.sub(r'\s+', '', s)
        if cleaned_s.isdigit() and len(cleaned_s) == 4:
            return cleaned_s
        
        # Если дошли сюда, не смогли распознать серию
        logger.warning(f"Не удалось извлечь корректную серию паспорта из '{s}'. Возвращено None.")
    return None

def _clean_passport_number(number: Optional[str]) -> Optional[str]:
    if number:
        cleaned = re.sub(r'\s+', '', str(number))
        if cleaned.isdigit() and len(cleaned) >= 6:
            return cleaned[-6:] # Берем последние 6 цифр, на случай если в номере было что-то еще
        # Если после удаления пробелов это не просто цифры или их меньше 6,
        # пробуем найти 6 цифр подряд в оригинальной строке
        match = re.search(r'(\d{6})', str(number))
        if match:
            return match.group(1)
    return None

def _clean_snils_number(snils_number: Optional[str]) -> Optional[str]:
    if snils_number:
        # Удаляем все нецифровые символы
        cleaned = re.sub(r"[^0-9]", "", str(snils_number))
        if len(cleaned) == 11: # СНИЛС должен содержать 11 цифр
            return cleaned
    return None

async def extract_document_data_from_image(
    image_bytes: bytes,
    document_type: DocumentTypeToExtract,
    filename: Optional[str] = "image.png" # Используется для описания в текстовой LLM
) -> Union[PassportData, SnilsData, OtherDocumentData, Dict[str, Any]]:
    """
    Извлекает данные из изображения документа с помощью мультимодальной LLM Ollama,
    обрабатывает ответ и возвращает Pydantic модель.
    Для типа 'OTHER' дополнительно вызывает текстовую LLM для "осмысления".
    """
    try:
        base64_image_string = base64.b64encode(image_bytes).decode("utf-8")
        
        client = ollama.AsyncClient(
            host=config.OLLAMA_BASE_URL, 
            timeout=config.MULTIMODAL_LLM_REQUEST_TIMEOUT
        )

        prompt = ""
        if document_type == DocumentTypeToExtract.PASSPORT:
            prompt = PASSPORT_EXTRACTION_PROMPT
            logger.info(f"Отправка изображения в модель Ollama ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) для ПАСПОРТА.")
        elif document_type == DocumentTypeToExtract.SNILS:
            prompt = SNILS_EXTRACTION_PROMPT
            logger.info(f"Отправка изображения в модель Ollama ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) для СНИЛС.")
        elif document_type == DocumentTypeToExtract.OTHER:
            prompt = OTHER_DOCUMENT_EXTRACTION_PROMPT
            logger.info(f"Отправка изображения в модель Ollama ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) для ДРУГОГО документа.")
        else:
            logger.error(f"Unknown document type for multimodal LLM: {document_type}")
            raise HTTPException(status_code=400, detail=f"Unknown document type: {document_type}")

        logger.info(
            f"Sending request to Ollama Multimodal LLM ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) "
            f"for document type: {document_type.value}. Filename: {filename}"
        )
        
        # Используем messages API для qwen-vl, так как он лучше работает с multimodal
        response_vision = await client.chat(
            model=config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [base64_image_string]
            }]
        )
        
        raw_response_text_vision = response_vision.get("message", {}).get("content", "")
        logger.debug(f"Raw response from Ollama Multimodal LLM ({document_type.value}): {raw_response_text_vision}")

        if not raw_response_text_vision:
            logger.error(f"Received empty response from Ollama Multimodal LLM for {document_type.value}.")
            raise HTTPException(
                status_code=502,
                detail=f"Received empty response from Ollama Multimodal LLM for {document_type.value}.",
            )

        json_content_str_vision = _extract_json_from_text(raw_response_text_vision)
        if not json_content_str_vision:
            logger.error(
                f"Could not extract JSON from Ollama Multimodal LLM response for {document_type.value}: {raw_response_text_vision[:500]}..."
            )
            raise HTTPException(
                status_code=502,
                detail=f"Failed to parse JSON structure from Ollama Multimodal LLM response for {document_type.value}.",
            )

        parsed_multimodal_data = _parse_llm_json_safely(json_content_str_vision, document_type.value)
        if not parsed_multimodal_data:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to parse JSON data from LLM response after extraction for {document_type.value}.",
            )

        if document_type == DocumentTypeToExtract.PASSPORT:
            return PassportData(
                passport_series=_clean_passport_series(parsed_multimodal_data.get("passport_series")),
                passport_number=_clean_passport_number(parsed_multimodal_data.get("passport_number")),
                last_name=parsed_multimodal_data.get("last_name"),
                first_name=parsed_multimodal_data.get("first_name"),
                middle_name=parsed_multimodal_data.get("middle_name"),
                sex=parsed_multimodal_data.get("gender"),
                birth_date=parse_date_flexible(parsed_multimodal_data.get("birth_date")),
                birth_place=parsed_multimodal_data.get("birth_place"),
                issuing_authority=parsed_multimodal_data.get("issued_by"),
                issue_date=parse_date_flexible(parsed_multimodal_data.get("issue_date")),
                department_code=parsed_multimodal_data.get("department_code"),
            )
        elif document_type == DocumentTypeToExtract.SNILS:
            return SnilsData(
                snils_number=_clean_snils_number(parsed_multimodal_data.get("snils_number")),
            )
        elif document_type == DocumentTypeToExtract.OTHER:
            identified_type_from_vision_llm = parsed_multimodal_data.get("identified_document_type")
            
            image_description = f"Изображение документа '{filename}'"
            if identified_type_from_vision_llm:
                image_description += f", предварительно идентифицированного qwen-vl как '{identified_type_from_vision_llm}'"
            
            data_for_text_llm = {
                "identified_document_type": identified_type_from_vision_llm,
                "extracted_fields": parsed_multimodal_data.get("extracted_fields"),
                "raw_text": parsed_multimodal_data.get("raw_text"),
                "multimodal_assessment": parsed_multimodal_data.get("multimodal_assessment")
            }

            # Вызываем обновленную функцию, которая теперь также возвращает стандартизированный тип
            text_reasoning, standardized_type_from_text_llm = await get_reasoning_and_standardized_type_from_text_llm(
                extracted_data_from_multimodal=data_for_text_llm,
                document_image_description=image_description,
                standard_document_types_list=PENSION_DOCUMENT_TYPES # Передаем список сюда
            )
            
            return OtherDocumentData(
                identified_document_type=identified_type_from_vision_llm,
                standardized_document_type=standardized_type_from_text_llm, # <--- Тип от qwen3
                extracted_fields=parsed_multimodal_data.get("extracted_fields"),
                multimodal_assessment=parsed_multimodal_data.get("multimodal_assessment"),
                text_llm_reasoning=text_reasoning
            )
        else: # На случай если DocumentTypeToExtract расширится без обновления этой функции
            logger.critical(f"Необработанный DocumentTypeToExtract в конце функции: {document_type.value}")
            raise HTTPException(status_code=500, detail="Internal server error: Unhandled document type.")

    except httpx.ReadTimeout:
        logger.error(
            f"Ollama Multimodal LLM ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) read timeout "
            f"for document type: {document_type.value}"
        )
        raise HTTPException(
            status_code=504, # Gateway Timeout
            detail=f"Request to Ollama Multimodal LLM timed out for {document_type.value}.",
        )
    except ollama.ResponseError as e:
        logger.error(
            f"Ollama API ResponseError for {document_type.value} "
            f"(model: {config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}): {e.status_code} - {e.error}",
            exc_info=True
        )
        raise HTTPException(
            status_code=502, # Bad Gateway
            detail=f"Ollama API error for {document_type.value}: {e.error} (status {e.status_code})",
        )
    except ollama.RequestError as e: # Покрывает проблемы соединения и др.
        logger.error(
            f"Ollama API RequestError for {document_type.value} "
            f"(model: {config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}): {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=503, # Service Unavailable
            detail=f"Could not connect to Ollama API for {document_type.value}.",
        )
    except HTTPException: # Перехватываем HTTP исключения, чтобы не попасть в общий Exception
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in extract_document_data_from_image for {document_type.value}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error processing document {document_type.value}.",
        ) 