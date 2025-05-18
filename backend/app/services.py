import io
from datetime import datetime
from typing import List, Dict, Any, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from .models import DocumentFormat# Используем Enum и модель ошибки

def mask_personal_data(personal_data: Dict[str, Any]) -> Dict[str, Any]:
    """Маскирует чувствительные персональные данные."""
    masked_data = {
        "full_name": "[ФИО скрыто]",
        "birth_date": "**.**.****",
        "snils": "***-***-*** **",
        "gender": personal_data.get("gender", "[Пол скрыт]"),
        "citizenship": "[Гражданство скрыто]",
        "name_change_info": {
            "old_full_name": "[ФИО скрыто]",
            "date_changed": personal_data.get("name_change_info", {}).get("date_changed", "[Дата скрыта]")
        } if personal_data.get("name_change_info") else {},
        "dependents": "[Данные скрыты]" # Заменяем число на текст
    }
    return masked_data

def _generate_pdf_report(
    masked_data: Dict[str, Any],
    errors: List[Dict[str, Any]],
    current_date: str,
    pension_type: str,
    final_status: str,
    explanation: str,
    case_id: int
) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []

    # Стили
    title_style = ParagraphStyle(
        name='TitleStyle', parent=styles['Title'], fontSize=16,
        spaceAfter=20, alignment=TA_CENTER
    )
    date_style = ParagraphStyle(
        name='DateStyle', parent=styles['Normal'], fontSize=12,
        spaceAfter=10, alignment=TA_RIGHT
    )
    heading2_style = ParagraphStyle(
        name='Heading2Style', parent=styles['Heading2'], fontSize=14,
        spaceBefore=12, spaceAfter=6
    )
    heading3_style = ParagraphStyle( # Добавлен, если понадобится для errors
        name='Heading3Style', parent=styles['Heading3'], fontSize=12,
        spaceBefore=6, spaceAfter=4
    )
    normal_style = ParagraphStyle(
        name='NormalStyle', parent=styles['Normal'], fontSize=12,
        spaceAfter=6, alignment=TA_JUSTIFY
    )
    error_style = ParagraphStyle( # Добавлен, если понадобится для errors
        name='ErrorStyle', parent=normal_style, spaceAfter=10
    )

    # Контент
    elements.append(Paragraph(f"Решение по пенсионному делу #{case_id}", title_style))
    elements.append(Paragraph(f"Дата: {current_date}", date_style))
    elements.append(Paragraph(f"Тип пенсии: {pension_type}", normal_style)) # Добавлено

    elements.append(Paragraph("Персональные данные (маскированные)", heading2_style))
    elements.append(Paragraph(f"ФИО: {masked_data['full_name']}", normal_style))
    elements.append(Paragraph(f"Дата рождения: {masked_data['birth_date']}", normal_style))
    elements.append(Paragraph(f"СНИЛС: {masked_data['snils']}", normal_style))
    elements.append(Paragraph(f"Пол: {masked_data['gender']}", normal_style))
    elements.append(Paragraph(f"Гражданство: {masked_data['citizenship']}", normal_style))
    if masked_data.get("name_change_info") and masked_data["name_change_info"].get('old_full_name'): # Проверка что есть данные
        elements.append(Paragraph(f"Смена имени: {masked_data['name_change_info']['old_full_name']} (дата: {masked_data['name_change_info']['date_changed']})", normal_style))
    elements.append(Paragraph(f"Иждивенцы: {masked_data['dependents']}", normal_style))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Решение по делу", heading2_style))
    elements.append(Paragraph(f"Статус: {'Утверждено' if final_status == 'СООТВЕТСТВУЕТ' else ('Отклонено' if final_status == 'НЕ СООТВЕТСТВУЕТ' else final_status)}", normal_style))
    elements.append(Paragraph(f"Объяснение: {explanation}", normal_style))
    
    # Логика для errors (если они будут передаваться и использоваться)
    if errors:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Выявленные ошибки (если есть):", heading3_style))
        for error in errors:
            error_text = (
                f"<b>Код:</b> {error.get('code', 'N/A')}<br/>"
                f"<b>Описание:</b> {error.get('description', 'N/A')}<br/>"
                f"<b>Основание (закон):</b> {error.get('law', 'N/A')}<br/>"
                f"<b>Рекомендация:</b> {error.get('recommendation', 'N/A')}"
            )
            elements.append(Paragraph(error_text, error_style))
    # else: # Если нет ошибок, можно ничего не добавлять или добавить "Ошибок не выявлено."
    # elements.append(Paragraph("Ошибок не выявлено.", normal_style))


    doc.build(elements)
    buffer.seek(0)
    return buffer

def _generate_docx_report(
    masked_data: Dict[str, Any],
    errors: List[Dict[str, Any]],
    current_date: str,
    pension_type: str,
    final_status: str,
    explanation: str,
    case_id: int
) -> io.BytesIO:
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)

    title = doc.add_heading(f"Решение по пенсионному делу #{case_id}", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    date_p = doc.add_paragraph(f"Дата: {current_date}")
    date_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in date_p.runs: run.font.size = Pt(12)

    doc.add_paragraph(f"Тип пенсии: {pension_type}", style='Normal').paragraph_format.space_after = Pt(6) # Добавлено

    doc.add_heading("Персональные данные (маскированные)", level=2)
    p = doc.add_paragraph()
    p.add_run("ФИО: ").bold = False
    p.add_run(masked_data['full_name'])
    p.paragraph_format.space_after = Pt(6)
    for run in p.runs: run.font.size = Pt(12)
    
    p = doc.add_paragraph(f"Дата рождения: {masked_data['birth_date']}")
    for run in p.runs: run.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p = doc.add_paragraph(f"СНИЛС: {masked_data['snils']}")
    for run in p.runs: run.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p = doc.add_paragraph(f"Пол: {masked_data['gender']}")
    for run in p.runs: run.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    p = doc.add_paragraph(f"Гражданство: {masked_data['citizenship']}")
    for run in p.runs: run.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    if masked_data.get("name_change_info") and masked_data["name_change_info"].get('old_full_name'): # Проверка
        p = doc.add_paragraph(f"Смена имени: {masked_data['name_change_info']['old_full_name']} (дата: {masked_data['name_change_info']['date_changed']})")
        for run in p.runs: run.font.size = Pt(12)
        p.paragraph_format.space_after = Pt(6)
    p = doc.add_paragraph(f"Иждивенцы: {masked_data['dependents']}")
    for run in p.runs: run.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(12)

    doc.add_heading("Решение по делу", level=2)
    p = doc.add_paragraph(f"Статус: {'Утверждено' if final_status == 'СООТВЕТСТВУЕТ' else ('Отклонено' if final_status == 'НЕ СООТВЕТСТВУЕТ' else final_status)}")
    for run in p.runs: run.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    
    p = doc.add_paragraph(f"Объяснение: {explanation}")
    for run in p.runs: run.font.size = Pt(12)
    p.paragraph_format.space_after = Pt(12)

    if errors: # Логика для errors
        doc.add_heading("Выявленные ошибки (если есть):", level=3)
        for error in errors:
            p = doc.add_paragraph()
            p.add_run("Код: ").bold = True
            p.add_run(f"{error.get('code', 'N/A')}\\n")
            p.add_run("Описание: ").bold = True
            p.add_run(f"{error.get('description', 'N/A')}\\n")
            p.add_run("Основание (закон): ").bold = True
            p.add_run(f"{error.get('law', 'N/A')}\\n")
            p.add_run("Рекомендация: ").bold = True
            p.add_run(f"{error.get('recommendation', 'N/A')}")
            for run in p.runs: run.font.size = Pt(12)
            p.paragraph_format.space_after = Pt(10)
    # else:
        # p = doc.add_paragraph("Ошибок не выявлено.")
        # for run in p.runs: run.font.size = Pt(12)


    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def generate_document(
    personal_data: Dict[str, Any],
    errors: List[Dict[str, Any]],
    pension_type: str,
    final_status: str,
    explanation: str,
    case_id: int,
    document_format: DocumentFormat
) -> Tuple[io.BytesIO, str, str]:
    """Генерирует документ указанного формата."""

    masked_data = mask_personal_data(personal_data)
    current_date = datetime.now().strftime("%d.%m.%Y")

    # document_format уже должен быть значением Enum (строкой), если приходит из main.py
    # В main.py: document_format=format.value
    # Если document_format это сам Enum объект, то нужно .value
    doc_format_value = document_format if isinstance(document_format, str) else document_format.value

    if doc_format_value == DocumentFormat.pdf.value: # Сравниваем значения
        buffer = _generate_pdf_report(masked_data, errors, current_date, pension_type, final_status, explanation, case_id)
        filename = f"pension_decision_{case_id}_{current_date}.pdf"
        mimetype = "application/pdf"
    elif doc_format_value == DocumentFormat.docx.value: # Сравниваем значения
        buffer = _generate_docx_report(masked_data, errors, current_date, pension_type, final_status, explanation, case_id)
        filename = f"pension_decision_{case_id}_{current_date}.docx"
        mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise ValueError(f"Unsupported document format: {doc_format_value}")

    return buffer, filename, mimetype 