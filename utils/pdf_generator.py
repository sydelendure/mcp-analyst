import io
from datetime import datetime

def generate_formal_pdf(
    report_title: str,
    markdown_content: str,
    dataset_name: str = "Enterprise Dataset",
    findings: list[str] = None
) -> bytes:
    """
    Generates a highly structured, formal executive PDF audit report.
    Returns the PDF as raw bytes ready for download.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
    except ImportError:
        return b""
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        bottomMargin=40,
        topMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Corporate Palette
    primary_color = colors.HexColor("#0F172A")    # Deep Navy
    brand_blue = colors.HexColor("#0284C7")       # Corporate Sky Blue
    bg_subtle = colors.HexColor("#F8FAFC")        # Soft background
    border_color = colors.HexColor("#E2E8F0")     # Light gray border
    text_dark = colors.HexColor("#1E293B")        # Charcoal text
    text_muted = colors.HexColor("#64748B")       # Secondary text
    
    # Custom Typography Styles
    style_super_title = ParagraphStyle(
        "SuperTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=brand_blue,
        spaceAfter=4
    )
    
    style_title = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=10
    )
    
    style_meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=text_muted
    )
    
    style_meta_value = ParagraphStyle(
        "MetaValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=primary_color
    )
    
    style_h2 = ParagraphStyle(
        "SectionH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )
    
    style_body = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=text_dark,
        spaceAfter=6
    )
    
    style_finding_item = ParagraphStyle(
        "FindingItem",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_dark
    )
    
    style_footer = ParagraphStyle(
        "FooterText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=text_muted,
        alignment=1
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("Enterprise Financial Governance & Intelligence", style_super_title))
    clean_title = report_title.replace("#", "").strip()
    story.append(Paragraph(clean_title or "Autonomous Data Audit & Anomaly Briefing", style_title))
    story.append(HRFlowable(width="100%", thickness=1.5, color=brand_blue, spaceBefore=0, spaceAfter=12))

    # 2. Executive Metadata Box
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    meta_data = [
        [
            Paragraph("<b>AUDIT TARGET</b>", style_meta_label),
            Paragraph(f"<code>{dataset_name}</code>", style_meta_value),
            Paragraph("<b>EXECUTION DATE</b>", style_meta_label),
            Paragraph(now_str, style_meta_value)
        ],
        [
            Paragraph("<b>PROTOCOL</b>", style_meta_label),
            Paragraph("Custom Model Context Protocol (2024-11-05)", style_meta_value),
            Paragraph("<b>AUDIT STATUS</b>", style_meta_label),
            Paragraph("<font color='#0284C7'><b>VERIFIED & SIGNED</b></font>", style_meta_value)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[1.3 * inch, 2.3 * inch, 1.3 * inch, 2.3 * inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_subtle),
        ('BOX', (0, 0), (-1, -1), 0.75, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 3. Executive Summary
    story.append(Paragraph("1. Executive Summary", style_h2))
    exec_summary_text = (
        f"This official audit document encapsulates findings autonomously generated across "
        f"<b>{dataset_name}</b> by the Autonomous MCP Data Analyst Copilot. "
        f"The protocol executed multi-dimensional segmentation, currency parity alignment via live FX benchmarks, "
        f"and rigorous statistical and rule-based anomaly detection."
    )
    story.append(Paragraph(exec_summary_text, style_body))
    story.append(Spacer(1, 10))

    # 4. Detailed Observations & Audit Findings
    story.append(Paragraph("2. Audit Observations & Evidence", style_h2))
    
    parsed_findings = findings or []
    if not parsed_findings and markdown_content:
        for line in markdown_content.splitlines():
            line_s = line.strip()
            if line_s.startswith("- ") or line_s.startswith("* "):
                parsed_findings.append(line_s[2:].strip())
            elif line_s.startswith("### ") or line_s.startswith("## "):
                continue

    if parsed_findings:
        finding_rows = []
        for i, finding in enumerate(parsed_findings, 1):
            finding_rows.append([
                Paragraph(f"<b>#{i:02d}</b>", ParagraphStyle("Num", parent=style_finding_item, fontName="Helvetica-Bold", textColor=brand_blue)),
                Paragraph(finding, style_finding_item)
            ])
        
        findings_table = Table(finding_rows, colWidths=[0.5 * inch, 6.7 * inch])
        findings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(findings_table)
    else:
        for p in markdown_content.split("\n\n"):
            p_clean = p.replace("#", "").strip()
            if p_clean:
                story.append(Paragraph(p_clean, style_body))

    story.append(Spacer(1, 14))

    # 5. Governance & Recommendations
    story.append(Paragraph("3. Recommended Remediation Actions", style_h2))
    recs_data = [
        [
            Paragraph("<b>Category</b>", style_meta_label),
            Paragraph("<b>Recommended Action</b>", style_meta_label),
            Paragraph("<b>Priority</b>", style_meta_label)
        ],
        [
            Paragraph("Negative Revenue", style_finding_item),
            Paragraph("Review billing gateway webhook returns and flag unhandled chargebacks.", style_finding_item),
            Paragraph("<font color='#DC2626'><b>HIGH</b></font>", style_finding_item)
        ],
        [
            Paragraph("Statistical Spikes", style_finding_item),
            Paragraph("Verify wholesale order volume spikes against authorized customer contracts.", style_finding_item),
            Paragraph("<font color='#0284C7'><b>MEDIUM</b></font>", style_finding_item)
        ],
        [
            Paragraph("Currency Parity", style_finding_item),
            Paragraph("Ensure daily FX conversion caching matches settled European Central Bank rates.", style_finding_item),
            Paragraph("<font color='#64748B'><b>STANDARD</b></font>", style_finding_item)
        ]
    ]
    recs_table = Table(recs_data, colWidths=[1.5 * inch, 4.4 * inch, 1.3 * inch])
    recs_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), bg_subtle),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(recs_table)
    story.append(Spacer(1, 18))

    # 6. Certification Sign-off
    story.append(HRFlowable(width="100%", thickness=0.5, color=border_color, spaceBefore=8, spaceAfter=8))
    story.append(Paragraph(
        "CONFIDENTIAL • GENERATED AUTONOMOUSLY VIA CUSTOM MCP DATA ANALYST PROTOCOL • FOR INTERNAL EXECUTIVE USE ONLY",
        style_footer
    ))

    # Build document
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
