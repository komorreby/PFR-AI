import logging
import json
from typing import Dict, List, Any, Tuple, Optional
from neo4j import GraphDatabase, Driver

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PensionGraphValidator:
    """
    Класс для проверки, диагностики и исправления графа знаний Neo4j
    для системы анализа пенсионного законодательства.
    """
    
    def __init__(self, uri: str, user: str, password: str, db_name: Optional[str] = None):
        """
        Инициализирует соединение с Neo4j.
        
        Args:
            uri: URI для подключения к Neo4j (например "bolt://localhost:7687").
            user: Имя пользователя Neo4j.
            password: Пароль для Neo4j.
            db_name: Имя базы данных Neo4j (по умолчанию 'neo4j').
        """
        try:
            self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
            self._driver.verify_connectivity()
            self._db_name = db_name if db_name is not None else "neo4j"
            logger.info(f"Успешное подключение к Neo4j по адресу {uri}, база данных: '{self._db_name}'")

            # Переносим keyword_mapping сюда
            self.keyword_mapping = {
                "retirement_standard": [
                    "страховая пенсия по старости", "пенсия по старости", 
                    "страховая пенсия", "общеустановленного пенсионного возраста"
                ],
                "disability_insurance": [
                    "страховая пенсия по инвалидности", "пенсия по инвалидности",
                    "инвалидам I группы", "инвалидам II группы", "инвалидам III группы"
                ],
                "survivor_insurance": [
                    "страховая пенсия по случаю потери кормильца", "потеря кормильца",
                    "потери кормильца", "иждивении", "нетрудоспособным членам семьи"
                ],
                "disability_social": [
                    "социальная пенсия по инвалидности", "инвалидам с детства",
                    "инвалидам I группы", "инвалидам II группы", "социальное обеспечение"
                ],
                "retirement_early": [
                    "досрочное назначение", "досрочно назначаемая", "вредных условиях",
                    "льготный стаж", "особых условиях труда", "северный стаж"
                ],
                "retirement_social": [
                    "социальная пенсия по старости", "социальное обеспечение",
                    "малочисленных народов Севера", "по государственному пенсионному обеспечению"
                ]
            }

        except Exception as e:
            logger.error(f"Не удалось подключиться к Neo4j: {e}", exc_info=True)
            raise
    
    def close(self):
        """
        Закрывает соединение с Neo4j.
        """
        if self._driver:
            self._driver.close()
            logger.info("Соединение с Neo4j закрыто.")
    
    def validate_graph_structure(self) -> Dict[str, Any]:
        """
        Проверяет целостность структуры графа и возвращает отчет с основными метриками.
        
        Returns:
            Dict с результатами проверки.
        """
        result = {}
        
        with self._driver.session(database=self._db_name) as session:
            # 1. Количество узлов каждого типа
            node_counts_query = """
            MATCH (n)
            WITH labels(n)[0] AS node_type, count(n) AS count
            RETURN node_type, count
            ORDER BY node_type
            """
            node_counts = session.run(node_counts_query).data()
            result["node_counts"] = {item["node_type"]: item["count"] for item in node_counts}
            
            # 2. Количество рёбер каждого типа
            edge_counts_query = """
            MATCH ()-[r]->()
            WITH type(r) AS rel_type, count(r) AS count
            RETURN rel_type, count
            ORDER BY rel_type
            """
            edge_counts = session.run(edge_counts_query).data()
            result["edge_counts"] = {item["rel_type"]: item["count"] for item in edge_counts}
            
            # 3. Проверка изолированных статей (статьи без связей с типами пенсий)
            isolated_articles_query = """
            MATCH (a:Article)
            WHERE NOT (a)-[:RELATES_TO_PENSION_TYPE]->(:PensionType)
            RETURN a.article_id AS article_id, a.number_text AS number_text
            ORDER BY a.article_id
            """
            isolated_articles = session.run(isolated_articles_query).data()
            result["isolated_articles"] = isolated_articles
            result["isolated_articles_count"] = len(isolated_articles)
            
            # 4. Проверка потенциально дублирующихся узлов PensionType
            duplicate_pt_query = """
            MATCH (p1:PensionType), (p2:PensionType)
            WHERE p1.name = p2.name AND id(p1) <> id(p2)
            RETURN p1.id AS id1, p1.name AS name1, p2.id AS id2, p2.name AS name2
            """
            duplicate_pt = session.run(duplicate_pt_query).data()
            result["duplicate_pension_types"] = duplicate_pt
            result["duplicate_pension_types_count"] = len(duplicate_pt)
            
            # 5. Статистика по типам пенсий и их связям
            pension_type_stats_query = """
            MATCH (pt:PensionType)
            OPTIONAL MATCH (a:Article)-[:RELATES_TO_PENSION_TYPE]->(pt)
            WITH pt, count(a) AS articles_count
            RETURN pt.id AS pension_type_id, pt.name AS name, articles_count
            ORDER BY articles_count DESC
            """
            pension_type_stats = session.run(pension_type_stats_query).data()
            result["pension_type_stats"] = pension_type_stats
        
        return result
    
    def create_basic_relations(self) -> int:
        """
        Создает базовые связи между статьями и типами пенсий на основе предопределенной конфигурации.
        
        Returns:
            Количество созданных связей.
        """
        # Конфигурация ключевых статей и соответствующих типов пенсий
        key_article_mappings = {
            "ФЗ-400-ФЗ-28_12_2013_Ст_8": ["retirement_standard"],
            "ФЗ-400-ФЗ-28_12_2013_Ст_9": ["disability_insurance"],
            "ФЗ-400-ФЗ-28_12_2013_Ст_10": ["survivor_insurance"],
            "ФЗ-166-ФЗ-15_12_2001_Ст_5": ["disability_social", "retirement_social"],
            "ФЗ-166-ФЗ-15_12_2001_Ст_9": ["disability_social"],
            "ФЗ-166-ФЗ-15_12_2001_Ст_11": ["retirement_social"],
            "ФЗ-400-ФЗ-28_12_2013_Ст_30": ["retirement_early"],
            "ФЗ-400-ФЗ-28_12_2013_Ст_31": ["retirement_early"],
            "ФЗ-400-ФЗ-28_12_2013_Ст_32": ["retirement_early"]
        }
        
        total_created = 0
        
        with self._driver.session(database=self._db_name) as session:
            for article_id, pension_types in key_article_mappings.items():
                for pension_type_id in pension_types:
                    # Проверяем существование статьи и типа пенсии
                    check_query = """
                    MATCH (a:Article {article_id: $article_id}), (p:PensionType {id: $pension_type_id})
                    RETURN count(a) > 0 AND count(p) > 0 AS both_exist
                    """
                    check_result = session.run(check_query, article_id=article_id, pension_type_id=pension_type_id).single()
                    
                    if check_result and check_result["both_exist"]:
                        # Создаем связь RELATES_TO_PENSION_TYPE, если она еще не существует
                        create_query = """
                        MATCH (a:Article {article_id: $article_id}), (p:PensionType {id: $pension_type_id})
                        MERGE (a)-[r:RELATES_TO_PENSION_TYPE]->(p)
                        ON CREATE SET r.source = "manual_mapping", r.created_at = datetime()
                        RETURN count(r) AS relations_created
                        """
                        create_result = session.run(create_query, article_id=article_id, pension_type_id=pension_type_id).single()
                        
                        if create_result and create_result["relations_created"] > 0:
                            logger.info(f"Создана связь между статьей {article_id} и типом пенсии {pension_type_id}")
                            total_created += 1
                    else:
                        logger.warning(f"Не удалось найти статью {article_id} или тип пенсии {pension_type_id}")
        
        return total_created
    
    def enhance_keyword_search(self, text_nodes_data: List[Tuple[str, Dict[str, Any]]]) -> int:
        """
        Улучшенный поиск ключевых слов в тексте узлов для создания дополнительных связей.
        
        Args:
            text_nodes_data: Список кортежей (node_text, node_metadata), 
                             где node_metadata содержит 'canonical_article_id'.
        Returns:
            Количество созданных связей.
        """
        total_created = 0
        
        with self._driver.session(database=self._db_name) as session:
            for node_text, node_metadata in text_nodes_data:
                article_id = node_metadata.get("canonical_article_id")
                
                if not article_id:
                    logger.warning(f"Пропуск текста узла из-за отсутствия 'canonical_article_id' в метаданных: {node_metadata}")
                    continue
                    
                processed_node_text = node_text.lower()
                
                # Проверяем, существует ли узел Article в Neo4j
                check_article_query = "MATCH (a:Article {article_id: $article_id}) RETURN count(a) > 0 AS article_exists"
                article_exists_result = session.run(check_article_query, article_id=article_id).single()
                if not (article_exists_result and article_exists_result["article_exists"]):
                    logger.warning(f"Узел Article с ID '{article_id}' не найден в Neo4j. Связь не будет создана для этого текста.")
                    continue

                for pension_type_id, keywords in self.keyword_mapping.items():
                    for keyword in keywords:
                        if keyword.lower() in processed_node_text:
                            # Проверяем, существует ли узел PensionType в Neo4j
                            check_pt_query = "MATCH (p:PensionType {id: $pension_type_id}) RETURN count(p) > 0 AS pt_exists"
                            pt_exists_result = session.run(check_pt_query, pension_type_id=pension_type_id).single()
                            if not (pt_exists_result and pt_exists_result["pt_exists"]):
                                logger.warning(f"Узел PensionType с ID '{pension_type_id}' не найден в Neo4j. Связь не будет создана.")
                                continue 

                            create_query = """
                            MATCH (a:Article {article_id: $article_id}), (p:PensionType {id: $pension_type_id})
                            MERGE (a)-[r:RELATES_TO_PENSION_TYPE]->(p)
                            ON CREATE SET r.source = "enhanced_keyword_search", 
                                          r.created_at = datetime(),
                                          r.keyword = $keyword
                            RETURN r IS NOT NULL AS created_or_exists, 
                                   (CASE WHEN r.source = "enhanced_keyword_search" AND r.created_at IS NOT NULL AND r.keyword = $keyword THEN true ELSE false END) AS was_created_now_by_this_rule
                            """
                            create_tx_result = session.run(create_query, 
                                                          article_id=article_id, 
                                                          pension_type_id=pension_type_id,
                                                          keyword=keyword).single()
                            
                            if create_tx_result and create_tx_result["was_created_now_by_this_rule"]:
                                logger.info(f"Создана связь RELATES_TO_PENSION_TYPE между статьей {article_id} и типом пенсии {pension_type_id} (ключевое слово: {keyword})")
                                total_created += 1
                            elif create_tx_result and create_tx_result["created_or_exists"]:
                                logger.debug(f"Связь RELATES_TO_PENSION_TYPE между статьей {article_id} и типом пенсии {pension_type_id} (ключевое слово: {keyword}) уже существует или создана другим правилом.")
                            else:
                                logger.warning(f"Не удалось создать или найти связь RELATES_TO_PENSION_TYPE для статьи {article_id} и типа пенсии {pension_type_id} с ключевым словом {keyword}.")
                            break 
        return total_created
    
    def create_report(self, report_path: str = "graph_validation_report.json") -> None:
        """
        Создает полный отчет о состоянии графа и сохраняет его в JSON файл.
        
        Args:
            report_path: Путь для сохранения файла отчета.
        """
        # Получаем данные валидации
        validation_data = self.validate_graph_structure()
        
        # Добавляем общую информацию и рекомендации
        report = {
            "timestamp": str(datetime.now()),
            "validation_data": validation_data,
            "summary": {
                "total_nodes": sum(validation_data["node_counts"].values()),
                "total_edges": sum(validation_data["edge_counts"].values()),
                "isolated_articles_percentage": round(validation_data["isolated_articles_count"] / 
                                                  validation_data["node_counts"].get("Article", 1) * 100, 2)
            },
            "recommendations": []
        }
        
        # Формируем рекомендации
        if validation_data["isolated_articles_count"] > 0:
            report["recommendations"].append({
                "type": "isolated_articles",
                "severity": "high" if report["summary"]["isolated_articles_percentage"] > 30 else "medium",
                "message": f"{validation_data['isolated_articles_count']} статей ({report['summary']['isolated_articles_percentage']}%) не имеют связей с типами пенсий",
                "suggested_action": "Запустите create_basic_relations() и enhance_keyword_search() для создания недостающих связей"
            })
        
        if validation_data["duplicate_pension_types_count"] > 0:
            report["recommendations"].append({
                "type": "duplicate_pension_types",
                "severity": "high",
                "message": f"Обнаружено {validation_data['duplicate_pension_types_count']} дублирующихся узлов типа PensionType",
                "suggested_action": "Выполните очистку базы и переиндексацию с исправленным кодом создания узлов PensionType"
            })
        
        # Сохраняем отчет в файл
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Отчет о состоянии графа сохранен в {report_path}")

if __name__ == "__main__":
    import os
    from datetime import datetime
    
    # Получаем параметры подключения из переменных окружения или используем значения по умолчанию
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "12345678")
    
    try:
        # Создаем экземпляр валидатора
        validator = PensionGraphValidator(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password
        )
        
        # Запускаем проверку
        validation_result = validator.validate_graph_structure()
        print("\n=== РЕЗУЛЬТАТЫ ПРОВЕРКИ ГРАФА ===")
        print(f"Всего узлов по типам: {validation_result['node_counts']}")
        print(f"Всего связей по типам: {validation_result['edge_counts']}")
        print(f"Статьи без связей с типами пенсий: {validation_result['isolated_articles_count']}")
        print(f"Дублирующиеся узлы PensionType: {validation_result['duplicate_pension_types_count']}")
        
        # Спрашиваем, нужно ли создать базовые связи
        create_relations = input("\nСоздать базовые связи между статьями и типами пенсий? (y/n): ")
        if create_relations.lower() == 'y':
            total_created = validator.create_basic_relations()
            print(f"Создано {total_created} новых связей")
            
        # Создаем полный отчет
        report_path = f"graph_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        validator.create_report(report_path)
        print(f"\nПолный отчет сохранен в файл: {report_path}")
        
    except Exception as e:
        print(f"Ошибка при выполнении проверки: {e}")
    finally:
        if 'validator' in locals():
            validator.close() 