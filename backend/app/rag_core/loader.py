# backend/app/rag_core/loader.py

from llama_index.core import Document
from typing import List
import os
import pymupdf
import re

# --- Определяем пути относительно расположения скрипта --- 
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR)) # Поднимаемся на 2 уровня (rag_core -> app -> backend)

DATA_DIR = os.path.join(BACKEND_DIR, "data") # Путь к data относительно backend
# -------------------------------------------------------

def clean_text(page_text: str) -> str:
    """Применяет базовую очистку к тексту страницы."""
    lines = page_text.split('\n')
    cleaned_lines = []
    for i, line in enumerate(lines):
        line = line.strip()
        # Простая эвристика для удаления колонтитулов/номеров страниц:
        # Удаляем очень короткие строки (<= 3 символа, часто номера страниц)
        # Удаляем строки в самом верху/низу страницы (первые/последние 2), если они короткие (< 70 символов)
        if len(line) <= 3:
            continue
        if (i < 2 or i > len(lines) - 3) and len(line) < 70:
             # Дополнительно проверяем, не похожа ли строка на начало статьи/пункта
             if not re.match(r"^(Статья|Глава|Раздел|\d{1,3}\.|\d{1,3}\))", line, re.IGNORECASE):
                 continue
        cleaned_lines.append(line)
    # Объединяем очищенные строки, исправляем переносы (простая замена дефиса+переноса на пустоту)
    full_text = '\n'.join(cleaned_lines)
    full_text = re.sub(r"-\n", "", full_text)
    return full_text

def load_and_preprocess_pdf(pdf_path: str) -> str:
    """Загружает PDF, извлекает и очищает текст."""
    full_cleaned_text = ""
    try:
        doc = pymupdf.open(pdf_path)
        print(f"Открыт PDF: {pdf_path}, Страниц: {doc.page_count}")
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text("text")
            cleaned_page_text = clean_text(page_text)
            full_cleaned_text += cleaned_page_text + "\n\n" # Добавляем доп. перенос между страницами
        doc.close()
        print("Извлечение и очистка текста завершены.")
    except Exception as e:
        print(f"Ошибка при обработке PDF {pdf_path}: {e}")
    return full_cleaned_text

def load_documents() -> List[Document]:
    """Ищет PDF в DATA_DIR, преобразует его в один очищенный Document."""
    pdf_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print(f"PDF файлы в директории {DATA_DIR} не найдены.")
        return []
        
    if len(pdf_files) > 1:
        print(f"Внимание: Найдено несколько PDF файлов в {DATA_DIR}. Используется первый: {pdf_files[0]}")
    
    pdf_path = os.path.join(DATA_DIR, pdf_files[0])
    cleaned_content = load_and_preprocess_pdf(pdf_path)
    
    if not cleaned_content:
        print("Не удалось извлечь содержимое из PDF.")
        return []

    # Создаем один документ со всем очищенным текстом
    # Метаданные (имя файла) будут использоваться LlamaIndex
    doc = Document(text=cleaned_content, metadata={"file_name": pdf_files[0]})
    print(f"Создан 1 LlamaIndex Document из файла {pdf_files[0]}. Общая длина текста: {len(cleaned_content)} символов.")
    
    return [doc] # Возвращаем список с одним документом

# В будущем здесь будет логика:
# - Разбиения на чанки (chunking)
# - Возможно, предварительной обработки текста

# Убираем блок if __name__ == '__main__', т.к. логика загрузки изменилась 