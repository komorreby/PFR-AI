from llama_index.core import Document
from typing import List
import os
from unstructured.partition.pdf import partition_pdf
from PyPDF2 import PdfReader, errors as pypdf_errors
from . import config

try:
    import markdownify
except ImportError:
    markdownify = None # Установим в None, если не установлена

def load_and_preprocess_pdf(pdf_path: str) -> str:
    """Загружает PDF, извлекает текст и структуру с использованием unstructured.partition.pdf.
       Использует 'fast' стратегию и пытается конвертировать таблицы в Markdown.
    """
    full_extracted_text = ""
    if markdownify is None:
         print("Внимание: Библиотека 'markdownify' не установлена. Таблицы будут добавлены как простой текст. Установите 'pip install markdownify'.")

    try:
        # Проверка количества страниц перед полной обработкой
        try:
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
            if num_pages > config.MAX_PDF_PAGES:
                print(f"Предупреждение: PDF файл {pdf_path} содержит {num_pages} страниц, что превышает лимит {config.MAX_PDF_PAGES}. Файл будет пропущен.")
                return ""
        except pypdf_errors.PdfReadError as e:
            print(f"Ошибка чтения PDF (PyPDF2) {pdf_path}: {e}. Файл будет пропущен.")
            return ""
        except Exception as e_count:
            print(f"Не удалось определить количество страниц в {pdf_path} ({e_count}). Попытка обработки файла целиком.")

        print(f"Начинаем обработку PDF: {pdf_path} с помощью unstructured (strategy='fast')")
        elements = partition_pdf(
            filename=pdf_path,
            strategy="fast",
            infer_table_structure=True,
            languages=["rus", "eng"]
            )

        print(f"Unstructured извлек {len(elements)} элементов. Обработка...")
        for i, element in enumerate(elements):
            if hasattr(element, 'category') and element.category == "Table":
                html_table = element.metadata.text_as_html if hasattr(element, 'metadata') and hasattr(element.metadata, 'text_as_html') else None
                if html_table and markdownify:
                    try:
                        markdown_table = markdownify.markdownify(html_table)
                        print(f"  Элемент {i+1}: Таблица найдена и конвертирована в Markdown.")
                        full_extracted_text += "\n\n" + markdown_table + "\n\n"
                    except Exception as md_err:
                        print(f"  Элемент {i+1}: Ошибка конвертации HTML таблицы в Markdown: {md_err}. Добавляем как текст.")
                        full_extracted_text += element.text + "\n\n"
                else:
                    print(f"  Элемент {i+1}: Таблица найдена, но HTML или markdownify недоступны. Добавляем как текст.")
                    full_extracted_text += element.text + "\n\n"
            else:
                if hasattr(element, 'category'):
                     print(f"  Элемент {i+1}: Тип '{element.category}'. Добавляем текст.")
                else:
                     print(f"  Элемент {i+1}: Тип неизвестен. Добавляем текст.")
                full_extracted_text += element.text + "\n\n"

        print(f"Обработка PDF {pdf_path} завершена. Длина текста: {len(full_extracted_text)} символов.")

    except ImportError as ie:
         print(f"Ошибка импорта при использовании unstructured: {ie}")
         print("Убедитесь, что установлены все зависимости для 'fast' стратегии: pip install unstructured[local-inference]")
         print("Также может потребоваться установить Tesseract OCR и pytesseract.")
         return ""
    except Exception as e:
        print(f"Ошибка при обработке PDF {pdf_path} с помощью unstructured: {e}")
        import traceback
        traceback.print_exc()
        return ""
    return full_extracted_text.strip()

def load_documents(directory_path: str) -> List[Document]:
    """Ищет ВСЕ PDF файлы в указанной директории, преобразует каждый в отдельный Document LlamaIndex с помощью unstructured."""
    if not os.path.isdir(directory_path):
        print(f"Ошибка: Указанный путь '{directory_path}' не является директорией или не существует.")
        return []
        
    pdf_files = [f for f in os.listdir(directory_path) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print(f"PDF файлы в директории {directory_path} не найдены.")
        return []
        
    print(f"Найдено {len(pdf_files)} PDF файлов для обработки в '{directory_path}': {pdf_files}")
    
    all_documents = []
    for pdf_file in pdf_files:
        pdf_path = os.path.join(directory_path, pdf_file)
        print(f"--- Начало обработки файла: {pdf_file} ---")
        cleaned_content = load_and_preprocess_pdf(pdf_path)
        
        if not cleaned_content:
            print(f"Предупреждение: Не удалось извлечь содержимое из {pdf_file}. Файл пропущен.")
            continue

        doc = Document(text=cleaned_content, metadata={"file_name": pdf_file})
        all_documents.append(doc)
        print(f"Создан LlamaIndex Document для файла {pdf_file}.")
        print(f"--- Завершение обработки файла: {pdf_file} ---")

    print(f"\nОбработка завершена. Загружено {len(all_documents)} документов LlamaIndex из '{directory_path}'.")
    return all_documents

# В будущем здесь будет логика:
# - Разбиения на чанки (chunking)
# - Возможно, предварительной обработки текста