import os
import sys
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import traceback

# Настройка путей для импорта модулей из родительской директории
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.graph_validator import PensionGraphValidator
from app.rag_core.config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    NEO4J_DATABASE,
    PENSION_TYPE_MAP
)
from app.rag_core.engine import PensionRAG
from app.graph_builder import KnowledgeGraphBuilder

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GraphEnricher:
    """
    Класс для обогащения и улучшения графа знаний на основе данных 
    из векторной базы и валидационных проверок.
    """
    
    def __init__(self, neo4j_uri: str = NEO4J_URI, neo4j_user: str = NEO4J_USER, 
                neo4j_password: str = NEO4J_PASSWORD, neo4j_db: str = NEO4J_DATABASE):
        """
        Инициализирует компоненты для работы с графом знаний.
        
        Args:
            neo4j_uri: URI для подключения к Neo4j.
            neo4j_user: Имя пользователя Neo4j.
            neo4j_password: Пароль для Neo4j.
            neo4j_db: Имя базы данных Neo4j.
        """
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.neo4j_db = neo4j_db
        
        self.validator = PensionGraphValidator(
            uri=neo4j_uri, 
            user=neo4j_user, 
            password=neo4j_password,
            db_name=neo4j_db
        )
        
        self.graph_builder = KnowledgeGraphBuilder(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            db_name=neo4j_db
        )
        
        # Попробуем инициализировать RAG движок, но это может занять время,
        # так что делаем это опционально
        try:
            self.rag_engine = PensionRAG()
            self.has_rag_engine = True
        except Exception as e:
            logger.warning(f"Не удалось инициализировать RAG движок: {e}")
            logger.warning("Некоторые функции обогащения будут недоступны.")
            self.has_rag_engine = False
    
    def close(self):
        """Закрывает соединения с Neo4j."""
        self.validator.close()
        self.graph_builder.close()
    
    def get_graph_status(self) -> Dict[str, Any]:
        """
        Получает текущий статус графа знаний.
        
        Returns:
            Словарь с метриками и статистикой графа.
        """
        return self.validator.validate_graph_structure()
        
    def apply_basic_fixes(self) -> Dict[str, Any]:
        """
        Применяет базовые исправления к графу знаний.
        
        Returns:
            Словарь с результатами исправлений.
        """
        results = {
            "basic_relations_created": 0,
            "errors": []
        }
        
        try:
            # 1. Создаем базовые связи между статьями и типами пенсий
            relations_created = self.validator.create_basic_relations()
            results["basic_relations_created"] = relations_created
            logger.info(f"Создано {relations_created} базовых связей между статьями и типами пенсий.")
        except Exception as e:
            error_text = f"Ошибка при создании базовых связей: {e}"
            logger.error(error_text)
            results["errors"].append(error_text)
            
        return results
        
    def enhance_graph_from_vector_store(self, max_nodes: int = 100) -> Dict[str, Any]:
        """
        Обогащает граф на основе текстовых узлов из векторного хранилища.
        
        Args:
            max_nodes: Максимальное количество узлов для обработки.
            
        Returns:
            Словарь с результатами обогащения.
        """
        if not self.has_rag_engine:
            return {"error": "Нет доступа к RAG движку. Невозможно выполнить обогащение из векторного хранилища."}
        
        results = {
            "nodes_processed": 0,
            "relations_created": 0,
            "errors": []
        }
        
        try:
            text_nodes = []
            
            # Используем хранилище из RAG движка для доступа к узлам
            docstore = self.rag_engine.index.storage_context.docstore
            
            node_keys = list(docstore.docs.keys())[:max_nodes]
            # text_nodes уже являются объектами LlamaIndex TextNode
            llama_nodes_from_docstore = [docstore.docs[key] for key in node_keys]
            
            logger.info(f"Получено {len(llama_nodes_from_docstore)} TextNode из векторного хранилища.")
            results["nodes_processed"] = len(llama_nodes_from_docstore)
            
            # Для каждого узла применяем улучшенный поиск ключевых слов
            # text_node_ids = [node.id_ for node in text_nodes] # Старый код
            
            nodes_for_validator = []
            for llama_node in llama_nodes_from_docstore: 
                if llama_node.get_content() and llama_node.metadata and llama_node.metadata.get("canonical_article_id"):
                    nodes_for_validator.append(
                        (llama_node.get_content(), llama_node.metadata)
                    )
                else:
                    logger.debug(f"Пропуск узла LlamaIndex {llama_node.id_} для enhance_keyword_search: отсутствует текст или canonical_article_id.")
            
            if nodes_for_validator:
                relations_created = self.validator.enhance_keyword_search(nodes_for_validator) # Передаем подготовленные данные
                results["relations_created"] = relations_created
                logger.info(f"Создано {relations_created} новых связей на основе улучшенного поиска ключевых слов.")
            else:
                logger.info("Не найдено подходящих узлов LlamaIndex для передачи в enhance_keyword_search.")
                results["relations_created"] = 0
            
        except Exception as e:
            error_text = f"Ошибка при обогащении графа из векторного хранилища: {e}"
            logger.error(error_text)
            results["errors"].append(error_text)
            traceback.print_exc()
        
        return results
    
    def fix_duplicate_pension_types(self) -> Dict[str, Any]:
        """
        Исправляет дублирующиеся узлы типов пенсий.
        
        Returns:
            Словарь с результатами исправлений.
        """
        results = {
            "duplicates_found": 0,
            "duplicates_fixed": 0,
            "errors": []
        }
        
        try:
            duplicates_query = """
            MATCH (p1:PensionType), (p2:PensionType)
            WHERE p1.name = p2.name AND id(p1) <> id(p2)
            RETURN id(p1) AS id1, p1.id AS p1_id, p1.name AS p1_name,
                   id(p2) AS id2, p2.id AS p2_id, p2.name AS p2_name
            """
            
            with self.graph_builder._driver.session(database=self.graph_builder._db_name) as session:
                duplicates = session.run(duplicates_query).data()
                results["duplicates_found"] = len(duplicates)
                
                if not duplicates:
                    logger.info("Дублирующихся узлов типов пенсий не обнаружено.")
                    return results
                
                fixed_count = 0
                
                for dup in duplicates:
                    id1, p1_id, p1_name = dup["id1"], dup["p1_id"], dup["p1_name"]
                    id2, p2_id, p2_name = dup["id2"], dup["p2_id"], dup["p2_name"]
                    
                    keep_id, delete_id = None, None
                    p1_is_canonical = p1_id in PENSION_TYPE_MAP # Используем ключи PENSION_TYPE_MAP
                    p2_is_canonical = p2_id in PENSION_TYPE_MAP

                    if p1_is_canonical and not p2_is_canonical:
                        keep_id, delete_id = id1, id2
                        logger.info(f"Сохраняем узел PensionType с ID {p1_id} (Neo4j ID: {id1}, name: {p1_name}), т.к. его ID есть в PENSION_TYPE_MAP. Удаляем дубликат с ID {p2_id} (Neo4j ID: {id2}, name: {p2_name})")
                    elif not p1_is_canonical and p2_is_canonical:
                        keep_id, delete_id = id2, id1
                        logger.info(f"Сохраняем узел PensionType с ID {p2_id} (Neo4j ID: {id2}, name: {p2_name}), т.к. его ID есть в PENSION_TYPE_MAP. Удаляем дубликат с ID {p1_id} (Neo4j ID: {id1}, name: {p1_name})")
                    elif p1_is_canonical and p2_is_canonical:
                        # Оба канонические - это странно, но выберем по меньшему Neo4j ID
                        if id1 < id2: 
                            keep_id, delete_id = id1, id2
                        else:
                            keep_id, delete_id = id2, id1
                        logger.warning(f"Оба узла ({p1_id}, {p2_id}) найдены в PENSION_TYPE_MAP. Сохраняем узел с Neo4j ID {keep_id}, удаляем {delete_id} по правилу наименьшего Neo4j ID.")
                    else: # Ни один не канонический
                        if id1 < id2:
                            keep_id, delete_id = id1, id2
                        else:
                            keep_id, delete_id = id2, id1
                        logger.info(f"Ни один из ID ({p1_id}, {p2_id}) не найден в PENSION_TYPE_MAP. Сохраняем узел с Neo4j ID {keep_id}, удаляем {delete_id} по правилу наименьшего Neo4j ID.")
                    
                    if keep_id is not None and delete_id is not None:
                        # Используем fix_query_simple, как вы указали
                        fix_query = """
                            MATCH (keep:PensionType) WHERE id(keep) = $keep_id
                            MATCH (delete:PensionType) WHERE id(delete) = $delete_id

                            OPTIONAL MATCH (article:Article)-[r_art:RELATES_TO_PENSION_TYPE]->(delete)
                            WHERE article IS NOT NULL
                            MERGE (article)-[new_r_art:RELATES_TO_PENSION_TYPE]->(keep)
                            SET new_r_art = properties(r_art)
                            DELETE r_art

                            OPTIONAL MATCH (condition:EligibilityCondition)-[r_cond:APPLIES_TO_PENSION_TYPE]->(delete)
                            WHERE condition IS NOT NULL
                            MERGE (condition)-[new_r_cond:APPLIES_TO_PENSION_TYPE]->(keep)
                            SET new_r_cond = properties(r_cond)
                            DELETE r_cond
                            
                            DETACH DELETE delete 
                        """
                        try:
                            session.run(fix_query, keep_id=keep_id, delete_id=delete_id)
                            logger.info(f"Узел Neo4j ID {delete_id} удален, связи перенесены на узел Neo4j ID {keep_id}.")
                            fixed_count += 1
                        except Exception as e_fix:
                            error_text = f"Ошибка при исправлении дубликата (keep: {keep_id}, delete: {delete_id}): {e_fix}"
                            logger.error(error_text, exc_info=True)
                            results["errors"].append(error_text)
                    else:
                        logger.error("Не удалось определить keep_id/delete_id для дубликатов, пропуск исправления.") # Этого не должно происходить

                results["duplicates_fixed"] = fixed_count
                logger.info(f"Исправлено {fixed_count} из {len(duplicates)} дублирующихся узлов.")
                
        except Exception as e:
            error_text = f"Ошибка при исправлении дублирующихся типов пенсий: {e}"
            logger.error(error_text)
            results["errors"].append(error_text)
            traceback.print_exc()
            
        return results
    
    def run_full_enrichment(self) -> Dict[str, Any]:
        """
        Запускает полный процесс обогащения и исправления графа знаний.
        
        Returns:
            Словарь с результатами процесса обогащения.
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "stages": {}
        }
        
        try:
            # 1. Проверяем текущее состояние графа
            graph_status = self.get_graph_status()
            results["initial_status"] = {
                "node_counts": graph_status["node_counts"],
                "edge_counts": graph_status["edge_counts"],
                "isolated_articles_count": graph_status["isolated_articles_count"],
                "duplicate_pension_types_count": graph_status["duplicate_pension_types_count"]
            }
            
            # 2. Исправляем дублирующиеся типы пенсий
            if graph_status["duplicate_pension_types_count"] > 0:
                logger.info("Найдены дублирующиеся узлы PensionType, исправляем...")
                duplicate_fix_results = self.fix_duplicate_pension_types()
                results["stages"]["fix_duplicates"] = duplicate_fix_results
            
            # 3. Применяем базовые исправления
            logger.info("Применяем базовые исправления к графу...")
            basic_fixes = self.apply_basic_fixes()
            results["stages"]["basic_fixes"] = basic_fixes
            
            # 4. Обогащаем граф из векторного хранилища
            if self.has_rag_engine:
                logger.info("Обогащаем граф данными из векторного хранилища...")
                vector_enrichment = self.enhance_graph_from_vector_store()
                results["stages"]["vector_enrichment"] = vector_enrichment
            
            # 5. Проверяем финальное состояние графа
            final_graph_status = self.get_graph_status()
            results["final_status"] = {
                "node_counts": final_graph_status["node_counts"],
                "edge_counts": final_graph_status["edge_counts"],
                "isolated_articles_count": final_graph_status["isolated_articles_count"],
                "duplicate_pension_types_count": final_graph_status["duplicate_pension_types_count"]
            }
            
            # Расчет изменений
            results["changes"] = {
                "new_edges": sum(final_graph_status["edge_counts"].values()) - sum(graph_status["edge_counts"].values()),
                "fixed_isolated_articles": graph_status["isolated_articles_count"] - final_graph_status["isolated_articles_count"],
                "fixed_duplicates": graph_status["duplicate_pension_types_count"] - final_graph_status["duplicate_pension_types_count"]
            }
            
        except Exception as e:
            error_text = f"Ошибка при выполнении полного обогащения графа: {e}"
            logger.error(error_text)
            results["error"] = error_text
            traceback.print_exc()
        
        return results
    
    def save_report(self, results: Dict[str, Any], report_path: str = "graph_enrichment_report.json") -> str:
        """
        Сохраняет отчет о процессе обогащения в JSON-файл.
        
        Args:
            results: Словарь с результатами обогащения.
            report_path: Путь для сохранения отчета.
            
        Returns:
            Путь к сохраненному файлу.
        """
        # Добавляем дату и время к имени файла, если не указаны в пути
        if not report_path.startswith("graph_enrichment_report_"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = f"graph_enrichment_report_{timestamp}.json"
            
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Отчет об обогащении графа сохранен в {report_path}")
        return report_path


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Инструмент для обогащения и исправления графа знаний.')
    parser.add_argument('--action', type=str, choices=['status', 'basic', 'vector', 'duplicates', 'full'], 
                        default='status', help='Действие для выполнения')
    parser.add_argument('--report', type=str, default='', 
                        help='Путь для сохранения отчета (по умолчанию - автоматически генерируемый)')
    parser.add_argument('--max-nodes', type=int, default=100, 
                        help='Максимальное количество узлов для обработки при обогащении из векторного хранилища')
    
    args = parser.parse_args()
    
    try:
        enricher = GraphEnricher()
        
        if args.action == 'status':
            # Проверяем текущий статус графа
            status = enricher.get_graph_status()
            print("\n=== ТЕКУЩИЙ СТАТУС ГРАФА ЗНАНИЙ ===")
            print(f"Узлы: {status['node_counts']}")
            print(f"Связи: {status['edge_counts']}")
            print(f"Изолированные статьи: {status['isolated_articles_count']}")
            print(f"Дублирующиеся узлы типов пенсий: {status['duplicate_pension_types_count']}")
            
            if args.report:
                enricher.validator.create_report(args.report)
                print(f"\nПодробный отчет сохранен в {args.report}")
        
        elif args.action == 'basic':
            # Применяем базовые исправления
            print("\n=== ПРИМЕНЕНИЕ БАЗОВЫХ ИСПРАВЛЕНИЙ ===")
            results = enricher.apply_basic_fixes()
            print(f"Создано {results['basic_relations_created']} базовых связей между статьями и типами пенсий.")
            if results['errors']:
                print(f"Ошибки: {results['errors']}")
                
            if args.report:
                enricher.save_report(results, args.report)
                print(f"\nОтчет сохранен в {args.report}")
        
        elif args.action == 'vector':
            # Обогащаем граф из векторного хранилища
            print("\n=== ОБОГАЩЕНИЕ ГРАФА ИЗ ВЕКТОРНОГО ХРАНИЛИЩА ===")
            results = enricher.enhance_graph_from_vector_store(max_nodes=args.max_nodes)
            if 'error' in results:
                print(f"Ошибка: {results['error']}")
            else:
                print(f"Обработано {results['nodes_processed']} узлов.")
                print(f"Создано {results['relations_created']} новых связей.")
                if results['errors']:
                    print(f"Ошибки: {results['errors']}")
                
            if args.report:
                enricher.save_report(results, args.report)
                print(f"\nОтчет сохранен в {args.report}")
        
        elif args.action == 'duplicates':
            # Исправляем дублирующиеся типы пенсий
            print("\n=== ИСПРАВЛЕНИЕ ДУБЛИРУЮЩИХСЯ ТИПОВ ПЕНСИЙ ===")
            results = enricher.fix_duplicate_pension_types()
            print(f"Найдено {results['duplicates_found']} дублирующихся узлов.")
            print(f"Исправлено {results['duplicates_fixed']} дублирующихся узлов.")
            if results['errors']:
                print(f"Ошибки: {results['errors']}")
                
            if args.report:
                enricher.save_report(results, args.report)
                print(f"\nОтчет сохранен в {args.report}")
        
        elif args.action == 'full':
            # Запускаем полное обогащение
            print("\n=== ПОЛНОЕ ОБОГАЩЕНИЕ ГРАФА ЗНАНИЙ ===")
            results = enricher.run_full_enrichment()
            
            if 'error' in results:
                print(f"Критическая ошибка: {results['error']}")
            else:
                print("\nРезультаты обогащения:")
                print(f"Создано новых связей: {results['changes']['new_edges']}")
                print(f"Исправлено изолированных статей: {results['changes']['fixed_isolated_articles']}")
                print(f"Исправлено дублирующихся узлов: {results['changes']['fixed_duplicates']}")
                
                report_path = args.report if args.report else "graph_enrichment_report.json"
                enricher.save_report(results, report_path)
                print(f"\nПолный отчет сохранен в {report_path}")
    
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        traceback.print_exc()
    finally:
        if 'enricher' in locals():
            enricher.close()
            print("\nСоединения с Neo4j закрыты.") 