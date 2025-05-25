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
from .models import PassportData, SnilsData, DocumentTypeToExtract, OtherDocumentData, WorkBookRecordEntry, WorkBookData, PENSION_DOCUMENT_TYPES # Импорт моделей данных

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
  "sex": "Мужской",
  "birth_date": "01.01.1980",
  "birth_place": "г. Москва, Российская Федерация",
  "issuing_authority": "ОВД 'Хорошево-Мневники' г. Москвы",
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

# WORK_BOOK_EXTRACTION_PROMPT теперь будет форматируемой строкой
WORK_BOOK_EXTRACTION_PROMPT_TEMPLATE = """Извлеки, пожалуйста, всю информацию о трудовой деятельности из этого изображения разворота трудовой книжки.
Мне нужен список всех записей о работе. Каждая запись должна содержать следующую информацию:
- 'date_in': дата приема на работу (обычно из левой части колонки 2 'Дата'). Формат ДД.ММ.ГГГГ.
- 'date_out': дата увольнения с работы (обычно из левой части колонки 2 'Дата'). Формат ДД.ММ.ГГГГ. Если работник не уволен, это поле должно быть null.
- 'organization': полное наименование организации (из колонки 3 'Сведения о приеме на работу, о переводах...').
- 'position': должность. Извлеки **только название должности, стараясь уложиться в 1-2 ключевых слова** (например, "учитель математики", "бухгалтер").

Представь ответ в формате JSON. В ответе должен быть ключ "records": список объектов с информацией о работе.
Поле "calculated_total_years" НЕ НУЖНО рассчитывать или включать в ответ. Оно должно быть null или отсутствовать.

Пример:
{{
  "records": [
    {{
      "date_in": "01.09.1999",
      "date_out": "31.03.2003",
      "organization": "Долгопрудненская физмат школа №5",
      "position": "учитель математики"
    }},
    {{
      "date_in": "26.12.2003",
      "date_out": null,
      "organization": "МОУ 'Средняя общеобразовательная школа №5'",
      "position": "учитель"
    }}
  ],
  "calculated_total_years": null
}}
Убедись, что все поля ('date_in', 'date_out', 'organization', 'position') присутствуют для каждой записи.
Если не удается четко определить даты, организацию или должность, лучше пропусти эту запись.
"""

# Промпт для LLM (Другие документы)
OTHER_DOCUMENT_EXTRACTION_PROMPT = """Это изображение документа. Пожалуйста, внимательно изучи его и предоставь следующую информацию в формате JSON:
1.  **identified_document_type**: Определи тип документа. **Важно: это значение должно быть ОБЯЗАТЕЛЬНО одним из следующих предопределенных типов**: ["Заявление о назначении пенсии", "Трудовая книжка", "Трудовой договор", "Справка от работодателя", "Справка от госоргана", "Военный билет", "Свидетельство о рождении ребенка", "Документ об уплате взносов", "Справка о зарплате за 60 месяцев до 2002 года", "Документ, подтверждающий особые условия труда", "Документ, подтверждающий педагогический стаж", "Документ, подтверждающий медицинский стаж", "Документ, подтверждающий льготный стаж", "Свидетельство о рождении всех детей", "Документ об инвалидности ребенка", "Справка об инвалидности", "Свидетельство о смерти кормильца", "Документ о родстве с умершим", "Документ об иждивении", "Справка из учебного заведения", "Свидетельство о перемене ФИО", "Документ о месте жительства", "Документ о месте пребывания", "Справка о составе семьи", "Документ, подтверждающий наличие иждивенцев"]. Выбери наиболее подходящий тип из этого списка.
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
    potential_json_matches = re.findall(r"(\{.*?\})", text, re.DOTALL)
    if potential_json_matches:
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

def calculate_total_work_years(records: List[WorkBookRecordEntry]) -> Optional[float]:
    if not records:
        return None

    total_days = 0
    current_date_for_calc = date.today() # Используем текущую дату для открытых периодов

    for record in records:
        if record.date_in:
            start_date = record.date_in
            end_date = record.date_out if record.date_out else current_date_for_calc

            if end_date >= start_date: # Проверка корректности дат
                period_days = (end_date - start_date).days + 1
                total_days += period_days
            else:
                logger.warning(f"Обнаружен некорректный период работы: {start_date} - {end_date}. Пропускается.")
    
    if total_days > 0:
        total_years = total_days / 365.25
        return round(total_years, 1)
    return 0.0

async def get_reasoning_and_standardized_type_from_text_llm(
    extracted_data_from_multimodal: Dict[str, Any], 
    document_image_description: str,
    standard_document_types_list: List[str]
) -> Tuple[str, Optional[str]]:
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
    filename: Optional[str] = "image.png",
    standard_document_names: Optional[List[str]] = None
) -> Union[PassportData, SnilsData, WorkBookData, OtherDocumentData, Dict[str, Any]]:
    """Извлекает структурированные данные из изображения документа с помощью мультимодальной LLM.
    Для типа 'other' дополнительно запрашивает осмысление и стандартизацию типа у текстовой LLM.
    """
    if not image_bytes:
        logger.error("Получены пустые байты изображения.")
        raise HTTPException(status_code=400, detail="Файл изображения пуст.")

    try:
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Ошибка при кодировании изображения в base64: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка обработки изображения.")

    if document_type == DocumentTypeToExtract.PASSPORT:
        prompt = PASSPORT_EXTRACTION_PROMPT
        data_model = PassportData
    elif document_type == DocumentTypeToExtract.SNILS:
        prompt = SNILS_EXTRACTION_PROMPT
        data_model = SnilsData
    elif document_type == DocumentTypeToExtract.WORK_BOOK:
        # Форматируем промпт для трудовой книжки с текущей датой
        current_date_str = datetime.now().strftime("%d.%m.%Y")
        prompt = WORK_BOOK_EXTRACTION_PROMPT_TEMPLATE.replace("{current_date_placeholder}", current_date_str)
        data_model = WorkBookData 
    elif document_type == DocumentTypeToExtract.OTHER:
        prompt = OTHER_DOCUMENT_EXTRACTION_PROMPT
        data_model = OtherDocumentData # Эта модель будет использоваться для начального извлечения
    else:
        logger.error(f"Неподдерживаемый тип документа для извлечения: {document_type}")
        raise HTTPException(status_code=400, detail=f"Неподдерживаемый тип документа: {document_type}")

    logger.info(f"Запрос к мультимодальной LLM ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) для документа: {filename or 'unknown'}, тип: {document_type.value}")
    
    try:
        # Используем AsyncClient для асинхронных вызовов
        client = ollama.AsyncClient(
            host=config.OLLAMA_BASE_URL, 
            timeout=config.LLM_REQUEST_TIMEOUT # Устанавливаем таймаут
        )
        response = await client.generate(
            model=config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME,
            prompt=prompt,
            images=[image_base64],
            format="json", # Просим JSON напрямую
            stream=False
        )
    except httpx.ReadTimeout:
        logger.error(f"Таймаут при запросе к Ollama ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) для {filename}. Timeout: {config.LLM_REQUEST_TIMEOUT}s")
        raise HTTPException(status_code=504, detail=f"Таймаут от сервиса обработки документов ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}).")
    except httpx.ConnectError:
        logger.error(f"Ошибка соединения с Ollama ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) по адресу {config.OLLAMA_BASE_URL} для {filename}.")
        raise HTTPException(status_code=503, detail=f"Сервис обработки документов ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) недоступен.")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запросе к Ollama ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) для {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка при взаимодействии с сервисом обработки документов ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}).")

    raw_response_text = response.get('response')
    if not raw_response_text:
        logger.warning(f"Мультимодальная LLM ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) вернула пустой ответ для {filename}. Тип: {document_type.value}")
        raise HTTPException(status_code=500, detail=f"Сервис обработки документов ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}) вернул пустой ответ.")

    logger.debug(f"Raw JSON response from {config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME} for {filename} ({document_type.value}): {raw_response_text[:500]}...")
    
    # JSON уже должен быть извлечен, так как мы просили format="json"
    # Но на всякий случай, если Ollama вернет JSON внутри текстового поля
    parsed_multimodal_data = _parse_llm_json_safely(raw_response_text, document_type.value)

    if not parsed_multimodal_data:
        logger.error(f"Не удалось извлечь или распарсить JSON от {config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME} для {filename}. Ответ: {raw_response_text[:500]}...")
        raise HTTPException(status_code=500, detail=f"Ошибка обработки ответа от сервиса ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}). Невалидный JSON.")

    try:
        if document_type == DocumentTypeToExtract.PASSPORT:
            # Очистка серии и номера паспорта
            parsed_multimodal_data['passport_series'] = _clean_passport_series(parsed_multimodal_data.get('passport_series'))
            parsed_multimodal_data['passport_number'] = _clean_passport_number(parsed_multimodal_data.get('passport_number'))
            # Преобразование дат
            parsed_multimodal_data['birth_date'] = parse_date_flexible(parsed_multimodal_data.get('birth_date'))
            parsed_multimodal_data['issue_date'] = parse_date_flexible(parsed_multimodal_data.get('issue_date'))
            return PassportData(**parsed_multimodal_data)
        
        elif document_type == DocumentTypeToExtract.SNILS:
            # Очистка номера СНИЛС
            parsed_multimodal_data['snils_number'] = _clean_snils_number(parsed_multimodal_data.get('snils_number'))
            # Преобразование дат
            parsed_multimodal_data['birth_date'] = parse_date_flexible(parsed_multimodal_data.get('birth_date'))
            return SnilsData(**parsed_multimodal_data)
        
        elif document_type == DocumentTypeToExtract.WORK_BOOK:
            extracted_records = []
            raw_records = parsed_multimodal_data.get("records", [])
            if isinstance(raw_records, list):
                for rec_data in raw_records:
                    if isinstance(rec_data, dict):
                        # Преобразование дат для каждой записи
                        rec_data['date_in'] = parse_date_flexible(rec_data.get('date_in'))
                        rec_data['date_out'] = parse_date_flexible(rec_data.get('date_out'))
                        try:
                            extracted_records.append(WorkBookRecordEntry(**rec_data))
                        except Exception as e_rec:
                            logger.warning(f"Ошибка валидации записи трудовой книжки: {rec_data}. Ошибка: {e_rec}")
            
            # Рассчитываем стаж здесь с помощью Python функции
            calculated_years_python = calculate_total_work_years(extracted_records)
            logger.info(f"Work book OCR: Python calculated total years: {calculated_years_python}")

            return WorkBookData(
                records=extracted_records,
                calculated_total_years=calculated_years_python 
            )

        elif document_type == DocumentTypeToExtract.OTHER:
            # Для OTHER, сначала получаем базовые данные от мультимодальной LLM
            initial_other_data = OtherDocumentData(**parsed_multimodal_data) 
            
            # Затем, если есть список стандартных документов, запрашиваем текстовую LLM
            if standard_document_names:
                logger.info(f"Запрос к текстовой LLM ({config.OLLAMA_LLM_MODEL_NAME}) для документа типа OTHER: {filename}")
                document_image_description = f"Документ, загруженный пользователем как '{filename or 'файл без имени'}' с предполагаемым типом 'other'"
                text_reasoning, standardized_type_from_text_llm = await get_reasoning_and_standardized_type_from_text_llm(
                    extracted_data_from_multimodal=parsed_multimodal_data, 
                    document_image_description=document_image_description,
                    standard_document_types_list=standard_document_names # <--- Передаем список
                )
                initial_other_data.text_llm_reasoning = text_reasoning
                initial_other_data.standardized_document_type = standardized_type_from_text_llm
                logger.info(f"Текстовая LLM вернула для {filename}: стандартизированный тип='{standardized_type_from_text_llm}', осмысление (начало)='{text_reasoning[:100]}...'")
            else:
                logger.warning(f"Список стандартных имен документов не предоставлен для {filename}. Пропуск анализа текстовой LLM.")
            return initial_other_data

    except Exception as e: # Ловим ошибки валидации Pydantic и другие
        logger.error(f"Ошибка при валидации данных Pydantic или другая ошибка после ответа LLM для {filename} ({document_type.value}): {e}", exc_info=True)
        logger.debug(f"Данные, вызвавшие ошибку валидации: {parsed_multimodal_data}")
        raise HTTPException(status_code=500, detail=f"Ошибка обработки данных, полученных от сервиса ({config.OLLAMA_MULTIMODAL_LLM_MODEL_NAME}). Некорректные данные.")
    
    return parsed_multimodal_data # Возврат по умолчанию, если ни один тип не совпал (не должно случиться) 