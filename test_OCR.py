from documentOCR import DocumentOCR  # Убедись, что имя файла совпадает (DocumentOCR.py)

ocr = DocumentOCR()
result = ocr.process_document(r"D:\4 курс\диплом\AI_Controller\Заявление о назначении накопительной пенсии (Образец заполнения).pdf")  # Укажи путь к своему файлу
print(result)