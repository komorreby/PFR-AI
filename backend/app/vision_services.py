# app/vision_services.py
import logging
from typing import Optional, Union, Dict, Any, List, Tuple
import base64
import json
import re
from datetime import datetime, date, timedelta

import httpx # <--- ДОБАВЛЕН ИМПОРТ
import ollama # Используем официальный клиент Ollama
from fastapi import HTTPException # <--- ДОБАВЛЕН ИМПОРТ HTTPException
from pydantic import BaseModel, ValidationError # Убедимся, что BaseModel и ValidationError импортированы

from .rag_core import config # Импорт конфигурации
from .models import PassportData, SnilsData, DocumentTypeToExtract, OtherDocumentData, WorkBookRecordEntry, WorkBookData, PENSION_DOCUMENT_TYPES, WorkBookEventRecord, WorkBookEventType # Импорт моделей данных

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
WORK_BOOK_EXTRACTION_PROMPT_TEMPLATE = """Ты — опытный эксперт-кадровик, специализирующийся на расшифровке сложных, рукописных трудовых книжек советского и российского образца. Тебе будет предоставлено изображение разворота такой книжки. Текст может быть неразборчивым, написанным от руки и частично перекрыт печатями или штампами.

Твоя задача — внимательно проанализировать КАЖДУЮ запись о работе (по номеру в колонке 1) и извлечь информацию в строго заданном формате JSON. Работай пошагово:

### ШАГ 1: Пойми структуру таблицы
- **Колонка 1:** Порядковый номер записи.
- **Колонка 2:** Дата события. ВНИМАНИЕ: она разделена на 3 части ('число', 'месяц', 'год'). Твоя задача — собрать их в единую дату.
- **Колонка 3:** Основные сведения. Здесь самое сложное. Одна запись может занимать несколько строк.
- **Колонка 4:** Документ-основание (например, "Приказ №...").

### ШАГ 2: Извлеки данные запись за записью
Для каждой записи (каждого номера из колонки 1) создай объект в JSON. ВАЖНО: запись об увольнении относится к предыдущей записи о приеме/переводе.

**Извлечение полей:**
- `event_date` (ОБЯЗАТЕЛЬНО): Собери дату из колонки 2 в формат "ДД.ММ.ГГГГ".
- `event_type` (ОБЯЗАТЕЛЬНО): Определи тип события из колонки 3. Возможные значения: "ПРИЕМ", "УВОЛЬНЕНИЕ", "ПЕРЕВОД", "СЛУЖБА", "ДРУГОЕ".
- `organization` (ОПЦИОНАЛЬНО): Извлеки ПОЛНОЕ название организации из колонки 3. Оно может быть на нескольких строках.
- `position` (ОПЦИОНАЛЬНО): Извлеки ПОЛНОЕ название должности. Не сокращай его.
- `raw_text` (ОБЯЗАТЕЛЬНО): Включи сюда полный, дословный текст из колонки 3 для этой записи. Это поможет для проверки.
- `document_info` (ОПЦИОНАЛЬНО): Текст из колонки 4.

### ШАГ 3: Представь результат в формате JSON

Твой ответ должен содержать ТОЛЬКО JSON и ничего больше.

**Пример структуры JSON:**
{
  "records": [
    {
      "event_date": "01.09.1998",
      "event_type": "ПРИЕМ",
      "organization": "Лицейское-техническое училище",
      "position": "мастер производственного обучения",
      "raw_text": "Принят мастером производственного обучения в Лицейское-техническое училище",
      "document_info": "Приказ №15 §10 от 31.08.98 г."
    },
    {
      "event_date": "01.09.1999",
      "event_type": "ПЕРЕВОД",
      "organization": "Лицейское-техническое училище",
      "position": "педагог-психолог",
      "raw_text": "Переведен на должность педагога-психолога",
      "document_info": "Пр. №22 §8 от 01.09.99 г."
    },
    {
      "event_date": "01.04.2001",
      "event_type": "УВОЛЬНЕНИЕ",
      "organization": null,
      "position": null,
      "raw_text": "Уволен по собственному желанию",
      "document_info": "Пр №5 §3 от 02.04.2001 г."
    }
  ]
}

### Ключевые правила и ограничения:
1.  **РУКОПИСНЫЙ ТЕКСТ:** Будь готов к неразборчивому почерку. Если не можешь прочитать слово, лучше пропусти его, чем придумай.
2.  **ПЕЧАТИ:** Старайся прочитать текст, даже если он под печатью. Если это невозможно, укажи это в `raw_text`.
3.  **СБОРКА ДАТЫ:** Всегда собирай дату из трех частей колонки 2.
4.  **УВОЛЬНЕНИЕ:** Запись об увольнении — это отдельное событие со своей датой. Не пытайся добавить `date_out` в запись о приеме.
5.  **НЕРЕЛЕВАНТНЫЕ ЗАПИСИ:** Если запись не относится к трудовой деятельности (например, "сведения о смене фамилии" или "вкладыш выдан"), НЕ включай ее в массив `records`.
6.  **ТОЧНОСТЬ ПРЕВЫШЕ ВСЕГО:** Если ты не уверен в каком-либо поле для записи, установи для него значение `null`, но ОБЯЗАТЕЛЬНО заполни `raw_text` и `event_date`.
"""

OTHER_DOCUMENT_EXTRACTION_PROMPT = """
Проанализируй изображение этого документа.
1.  Определи тип документа (например, "Справка о доходах", "Свидетельство о рождении", "Военный билет", "Диплом" и т.д.).
2.  Извлеки все значимые поля и их значения из документа.
3.  Извлеки весь видимый текст (OCR).
4.  Дай краткую оценку изображения (например, "качественное фото", "скан с замятыми углами", "текст частично нечитаем").

Представь ответ СТРОГО в формате JSON. Пример структуры:
{
  "identified_document_type": "Справка о доходах 2-НДФЛ",
  "extracted_fields": {
    "financial_year": "2023",
    "employer_name": "ООО 'Ромашка'",
    "employee_name": "Иванов Иван Иванович",
    "total_income": "1200000.00"
  },
  "raw_text": "Справка о доходах и суммах налога физического лица...\\nООО 'Ромашка'...",
  "multimodal_assessment": "Качественный скан документа, все поля хорошо читаемы."
}
Убедись, что все поля в JSON присутствуют, даже если они пустые (null или пустой объект/строка).
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

def _calculate_work_periods_and_total_years_from_events(
    events: List[WorkBookEventRecord]
) -> Tuple[List[WorkBookRecordEntry], float]:
    """
    Рассчитывает общий стаж и формирует периоды работы на основе списка событий.
    Возвращает кортеж: (список периодов работы, общий стаж в годах).
    """
    if not events:
        return [], 0.0

    total_days = 0
    work_periods: List[WorkBookRecordEntry] = []
    
    # Сортируем записи по дате, если они еще не отсортированы
    sorted_events = sorted(events, key=lambda r: r.event_date if r.event_date else date.min)

    active_period_start_date: Optional[date] = None
    active_period_details: Dict[str, Any] = {}

    for event in sorted_events:
        if not event.event_date or not event.event_type:
            logger.warning(f"Пропуск события из-за отсутствия даты или типа: {event}")
            continue

        # Начало нового периода работы
        if event.event_type in [WorkBookEventType.RECEPTION, WorkBookEventType.SERVICE, WorkBookEventType.TRANSFER]:
            # Если уже был активный период, его нужно закрыть датой, предшествующей текущему событию
            if active_period_start_date:
                end_date_for_previous = event.event_date - timedelta(days=1)
                if end_date_for_previous >= active_period_start_date:
                    period_days = (end_date_for_previous - active_period_start_date).days + 1
                    total_days += period_days
                    active_period_details['date_out'] = end_date_for_previous
                    work_periods.append(WorkBookRecordEntry(**active_period_details))
                    logger.info(f"Период работы закрыт (переводом/новым приемом): {active_period_start_date} - {end_date_for_previous}. Дней: {period_days}")

            # Начинаем новый активный период
            active_period_start_date = event.event_date
            active_period_details = {
                "date_in": active_period_start_date,
                "organization": event.organization,
                "position": event.position,
                "raw_text": event.raw_text,
                "document_info": event.document_info
            }
            logger.info(f"Начало нового периода работы: {active_period_start_date} ({event.raw_text})")

        # Завершение периода работы
        elif event.event_type == WorkBookEventType.DISMISSAL and active_period_start_date:
            end_date = event.event_date
            if end_date >= active_period_start_date:
                period_days = (end_date - active_period_start_date).days + 1
                total_days += period_days
                
                # Завершаем и добавляем период
                active_period_details['date_out'] = end_date
                # Дополняем текст информацией об увольнении
                active_period_details['raw_text'] = f"{active_period_details.get('raw_text', '')}\n{event.raw_text or ''}".strip()
                active_period_details['document_info'] = f"{active_period_details.get('document_info', '')}\n{event.document_info or ''}".strip()

                work_periods.append(WorkBookRecordEntry(**active_period_details))
                logger.info(f"Завершение периода работы: {end_date}. Добавлено дней: {period_days}")
            else:
                logger.warning(f"Обнаружен некорректный период: увольнение {end_date} раньше приема {active_period_start_date}. Пропускается.")
            
            # Сбрасываем активный период
            active_period_start_date = None
            active_period_details = {}

    # Если после цикла остался незавершенный период (работник не уволен)
    if active_period_start_date:
        end_date = date.today()
        period_days = (end_date - active_period_start_date).days + 1
        total_days += period_days
        active_period_details['date_out'] = None # Явно указываем, что период не закрыт
        work_periods.append(WorkBookRecordEntry(**active_period_details))
        logger.info(f"Обнаружен незакрытый период работы с {active_period_start_date}. Стаж посчитан до сегодня. Добавлено дней: {period_days}")

    total_years = round(total_days / 365.25, 2) if total_days > 0 else 0.0
    return work_periods, total_years

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
        prompt = WORK_BOOK_EXTRACTION_PROMPT_TEMPLATE
        data_model = None 
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
            # 1. Извлекаем "сырые" события, как их вернула LLM
            raw_events_data = parsed_multimodal_data.get("records", [])
            if not isinstance(raw_events_data, list):
                 raise HTTPException(status_code=500, detail=f"LLM вернула для трудовой книжки не список, а {type(raw_events_data)}.")
            
            # 2. Валидируем "сырые" события в нашу модель WorkBookEventRecord
            validated_events: List[WorkBookEventRecord] = []
            for event_data in raw_events_data:
                try:
                    # Преобразование event_date в объект date перед валидацией
                    event_data['event_date'] = parse_date_flexible(event_data.get('event_date'))
                    validated_events.append(WorkBookEventRecord(**event_data))
                except (ValidationError, TypeError) as e:
                    logger.warning(f"Ошибка валидации Pydantic для события трудовой книжки: {e}. Данные: {event_data}")
                    # Пропускаем невалидные записи, но логируем их
                    continue
            
            # 3. Обрабатываем события: создаем периоды работы и считаем стаж
            processed_periods, calculated_years = _calculate_work_periods_and_total_years_from_events(validated_events)
            
            # 4. Собираем итоговый объект WorkBookData
            return WorkBookData(
                raw_events=validated_events,
                records=processed_periods,
                calculated_total_years=calculated_years
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
    
    return parsed_multimodal_data # Возврат по умолчанию, если ни один тип не совпал 