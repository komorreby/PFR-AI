import pytesseract
from PIL import Image, ImageDraw # Добавил ImageDraw для возможной отладки зон
import io
import logging
from typing import Dict, Union, Optional, Tuple # Добавил Tuple
import re
import datetime

logger = logging.getLogger(__name__)

# TODO: Пользователь должен заполнить эти координаты
# Координаты (x, y, width, height) для каждого поля на изображении паспорта
# Пример (НУЖНО ЗАМЕНИТЬ РЕАЛЬНЫМИ ЗНАЧЕНИЯМИ!):
PASSPORT_ROIS = {
    # Пример: x, y, ширина, высота
    # Эти значения вы должны получить из графического редактора для ВАШЕГО эталонного изображения
    "LAST_NAME": (349, 654, 414, 53),
    "FIRST_NAME": (334, 756, 408, 45),
    "MIDDLE_NAME": (354, 802, 390, 45),
    "BIRTH_DATE_TEXT":  (474, 848, 292, 45),   # Текстовая дата рождения (если есть отдельно от MRZ)
    "GENDER":  (310, 845, 100, 45),
    "PASSPORT_SERIES":  (775, 750, 50, 140),    # Обычно вверху
    "PASSPORT_NUMBER":  (775, 905, 50, 140),   # Обычно вверху
    "ISSUE_DATE": (145,250,190,45),
    "ISSUED_BY": (68,109,710,142),
    "DEPARTMENT_CODE": (465,250,210,40),
    "BIRTH_PLACE": (312,890,437,136),
    # Добавьте другие поля по необходимости
}


def ocr_image_region(image: Image.Image, roi: Tuple[int, int, int, int], lang: str = 'rus') -> str:
    """
    Выполняет OCR на указанном регионе (ROI) изображения.

    Args:
        image: Объект PIL.Image.
        roi: Кортеж (x, y, width, height), определяющий регион.
        lang: Язык для Tesseract.

    Returns:
        str: Распознанный текст из региона.
    """
    try:
        x, y, width, height = roi
        img_width, img_height = image.size
        
        # Корректировка ROI, чтобы он не выходил за пределы изображения
        crop_x1 = max(0, x)
        crop_y1 = max(0, y)
        crop_x2 = min(img_width, x + width)
        crop_y2 = min(img_height, y + height)

        if crop_x1 >= crop_x2 or crop_y1 >= crop_y2:
            logger.warning(f"ROI {roi} имеет нулевую или отрицательную ширину/высоту после корректировки или находится вне изображения. Пропуск.")
            return ""

        cropped_image = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        # Для отладки можно сохранять вырезанные зоны:
        # cropped_image.save(f"debug_crop_{x}_{y}_{width}_{height}.png")
        
        # Для улучшения OCR на зонах можно попробовать разные --psm, например, 7 (одна строка текста)
        # config = f'--psm 7 -l {lang}' # Для полей, где точно одна строка
        config = f'-l {lang}' # Общий случай
        text = pytesseract.image_to_string(cropped_image, config=config)
        logger.debug(f"OCR для зоны {roi} ({x},{y},{width},{height}) -> ({crop_x1},{crop_y1},{crop_x2},{crop_y2}): '{text.strip()}'")
        return text.strip()
    except Exception as e:
        logger.error(f"Ошибка OCR для региона {roi}: {str(e)}", exc_info=True)
        return ""


def parse_mrz(text: str) -> Dict[str, str]:
    """
    Пытается извлечь данные из машиночитаемой зоны (MRZ) паспорта.
    """
    mrz_data = {}
    # Разделяем текст на строки, убираем пустые и лишние пробелы
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Ищем строки, похожие на MRZ (длинные, с символами '<')
    mrz_lines = [line for line in lines if '<<<' in line and len(line) > 35 and len(line) < 60]


    if not mrz_lines:
        logger.info("MRZ-подобные строки не найдены в общем тексте.")
        return mrz_data

    logger.info(f"Кандидаты на MRZ строки: {mrz_lines}")

    line1_str = None
    line2_str = None

    # Эвристика для определения первой и второй строки MRZ
    # Первая строка обычно начинается с P< и содержит много букв
    # Вторая строка обычно содержит много цифр (номер паспорта, даты)
    
    if len(mrz_lines) == 1: # Если только одна строка, предполагаем, что это может быть первая или вторая
        if mrz_lines[0].startswith('P<'):
            line1_str = mrz_lines[0]
        elif re.search(r"\d{6}[MFX<]\d{7}", mrz_lines[0]): # Похоже на часть второй строки с датами
            line2_str = mrz_lines[0]
        else: # Если неясно, считаем ее первой для общего разбора
            line1_str = mrz_lines[0]
            
    elif len(mrz_lines) >= 2:
        # Часто MRZ идет парой. Попробуем взять последние две, если их много.
        # Или первые две, если порядок важен. Для паспорта РФ обычно 2 строки.
        
        # Попытка найти по характерным признакам
        for line in mrz_lines:
            if line.startswith('P<') and not line1_str:
                line1_str = line
            elif re.search(r"[A-Z0-9<]{9}[0-9<][A-Z]{3}[0-9]{6}[MFX<]", line) and not line2_str: # Более полный паттерн для второй строки
                 line2_str = line
        
        if not line1_str and not line2_str: # Если по признакам не нашли, берем первые две
            line1_str = mrz_lines[0]
            line2_str = mrz_lines[1]
        elif not line1_str and mrz_lines[0] != line2_str : # Если нашли вторую, а первая не нашлась, то первая из списка - кандидат
            line1_str = mrz_lines[0]
        elif not line2_str and mrz_lines[0] != line1_str and len(mrz_lines) > 1 : # Если нашли первую, а вторая нет
             line2_str = mrz_lines[1]


    if line1_str:
        logger.info(f"MRZ строка 1 (кандидат): {line1_str}")
        # Формат P<RUSLAST_NAME<<FIRST_NAME<MIDDLE_NAME<<<<<<<< (длина 44 для РФ)
        # P<RUSZDRI L7K<<SERGEQ<ANATOL IEVI3<<<<<KDEECC< (пример пользователя, немного отличается)
        # PN RUS LYOVOCHKIN<<SERGEY<VLADIMIROVICH<<<<<<<<<<< (новый пример)
        # Используем более гибкий regex, допускающий P< или PN и более гибкое кол-во '<' в конце
        match = re.match(r"P(?:<|N)([A-Z]{3})([^<]+)<<([^<]+)(?:<([^<]*))?<{4,}", line1_str)
        if not match: # Попробуем вариант, где отчество может отсутствовать или быть частью имени
            match = re.match(r"P(?:<|N)([A-Z]{3})([^<]+)<<([^<]+)<{4,}", line1_str)

        if match:
            # country = match.group(1) # RUS
            raw_last_name = match.group(2).replace('<', ' ').strip()
            raw_first_name = match.group(3).replace('<', ' ').strip()
            raw_middle_name = ""
            if len(match.groups()) > 3 and match.group(4):
                 raw_middle_name = match.group(4).replace('<', ' ').strip()
            
            # Иногда имя и отчество могут быть вместе в третьей группе, разделенные пробелом
            if not raw_middle_name and ' ' in raw_first_name:
                parts = raw_first_name.split(' ', 1)
                raw_first_name = parts[0]
                raw_middle_name = parts[1] if len(parts) > 1 else ''
            
            mrz_data['last_name'] = re.sub(r"[^A-ZА-ЯЁ0-9\s-]", "", raw_last_name, flags=re.IGNORECASE)
            mrz_data['first_name'] = re.sub(r"[^A-ZА-ЯЁ0-9\s-]", "", raw_first_name, flags=re.IGNORECASE)
            if raw_middle_name:
                mrz_data['middle_name'] = re.sub(r"[^A-ZА-ЯЁ0-9\s-]", "", raw_middle_name, flags=re.IGNORECASE)
            logger.info(f"Из MRZ (строка 1): Фамилия='{mrz_data.get('last_name')}', Имя='{mrz_data.get('first_name')}', Отчество='{mrz_data.get('middle_name')}'")

    if line2_str:
        logger.info(f"MRZ строка 2 (кандидат): {line2_str}")
        # Формат: PASSPORT_NUM<CHECKSUM NAT YYMMDDGENDER EXPIRY_DATE<CHECKSUM...
        # Пример: 3919353498RUS7207233M<<<<<<<4151218910003<50 (длина 44 для РФ)
        # Пример2: 521643852UA7207177M<<<<... (паспорт2.jpg)
        #         НомерПаспЧК Страна ГГММДДПол ...
        # Обновленный regex для большей гибкости с номером паспорта, его необязательным чек-суммой и длиной гражданства
        # Regex для извлечения: Номер паспорта, Гражданство, Год, Месяц, День рождения, Чек-сумма ДР, Пол
        mrz_line2_pattern = r"([A-Z0-9<]{1,9})([A-Z<]{2,3})([0-9<]{2})([0-9<]{2})([0-9<]{2})([0-9<])([MFX<])"
        match_details = re.match(mrz_line2_pattern, line2_str)

        if match_details:
            passport_number_mrz = match_details.group(1).replace('<', '')
            # nationality_mrz = match_details.group(2).replace('<','') # Группа 2 теперь гражданство
            year_short = match_details.group(3)  # Группа 3 теперь год
            month = match_details.group(4)       # Группа 4 теперь месяц
            day = match_details.group(5)         # Группа 5 теперь день
            # dob_checksum = match_details.group(6) # Группа 6 теперь чек-сумма ДР
            gender_mrz = match_details.group(7).replace('<','') # Группа 7 теперь пол
            
            # Закомментированные поля ниже относятся к старой структуре regex и данным об истечении срока
            # expiry_year_short = match_details.group(8)
            # expiry_month = match_details.group(9)
            # expiry_day = match_details.group(10)
            # checksum_overall = match_details.group(11)

            if passport_number_mrz and not mrz_data.get('passport_number_mrz'):
                 mrz_data['passport_number_mrz'] = passport_number_mrz # Это будет только номер без серии
                 logger.info(f"Из MRZ (строка 2): Номер паспорта (MRZ)='{passport_number_mrz}'")

            if year_short and month and day:
                try:
                    year_int = int(year_short)
                    current_year_short_digits = datetime.date.today().year % 100
                    century = "19" if year_int > current_year_short_digits else "20" # Простая эвристика
                    full_year = century + year_short
                    mrz_data['birth_date'] = f"{day}.{month}.{full_year}"
                    logger.info(f"Из MRZ (строка 2): Дата рождения='{mrz_data['birth_date']}'")
                except ValueError:
                    logger.warning(f"Не удалось преобразовать дату из MRZ: {year_short}-{month}-{day}")
            
            if gender_mrz:
                mrz_data['gender'] = "МУЖ" if gender_mrz == 'M' else ("ЖЕН" if gender_mrz == 'F' else None)
                if mrz_data['gender']:
                    logger.info(f"Из MRZ (строка 2): Пол='{mrz_data['gender']}'")
    
    if mrz_data:
        logger.info(f"Итоговые данные из MRZ: {mrz_data}")
    return mrz_data


def extract_text_from_image(file_bytes: bytes) -> Tuple[Optional[str], Optional[Image.Image]]:
    """
    Извлекает текст из всего изображения и возвращает текст и объект изображения.
    """
    try:
        image = Image.open(io.BytesIO(file_bytes))
        if image.mode == 'RGBA': # Конвертация для PIL операций и Tesseract
            image = image.convert('RGB')
            
        # Общее OCR всего документа для MRZ и как fallback
        full_text = pytesseract.image_to_string(image, lang='rus+eng') 
        logger.info(f"Tesseract OCR (весь документ): текст извлечен, длина {len(full_text)}.")
        # Логируем только если текст не слишком длинный, чтобы не засорять логи
        if len(full_text) < 1000:
            logger.debug(f"Полный извлеченный текст (весь документ): \n{full_text}")
        else:
            logger.debug(f"Полный извлеченный текст (весь документ): (слишком длинный для лога, {len(full_text)} символов)")
        return full_text.strip(), image
    except pytesseract.TesseractNotFoundError as e_tess:
        logger.error(f"Tesseract не найден или не в PATH: {str(e_tess)}", exc_info=True)
        raise # Перевыбрасываем, чтобы обработать выше и вернуть корректную ошибку пользователю
    except Exception as e:
        logger.error(f"Ошибка при извлечении текста Tesseract или открытии изображения: {str(e)}", exc_info=True)
        return None, None


def extract_passport_info(full_text: Optional[str], image_obj: Optional[Image.Image]) -> Dict[str, str]:
    """
    Извлекает информацию из паспорта, используя OCR по зонам и MRZ.
    """
    result = {}
    
    # 1. Извлечение по зонам (ROI)
    if image_obj:
        logger.info("Начало извлечения по зонам (ROI)...")
        for field_name_upper, roi_coords in PASSPORT_ROIS.items():
            field_name = field_name_upper.lower() # Ключи в результате будут в нижнем регистре
            if roi_coords:
                lang_for_field = 'rus' # По умолчанию русский
                # Можно добавить специфичные языки или опции для полей
                # if field_name_upper in ["PASSPORT_SERIES", "PASSPORT_NUMBER", "DEPARTMENT_CODE"]:
                #    lang_for_field = 'digits_rus' # Пример кастомного языка (если настроен) или просто 'rus'
                
                zone_text = ocr_image_region(image_obj, roi_coords, lang=lang_for_field)
                if zone_text:
                    cleaned_text = re.sub(r"[\n\r]+", " ", zone_text).strip() # Заменяем переносы строк на пробелы
                    cleaned_text = re.sub(r"\s+", " ", cleaned_text) # Убираем множественные пробелы
                    
                    # Дополнительная чистка для специфичных полей
                    if field_name_upper == "PASSPORT_SERIES" or field_name_upper == "PASSPORT_NUMBER" or field_name_upper == "DEPARTMENT_CODE":
                        cleaned_text = re.sub(r'[^\d]', '', cleaned_text) # Оставляем только цифры
                        if field_name_upper == "PASSPORT_SERIES" and len(cleaned_text) > 4: # Серия обычно 4 цифры
                            cleaned_text = cleaned_text[:4]
                        if field_name_upper == "PASSPORT_NUMBER" and len(cleaned_text) > 6: # Номер обычно 6 цифр
                            cleaned_text = cleaned_text[:6]
                    elif field_name_upper == "BIRTH_DATE_TEXT" or field_name_upper == "ISSUE_DATE":
                         # Попытка извлечь дату ДД.ММ.ГГГГ
                        date_match = re.search(r"(\d{2}\.\d{2}\.\d{4})", cleaned_text)
                        if date_match:
                            cleaned_text = date_match.group(1)
                        else: # Если не нашли, оставляем как есть, но логируем
                            logger.info(f"Для поля {field_name_upper} не найден формат ДД.ММ.ГГГГ в '{cleaned_text}'")
                    elif field_name_upper == "GENDER":
                        # Убираем точку и все что после нее, затем лишние пробелы
                        cleaned_text = cleaned_text.split('.')[0].strip()
                        # Дополнительно убедимся, что остается только МУЖ или ЖЕН
                        if "МУЖ" in cleaned_text:
                            cleaned_text = "МУЖ"
                        elif "ЖЕН" in cleaned_text:
                            cleaned_text = "ЖЕН"
                        # Если ни то, ни другое, оставляем как есть для анализа логов, но можем добавить предупреждение
                        # else:
                        # logger.warning(f"Не удалось определить пол из '{zone_text}' -> '{cleaned_text}'")
                    elif field_name_upper == "ISSUED_BY":
                        # Удаляем "Паспорт выдан." (регистронезависимо) и лишние пробелы по краям
                        cleaned_text = re.sub(r"(?i)Паспорт выдан\.", "", cleaned_text).strip()
                        cleaned_text = re.sub(r"\s+", " ", cleaned_text) # Убираем множественные пробелы еще раз
                    elif field_name_upper == "BIRTH_PLACE":
                        # Удаляем "© — " и "дення." и лишние пробелы
                        cleaned_text = cleaned_text.replace("© — ", "").replace("дення.", "").strip()
                        cleaned_text = re.sub(r"\s+", " ", cleaned_text) # Убираем множественные пробелы


                    if cleaned_text:
                        result[field_name] = cleaned_text
                        logger.info(f"Зона '{field_name_upper}': '{cleaned_text}' (ROI: {roi_coords})")
                    else:
                        logger.info(f"Зона '{field_name_upper}': пусто после чистки (ROI: {roi_coords}).")
                else:
                    logger.info(f"Зона '{field_name_upper}': OCR не дал результата (ROI: {roi_coords}).")
            # else: # Не логируем пропуск, если ROI None, т.к. пользователь еще не заполнил
            #    logger.debug(f"Координаты для зоны '{field_name_upper}' не заданы. Пропуск.")
        logger.info(f"Результаты после OCR по зонам: {result}")
    else:
        logger.warning("Объект изображения отсутствует, извлечение по зонам (ROI) невозможно.")

    # 2. Извлечение из MRZ (если есть общий текст)
    if full_text:
        logger.info("Начало извлечения из MRZ...")
        mrz_extracted_data = parse_mrz(full_text)
        for key, value in mrz_extracted_data.items():
            field_key_lower = key.lower()
            if value: # Добавляем только если есть значение
                if field_key_lower not in result or not result.get(field_key_lower):
                    result[field_key_lower] = value
                    logger.info(f"Добавлено из MRZ: {field_key_lower} = '{value}'")
                elif result.get(field_key_lower) != value : # Если есть и из ROI и из MRZ, и они разные
                    # Для некоторых полей MRZ может быть точнее (например, дата рождения, ФИО)
                    # Здесь можно добавить логику приоритетов. Пока что MRZ перезаписывает, если отличается.
                    logger.info(f"Поле '{field_key_lower}': ROI='{result.get(field_key_lower)}', MRZ='{value}'. MRZ перезаписывает.")
                    result[field_key_lower] = value
    else:
        logger.info("Общий текст отсутствует, извлечение из MRZ невозможно.")
            
    # 3. Резервные паттерны (если что-то критичное не извлеклось)
    # Например, если дата рождения все еще отсутствует
    if 'birth_date' not in result and full_text:
        birth_pattern_fallback = r"\b(\d{2}\.\d{2}\.\d{4})\b"
        birth_match = re.search(birth_pattern_fallback, full_text)
        if birth_match:
            result['birth_date'] = birth_match.group(1)
            logger.info(f"Дата рождения найдена резервным текстовым паттерном из полного текста: {result['birth_date']}")

    # Очистка финальных результатов (например, ФИО от лишних символов, если нужно)
    for key in ['last_name', 'first_name', 'middle_name']:
        if key in result:
            result[key] = result[key].replace('.', '').strip() # Убираем точки и лишние пробелы

    logger.info(f"Итоговые извлеченные поля: {result}")
    return result


def process_document(file_bytes: bytes, document_type: str = "passport", filename: str = "unknown.png") -> Dict[str, Union[str, Dict[str, str]]]:
    """
    Обрабатывает документ и извлекает информацию (Tesseract с зонами и MRZ).
    """
    logger.info(f"Начало обработки документа: {filename}, тип: {document_type}")
    
    extracted_text_payload = { # Инициализация на случай ошибок
        "extracted_text": "",
        "extracted_fields": {},
        "error": None 
    }

    try:
        full_extracted_text, image_object = extract_text_from_image(file_bytes)
        
        extracted_text_payload["extracted_text"] = full_extracted_text if full_extracted_text else ""
        
        if document_type == "passport":
            extracted_text_payload["extracted_fields"] = extract_passport_info(full_extracted_text, image_object)
        
        logger.info(f"Документ {filename} обработан. Длина общего текста: {len(extracted_text_payload['extracted_text'])}.")
        return extracted_text_payload

    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract не установлен или не найден в PATH.", exc_info=True)
        extracted_text_payload["error"] = "Tesseract OCR не установлен или не найден в системном PATH. Установите его и перезапустите сервер."
        return extracted_text_payload
    except Exception as e:
        logger.error(f"Критическая ошибка при обработке документа {filename}: {str(e)}", exc_info=True)
        extracted_text_payload["error"] = f"Ошибка обработки документа: {str(e)}"
        return extracted_text_payload
