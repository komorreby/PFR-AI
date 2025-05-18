# backend/test_tool.py
import json5
import logging
import sys

# Добавляем корневую директорию backend в PYTHONPATH, чтобы можно было импортировать app.*
# Это нужно, если вы запускаете скрипт напрямую из backend/
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# sys.path.append(os.path.dirname(SCRIPT_DIR)) # Закомментировано, так как может быть избыточным при правильной структуре проекта

# Настройка базового логирования для вывода в консоль
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_tool_test():
    logger.info("Начало тестирования PensionKnowledgeRetrieverTool...")
    try:
        # Импорты здесь, чтобы избежать проблем с путем на глобальном уровне до sys.path.append, если он нужен
        from app.rag_core.engine import PensionRAG
        from app.agent_tools.pension_knowledge_retriever_tool import PensionKnowledgeRetrieverTool
    except ImportError as e:
        logger.error(f"Ошибка импорта: {e}. Убедитесь, что скрипт запускается из директории backend или PYTHONPATH настроен корректно.")
        logger.error("Текущий sys.path: " + str(sys.path))
        logger.error("Текущая рабочая директория: " + os.getcwd())
        return

    logger.info("Инициализация PensionRAG (может занять время)...")
    rag_engine_instance = None
    try:
        rag_engine_instance = PensionRAG() # Убедитесь, что ваш PensionRAG может быть так инициализирован
        logger.info("PensionRAG инициализирован.")
    except Exception as e:
        logger.error(f"Не удалось инициализировать PensionRAG: {e}", exc_info=True)
        return

    tool = PensionKnowledgeRetrieverTool(pension_rag_engine=rag_engine_instance)
    logger.info(f"Инструмент {tool.name} инициализирован.")

    test_params = {
        "query": "Условия назначения страховой пенсии по старости для женщин",
        "pension_type": "retirement_standard" # Пример кода типа пенсии
    }
    # Метод call ожидает строку JSON
    params_str = json5.dumps(test_params)
    
    logger.info(f"\nВызов инструмента с параметрами: {params_str}")
    result = None
    try:
        result = tool.call(params=params_str)
    except Exception as e:
        logger.error(f"Ошибка во время вызова tool.call: {e}", exc_info=True)
        # Продолжаем, чтобы попытаться закрыть ресурсы

    logger.info("\nРезультат от инструмента:")
    if result:
        # Печатаем частями, чтобы было легче читать длинный вывод
        for i, line in enumerate(result.split('\n')):
            print(line)
            if i > 50 and len(result.split('\n')) > 100: # Ограничиваем вывод для очень длинных результатов
                print("... (вывод сокращен) ...")
                break
    else:
        logger.warning("Инструмент не вернул результат или произошла ошибка во время вызова.")

    # Закрытие ресурсов PensionRAG, если необходимо (особенно Neo4j)
    if rag_engine_instance and hasattr(rag_engine_instance, 'graph_builder') and rag_engine_instance.graph_builder:
        try:
            logger.info("Закрытие соединения Neo4j...")
            rag_engine_instance.graph_builder.close()
            logger.info("Соединение Neo4j успешно закрыто.")
        except Exception as e:
            logger.error(f"Ошибка при закрытии соединения Neo4j: {e}", exc_info=True)
    
    logger.info("Тестирование PensionKnowledgeRetrieverTool завершено.")

if __name__ == "__main__":
    run_tool_test() 