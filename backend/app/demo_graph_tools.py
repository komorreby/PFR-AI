#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Демонстрационный скрипт для запуска инструментов работы с графом знаний.
Последовательно выполняет диагностику, исправление и обогащение графа.
"""

import os
import sys
import time
import logging
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Настраиваем пути для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.graph_validator import PensionGraphValidator
from app.graph_enricher import GraphEnricher
from app.rag_core.config import (
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    NEO4J_DATABASE
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"graph_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

console = Console()

def print_header(text):
    """Выводит заголовок с красивым форматированием."""
    console.print("\n")
    console.print(Panel(
        f"[bold cyan]{text}[/bold cyan]",
        border_style="cyan",
        expand=False,
        padding=(1, 2)
    ))
    console.print("\n")

def print_status_table(status):
    """Выводит таблицу со статусом графа."""
    table = Table(title="Текущий статус графа знаний", show_header=True, header_style="bold magenta")
    table.add_column("Метрика", style="dim")
    table.add_column("Значение")
    
    # Добавляем строки с данными
    table.add_row("Узлы Law", str(status["node_counts"].get("Law", 0)))
    table.add_row("Узлы Article", str(status["node_counts"].get("Article", 0)))
    table.add_row("Узлы PensionType", str(status["node_counts"].get("PensionType", 0)))
    
    table.add_row("Связи CONTAINS", str(status["edge_counts"].get("CONTAINS", 0)))
    table.add_row("Связи RELATES_TO_PENSION_TYPE", str(status["edge_counts"].get("RELATES_TO_PENSION_TYPE", 0)))
    
    table.add_row("Изолированные статьи", str(status["isolated_articles_count"]))
    table.add_row("Дублирующиеся узлы PensionType", str(status["duplicate_pension_types_count"]))
    
    console.print(table)

def demo_graph_tools():
    """
    Демонстрирует работу инструментов для графа знаний:
    1. Проверяет текущий статус
    2. Исправляет дублирующиеся узлы
    3. Создает базовые связи между статьями и типами пенсий
    4. Обогащает граф данными из векторного хранилища
    5. Показывает итоговый статус
    """
    try:
        print_header("Инициализация GraphEnricher")
        enricher = GraphEnricher(
            neo4j_uri=NEO4J_URI,
            neo4j_user=NEO4J_USER,
            neo4j_password=NEO4J_PASSWORD,
            neo4j_db=NEO4J_DATABASE
        )
        console.print("[green]GraphEnricher успешно инициализирован[/green]")
        
        print_header("Проверка начального состояния графа")
        initial_status = enricher.get_graph_status()
        print_status_table(initial_status)
        
        if initial_status["duplicate_pension_types_count"] > 0:
            print_header(f"Исправление {initial_status['duplicate_pension_types_count']} дублирующихся узлов PensionType")
            dup_results = enricher.fix_duplicate_pension_types()
            console.print(f"[green]Исправлено {dup_results['duplicates_fixed']} из {dup_results['duplicates_found']} дублирующихся узлов[/green]")
        else:
            console.print("[yellow]Дублирующихся узлов не обнаружено, пропускаем этот шаг[/yellow]")
            
        print_header("Применение базовых исправлений к графу")
        basic_results = enricher.apply_basic_fixes()
        console.print(f"[green]Создано {basic_results['basic_relations_created']} базовых связей между статьями и типами пенсий[/green]")
        
        if enricher.has_rag_engine:
            print_header("Обогащение графа данными из векторного хранилища")
            vector_results = enricher.enhance_graph_from_vector_store(max_nodes=100)
            
            if "error" in vector_results:
                console.print(f"[red]Ошибка: {vector_results['error']}[/red]")
            else:
                console.print(f"[green]Обработано {vector_results['nodes_processed']} узлов[/green]")
                console.print(f"[green]Создано {vector_results['relations_created']} новых связей[/green]")
        else:
            console.print("[yellow]RAG движок недоступен, пропускаем обогащение из векторного хранилища[/yellow]")
            
        print_header("Проверка итогового состояния графа")
        final_status = enricher.get_graph_status()
        print_status_table(final_status)
        
        print_header("Изменения в графе знаний")
        changes_table = Table(title="Результаты обогащения", show_header=True, header_style="bold green")
        changes_table.add_column("Метрика", style="dim")
        changes_table.add_column("До", justify="right")
        changes_table.add_column("После", justify="right")
        changes_table.add_column("Изменение", justify="right")
        
        # Добавляем строки с данными
        changes_table.add_row(
            "Узлы всего", 
            str(sum(initial_status["node_counts"].values())),
            str(sum(final_status["node_counts"].values())),
            str(sum(final_status["node_counts"].values()) - sum(initial_status["node_counts"].values()))
        )
        changes_table.add_row(
            "Связи всего", 
            str(sum(initial_status["edge_counts"].values())),
            str(sum(final_status["edge_counts"].values())),
            str(sum(final_status["edge_counts"].values()) - sum(initial_status["edge_counts"].values()))
        )
        changes_table.add_row(
            "Изолированные статьи", 
            str(initial_status["isolated_articles_count"]),
            str(final_status["isolated_articles_count"]),
            str(final_status["isolated_articles_count"] - initial_status["isolated_articles_count"])
        )
        changes_table.add_row(
            "Дублирующиеся узлы", 
            str(initial_status["duplicate_pension_types_count"]),
            str(final_status["duplicate_pension_types_count"]),
            str(final_status["duplicate_pension_types_count"] - initial_status["duplicate_pension_types_count"])
        )
        
        console.print(changes_table)
        
        # Создаем и сохраняем отчет
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"graph_enrichment_report_{timestamp}.json"
        report_results = {
            "timestamp": timestamp,
            "initial_status": initial_status,
            "final_status": final_status,
            "changes": {
                "new_nodes": sum(final_status["node_counts"].values()) - sum(initial_status["node_counts"].values()),
                "new_edges": sum(final_status["edge_counts"].values()) - sum(initial_status["edge_counts"].values()),
                "fixed_isolated_articles": initial_status["isolated_articles_count"] - final_status["isolated_articles_count"],
                "fixed_duplicates": initial_status["duplicate_pension_types_count"] - final_status["duplicate_pension_types_count"]
            }
        }
        enricher.save_report(report_results, report_path)
        console.print(f"[green]Отчет сохранен в: {report_path}[/green]")
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении демо: {e}", exc_info=True)
        console.print(f"[bold red]Критическая ошибка: {e}[/bold red]")
    finally:
        if 'enricher' in locals():
            enricher.close()
            console.print("[green]Соединения с Neo4j закрыты[/green]")

if __name__ == "__main__":
    print_header("ДЕМОНСТРАЦИЯ ИНСТРУМЕНТОВ ДЛЯ РАБОТЫ С ГРАФОМ ЗНАНИЙ")
    console.print("[yellow]Этот скрипт последовательно выполнит диагностику, исправление и обогащение графа знаний.[/yellow]")
    console.print("[yellow]Убедитесь, что Neo4j запущен и доступен по указанным в конфигурации параметрам.[/yellow]")
    
    proceed = input("\nПродолжить? (y/n): ")
    if proceed.lower() == 'y':
        start_time = time.time()
        demo_graph_tools()
        elapsed_time = time.time() - start_time
        console.print(f"[cyan]Демонстрация завершена за {elapsed_time:.2f} секунд[/cyan]")
    else:
        console.print("[red]Демонстрация отменена пользователем[/red]") 